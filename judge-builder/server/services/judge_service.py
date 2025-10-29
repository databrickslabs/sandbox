"""Judge service for core CRUD operations and versioning."""

import json
import logging
from typing import Dict, List, Optional

import mlflow

from server.judges.instruction_judge import InstructionJudge
from server.models import (
    JudgeCreateRequest,
    JudgeResponse,
    SchemaInfo,
)
from server.utils.schema_analysis import (
    extract_categorical_options_from_instruction,
    is_binary_categorical_options,
)

from .base_service import BaseService

logger = logging.getLogger(__name__)


class JudgeService(BaseService):
    """Core judge management and versioning."""

    def __init__(self):
        super().__init__()
        # In-memory storage for judges (keyed by judge_id)
        self._judges: Dict[str, InstructionJudge] = {}
        # Version history storage (keyed by judge_id, then version)
        self._versions: Dict[str, Dict[int, InstructionJudge]] = {}
        # Cache for judge_builder experiments to avoid repeated searches
        self._judge_experiments_cache = None

    def _judge_to_response(self, judge: InstructionJudge) -> JudgeResponse:
        """Convert a CustomPromptJudge to JudgeResponse."""
        # Perform schema analysis once and cache it
        try:
            options = extract_categorical_options_from_instruction(judge.user_instructions)
            schema_info = SchemaInfo(
                is_binary=is_binary_categorical_options(options),
                options=options
            )
        except Exception as e:
            logger.warning(f'Schema analysis failed for judge {judge.id}: {e}')
            # Default to binary categorical for backward compatibility
            schema_info = SchemaInfo(
                is_binary=True,
                options=['Pass', 'Fail']
            )
        
        return JudgeResponse(
            id=judge.id,
            name=judge.name,
            instruction=judge.user_instructions,  # Use user instructions for display
            experiment_id=judge.experiment_id,
            version=judge.version,
            labeling_run_id=judge.labeling_run_id,
            schema_info=schema_info,
            alignment_model_config=getattr(judge, 'alignment_model_config', None),
        )

    def _get_judge_experiments(self, force_refresh: bool = False):
        """Get judge_builder experiments with caching."""
        if self._judge_experiments_cache is None or force_refresh:
            self._judge_experiments_cache = mlflow.search_experiments(
                view_type=mlflow.entities.ViewType.ACTIVE_ONLY,
                filter_string="tags.judge_builder = 'true'",
                max_results=100,
            )
        return self._judge_experiments_cache

    # Core CRUD operations
    def create_judge(self, request: JudgeCreateRequest) -> JudgeResponse:
        """Create a new judge."""
        logger.info(f'Creating judge: {request.name}')

        # Create the judge instance using InstructionJudge
        judge = InstructionJudge(
            name=request.name,
            user_instructions=request.instruction,
            experiment_id=request.experiment_id,
        )

        # Store alignment model config if provided
        if request.alignment_model_config:
            judge.alignment_model_config = request.alignment_model_config
            logger.info(f'Judge created with alignment model config: {request.alignment_model_config.model_type}')

        # Store in memory
        self._judges[judge.id] = judge

        # Initialize version history
        if judge.id not in self._versions:
            self._versions[judge.id] = {}
        self._versions[judge.id][judge.version] = judge

        # Store alignment model config in metadata if provided
        if request.alignment_model_config:
            self._update_judge_metadata(
                judge.id,
                judge.experiment_id,
                {'alignment_model_config': request.alignment_model_config.model_dump()}
            )

        # Invalidate experiment cache since we created a new judge
        self._judge_experiments_cache = None

        logger.info(f"Created judge {judge.id} with name '{judge.name}'")
        return self._judge_to_response(judge)

    def get_judge(self, judge_id: str) -> Optional[JudgeResponse]:
        """Get a judge by ID, recreating from metadata if necessary."""
        judge = self._judges.get(judge_id)
        if judge:
            logger.debug(f'Retrieved judge {judge_id} from cache')
            return self._judge_to_response(judge)

        # Try to recreate from experiment metadata
        recreated_judge = self._get_or_recreate_judge(judge_id)
        if recreated_judge:
            logger.debug(f'Recreated judge {judge_id} from metadata')
            return self._judge_to_response(recreated_judge)

        logger.warning(f'Judge {judge_id} not found')
        return None

    def list_judges(self) -> List[JudgeResponse]:
        """List all judges."""
        logger.debug(f'Listing {len(self._judges)} judges')
        return [self._judge_to_response(judge) for judge in self._judges.values()]

    def delete_judge(self, judge_id: str) -> bool:
        """Delete a judge."""
        if judge_id in self._judges:
            judge = self._judges[judge_id]
            logger.info(f'Deleting judge {judge_id} ({judge.name})')

            # Remove from judges and version history
            del self._judges[judge_id]
            if judge_id in self._versions:
                del self._versions[judge_id]

            return True

        logger.warning(f'Cannot delete judge {judge_id}: not found')
        return False

    def update_alignment_model_config(
        self, judge_id: str, config: Optional['AlignmentModelConfig']
    ) -> Optional[JudgeResponse]:
        """Update the alignment model configuration for a judge."""
        judge = self._judges.get(judge_id)
        if not judge:
            # Try to recreate from metadata
            judge = self._get_or_recreate_judge(judge_id)
            if not judge:
                logger.warning(f'Judge {judge_id} not found')
                return None

        # Update the alignment model config
        judge.alignment_model_config = config

        # Persist to metadata
        if config:
            self._update_judge_metadata(
                judge_id, judge.experiment_id, {'alignment_model_config': config.model_dump()}
            )
        else:
            # Remove alignment_model_config from metadata if config is None
            self._update_judge_metadata(judge_id, judge.experiment_id, {'alignment_model_config': None})

        logger.info(
            f'Updated alignment model config for judge {judge_id}: '
            f'{config.model_type if config else "default"}'
        )
        return self._judge_to_response(judge)

    # Version management
    def create_new_version(self, judge_id: str, aligned_instruction: str) -> JudgeResponse:
        """Create new judge version with aligned instruction."""
        if judge_id not in self._judges:
            raise ValueError(f'Judge {judge_id} not found')

        current_judge = self._judges[judge_id]
        new_version = current_judge.version + 1

        # Create new judge instance with aligned instructions
        new_judge = InstructionJudge(
            name=current_judge.name,
            user_instructions=current_judge.user_instructions,  # Keep original user instructions
            experiment_id=current_judge.experiment_id,
            system_instructions=aligned_instruction,
        )

        # Override the auto-generated values
        new_judge.id = judge_id  # Keep same ID
        new_judge.version = new_version
        new_judge.labeling_run_id = current_judge.labeling_run_id  # Carry over labeling run ID

        # Update storage
        self._judges[judge_id] = new_judge
        self._versions[judge_id][new_version] = new_judge

        # Update experiment metadata with new version and optimized instructions
        self._update_judge_version_in_metadata(judge_id, new_version, new_judge.experiment_id, aligned_instruction)

        # Also update labeling_run_id in metadata if it exists
        if current_judge.labeling_run_id:
            self._update_judge_metadata(judge_id, new_judge.experiment_id, {'labeling_run_id': current_judge.labeling_run_id})

        # Register scorer for the new version
        try:
            new_judge.register_scorer()
        except Exception as e:
            logger.error(f'Failed to register scorer for judge {judge_id} version {new_version}: {e}')

        logger.info(f'Created version {new_version} for judge {judge_id}')
        return self._judge_to_response(new_judge)


    def _get_or_recreate_judge(self, judge_id: str) -> Optional[InstructionJudge]:
        """Get judge from cache or recreate from experiment metadata."""
        judge = self._judges.get(judge_id)
        if judge:
            return judge

        # Use cached experiments
        experiments = self._get_judge_experiments()

        for experiment in experiments:
            if experiment.tags and 'judges' in experiment.tags:
                judges_metadata = json.loads(experiment.tags['judges'])
                if judge_id not in judges_metadata:
                    continue

                metadata = judges_metadata[judge_id]

                # Recreate judge from metadata
                judge = InstructionJudge(
                    name=metadata['name'],
                    user_instructions=metadata['instruction'],  # Keep original for display
                    experiment_id=experiment.experiment_id,
                )

                # Override auto-generated values with stored ones
                judge.id = judge_id
                judge.version = metadata.get('version', 1)

                # Set labeling_run_id if available in metadata
                if 'labeling_run_id' in metadata and metadata['labeling_run_id']:
                    judge.labeling_run_id = metadata['labeling_run_id']

                # Restore alignment_model_config if available in metadata
                if 'alignment_model_config' in metadata and metadata['alignment_model_config']:
                    from server.models import AlignmentModelConfig
                    judge.alignment_model_config = AlignmentModelConfig(**metadata['alignment_model_config'])

                # For InstructionJudge, we don't need to manually handle optimized instructions
                # The MLflow judge handles this internally
                # TODO: We may need to recreate the judge with optimized instructions if needed

                # Cache the recreated judge
                self._judges[judge_id] = judge

                # Initialize version history
                if judge_id not in self._versions:
                    self._versions[judge_id] = {}
                self._versions[judge_id][judge.version] = judge

                logger.debug(
                    f'Recreated judge {judge_id} from experiment {experiment.experiment_id}'
                )
                return judge

        return None

    def _update_judge_metadata(self, judge_id: str, experiment_id: str, updates: dict):
        """Helper method to update judge metadata in experiment tags."""
        try:
            import json

            # Get current experiment
            experiment = mlflow.get_experiment(experiment_id)
            if not experiment or not experiment.tags:
                logger.warning(f'No experiment found or no tags for experiment {experiment_id}')
                return False

            # Get current judges metadata
            judges_metadata = {}
            if 'judges' in experiment.tags:
                judges_metadata = json.loads(experiment.tags['judges'])

            # Update the judge metadata
            if judge_id in judges_metadata:
                judges_metadata[judge_id].update(updates)

                # Update experiment tags
                mlflow.set_experiment_tag('judges', json.dumps(judges_metadata))
                logger.debug(f'Updated metadata for judge {judge_id}: {updates}')
                return True
            else:
                logger.warning(f'Judge {judge_id} not found in experiment metadata')
                return False

        except Exception as e:
            logger.error(f'Failed to update judge metadata: {e}')
            return False

    def _update_judge_version_in_metadata(self, judge_id: str, new_version: int, experiment_id: str, optimized_instructions: str = None):
        """Update the judge version and optimized instructions in experiment metadata."""
        updates = {'version': new_version}
        if optimized_instructions:
            updates['optimized_instructions'] = optimized_instructions
        self._update_judge_metadata(judge_id, experiment_id, updates)

    def update_judge_labeling_run_id(self, judge_id: str, labeling_run_id: str):
        """Update the labeling run ID for a judge."""
        if judge_id in self._judges:
            judge = self._judges[judge_id]
            # Update the stored judge response if it has labeling_run_id attribute
            for version, version_judge in self._versions.get(judge_id, {}).items():
                if hasattr(version_judge, 'labeling_run_id'):
                    version_judge.labeling_run_id = labeling_run_id

            # Update experiment metadata with labeling_run_id
            self._update_judge_metadata(judge_id, judge.experiment_id, {'labeling_run_id': labeling_run_id})

            logger.debug(f'Updated labeling run ID for judge {judge_id}: {labeling_run_id}')
        else:
            logger.warning(f'Judge {judge_id} not found when trying to update labeling run ID')

    async def load_all_judges_on_startup(self):
        """Load all judges from experiments into cache on application startup."""
        logger.info('Loading all judges into cache on startup...')
        try:
            # Load experiments (this will populate the cache)
            experiments = self._get_judge_experiments()

            judge_count = 0
            for experiment in experiments:
                if experiment.tags and 'judges' in experiment.tags:
                    judges_metadata = json.loads(experiment.tags['judges'])
                    for judge_id in judges_metadata.keys():
                        # Use existing method to load/recreate each judge
                        judge = self._get_or_recreate_judge(judge_id)
                        if judge:
                            judge_count += 1

            logger.info(f'Successfully loaded {judge_count} judges into cache')
        except Exception as e:
            logger.error(f'Failed to load judges on startup: {e}')


# Global service instance
judge_service = JudgeService()
