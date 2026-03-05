"""Instruction-based judge implementation using MLflow make_judge API."""

import logging
from typing import Any, Callable, Dict, List, Optional

import mlflow
from mlflow.genai.judges import make_judge
from mlflow.genai.utils.trace_utils import parse_inputs_to_str, parse_outputs_to_str

from server.judges.base_judge import BaseJudge
from server.utils.naming_utils import create_scorer_name, sanitize_judge_name
from server.utils.dspy_utils import DEFAULT_ALIGNMENT_MODEL

logger = logging.getLogger(__name__)


class InstructionJudge(BaseJudge):
    """Judge implementation using MLflow's make_judge API."""

    def __init__(
        self,
        name: str,
        user_instructions: str,
        system_instructions: str | None = None,
        experiment_id: Optional[str] = None,
    ):
        """Initialize InstructionJudge with MLflow make_judge API."""
        super().__init__(name, user_instructions, experiment_id)

        self.system_instructions = system_instructions if system_instructions else user_instructions

        # Create MLflow judge using make_judge API - this becomes our scorer_func
        logger.info(f"Creating MLflow judge with:")
        logger.info(f"  name: {sanitize_judge_name(self.name)}")
        logger.info(f"  instructions: {self.system_instructions}")
        
        self.scorer_func = make_judge(
            name=sanitize_judge_name(self.name),
            instructions=self.system_instructions,
        )

    def _create_scorer(self) -> Callable:
        """Create scorer function placeholder - actual scorer created in __init__."""
        return lambda inputs, outputs, trace=None: self.evaluate(inputs, outputs, trace)

    def evaluate(self, inputs: Dict[str, Any], outputs: Dict[str, Any], trace=None):
        """Evaluate using the MLflow judge."""
        try:
            if trace is not None:
                # Use trace-based evaluation with canonical MLflow parsing
                feedback_obj = self.scorer_func(trace=trace)
            else:
                # Fallback for backward compatibility - use canonical parsing
                request = parse_inputs_to_str(inputs)
                response = parse_outputs_to_str(outputs)
                feedback_obj = self.scorer_func(
                    inputs={'request': request}, outputs={'response': response}
                )

            # Add version metadata for compatibility
            if hasattr(feedback_obj, 'metadata') and feedback_obj.metadata is not None:
                feedback_obj.metadata['version'] = str(self.version)
            elif hasattr(feedback_obj, 'metadata'):
                feedback_obj.metadata = {'version': str(self.version)}

            return feedback_obj

        except Exception as e:
            logger.error(f'InstructionJudge evaluation failed: {str(e)}')
            # Return error feedback - MLflow classes are always available
            from mlflow.entities import AssessmentError, AssessmentSource, Feedback
            return Feedback(
                name=sanitize_judge_name(self.name),
                source=AssessmentSource(
                    source_type='LLM_JUDGE', source_id='instruction_judge'
                ),
                error=AssessmentError(
                    error_code='EVALUATION_ERROR',
                    error_message=f'Evaluation failed: {str(e)}',
                ),
            )

    def register_scorer(self) -> Any:
        """Register the judge as an MLflow scorer."""
        import re
        from databricks.sdk import WorkspaceClient

        try:
            scorer_name = create_scorer_name(self.name, self.version)

            if self.experiment_id:
                return self.scorer_func.register(
                    name=scorer_name, experiment_id=self.experiment_id
                )
            else:
                return self.scorer_func.register(name=scorer_name)

        except Exception as e:
            error_message = str(e)

            # Check if this is a permission error
            if 'PERMISSION_DENIED' in error_message and 'job' in error_message:
                # Parse job ID and user email from error message
                job_match = re.search(r'on job (\d+)', error_message)
                user_match = re.search(r'User ([\w.@-]+)', error_message)

                if job_match and user_match:
                    job_id = job_match.group(1)
                    user_email = user_match.group(1)

                    # Create a user-friendly error message
                    friendly_message = (
                        f'Failed to register the new scorer version. '
                        f'The user {user_email} does not have manage permissions on job {job_id}. '
                        f'Please grant permissions to the user and try again.'
                    )
                    logger.error(friendly_message)
                    raise RuntimeError(friendly_message) from e

            # For other errors, log and re-raise with original message
            logger.warning(f'Failed to register InstructionJudge scorer: {e}')
            raise

    def optimize(self, traces: List[mlflow.entities.Trace], alignment_model: Optional[str] = None) -> bool:
        """Optimize the judge using labeled traces with optional custom alignment model.

        Args:
            traces: List of MLflow traces with human feedback for alignment
            alignment_model: Optional model identifier for alignment (e.g., 'databricks:/my-endpoint')
                           If None, uses default alignment model.

        Returns:
            True if alignment succeeded, False otherwise
        """
        logger.info(
            f'Starting optimization for judge {self.name} with {len(traces)} traces'
        )

        try:
            from server.judges.custom_simba_optimizer import CustomSIMBAAlignmentOptimizer

            model = alignment_model if alignment_model else DEFAULT_ALIGNMENT_MODEL
            optimizer = CustomSIMBAAlignmentOptimizer(model=model)
            self.scorer_func = self.scorer_func.align(traces=traces, optimizer=optimizer)

            logger.debug(f'Successfully aligned judge {self.name}')
            return True

        except Exception as e:
            logger.error(f'Alignment failed for judge {self.name}: {e}')
            return False
