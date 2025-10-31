"""Custom SIMBA optimizer that uses our AgentEvalLM instead of MLflow's construct_dspy_lm."""

import logging

import dspy
from mlflow.entities.trace import Trace
from mlflow.exceptions import MlflowException
from mlflow.genai.judges import make_judge
from mlflow.genai.judges.base import Judge
from mlflow.genai.judges.optimizers.dspy_utils import (
    agreement_metric,
    convert_mlflow_uri_to_litellm,
    trace_to_dspy_example,
)
from mlflow.genai.judges.optimizers.simba import SIMBAAlignmentOptimizer
from mlflow.genai.judges.utils import _suppress_litellm_nonfatal_errors
from mlflow.protos.databricks_pb2 import INTERNAL_ERROR, INVALID_PARAMETER_VALUE

from server.utils.dspy_utils import AgentEvalLM, DEFAULT_ALIGNMENT_MODEL

logger = logging.getLogger(__name__)


class CustomSIMBAAlignmentOptimizer(SIMBAAlignmentOptimizer):
    """Custom SIMBA optimizer that uses our AgentEvalLM."""

    @_suppress_litellm_nonfatal_errors
    def align(self, judge: Judge, traces: list[Trace]) -> Judge:
        """
        Main alignment method that uses our AgentEvalLM instead of construct_dspy_lm.

        Args:
            judge: The judge to be optimized
            traces: List of traces containing alignment data.

        Returns:
            A new optimized Judge instance
        """
        try:
            if not traces:
                raise MlflowException(
                    'No traces provided for alignment',
                    error_code=INVALID_PARAMETER_VALUE,
                )

            self._logger.debug(f'Setting up DSPy context with model: {self._model}')

            # Construct DSPy LM using our logic instead of MLflow's construct_dspy_lm
            if self._model and ':' in self._model:
                # If model has a colon (e.g., databricks:/endpoint), use litellm
                logger.info(f'Using litellm for model: {self._model}')
                model_litellm = convert_mlflow_uri_to_litellm(self._model)
                optimizer_lm = dspy.LM(model=model_litellm)
            else:
                # Otherwise use our AgentEvalLM with the model name
                resolved_model = self._model if self._model else DEFAULT_ALIGNMENT_MODEL
                logger.info(f'Using AgentEvalLM with model: {resolved_model}')
                optimizer_lm = AgentEvalLM(model=resolved_model)

            with dspy.context(lm=optimizer_lm):
                # Create DSPy program that will simulate the judge
                program = self._get_dspy_program_from_judge(judge)
                self._logger.debug("Created DSPy program with signature using judge's model")

                # Convert traces to DSPy format
                dspy_examples = []
                for trace in traces:
                    example = trace_to_dspy_example(trace, judge)
                    if example is not None:
                        dspy_examples.append(example)

                self._logger.info(
                    f'Preparing optimization with {len(dspy_examples)} examples '
                    f'from {len(traces)} traces'
                )

                if not dspy_examples:
                    raise MlflowException(
                        f'No valid examples could be created from traces. '
                        f'Ensure that the provided traces contain Feedback entries '
                        f'with name {judge.name}',
                        error_code=INVALID_PARAMETER_VALUE,
                    )

                min_traces = self.get_min_traces_required()
                if len(dspy_examples) < min_traces:
                    raise MlflowException(
                        f'At least {min_traces} valid traces are required for optimization. '
                        f'Label more traces with Feedback entries with name {judge.name}',
                        error_code=INVALID_PARAMETER_VALUE,
                    )

                self._logger.debug('Starting DSPy optimization...')

                # Use the algorithm-specific optimization method
                optimized_program = self._dspy_optimize(
                    program, dspy_examples, agreement_metric
                )

                self._logger.debug('DSPy optimization completed')

                # Create optimized judge with DSPy-optimized instructions
                optimized_instructions = optimized_program.signature.instructions
                return make_judge(
                    name=judge.name, instructions=optimized_instructions, model=judge.model
                )

        except Exception as e:
            raise MlflowException(
                f'Alignment optimization failed: {e!s}', error_code=INTERNAL_ERROR
            ) from e
