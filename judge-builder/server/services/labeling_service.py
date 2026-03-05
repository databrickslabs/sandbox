"""Labeling service for managing examples and labeling sessions."""

import logging
from datetime import datetime
from typing import Any, Optional

import mlflow
import mlflow.genai.label_schemas as schemas
import mlflow.genai.labeling as labeling

from server.models import (
    CreateLabelingSessionRequest,
    CreateLabelingSessionResponse,
    LabelingProgress,
    TraceExample,
    TraceRequest,
)
from server.utils.constants import ALIGNED_SAMPLES_COUNT
from server.utils.naming_utils import create_session_name, get_short_id, sanitize_judge_name
from server.utils.schema_analysis import extract_categorical_options_from_instruction  # For fallback only

from .base_service import BaseService

logger = logging.getLogger(__name__)


class LabelingService(BaseService):
    """Service for MLflow labeling session operations."""

    def create_labeling_session(
        self,
        judge_id: str,
        request: CreateLabelingSessionRequest,
    ) -> CreateLabelingSessionResponse:
        """Create a labeling session for a judge with custom pass/fail schema."""
        from server.services.judge_service import judge_service

        judge_response = judge_service.get_judge(judge_id)
        if not judge_response:
            raise ValueError(f'Judge with ID {judge_id} not found')

        mlflow.set_experiment(experiment_id=judge_response.experiment_id)

        instruction_text = f"""Please review the conversation and evaluate whether it satisfies the judge's instruction as follows:
        {judge_response.instruction}"""

        # Use cached schema information from judge, with fallback to analysis if not available
        if judge_response.schema_info:
            schema_input = schemas.InputCategorical(options=judge_response.schema_info.options)
            logger.info(f'Using cached schema for judge {judge_response.name}: {len(judge_response.schema_info.options)} options')
        else:
            # Fallback: extract options from instruction (backward compatibility)
            try:
                options = extract_categorical_options_from_instruction(judge_response.instruction)
                schema_input = schemas.InputCategorical(options=options)
                logger.debug(f'Generated schema for judge {judge_response.name}: {len(options)} options')
            except Exception as e:
                logger.warning(f'Schema analysis failed for judge {judge_response.name}: {e}, using pass/fail fallback')
                schema_input = schemas.InputCategorical(options=['Pass', 'Fail'])

        schema_name = sanitize_judge_name(judge_response.name)
        schemas.create_label_schema(
            name=schema_name,
            type='feedback',
            title=f'Judge Example Labeling: {judge_response.name}',
            instruction=instruction_text,
            input=schema_input,
            enable_comment=True,
            overwrite=True,
        )

        session_name = create_session_name(judge_response.name, judge_id)
        session = labeling.create_labeling_session(
            name=session_name,
            assigned_users=request.sme_emails,
            label_schemas=[schema_name],
        )

        # Update the judge with the labeling run ID
        judge_service.update_judge_labeling_run_id(judge_id, session.mlflow_run_id)
        logger.info(f'Updated judge {judge_id} with labeling_run_id: {session.mlflow_run_id}')

        return CreateLabelingSessionResponse(
            session_id=session.mlflow_run_id,
            mlflow_run_id=session.mlflow_run_id,
            labeling_url=session.url,
            created_at=datetime.utcnow().isoformat() + 'Z',
        )

    def get_labeling_session(self, judge_id: str) -> Optional[Any]:
        """Get the labeling session for a judge."""
        # Get judge to extract experiment_id
        from server.services.judge_service import judge_service

        judge_response = judge_service.get_judge(judge_id)
        if not judge_response:
            raise ValueError(f'Judge with ID {judge_id} not found')

        experiment_id = judge_response.experiment_id
        mlflow.set_experiment(experiment_id=experiment_id)
        session = self._get_labeling_session(judge_id)
        if not session:
            raise ValueError('No labeling session found for this judge')

        return session

    def _get_labeling_session(self, judge_id: str) -> Optional[labeling.LabelingSession]:
        """Helper method to get the single labeling session for a judge."""
        all_sessions = labeling.get_labeling_sessions()

        # Look for sessions matching this judge (using short ID)
        short_id = get_short_id(judge_id)

        for session in all_sessions:
            session_name = session.name
            # Check if session belongs to this judge (ends with short ID)
            if short_id in session_name:
                return session

        return None


    def delete_labeling_session(self, judge_id: str) -> bool:
        """Delete the labeling session for a judge."""
        # Get the session for this judge
        session = self._get_labeling_session(judge_id)
        if not session:
            logger.warning(f'No labeling session found for judge {judge_id}')
            return False

        labeling.delete_labeling_session(session)
        logger.info(f'Deleted labeling session for judge {judge_id}')
        return True

    def add_examples(self, judge_id: str, request: TraceRequest) -> list:
        """Add examples (traces) to the existing labeling session for a judge."""
        from server.services.judge_service import judge_service

        judge_response = judge_service.get_judge(judge_id)
        if not judge_response:
            raise ValueError(f'Judge with ID {judge_id} not found')

        experiment_id = judge_response.experiment_id
        if not experiment_id:
            raise ValueError('No experiment ID found for judge')

        mlflow.set_experiment(experiment_id=experiment_id)

        # Get the single labeling session for this judge
        session = self._get_labeling_session(judge_id)
        if not session:
            raise ValueError('No labeling session found for this judge')

        # Get existing trace IDs in the session
        existing_trace_ids = set()
        try:
            from databricks.rag_eval.clients.managedevals import managed_evals_client

            client = managed_evals_client.ManagedEvalsClient()
            items = client.list_items_in_labeling_session(session)

            # Extract trace IDs from items (trace_id is nested in item.source.trace_id)
            for item in items:
                if hasattr(item, 'source') and item.source and hasattr(item.source, 'trace_id'):
                    trace_id = item.source.trace_id
                    if trace_id:
                        existing_trace_ids.add(trace_id)

            logger.info(f'Found {len(existing_trace_ids)} existing traces in session')
        except Exception as e:
            logger.warning(f'Failed to get existing traces from session: {e}')
            # Continue without filtering if we can't get existing traces

        # Get real traces from MLflow, filtering out duplicates
        target_traces = []
        skipped_count = 0
        for trace_id in request.trace_ids:
            # Skip if trace already exists in session
            if trace_id in existing_trace_ids:
                skipped_count += 1
                continue

            try:
                # Fetch the actual trace from MLflow
                trace = mlflow.get_trace(trace_id)
                if trace:
                    target_traces.append(trace)
            except Exception as e:
                logger.warning(f'Failed to fetch trace {trace_id}: {e}')
                continue

        if skipped_count > 0:
            logger.info(f'Skipped {skipped_count} duplicate trace(s)')

        if not target_traces:
            if skipped_count > 0:
                return []
            raise ValueError('No valid traces found')

        # Add traces to the session
        from mlflow import environment_variables as mlflow_env_vars

        mlflow_env_vars.MLFLOW_ENABLE_ASYNC_TRACE_LOGGING.set(False)

        session.add_traces(target_traces)
        logger.info(f'Added {len(target_traces)} new trace(s) to session {session.mlflow_run_id}')

        # Convert traces to TraceExample objects using the from_traces class method
        return TraceExample.from_traces(target_traces)

    def get_examples(self, judge_id: str, include_judge_results: bool = False) -> list:
        """Get examples for a judge by searching traces in experiment and labeling session."""
        # Get judge to extract experiment_id
        from server.services.judge_service import judge_service

        judge_response = judge_service.get_judge(judge_id)
        if not judge_response:
            raise ValueError(f'Judge with ID {judge_id} not found')

        mlflow.set_experiment(experiment_id=judge_response.experiment_id)

        # Get the labeling session for this judge
        session = self._get_labeling_session(judge_id)
        if not session:
            return []

        from server.services.experiment_service import experiment_service

        traces = experiment_service.get_experiment_traces(
            judge_response.experiment_id, session.mlflow_run_id
        )

        # If include_judge_results is True, populate judge_assessment for each trace
        if include_judge_results:
            from server.services.cache_service import cache_service
            from server.utils.parsing_utils import get_scorer_feedback_from_trace

            for trace_example in traces:
                try:
                    # Get the full trace from cache to access assessments
                    full_trace = cache_service.get_trace(trace_example.trace_id)
                    if full_trace:
                        # Get judge assessment for current judge version
                        judge_assessment = get_scorer_feedback_from_trace(
                            judge_response.name, judge_response.version, full_trace
                        )
                        trace_example.judge_assessment = judge_assessment
                except Exception as e:
                    logger.warning(f'Failed to get judge assessment for trace {trace_example.trace_id}: {e}')
                    trace_example.judge_assessment = None

        return traces

    def get_labeling_progress(self, judge_id: str) -> LabelingProgress:
        """Get labeling progress for a judge."""
        from server.services.judge_service import judge_service

        try:
            # Get judge and validate
            judge_response = judge_service.get_judge(judge_id)
            if not judge_response:
                logger.warning(f'Judge {judge_id} not found')
                return self._empty_progress()

            mlflow.set_experiment(experiment_id=judge_response.experiment_id)

            # Get the labeling session
            session = self._get_labeling_session(judge_id)
            if not session:
                logger.info(f'No labeling session found for judge {judge_id}')
                return self._empty_progress()

            # Get both total and labeled counts in single call
            total_examples, labeled_examples = self._get_session_counts(
                session, judge_response.experiment_id
            )

            # Get used_for_alignment from judge's labeling run ID
            used_for_alignment = self._get_used_for_alignment_from_judge(judge_response)

            # Get assigned SMEs from the labeling session
            assigned_smes = getattr(session, 'assigned_users', [])

            return LabelingProgress(
                total_examples=total_examples,
                labeled_examples=labeled_examples,
                used_for_alignment=used_for_alignment,
                labeling_session_url=getattr(session, 'url', None),
                assigned_smes=assigned_smes,
            )

        except Exception as e:
            logger.error(f'Failed to get labeling progress for judge {judge_id}: {e}')
            return self._empty_progress()

    def _empty_progress(self) -> LabelingProgress:
        """Return empty progress for error cases."""
        return LabelingProgress(
            total_examples=0,
            labeled_examples=0,
            used_for_alignment=0,
            labeling_session_url=None,
            assigned_smes=[],
        )

    def _get_session_counts(self, session, experiment_id: str) -> tuple[int, int]:
        """Get both total and labeled counts for a labeling session.

        Returns:
            tuple[int, int]: (total_examples, labeled_examples)
        """
        try:
            # Use managed evals client to get all items in the session
            from databricks.rag_eval.clients.managedevals import managed_evals_client

            client = managed_evals_client.ManagedEvalsClient()
            items = client.list_items_in_labeling_session(session)

            total_examples = len(items)
            labeled_examples = sum(
                1
                for item in items
                if hasattr(item, 'state') and item.state and str(item.state) == 'COMPLETED'
            )

            return total_examples, labeled_examples

        except Exception as e:
            logger.warning(f'Failed to get session counts: {e}')
            return 0, 0

    def _get_used_for_alignment_from_judge(self, judge_response) -> int:
        """Get used_for_alignment count from judge's labeling run MLflow tags."""
        try:
            if not judge_response.labeling_run_id:
                return 0

            import mlflow
            run = mlflow.get_run(judge_response.labeling_run_id)
            if run and run.data.tags:
                aligned_count = run.data.tags.get(ALIGNED_SAMPLES_COUNT)
                if aligned_count:
                    return int(aligned_count)
            return 0
        except Exception as e:
            logger.warning(f'Failed to get aligned samples count from run tags: {e}')
            return 0


# Global service instance
labeling_service = LabelingService()
