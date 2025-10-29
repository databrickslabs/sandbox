"""Judge Builder service for orchestrating judge creation and management."""

import json
import logging
from typing import List, Optional

import mlflow

from server.models import (
    CreateLabelingSessionRequest,
    JudgeCreateRequest,
    JudgeResponse,
)
from server.utils.naming_utils import (
    create_dataset_table_name,
    create_scorer_name,
    sanitize_judge_name,
)

from .base_service import BaseService
from .experiment_service import experiment_service
from .judge_service import judge_service
from .labeling_service import labeling_service

logger = logging.getLogger(__name__)


def _is_not_found_error(error_message: str) -> bool:
    """Check if an error message indicates a 'not found' condition."""
    error_msg = str(error_message).lower()
    not_found_indicators = [
        'not found',
        'does not exist',
        'not exist',
        'no registered scorer',
        'no such',
        '404',
        'not available'
    ]
    return any(indicator in error_msg for indicator in not_found_indicators)


class JudgeBuilderService(BaseService):
    """Orchestrates judge creation, labeling sessions, and experiment metadata."""

    def __init__(self):
        super().__init__()
        self.judge_service = judge_service
        self.labeling_service = labeling_service

    def create_judge_builder(self, request: JudgeCreateRequest) -> JudgeResponse:
        """Create a complete judge builder with judge, labeling session, and experiment metadata."""
        try:
            logger.info(f'Creating judge builder: {request.name}')

            # 1. Validate experiment exists
            try:
                experiment = mlflow.get_experiment(request.experiment_id)
                if not experiment:
                    raise ValueError(f'Experiment {request.experiment_id} not found')
                logger.debug(f'Validated experiment: {experiment.name} ({request.experiment_id})')
            except Exception as e:
                logger.error(f'Failed to validate experiment {request.experiment_id}: {e}')
                raise ValueError(f'Invalid experiment ID: {request.experiment_id}')

            # 2. Create the judge using JudgeService
            judge_response = self.judge_service.create_judge(request)
            logger.info(f'Created judge: {judge_response.id}')

            # 3. Register scorer (CRITICAL STEP - must happen before metadata storage)
            judge = self.judge_service._judges.get(judge_response.id)
            if not judge:
                raise ValueError(f'Judge {judge_response.id} not found after creation')

            try:
                judge.register_scorer()
                logger.debug(f'Successfully registered scorer for judge {judge_response.name}')
            except Exception as e:
                logger.error(f'CRITICAL: Failed to register scorer for judge {judge_response.name}: {e}')
                # Clean up the judge from memory since scorer registration failed
                self.judge_service.delete_judge(judge_response.id)
                raise ValueError(f'Judge creation failed: scorer registration failed. {str(e)}')

            # 4. Store judge metadata in experiment tags
            try:
                self._store_judge_metadata_in_experiment(judge_response)
                logger.debug(f'Stored judge metadata in experiment for judge {judge_response.id}')
            except Exception as e:
                logger.warning(f'Failed to store judge metadata: {e}')
                # Continue with judge creation even if metadata storage fails

            # 5. Create initial labeling session if SME emails provided
            if hasattr(request, 'sme_emails') and request.sme_emails:
                try:
                    labeling_request = CreateLabelingSessionRequest(
                        trace_ids=[], sme_emails=request.sme_emails
                    )
                    labeling_response = self.labeling_service.create_labeling_session(
                        judge_response.id, labeling_request
                    )
                    # Update judge with labeling run ID
                    judge_response.labeling_run_id = labeling_response.mlflow_run_id
                    self.judge_service.update_judge_labeling_run_id(judge_response.id, labeling_response.mlflow_run_id)
                    logger.debug(f'Created initial labeling session for judge {judge_response.id} with run ID {labeling_response.mlflow_run_id}')
                except Exception as e:
                    logger.warning(
                        f'Failed to create initial labeling session (judge still created): {e}'
                    )

            logger.debug(f'Successfully created complete judge builder: {judge_response.id}')
            return judge_response

        except Exception as e:
            logger.error(f'Failed to create judge builder: {e}')
            raise

    def get_judge_builder(self, judge_id: str) -> Optional[JudgeResponse]:
        """Get a judge builder by ID."""
        return self.judge_service.get_judge(judge_id)

    def list_judge_builders(self) -> List[JudgeResponse]:
        """List all judge builders from experiment metadata."""
        try:
            logger.info('Listing all judge builders from experiment metadata')

            # Get experiments with judge_builder tag using experiment service with filtered search
            # Use view_type=ACTIVE_ONLY, max_results=100, and filter for judge_builder tag
            # Based on MLflow docs, filter for experiments that have the judge_builder tag
            experiments = experiment_service.list_experiments(
                filter_string="tags.judge_builder = 'true'", max_results=100
            )
            discovered_judge_ids = set()

            for experiment in experiments:
                try:
                    if experiment.tags and 'judges' in experiment.tags:
                        judges_metadata = json.loads(experiment.tags['judges'])

                        for judge_id in judges_metadata.keys():
                            # All judges in this experiment's metadata are valid
                            discovered_judge_ids.add(judge_id)

                except Exception as e:
                    logger.warning(
                        f'Failed to parse judges metadata from experiment {experiment.experiment_id}: {e}'
                    )
                    continue

            # Use get_judge_builder for each discovered judge to ensure consistency
            judge_responses = []
            for judge_id in discovered_judge_ids:
                try:
                    judge_response = self.get_judge_builder(judge_id)
                    if judge_response:
                        judge_responses.append(judge_response)
                    else:
                        logger.warning(f'Judge {judge_id} found in metadata but not retrievable')
                except Exception as e:
                    logger.warning(f'Failed to retrieve judge {judge_id}: {e}')
                    continue

            logger.debug(
                f'Successfully retrieved {len(judge_responses)} judges from experiment metadata'
            )
            return judge_responses

        except Exception as e:
            logger.error(f'Failed to list judge builders: {e}')
            return []

    def delete_judge_builder(self, judge_id: str) -> tuple[bool, list[str]]:
        """Delete a judge builder and all associated resources.
        
        Returns:
            tuple[bool, list[str]]: (success, warnings) where success indicates if deletion completed,
            and warnings contains any non-critical issues encountered during deletion.
        """
        try:
            logger.info(f'Deleting judge builder: {judge_id}')

            # Get judge info before deletion
            judge_response = self.judge_service.get_judge(judge_id)
            if not judge_response:
                logger.warning(f'Judge {judge_id} not found')
                return False, [f'Judge {judge_id} not found']

            deletion_warnings = []

            # 1. Remove judge from experiment metadata
            try:
                self._remove_judge_from_experiment_metadata(judge_id, judge_response.experiment_id)
                logger.debug(f'Removed judge from experiment metadata: {judge_id}')
            except Exception as e:
                warning_msg = f'Failed to remove judge from experiment metadata: {e}'
                logger.warning(warning_msg)
                if not _is_not_found_error(str(e)):
                    deletion_warnings.append(warning_msg)

            # 2. Delete MLflow run for labeling session and the labeling session itself
            try:
                # Get the labeling session first to extract run_id
                session = self.labeling_service._get_labeling_session(judge_id)
                if session:
                    # Delete the underlying MLflow run
                    try:
                        mlflow.delete_run(session.mlflow_run_id)
                        logger.info(
                            f'Deleted MLflow run {session.mlflow_run_id} for labeling session'
                        )
                    except Exception as run_error:
                        logger.warning(
                            f'Failed to delete MLflow run {session.mlflow_run_id}: {run_error}'
                        )

                # Delete the labeling session
                self.labeling_service.delete_labeling_session(judge_id)
                logger.debug(f'Deleted labeling session for judge: {judge_id}')
            except Exception as e:
                warning_msg = f'Failed to delete labeling session: {e}'
                logger.warning(warning_msg)
                if not _is_not_found_error(str(e)):
                    deletion_warnings.append(warning_msg)

            # 3. Delete MLflow scorer registration using helper function
            try:
                from mlflow.genai.scorers import delete_scorer

                scorer_name = create_scorer_name(judge_response.name, judge_response.version)
                delete_scorer(name=scorer_name)
                logger.debug(
                    f'Successfully deleted MLflow scorer {scorer_name} for judge {judge_id}'
                )
            except Exception as e:
                warning_msg = f'Failed to delete MLflow scorer: {e}'
                logger.warning(warning_msg)
                if 'No registered scorer' not in str(e):
                    deletion_warnings.append(warning_msg)

            # 4. Delete label schema
            try:
                import mlflow.genai.label_schemas as schemas

                schema_name = sanitize_judge_name(judge_response.name)
                schemas.delete_label_schema(schema_name)
                logger.debug(f'Successfully deleted label schema {schema_name} for judge {judge_id}')
            except Exception as e:
                warning_msg = f'Failed to delete label schema: {e}'
                logger.warning(warning_msg)
                if not _is_not_found_error(str(e)):
                    deletion_warnings.append(warning_msg)

            # 5. Delete the judge from JudgeService
            try:
                self.judge_service.delete_judge(judge_id)
                logger.debug(f'Deleted judge from service: {judge_id}')
            except Exception as e:
                warning_msg = f'Failed to delete judge from service: {e}'
                logger.warning(warning_msg)
                if not _is_not_found_error(str(e)):
                    deletion_warnings.append(warning_msg)

            # Return success with any warnings
            if deletion_warnings:
                logger.warning(f'Judge {judge_id} deleted with warnings: {"; ".join(deletion_warnings)}')
                return True, deletion_warnings
            else:
                logger.info(f'Successfully deleted complete judge builder: {judge_id}')
                return True, []

        except Exception as e:
            logger.error(f'Failed to delete judge builder {judge_id}: {e}')
            # Even if there's a critical failure, still try to return partial success
            # The judge may have been partially cleaned up
            return False, [f'Critical deletion failure: {str(e)}']

    def _store_judge_metadata_in_experiment(self, judge_response: JudgeResponse):
        """Store judge metadata as experiment tags."""
        try:
            # Set experiment context
            mlflow.set_experiment(experiment_id=judge_response.experiment_id)

            # Generate dataset name for backward compatibility
            create_dataset_table_name(judge_response.name, judge_response.id)

            # Create metadata structure
            judge_metadata = {
                'judge_id': judge_response.id,
                'name': judge_response.name,
                'instruction': judge_response.instruction,
                'version': judge_response.version,
            }

            # Get existing judges metadata from experiment tags
            experiment = mlflow.get_experiment(judge_response.experiment_id)
            existing_judges = {}
            if experiment and experiment.tags and 'judges' in experiment.tags:
                try:
                    existing_judges = json.loads(experiment.tags['judges'])
                except Exception as parse_error:
                    logger.warning(f'Failed to parse existing judges metadata: {parse_error}')

            # Add this judge to the metadata
            existing_judges[judge_response.id] = judge_metadata

            # Store updated judges metadata
            mlflow.set_experiment_tag('judges', json.dumps(existing_judges))

            # Set judge_builder tag to indicate this experiment contains judge builders
            mlflow.set_experiment_tag('judge_builder', 'true')

            logger.info(
                f'Stored metadata for judge {judge_response.id} in experiment {judge_response.experiment_id}'
            )

        except Exception as e:
            logger.error(f'Failed to store judge metadata: {e}')
            raise

    def _remove_judge_from_experiment_metadata(self, judge_id: str, experiment_id: str):
        """Remove judge from experiment metadata tags."""
        try:
            mlflow.set_experiment(experiment_id=experiment_id)

            # Get existing judges metadata
            experiment = mlflow.get_experiment(experiment_id)
            if not experiment or not experiment.tags or 'judges' not in experiment.tags:
                logger.warning(f'No judges metadata found in experiment {experiment_id}')
                return

            try:
                existing_judges = json.loads(experiment.tags['judges'])
            except Exception as parse_error:
                logger.warning(f'Failed to parse existing judges metadata: {parse_error}')
                return

            # Remove this judge from metadata
            if judge_id in existing_judges:
                del existing_judges[judge_id]

                # Update experiment tags
                if existing_judges:
                    mlflow.set_experiment_tag('judges', json.dumps(existing_judges))
                else:
                    # Remove both tags entirely if no judges remain
                    try:
                        mlflow.delete_experiment_tag('judges')
                        mlflow.delete_experiment_tag('judge_builder')
                    except Exception:
                        # delete_experiment_tag might not be available, just log and continue
                        logger.warning(
                            'Could not delete empty judges/judge_builder tags from experiment'
                        )

                logger.info(f'Removed judge {judge_id} from experiment {experiment_id} metadata')
            else:
                logger.warning(f'Judge {judge_id} not found in experiment {experiment_id} metadata')

        except Exception as e:
            logger.error(f'Failed to remove judge from experiment metadata: {e}')
            raise


# Global service instance
judge_builder_service = JudgeBuilderService()
