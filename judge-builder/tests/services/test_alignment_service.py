"""Unit tests for alignment service."""

from unittest.mock import Mock, patch

import pytest
from mlflow.entities import Assessment, AssessmentSource, Trace

from server.models import (
    ConfusionMatrix,
    JudgeResponse,
    SingleJudgeTestRequest,
    TraceRequest,
)
from server.services.alignment_service import AlignmentService


@pytest.fixture
def alignment_service():
    return AlignmentService()


@pytest.fixture
def mock_judge():
    return JudgeResponse(
        id='judge-123',
        name='Test Judge',
        instruction='Test instruction',
        experiment_id='exp-123',
        version=2,
    )


@pytest.fixture
def mock_trace():
    trace = Mock(spec=Trace)
    trace.info.trace_id = 'trace-123'
    trace.data.request = {'request': 'test request'}
    trace.data.response = {'response': 'test response'}
    return trace


@pytest.fixture
def mock_assessment():
    assessment = Mock(spec=Assessment)
    assessment.name = 'test_judge'
    assessment.source = Mock(spec=AssessmentSource)
    assessment.source.source_type = 'HUMAN'
    assessment.error = None
    assessment.feedback = Mock()
    assessment.feedback.value = 'Pass'
    return assessment


class TestAlignmentService:
    """Test cases for AlignmentService."""

    def test_get_judge_scorer_success(self, alignment_service, mock_judge):
        """Test successful retrieval of judge scorer."""
        mock_scorer = Mock()
        mock_scorer.name = 'v2_instruction_judge_test_judge'

        with patch('server.services.alignment_service.scorers.list_scorers') as mock_list:
            mock_list.return_value = [mock_scorer]

            result = alignment_service._get_judge_scorer(mock_judge)

            assert result == mock_scorer
            mock_list.assert_called_once()

    def test_get_judge_scorer_not_found(self, alignment_service, mock_judge):
        """Test when judge scorer is not found."""
        with patch('server.services.alignment_service.scorers.list_scorers') as mock_list:
            mock_list.return_value = []

            result = alignment_service._get_judge_scorer(mock_judge)

            assert result is None

    @patch('server.services.alignment_service.cache_service')
    def test_evaluate_judge_cached(self, mock_cache_service, alignment_service, mock_judge):
        """Test judge evaluation with cached result."""
        mock_cache_service.get_evaluation_run_id.return_value = 'cached-run-123'

        request = TraceRequest(trace_ids=['trace-1', 'trace-2'])
        result = alignment_service.evaluate_judge('judge-123', request)

        assert result.judge_id == 'judge-123'
        assert result.mlflow_run_id == 'cached-run-123'
        assert result.total_traces == 2

    @patch('server.services.alignment_service.mlflow')
    @patch('server.services.alignment_service.cache_service')
    @patch('server.services.alignment_service.evaluate')
    def test_evaluate_judge_new_evaluation(self, mock_evaluate, mock_cache_service, mock_mlflow,
                                         alignment_service, mock_judge, mock_trace):
        """Test judge evaluation with new evaluation run."""
        # Setup mocks
        mock_cache_service.get_evaluation_run_id.return_value = None
        mock_cache_service.get_trace.return_value = mock_trace
        mock_scorer = Mock()
        mock_scorer.name = 'v2_instruction_judge_test_judge'
        mock_run = Mock()
        mock_run.info.run_id = 'new-run-123'
        mock_mlflow.start_run.return_value.__enter__.return_value = mock_run

        with patch.object(alignment_service, '_get_judge_scorer', return_value=mock_scorer), \
             patch('server.services.alignment_service.judge_service') as mock_judge_service:
            mock_judge_service.get_judge.return_value = mock_judge

            request = TraceRequest(trace_ids=['trace-1'])
            result = alignment_service.evaluate_judge('judge-123', request)

            assert result.judge_id == 'judge-123'
            assert result.mlflow_run_id == 'new-run-123'
            mock_evaluate.assert_called_once()

    def test_test_judge_success(self, alignment_service, mock_judge, mock_trace):
        """Test successful judge testing on single trace."""
        mock_scorer = Mock()
        mock_feedback = Mock()
        mock_scorer.return_value = mock_feedback

        with patch('server.services.alignment_service.cache_service') as mock_cache_service, \
             patch('server.services.alignment_service.judge_service') as mock_judge_service, \
             patch.object(alignment_service, '_get_judge_scorer', return_value=mock_scorer):

            mock_judge_service.get_judge.return_value = mock_judge
            mock_judge_service._judges = {'judge-123': Mock()}
            mock_cache_service.get_trace.return_value = mock_trace

            request = SingleJudgeTestRequest(trace_id='trace-123')
            result = alignment_service.test_judge('judge-123', request)

            assert result.judge_id == 'judge-123'
            assert result.trace_id == 'trace-123'
            assert result.feedback == mock_feedback

    def test_get_alignment_comparison_version_check(self, alignment_service):
        """Test alignment comparison version requirement."""
        mock_judge_v1 = JudgeResponse(
            id='judge-123', name='Test', instruction='Test', experiment_id='exp', version=1
        )

        with patch('server.services.alignment_service.judge_service') as mock_judge_service:
            mock_judge_service.get_judge.return_value = mock_judge_v1

            with pytest.raises(ValueError, match='must have version >= 2'):
                alignment_service.get_alignment_comparison('judge-123')

    @patch('server.services.alignment_service.cache_service')
    @patch('server.services.alignment_service.get_human_feedback_from_trace')
    @patch('server.services.alignment_service.get_scorer_feedback_from_trace')
    @patch('server.services.alignment_service.assessment_has_error')
    def test_get_alignment_comparison_success(self, mock_has_error, mock_get_scorer,
                                            mock_get_human, mock_cache_service,
                                            alignment_service, mock_judge, mock_trace,
                                            mock_assessment):
        """Test successful alignment comparison."""
        # Setup mocks
        mock_judge.version = 2
        mock_cache_service.get_evaluation_run_id.return_value = 'run-123'
        mock_cache_service.get_trace.return_value = mock_trace
        mock_get_human.return_value = mock_assessment
        mock_get_scorer.return_value = mock_assessment
        mock_has_error.return_value = False

        mock_example = Mock()
        mock_example.trace_id = 'trace-123'

        with patch('server.services.alignment_service.judge_service') as mock_judge_service, \
             patch('server.services.alignment_service.labeling_service') as mock_labeling_service:

            mock_judge_service.get_judge.return_value = mock_judge
            mock_labeling_service.get_examples.return_value = [mock_example]

            result = alignment_service.get_alignment_comparison('judge-123')

            assert 'metrics' in result
            assert 'comparisons' in result
            assert result['metrics'].total_samples == 1
            assert len(result['comparisons']) == 1

    def test_calculate_confusion_matrix(self, alignment_service):
        """Test confusion matrix calculation."""
        human_labels = ['pass', 'pass', 'fail', 'fail']
        judge_results = ['pass', 'fail', 'pass', 'fail']

        matrix = alignment_service.calculate_confusion_matrix(human_labels, judge_results)

        assert matrix.true_positive == 1  # human pass, judge pass
        assert matrix.false_negative == 1  # human pass, judge fail
        assert matrix.false_positive == 1  # human fail, judge pass
        assert matrix.true_negative == 1  # human fail, judge fail

    def test_confusion_matrix_accuracy_calculation(self, alignment_service):
        """Test ConfusionMatrix accuracy property."""
        # Test case from user's screenshot: TP=4, FN=0, FP=3, TN=3
        matrix = ConfusionMatrix(
            true_positive=4,
            false_negative=0,
            false_positive=3,
            true_negative=3
        )
        
        # Accuracy should be (4+3)/(4+0+3+3) = 7/10 = 0.7 = 70%
        assert matrix.accuracy == 0.7
        
    def test_confusion_matrix_edge_cases(self, alignment_service):
        """Test ConfusionMatrix edge cases."""
        # Perfect accuracy
        perfect = ConfusionMatrix(true_positive=5, false_negative=0, false_positive=0, true_negative=5)
        assert perfect.accuracy == 1.0
        
        # Zero accuracy
        worst = ConfusionMatrix(true_positive=0, false_negative=5, false_positive=5, true_negative=0)
        assert worst.accuracy == 0.0
        
        # Empty matrix
        empty = ConfusionMatrix(true_positive=0, false_negative=0, false_positive=0, true_negative=0)
        assert empty.accuracy == 0.0

    def test_calculate_confusion_matrix_user_case(self, alignment_service):
        """Test the specific case from user's screenshot."""
        # To get TP=4, FN=0, FP=3, TN=3:
        # 4 cases: human=pass, judge=pass (TP)
        # 0 cases: human=pass, judge=fail (FN)
        # 3 cases: human=fail, judge=pass (FP) 
        # 3 cases: human=fail, judge=fail (TN)
        human_labels = ['pass', 'pass', 'pass', 'pass', 'fail', 'fail', 'fail', 'fail', 'fail', 'fail']
        judge_results = ['pass', 'pass', 'pass', 'pass', 'pass', 'pass', 'pass', 'fail', 'fail', 'fail']
        
        matrix = alignment_service.calculate_confusion_matrix(human_labels, judge_results)
        
        assert matrix.true_positive == 4
        assert matrix.false_negative == 0  
        assert matrix.false_positive == 3
        assert matrix.true_negative == 3
        assert matrix.accuracy == 0.7  # 70%

    @patch('server.services.alignment_service.cache_service')
    def test_run_alignment_success(self, mock_cache_service, alignment_service,
                                 mock_judge, mock_trace):
        """Test successful alignment run."""
        mock_cache_service.get_trace.return_value = mock_trace
        mock_example = Mock()
        mock_example.trace_id = 'trace-123'

        with patch('server.services.alignment_service.judge_service') as mock_judge_service, \
             patch('server.services.alignment_service.labeling_service') as mock_labeling_service, \
             patch.object(alignment_service, 'evaluate_judge') as mock_evaluate:

            mock_judge_service.get_judge.return_value = mock_judge
            mock_judge_service._judges = {'judge-123': Mock()}
            mock_new_judge = Mock()
            mock_new_judge.id = 'judge-123'
            mock_new_judge.version = 3
            mock_judge_service.create_new_version.return_value = mock_new_judge
            mock_labeling_service.get_examples.return_value = [mock_example]

            result = alignment_service.run_alignment('judge-123')

            assert result.success
            assert result.judge_id == 'judge-123'
            assert result.new_version == 3
            assert mock_evaluate.call_count == 2  # Initial and new version evaluations
