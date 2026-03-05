"""Unit tests for judge builder service."""

from unittest.mock import Mock, patch

import pytest

from server.models import JudgeCreateRequest, JudgeResponse
from server.services.judge_builder_service import JudgeBuilderService


@pytest.fixture
def judge_builder_service():
    """Create a judge builder service instance for testing."""
    return JudgeBuilderService()


@pytest.fixture
def mock_judge_create_request():
    """Create a mock judge create request."""
    return JudgeCreateRequest(
        name='Test Judge',
        instruction='Test instruction',
        experiment_id='exp-123',
        sme_emails=['test@example.com']
    )


@pytest.fixture
def mock_judge_response():
    """Create a mock judge response."""
    return JudgeResponse(
        id='judge-123',
        name='Test Judge',
        instruction='Test instruction',
        experiment_id='exp-123',
        version=1
    )


class TestJudgeBuilderService:
    """Test cases for JudgeBuilderService."""

    @patch('server.services.judge_builder_service.mlflow')
    def test_experiment_validation_success(self, mock_mlflow, judge_builder_service, mock_judge_create_request):
        """Test successful experiment validation during judge creation."""
        mock_experiment = Mock()
        mock_experiment.name = 'Test Experiment'
        mock_mlflow.get_experiment.return_value = mock_experiment

        with patch.object(judge_builder_service.judge_service, 'create_judge') as mock_create, \
             patch.object(judge_builder_service, '_store_judge_metadata_in_experiment'), \
             patch.object(judge_builder_service.labeling_service, 'create_labeling_session'):
            mock_create.return_value = Mock(id='judge-123', name='Test')

            # This should not raise an exception
            judge_builder_service.create_judge_builder(mock_judge_create_request)

            mock_mlflow.get_experiment.assert_called_once_with('exp-123')

    @patch('server.services.judge_builder_service.mlflow')
    def test_experiment_validation_failure(self, mock_mlflow, judge_builder_service, mock_judge_create_request):
        """Test experiment validation failure during judge creation."""
        mock_mlflow.get_experiment.side_effect = Exception('Not found')

        with pytest.raises(ValueError, match='Invalid experiment ID'):
            judge_builder_service.create_judge_builder(mock_judge_create_request)

    @patch('server.services.judge_builder_service.mlflow')
    def test_create_judge_builder_success(self, mock_mlflow, judge_builder_service, mock_judge_create_request, mock_judge_response):
        """Test successful judge creation."""
        # Mock dependencies
        mock_experiment = Mock()
        mock_experiment.name = 'Test Experiment'
        mock_experiment_service.get_experiment.return_value = mock_experiment
        mock_judge_service.create_judge.return_value = mock_judge_response

        with patch.object(judge_builder_service, '_register_scorer') as mock_register, \
             patch.object(judge_builder_service, '_store_judge_metadata') as mock_store, \
             patch.object(judge_builder_service, '_create_initial_labeling_session') as mock_labeling:

            mock_register.return_value = True

            result = judge_builder_service.create_judge(mock_judge_create_request)

            assert result == mock_judge_response
            mock_judge_service.create_judge.assert_called_once()
            mock_register.assert_called_once()
            mock_store.assert_called_once()
            mock_labeling.assert_called_once()

    @patch('server.services.judge_builder_service.judge_service')
    @patch('server.services.judge_builder_service.experiment_service')
    def test_create_judge_scorer_registration_fails(self, mock_experiment_service, mock_judge_service,
                                                  judge_builder_service, mock_judge_create_request, mock_judge_response):
        """Test judge creation when scorer registration fails."""
        # Mock dependencies
        mock_experiment = Mock()
        mock_experiment_service.get_experiment.return_value = mock_experiment
        mock_judge_service.create_judge.return_value = mock_judge_response

        with patch.object(judge_builder_service, '_register_scorer') as mock_register:
            mock_register.return_value = False

            with pytest.raises(ValueError, match='Failed to register scorer'):
                judge_builder_service.create_judge(mock_judge_create_request)

    def test_register_scorer_success(self, judge_builder_service, mock_judge_response):
        """Test successful scorer registration."""
        with patch('server.services.judge_builder_service.judge_service') as mock_judge_service:
            mock_judge_instance = Mock()
            mock_judge_instance.register_scorer.return_value = 'scorer-123'
            mock_judge_service._judges = {'judge-123': mock_judge_instance}

            result = judge_builder_service._register_scorer(mock_judge_response)

            assert result is True
            mock_judge_instance.register_scorer.assert_called_once()

    def test_register_scorer_no_judge_instance(self, judge_builder_service, mock_judge_response):
        """Test scorer registration when judge instance not found."""
        with patch('server.services.judge_builder_service.judge_service') as mock_judge_service:
            mock_judge_service._judges = {}

            result = judge_builder_service._register_scorer(mock_judge_response)

            assert result is False

    def test_register_scorer_exception(self, judge_builder_service, mock_judge_response):
        """Test scorer registration when exception occurs."""
        with patch('server.services.judge_builder_service.judge_service') as mock_judge_service:
            mock_judge_instance = Mock()
            mock_judge_instance.register_scorer.side_effect = Exception('Registration failed')
            mock_judge_service._judges = {'judge-123': mock_judge_instance}

            result = judge_builder_service._register_scorer(mock_judge_response)

            assert result is False

    @patch('server.services.judge_builder_service.mlflow')
    def test_store_judge_metadata_success(self, mock_mlflow, judge_builder_service, mock_judge_response):
        """Test successful judge metadata storage."""
        mock_run_context = Mock()
        mock_run_context.info.run_id = 'run-123'
        mock_mlflow.start_run.return_value.__enter__.return_value = mock_run_context

        judge_builder_service._store_judge_metadata(mock_judge_response)

        mock_mlflow.start_run.assert_called_once()
        mock_mlflow.set_tag.assert_called()
        mock_mlflow.log_param.assert_called()

    @patch('server.services.judge_builder_service.mlflow')
    def test_store_judge_metadata_exception(self, mock_mlflow, judge_builder_service, mock_judge_response):
        """Test judge metadata storage when exception occurs."""
        mock_mlflow.start_run.side_effect = Exception('MLflow error')

        # Should not raise exception, just log warning
        judge_builder_service._store_judge_metadata(mock_judge_response)

        mock_mlflow.start_run.assert_called_once()

    @patch('server.services.judge_builder_service.labeling_service')
    def test_create_initial_labeling_session_success(self, mock_labeling_service, judge_builder_service, mock_judge_response):
        """Test successful initial labeling session creation."""
        mock_labeling_service.create_labeling_session.return_value = 'session-123'

        judge_builder_service._create_initial_labeling_session(mock_judge_response)

        mock_labeling_service.create_labeling_session.assert_called_once_with('judge-123')

    @patch('server.services.judge_builder_service.labeling_service')
    def test_create_initial_labeling_session_exception(self, mock_labeling_service, judge_builder_service, mock_judge_response):
        """Test initial labeling session creation when exception occurs."""
        mock_labeling_service.create_labeling_session.side_effect = Exception('Labeling error')

        # Should not raise exception, just log warning
        judge_builder_service._create_initial_labeling_session(mock_judge_response)

        mock_labeling_service.create_labeling_session.assert_called_once()

    @patch('server.services.judge_builder_service.mlflow')
    def test_list_judges_success(self, mock_mlflow, judge_builder_service):
        """Test successful judge listing."""
        # Mock MLflow search response
        mock_run1 = Mock()
        mock_run1.data.tags = {
            'judge_id': 'judge-1',
            'judge_name': 'Judge 1',
            'judge_instruction': 'Instruction 1',
            'judge_version': '1'
        }
        mock_run1.data.params = {'experiment_id': 'exp-123'}

        mock_run2 = Mock()
        mock_run2.data.tags = {
            'judge_id': 'judge-2',
            'judge_name': 'Judge 2',
            'judge_instruction': 'Instruction 2',
            'judge_version': '2'
        }
        mock_run2.data.params = {'experiment_id': 'exp-456'}

        mock_mlflow.search_runs.return_value = [mock_run1, mock_run2]

        with patch('server.services.judge_builder_service.judge_service') as mock_judge_service:
            mock_judge_service.recreate_judge.return_value = True

            result = judge_builder_service.list_judges()

            assert len(result) == 2
            assert result[0].id == 'judge-1'
            assert result[1].id == 'judge-2'

    @patch('server.services.judge_builder_service.mlflow')
    def test_list_judges_recreation_failure(self, mock_mlflow, judge_builder_service):
        """Test judge listing when recreation fails."""
        mock_run = Mock()
        mock_run.data.tags = {
            'judge_id': 'judge-1',
            'judge_name': 'Judge 1',
            'judge_instruction': 'Instruction 1',
            'judge_version': '1'
        }
        mock_run.data.params = {'experiment_id': 'exp-123'}

        mock_mlflow.search_runs.return_value = [mock_run]

        with patch('server.services.judge_builder_service.judge_service') as mock_judge_service:
            mock_judge_service.recreate_judge.return_value = False

            result = judge_builder_service.list_judges()

            assert len(result) == 0  # Should skip failed recreations

    @patch('server.services.judge_builder_service.mlflow')
    def test_list_judges_incomplete_metadata(self, mock_mlflow, judge_builder_service):
        """Test judge listing with incomplete metadata."""
        mock_run = Mock()
        mock_run.data.tags = {
            'judge_id': 'judge-1',
            'judge_name': 'Judge 1',
            # Missing judge_instruction and judge_version
        }
        mock_run.data.params = {'experiment_id': 'exp-123'}

        mock_mlflow.search_runs.return_value = [mock_run]

        result = judge_builder_service.list_judges()

        assert len(result) == 0  # Should skip incomplete metadata

    @patch('server.services.judge_builder_service.judge_service')
    def test_get_judge_success(self, mock_judge_service, judge_builder_service, mock_judge_response):
        """Test successful judge retrieval."""
        mock_judge_service.get_judge.return_value = mock_judge_response

        result = judge_builder_service.get_judge('judge-123')

        assert result == mock_judge_response
        mock_judge_service.get_judge.assert_called_once_with('judge-123')

    @patch('server.services.judge_builder_service.judge_service')
    def test_delete_judge_success(self, mock_judge_service, judge_builder_service):
        """Test successful judge deletion."""
        mock_judge_service.delete_judge.return_value = True

        result = judge_builder_service.delete_judge('judge-123')

        assert result is True
        mock_judge_service.delete_judge.assert_called_once_with('judge-123')

    @patch('server.services.judge_builder_service.judge_service')
    def test_delete_judge_failure(self, mock_judge_service, judge_builder_service):
        """Test judge deletion failure."""
        mock_judge_service.delete_judge.return_value = False

        result = judge_builder_service.delete_judge('judge-123')

        assert result is False

    def test_recreate_judge_from_metadata_success(self, judge_builder_service):
        """Test successful judge recreation from metadata."""
        metadata = {
            'judge_id': 'judge-123',
            'judge_name': 'Test Judge',
            'judge_instruction': 'Test instruction',
            'judge_version': '2',
            'experiment_id': 'exp-123'
        }

        with patch('server.services.judge_builder_service.judge_service') as mock_judge_service:
            mock_judge_service.recreate_judge.return_value = True

            result = judge_builder_service._recreate_judge_from_metadata(metadata)

            assert result.id == 'judge-123'
            assert result.version == 2
            mock_judge_service.recreate_judge.assert_called_once()

    def test_recreate_judge_from_metadata_missing_fields(self, judge_builder_service):
        """Test judge recreation with missing required fields."""
        metadata = {
            'judge_id': 'judge-123',
            'judge_name': 'Test Judge',
            # Missing judge_instruction, judge_version, experiment_id
        }

        result = judge_builder_service._recreate_judge_from_metadata(metadata)

        assert result is None

    @patch('server.services.judge_builder_service.judge_service')
    def test_recreate_judge_from_metadata_recreation_failure(self, mock_judge_service, judge_builder_service):
        """Test judge recreation when service recreation fails."""
        metadata = {
            'judge_id': 'judge-123',
            'judge_name': 'Test Judge',
            'judge_instruction': 'Test instruction',
            'judge_version': '1',
            'experiment_id': 'exp-123'
        }

        mock_judge_service.recreate_judge.return_value = False

        result = judge_builder_service._recreate_judge_from_metadata(metadata)

        assert result is None
