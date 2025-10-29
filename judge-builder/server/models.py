"""Data models for Judge Builder API."""

from typing import List, Optional

from mlflow.entities import Feedback
from pydantic import BaseModel, Field


class SchemaInfo(BaseModel):
    """Information about the labeling schema options."""

    is_binary: bool = Field(..., description='Whether the schema represents binary outcomes')
    options: List[str] = Field(..., description='Possible output values for this schema')


class ServingEndpointConfig(BaseModel):
    """Configuration for a Databricks serving endpoint."""

    endpoint_name: str = Field(..., description='Name of the serving endpoint')


class AlignmentModelConfig(BaseModel):
    """Configuration for alignment model selection."""

    model_type: str = Field(default='default', description='Type: "default" or "serving_endpoint"')
    serving_endpoint: Optional[ServingEndpointConfig] = Field(
        None, description='Serving endpoint config when model_type="serving_endpoint"'
    )


class JudgeCreateRequest(BaseModel):
    """Request model for creating a new judge."""

    name: str = Field(..., description='Human-readable name for the judge')
    instruction: str = Field(..., description='Natural language evaluation criteria')
    experiment_id: str = Field(..., description='MLflow experiment ID to attach judge to')
    sme_emails: Optional[List[str]] = Field(
        None, description='Optional list of SME email addresses for labeling session'
    )
    alignment_model_config: Optional[AlignmentModelConfig] = Field(
        None, description='Optional alignment model configuration'
    )


class JudgeResponse(BaseModel):
    """Response model for judge information."""

    id: str = Field(..., description='Unique judge identifier')
    name: str = Field(..., description='Human-readable name for the judge')
    instruction: str = Field(
        ..., description='User-provided evaluation criteria (always shown to user)'
    )
    experiment_id: str = Field(..., description='MLflow experiment ID')
    version: int = Field(default=1, description='Judge version number')
    labeling_run_id: Optional[str] = Field(None, description='MLflow run ID for labeling session')
    schema_info: Optional[SchemaInfo] = Field(None, description='Cached schema analysis for consistent use')
    alignment_model_config: Optional[AlignmentModelConfig] = Field(
        None, description='Alignment model configuration'
    )
    # Note: system_instruction (enhanced/aligned version) is stored internally but not exposed to user


class TraceRequest(BaseModel):
    """Request model for adding traces as examples or for evaluation."""

    trace_ids: List[str] = Field(..., description='List of trace IDs to process')


class TraceExample(BaseModel):
    """Model for trace-based examples used in evaluation and labeling."""

    trace_id: str = Field(..., description='MLflow trace ID (also serves as unique identifier)')
    request: str = Field(..., description='User request from trace')
    response: str = Field(..., description='Model response from trace')
    feedback: Optional[Feedback] = Field(
        None, description='Judge evaluation feedback (MLflow Feedback object)'
    )
    assessments: Optional[List] = Field(
        None, description='All MLflow assessments for this trace'
    )
    judge_assessment: Optional[Feedback] = Field(
        None, description='Judge assessment for the current judge version'
    )

    @classmethod
    @classmethod
    def from_traces(cls, traces) -> List['TraceExample']:
        """Create Example objects from MLflow trace objects."""
        from server.utils.parsing_utils import (
            extract_request_from_trace,
            extract_response_from_trace,
        )

        examples = []
        for trace in traces:
            # Extract request and response from trace using helper functions
            request_text = extract_request_from_trace(trace)
            response_text = extract_response_from_trace(trace)

            example = cls(
                trace_id=trace.info.trace_id,
                request=request_text,
                response=response_text,
                feedback=None,
            )
            examples.append(example)
        return examples


class TraceExamplesResponse(BaseModel):
    """Response model for trace-based examples."""

    judge_id: str = Field(..., description='Judge identifier')
    examples: List[TraceExample] = Field(..., description='List of trace examples')
    total_count: int = Field(..., description='Total number of examples')


class LabelingProgress(BaseModel):
    """Model for labeling progress."""

    total_examples: int = Field(..., description='Total number of examples')
    labeled_examples: int = Field(..., description='Number of labeled examples')
    used_for_alignment: int = Field(..., description='Number used for alignment')
    labeling_session_url: Optional[str] = Field(None, description='URL to labeling session')
    assigned_smes: Optional[List[str]] = Field(
        None, description='SME email addresses assigned to labeling session'
    )


class AlignmentResponse(BaseModel):
    """Response model for alignment results."""

    judge_id: str = Field(..., description='Judge identifier')
    success: bool = Field(..., description='Whether alignment succeeded')
    message: str = Field(..., description='Result message')
    new_version: int = Field(..., description='New judge version number')
    improvement_metrics: Optional[dict] = Field(None, description='Performance improvement metrics')


class AlignmentStartResponse(BaseModel):
    """Response model for starting alignment in background."""

    judge_id: str = Field(..., description='Judge identifier')
    success: bool = Field(..., description='Whether alignment started successfully')
    message: str = Field(..., description='Status message')


class AlignmentTaskStatus(BaseModel):
    """Status of a background alignment task."""

    status: str = Field(..., description='Task status: running, completed, or failed')
    result: Optional[AlignmentResponse] = Field(None, description='Alignment result if completed')
    error_type: Optional[str] = Field(None, description='Error type if failed: not_found, optimization_failure, or unknown')
    error_message: Optional[str] = Field(None, description='Error message if failed')
    error_traceback: Optional[str] = Field(None, description='Error traceback if failed')

    @classmethod
    def running(cls) -> 'AlignmentTaskStatus':
        """Create a running status."""
        return cls(status='running', result=None, error_type=None, error_message=None, error_traceback=None)

    @classmethod
    def completed(cls, result: AlignmentResponse) -> 'AlignmentTaskStatus':
        """Create a completed status with result."""
        return cls(status='completed', result=result, error_type=None, error_message=None, error_traceback=None)

    @classmethod
    def failed(cls, error_type: str, error_message: str, error_traceback: Optional[str] = None) -> 'AlignmentTaskStatus':
        """Create a failed status with error details."""
        return cls(status='failed', result=None, error_type=error_type, error_message=error_message, error_traceback=error_traceback)


class UserInfo(BaseModel):
    """User information model."""

    userName: str = Field(..., description='Username')
    displayName: str = Field(..., description='Display name')
    databricks_host: Optional[str] = Field(None, description='Databricks workspace host URL')
    service_principal_id: Optional[str] = Field(None, description='Databricks service principal ID')


class JudgeTraceResult(BaseModel):
    """Judge evaluation result for a specific trace."""

    trace_id: str = Field(..., description='MLflow trace ID')
    feedback: Feedback = Field(
        ..., description='Judge evaluation feedback (MLflow Feedback object)'
    )
    confidence: Optional[float] = Field(None, description='Judge confidence score')
    judge_version: int = Field(..., description='Judge version used for evaluation')


class AlignmentComparison(BaseModel):
    """Comparison between human and judge feedback for alignment view."""

    trace_id: str = Field(..., description='MLflow trace ID')
    request: str = Field(..., description='User request from trace')
    response: str = Field(..., description='Model response from trace')
    human_feedback: Feedback = Field(..., description='Human feedback (MLflow Feedback object)')
    previous_judge_feedback: Feedback = Field(
        ..., description='Previous judge version feedback (MLflow Feedback object)'
    )
    new_judge_feedback: Feedback = Field(
        ..., description='New judge version feedback (MLflow Feedback object)'
    )


class ConfusionMatrix(BaseModel):
    """Confusion matrix results for judge vs human comparison."""

    true_positive: int = Field(..., description='Judge Pass & Human Pass')
    false_negative: int = Field(..., description='Judge Fail & Human Pass')
    false_positive: int = Field(..., description='Judge Pass & Human Fail')
    true_negative: int = Field(..., description='Judge Fail & Human Fail')

    @property
    def accuracy(self) -> float:
        """Calculate accuracy from confusion matrix."""
        total = self.true_positive + self.false_negative + self.false_positive + self.true_negative
        if total == 0:
            return 0.0
        return (self.true_positive + self.true_negative) / total

    @property
    def precision(self) -> float:
        """Calculate precision (positive predictive value)."""
        denominator = self.true_positive + self.false_positive
        if denominator == 0:
            return 0.0
        return self.true_positive / denominator

    @property
    def recall(self) -> float:
        """Calculate recall (sensitivity)."""
        denominator = self.true_positive + self.false_negative
        if denominator == 0:
            return 0.0
        return self.true_positive / denominator


class AlignmentMetrics(BaseModel):
    """Metrics showing judge performance improvement."""

    total_samples: int = Field(..., description='Total number of samples')
    previous_agreement_count: int = Field(..., description='Previous version agreement count')
    new_agreement_count: int = Field(..., description='New version agreement count')
    schema_info: SchemaInfo = Field(..., description='Information about the labeling schema')
    confusion_matrix_previous: Optional[ConfusionMatrix] = Field(
        None, description='Previous version confusion matrix (only for binary outcomes)'
    )
    confusion_matrix_new: Optional[ConfusionMatrix] = Field(
        None, description='New version confusion matrix (only for binary outcomes)'
    )

    @property
    def previous_agreement_rate(self) -> float:
        """Calculate previous version agreement rate on the fly."""
        if self.total_samples == 0:
            return 0.0
        return self.previous_agreement_count / self.total_samples

    @property
    def new_agreement_rate(self) -> float:
        """Calculate new version agreement rate on the fly."""
        if self.total_samples == 0:
            return 0.0
        return self.new_agreement_count / self.total_samples


class EvaluationResult(BaseModel):
    """Result from running judge evaluation on traces."""

    judge_id: str = Field(..., description='Judge identifier')
    judge_version: int = Field(..., description='Judge version used for evaluation')
    mlflow_run_id: str = Field(..., description='MLflow run ID for this evaluation')
    evaluation_results: List[JudgeTraceResult] = Field(
        ..., description='Individual trace evaluation results'
    )
    total_traces: int = Field(..., description='Total number of traces evaluated')


class SingleJudgeTestRequest(BaseModel):
    """Request model for testing judge on a single trace."""

    trace_id: str = Field(..., description='MLflow trace ID to test on')


class SingleJudgeTestResponse(BaseModel):
    """Response model for single trace judge test."""

    judge_id: str = Field(..., description='Judge identifier')
    judge_version: int = Field(..., description='Judge version used')
    trace_id: str = Field(..., description='Tested trace ID')
    feedback: Feedback = Field(
        ..., description='Judge evaluation feedback (MLflow Feedback object)'
    )


class CreateLabelingSessionRequest(BaseModel):
    """Request model for creating a labeling session."""

    trace_ids: List[str] = Field(
        ..., description='List of trace IDs to include in labeling session'
    )
    sme_emails: List[str] = Field(..., description='SME email addresses for labeling session')


class CreateLabelingSessionResponse(BaseModel):
    """Response model for creating a labeling session."""

    session_id: str = Field(..., description='Labeling session identifier')
    mlflow_run_id: str = Field(..., description='MLflow run ID for the labeling dataset')
    labeling_url: str = Field(..., description='URL to the labeling interface')
    created_at: str = Field(..., description='When session was created')


class LabelingSessionInfo(BaseModel):
    """Information about a labeling session."""

    session_id: str = Field(..., description='Labeling session identifier')
    judge_id: str = Field(..., description='Judge this session belongs to')
    mlflow_run_id: str = Field(..., description='Associated MLflow run ID')
    labeling_url: str = Field(..., description='URL to the labeling interface')
    assigned_smes: List[str] = Field(..., description='SME email addresses')
    status: str = Field(..., description='Session status (active, completed, expired)')
    total_traces: int = Field(..., description='Total number of traces')
    labeled_traces: int = Field(..., description='Number of labeled traces')
    created_at: str = Field(..., description='When session was created')


# Test Judge Models
class TestJudgeRequest(BaseModel):
    """Request model for testing a judge on a single trace."""

    trace_id: str = Field(..., description='MLflow trace ID to test on')


class TestJudgeResponse(BaseModel):
    """Response model for testing a judge."""

    trace_id: str = Field(..., description='MLflow trace ID that was tested')
    feedback: Feedback = Field(
        ..., description='Judge evaluation feedback (MLflow Feedback object)'
    )
