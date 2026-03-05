"""Unit tests for data models."""

import unittest
from unittest import TestCase
from unittest.mock import Mock

from mlflow.entities import Feedback
from pydantic import ValidationError

from server.models import (
    AlignmentResponse,
    ConfusionMatrix,
    EvaluationResult,
    JudgeCreateRequest,
    JudgeResponse,
    JudgeTraceResult,
    LabelingProgress,
    SingleJudgeTestRequest,
    SingleJudgeTestResponse,
    TraceExample,
    TraceExamplesResponse,
    TraceRequest,
)


class TestTraceRequest(TestCase):
    """Test cases for TraceRequest model."""

    def test_trace_request_valid(self):
        """Test TraceRequest with valid data."""
        request = TraceRequest(trace_ids=['trace1', 'trace2', 'trace3'])
        self.assertEqual(request.trace_ids, ['trace1', 'trace2', 'trace3'])

    def test_trace_request_empty_list(self):
        """Test TraceRequest with empty list."""
        request = TraceRequest(trace_ids=[])
        self.assertEqual(request.trace_ids, [])

    def test_trace_request_missing_field(self):
        """Test TraceRequest validation with missing required field."""
        with self.assertRaises(ValidationError):
            TraceRequest()

    def test_trace_request_wrong_type(self):
        """Test TraceRequest validation with wrong data type."""
        with self.assertRaises(ValidationError):
            TraceRequest(trace_ids='not_a_list')


class TestTraceExample(TestCase):
    """Test cases for TraceExample model."""

    def test_trace_example_basic(self):
        """Test TraceExample with basic required fields."""
        example = TraceExample(
            trace_id='trace123', request='What is AI?', response='AI is artificial intelligence.'
        )
        self.assertEqual(example.trace_id, 'trace123')
        self.assertEqual(example.request, 'What is AI?')
        self.assertEqual(example.response, 'AI is artificial intelligence.')
        self.assertIsNone(example.feedback)
        # feedback is None, so no need to check rationale

    def test_trace_example_with_optional_fields(self):
        """Test TraceExample with all fields including optional ones."""
        example = TraceExample(
            trace_id='trace456',
            request='Explain ML',
            response='ML is machine learning',
            feedback=Feedback(value='pass', rationale='Response is accurate'),
            # Already included in Feedback object above
        )
        self.assertEqual(example.trace_id, 'trace456')
        self.assertEqual(example.request, 'Explain ML')
        self.assertEqual(example.response, 'ML is machine learning')
        self.assertEqual(example.feedback.value, 'pass')
        self.assertEqual(example.feedback.rationale, 'Response is accurate')

    def test_trace_example_missing_required_fields(self):
        """Test TraceExample validation with missing required fields."""
        with self.assertRaises(ValidationError):
            TraceExample(trace_id='trace1')  # Missing request and response

        with self.assertRaises(ValidationError):
            TraceExample(request='What?')  # Missing trace_id and response

    def test_trace_example_from_traces_method(self):
        """Test TraceExample.from_traces class method."""
        # Mock MLflow trace objects
        mock_trace1 = Mock()
        mock_trace1.info.trace_id = 'trace1'
        mock_trace1.data.request = 'What is AI?'
        mock_trace1.data.response = 'AI is artificial intelligence'

        mock_trace2 = Mock()
        mock_trace2.info.trace_id = 'trace2'
        mock_trace2.data.request = {'inputs': 'Explain ML'}
        mock_trace2.data.response = {'outputs': 'ML is machine learning'}

        traces = [mock_trace1, mock_trace2]
        examples = TraceExample.from_traces(traces)

        self.assertEqual(len(examples), 2)

        # Check first example
        self.assertEqual(examples[0].trace_id, 'trace1')
        self.assertEqual(examples[0].request, 'What is AI?')
        self.assertEqual(examples[0].response, 'AI is artificial intelligence')
        self.assertIsNone(examples[0].feedback)
        # feedback is None, so no need to check rationale

        # Check second example
        self.assertEqual(examples[1].trace_id, 'trace2')
        self.assertEqual(examples[1].request, 'Explain ML')
        self.assertEqual(examples[1].response, 'ML is machine learning')

    def test_trace_example_from_traces_with_fallback(self):
        """Test TraceExample.from_traces with fallback to preview fields."""
        # Mock trace with no data.request/response but has preview fields
        mock_trace = Mock()
        mock_trace.info.trace_id = 'trace3'
        mock_trace.data.request = None
        mock_trace.data.response = None
        mock_trace.info.request_preview = 'Preview request'
        mock_trace.info.response_preview = 'Preview response'

        # Mock hasattr to return False for data fields
        def mock_hasattr(obj, name):
            if name in ['request', 'response']:
                return False
            return True

        import builtins

        original_hasattr = builtins.hasattr
        builtins.hasattr = mock_hasattr

        try:
            examples = TraceExample.from_traces([mock_trace])
            self.assertEqual(len(examples), 1)
            self.assertEqual(examples[0].trace_id, 'trace3')
            self.assertEqual(examples[0].request, 'Preview request')
            self.assertEqual(examples[0].response, 'Preview response')
        finally:
            builtins.hasattr = original_hasattr

    def test_trace_example_from_traces_empty_list(self):
        """Test TraceExample.from_traces with empty list."""
        examples = TraceExample.from_traces([])
        self.assertEqual(examples, [])


class TestJudgeCreateRequest(TestCase):
    """Test cases for JudgeCreateRequest model."""

    def test_judge_create_request_valid(self):
        """Test JudgeCreateRequest with valid data."""
        request = JudgeCreateRequest(
            name='Quality Judge',
            instruction='Check if response is helpful',
            experiment_id='123456',
            sme_emails=['user1@test.com', 'user2@test.com'],
        )
        self.assertEqual(request.name, 'Quality Judge')
        self.assertEqual(request.instruction, 'Check if response is helpful')
        self.assertEqual(request.experiment_id, '123456')
        self.assertEqual(request.sme_emails, ['user1@test.com', 'user2@test.com'])

    def test_judge_create_request_without_optional_fields(self):
        """Test JudgeCreateRequest without optional sme_emails."""
        request = JudgeCreateRequest(
            name='Simple Judge', instruction='Basic check', experiment_id='789'
        )
        self.assertEqual(request.name, 'Simple Judge')
        self.assertEqual(request.instruction, 'Basic check')
        self.assertEqual(request.experiment_id, '789')
        self.assertIsNone(request.sme_emails)

    def test_judge_create_request_missing_required_fields(self):
        """Test JudgeCreateRequest validation with missing required fields."""
        with self.assertRaises(ValidationError):
            JudgeCreateRequest(name='Judge', instruction='Check')  # Missing experiment_id

        with self.assertRaises(ValidationError):
            JudgeCreateRequest()  # Missing all required fields


class TestJudgeResponse(TestCase):
    """Test cases for JudgeResponse model."""

    def test_judge_response_valid(self):
        """Test JudgeResponse with valid data."""
        response = JudgeResponse(
            id='judge123',
            name='Quality Judge',
            instruction='Check quality',
            experiment_id='exp456',
            version=2,
        )
        self.assertEqual(response.id, 'judge123')
        self.assertEqual(response.name, 'Quality Judge')
        self.assertEqual(response.instruction, 'Check quality')
        self.assertEqual(response.experiment_id, 'exp456')
        self.assertEqual(response.version, 2)

    def test_judge_response_default_version(self):
        """Test JudgeResponse with default version."""
        response = JudgeResponse(
            id='judge456', name='Test Judge', instruction='Test instruction', experiment_id='exp789'
        )
        self.assertEqual(response.version, 1)  # Default version


class TestConfusionMatrix(TestCase):
    """Test cases for ConfusionMatrix model."""

    def test_confusion_matrix_basic(self):
        """Test ConfusionMatrix with basic values."""
        cm = ConfusionMatrix(true_positive=10, false_negative=5, false_positive=3, true_negative=12)
        self.assertEqual(cm.true_positive, 10)
        self.assertEqual(cm.false_negative, 5)
        self.assertEqual(cm.false_positive, 3)
        self.assertEqual(cm.true_negative, 12)

    def test_confusion_matrix_accuracy(self):
        """Test ConfusionMatrix accuracy calculation."""
        cm = ConfusionMatrix(true_positive=10, false_negative=5, false_positive=3, true_negative=12)
        # Accuracy = (TP + TN) / Total = (10 + 12) / 30 = 0.7333...
        self.assertAlmostEqual(cm.accuracy, 22 / 30, places=4)

    def test_confusion_matrix_accuracy_zero_total(self):
        """Test ConfusionMatrix accuracy with zero total."""
        cm = ConfusionMatrix(true_positive=0, false_negative=0, false_positive=0, true_negative=0)
        self.assertEqual(cm.accuracy, 0.0)

    def test_confusion_matrix_precision(self):
        """Test ConfusionMatrix precision calculation."""
        cm = ConfusionMatrix(true_positive=10, false_negative=5, false_positive=3, true_negative=12)
        # Precision = TP / (TP + FP) = 10 / (10 + 3) = 0.769...
        self.assertAlmostEqual(cm.precision, 10 / 13, places=4)

    def test_confusion_matrix_precision_zero_denominator(self):
        """Test ConfusionMatrix precision with zero denominator."""
        cm = ConfusionMatrix(true_positive=0, false_negative=5, false_positive=0, true_negative=12)
        self.assertEqual(cm.precision, 0.0)

    def test_confusion_matrix_recall(self):
        """Test ConfusionMatrix recall calculation."""
        cm = ConfusionMatrix(true_positive=10, false_negative=5, false_positive=3, true_negative=12)
        # Recall = TP / (TP + FN) = 10 / (10 + 5) = 0.6667...
        self.assertAlmostEqual(cm.recall, 10 / 15, places=4)

    def test_confusion_matrix_recall_zero_denominator(self):
        """Test ConfusionMatrix recall with zero denominator."""
        cm = ConfusionMatrix(true_positive=0, false_negative=0, false_positive=3, true_negative=12)
        self.assertEqual(cm.recall, 0.0)


class TestTraceExamplesResponse(TestCase):
    """Test cases for TraceExamplesResponse model."""

    def test_trace_examples_response_valid(self):
        """Test TraceExamplesResponse with valid data."""
        examples = [
            TraceExample(trace_id='t1', request='Q1', response='A1'),
            TraceExample(trace_id='t2', request='Q2', response='A2'),
        ]
        response = TraceExamplesResponse(judge_id='judge123', examples=examples, total_count=2)
        self.assertEqual(response.judge_id, 'judge123')
        self.assertEqual(len(response.examples), 2)
        self.assertEqual(response.total_count, 2)


class TestLabelingProgress(TestCase):
    """Test cases for LabelingProgress model."""

    def test_labeling_progress_basic(self):
        """Test LabelingProgress with basic fields."""
        progress = LabelingProgress(total_examples=100, labeled_examples=50, used_for_alignment=30)
        self.assertEqual(progress.total_examples, 100)
        self.assertEqual(progress.labeled_examples, 50)
        self.assertEqual(progress.used_for_alignment, 30)
        self.assertIsNone(progress.labeling_session_url)

    def test_labeling_progress_with_url(self):
        """Test LabelingProgress with labeling session URL."""
        progress = LabelingProgress(
            total_examples=100,
            labeled_examples=75,
            used_for_alignment=60,
            labeling_session_url='https://example.com/session/123',
        )
        self.assertEqual(progress.labeling_session_url, 'https://example.com/session/123')


class TestAlignmentResponse(TestCase):
    """Test cases for AlignmentResponse model."""

    def test_alignment_response_success(self):
        """Test AlignmentResponse for successful alignment."""
        response = AlignmentResponse(
            judge_id='judge123',
            success=True,
            message='Alignment completed successfully',
            new_version=2,
            improvement_metrics={'accuracy': 0.85, 'improvement': 0.1},
        )
        self.assertEqual(response.judge_id, 'judge123')
        self.assertTrue(response.success)
        self.assertEqual(response.message, 'Alignment completed successfully')
        self.assertEqual(response.new_version, 2)
        self.assertIsNotNone(response.improvement_metrics)

    def test_alignment_response_failure(self):
        """Test AlignmentResponse for failed alignment."""
        response = AlignmentResponse(
            judge_id='judge456',
            success=False,
            message='Alignment failed due to insufficient data',
            new_version=1,
        )
        self.assertEqual(response.judge_id, 'judge456')
        self.assertFalse(response.success)
        self.assertEqual(response.message, 'Alignment failed due to insufficient data')
        self.assertEqual(response.new_version, 1)
        self.assertIsNone(response.improvement_metrics)


class TestJudgeTraceResult(TestCase):
    """Test cases for JudgeTraceResult model."""

    def test_judge_trace_result_basic(self):
        """Test JudgeTraceResult with required fields."""
        result = JudgeTraceResult(
            trace_id='trace123',
            feedback=Feedback(value='pass', rationale='Response is helpful and accurate'),
            # Already included in Feedback object above
            judge_version=1,
        )
        self.assertEqual(result.trace_id, 'trace123')
        self.assertEqual(result.feedback.value, 'pass')
        self.assertEqual(result.feedback.rationale, 'Response is helpful and accurate')
        self.assertEqual(result.judge_version, 1)
        self.assertIsNone(result.confidence)

    def test_judge_trace_result_with_confidence(self):
        """Test JudgeTraceResult with confidence score."""
        result = JudgeTraceResult(
            trace_id='trace456',
            feedback=Feedback(value='fail', rationale='Response is unclear'),
            # Already included in Feedback object above
            confidence=0.92,
            judge_version=2,
        )
        self.assertEqual(result.confidence, 0.92)


class TestSingleJudgeTestRequest(TestCase):
    """Test cases for SingleJudgeTestRequest model."""

    def test_single_judge_test_request_valid(self):
        """Test SingleJudgeTestRequest with valid trace ID."""
        request = SingleJudgeTestRequest(trace_id='trace123')
        self.assertEqual(request.trace_id, 'trace123')

    def test_single_judge_test_request_missing_field(self):
        """Test SingleJudgeTestRequest validation with missing field."""
        with self.assertRaises(ValidationError):
            SingleJudgeTestRequest()


class TestSingleJudgeTestResponse(TestCase):
    """Test cases for SingleJudgeTestResponse model."""

    def test_single_judge_test_response_valid(self):
        """Test SingleJudgeTestResponse with valid data."""
        response = SingleJudgeTestResponse(
            judge_id='judge123',
            judge_version=1,
            trace_id='trace456',
            feedback=Feedback(value='pass', rationale='Good response'),
            # Already included in Feedback object above
            confidence=0.88,
            test_timestamp='2024-01-01T10:00:00Z',
        )
        self.assertEqual(response.judge_id, 'judge123')
        self.assertEqual(response.judge_version, 1)
        self.assertEqual(response.trace_id, 'trace456')
        self.assertEqual(response.feedback.value, 'pass')
        self.assertEqual(response.feedback.rationale, 'Good response')
        self.assertEqual(response.confidence, 0.88)
        self.assertEqual(response.test_timestamp, '2024-01-01T10:00:00Z')


class TestEvaluationResult(TestCase):
    """Test cases for EvaluationResult model."""

    def test_evaluation_result_valid(self):
        """Test EvaluationResult with valid data."""
        results = [
            JudgeTraceResult(
                trace_id='t1', feedback=Feedback(value='pass', rationale='Good'), judge_version=1
            ),
            JudgeTraceResult(
                trace_id='t2', feedback=Feedback(value='fail', rationale='Bad'), judge_version=1
            ),
        ]

        eval_result = EvaluationResult(
            judge_id='judge123',
            judge_version=1,
            mlflow_run_id='run456',
            evaluation_results=results,
            total_traces=2,
            pass_count=1,
            fail_count=1,
            evaluation_timestamp='2024-01-01T10:00:00Z',
        )

        self.assertEqual(eval_result.judge_id, 'judge123')
        self.assertEqual(eval_result.judge_version, 1)
        self.assertEqual(eval_result.mlflow_run_id, 'run456')
        self.assertEqual(len(eval_result.evaluation_results), 2)
        self.assertEqual(eval_result.total_traces, 2)
        self.assertEqual(eval_result.pass_count, 1)
        self.assertEqual(eval_result.fail_count, 1)


if __name__ == '__main__':
    unittest.main()
