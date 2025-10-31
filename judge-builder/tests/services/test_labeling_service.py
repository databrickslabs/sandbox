"""Unit tests for LabelingService with mocked MLflow calls."""

import unittest
from unittest import TestCase
from unittest.mock import Mock, patch

from server.models import (
    CreateLabelingSessionRequest,
    CreateLabelingSessionResponse,
    JudgeResponse,
    LabelingProgress,
    TraceExample,
    TraceRequest,
)
from server.services.labeling_service import LabelingService


class TestLabelingService(TestCase):
    """Test cases for LabelingService class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.service = LabelingService()
        self.mock_judge_response = JudgeResponse(
            id='judge123',
            name='Quality Judge',
            instruction='Check if response is helpful',
            experiment_id='exp456',
            version=1,
        )

    @patch('server.services.labeling_service.mlflow')
    @patch('server.services.labeling_service.schemas')
    @patch('server.services.labeling_service.labeling')
    @patch('server.services.judge_service.judge_service')
    def test_create_labeling_session_success(
        self, mock_judge_service, mock_labeling, mock_schemas, mock_mlflow
    ):
        """Test successful labeling session creation."""
        # Mock judge service response
        mock_judge_service.get_judge.return_value = self.mock_judge_response

        # Mock MLflow labeling session
        mock_session = Mock()
        mock_session.mlflow_run_id = 'run123'
        mock_session.url = 'https://databricks.com/labeling/session/123'
        mock_labeling.create_labeling_session.return_value = mock_session

        # Test request
        request = CreateLabelingSessionRequest(
            trace_ids=['trace1', 'trace2'], sme_emails=['user1@test.com', 'user2@test.com']
        )

        result = self.service.create_labeling_session('judge123', request)

        # Verify MLflow calls
        mock_mlflow.set_experiment.assert_called_once_with(experiment_id='exp456')
        mock_schemas.create_label_schema.assert_called_once()
        mock_labeling.create_labeling_session.assert_called_once()

        # Verify result
        self.assertIsInstance(result, CreateLabelingSessionResponse)
        self.assertEqual(result.session_id, 'run123')
        self.assertEqual(result.mlflow_run_id, 'run123')
        self.assertEqual(result.labeling_url, 'https://databricks.com/labeling/session/123')
        self.assertIsNotNone(result.created_at)

    @patch('server.services.judge_service.judge_service')
    def test_create_labeling_session_judge_not_found(self, mock_judge_service):
        """Test labeling session creation with nonexistent judge."""
        mock_judge_service.get_judge.return_value = None

        request = CreateLabelingSessionRequest(trace_ids=['trace1'], sme_emails=['user@test.com'])

        with self.assertRaises(ValueError) as context:
            self.service.create_labeling_session('nonexistent', request)

        self.assertIn('Judge with ID nonexistent not found', str(context.exception))

    @patch('server.services.labeling_service.mlflow')
    @patch('server.services.labeling_service.schemas')
    @patch('server.services.labeling_service.labeling')
    @patch('server.services.judge_service.judge_service')
    def test_create_labeling_session_schema_configuration(
        self, mock_judge_service, mock_labeling, mock_schemas, mock_mlflow
    ):
        """Test that labeling session creates proper schema configuration."""
        mock_judge_service.get_judge.return_value = self.mock_judge_response

        mock_session = Mock()
        mock_session.mlflow_run_id = 'run123'
        mock_session.url = 'https://test.com/session'
        mock_labeling.create_labeling_session.return_value = mock_session

        request = CreateLabelingSessionRequest(trace_ids=['trace1'], sme_emails=['user@test.com'])

        self.service.create_labeling_session('judge123', request)

        # Verify schema creation parameters
        schema_call = mock_schemas.create_label_schema.call_args
        self.assertIn('name', schema_call.kwargs)
        self.assertIn('type', schema_call.kwargs)
        self.assertEqual(schema_call.kwargs['type'], 'feedback')
        self.assertIn('instruction', schema_call.kwargs)
        self.assertTrue(schema_call.kwargs['enable_comment'])
        self.assertTrue(schema_call.kwargs['overwrite'])

        # Verify input options
        input_config = schema_call.kwargs['input']
        self.assertIsNotNone(input_config)

    @patch('server.services.labeling_service.mlflow')
    @patch('server.services.judge_service.judge_service')
    @patch.object(LabelingService, '_get_labeling_session')
    def test_get_labeling_session_success(self, mock_get_session, mock_judge_service, mock_mlflow):
        """Test successful retrieval of labeling session."""
        mock_judge_service.get_judge.return_value = self.mock_judge_response

        mock_session = Mock()
        mock_session.mlflow_run_id = 'run123'
        mock_session.url = 'https://test.com/session'
        mock_get_session.return_value = mock_session

        result = self.service.get_labeling_session('judge123')

        # Verify calls
        mock_mlflow.set_experiment.assert_called_once_with(experiment_id='exp456')
        mock_get_session.assert_called_once_with('judge123')

        self.assertEqual(result, mock_session)

    @patch('server.services.judge_service.judge_service')
    def test_get_labeling_session_judge_not_found(self, mock_judge_service):
        """Test get labeling session with nonexistent judge."""
        mock_judge_service.get_judge.return_value = None

        with self.assertRaises(ValueError) as context:
            self.service.get_labeling_session('nonexistent')

        self.assertIn('Judge with ID nonexistent not found', str(context.exception))

    @patch('server.services.labeling_service.mlflow')
    @patch('server.services.judge_service.judge_service')
    @patch.object(LabelingService, '_get_labeling_session')
    def test_get_labeling_session_no_session_found(
        self, mock_get_session, mock_judge_service, mock_mlflow
    ):
        """Test get labeling session when no session exists."""
        mock_judge_service.get_judge.return_value = self.mock_judge_response
        mock_get_session.return_value = None

        with self.assertRaises(ValueError) as context:
            self.service.get_labeling_session('judge123')

        self.assertIn('No labeling session found for this judge', str(context.exception))

    @patch('server.services.labeling_service.labeling')
    def test_get_labeling_session_helper_method(self, mock_labeling):
        """Test the _get_labeling_session helper method."""
        # Mock labeling sessions
        mock_session1 = Mock()
        mock_session1.name = 'other_session_abc123'

        mock_session2 = Mock()
        mock_session2.name = 'quality_judge_def45678_labeling'  # Match first 8 chars of judge ID

        mock_labeling.get_labeling_sessions.return_value = [mock_session1, mock_session2]

        # Test with judge ID that matches session2 (first 8 chars: "def45678")
        result = self.service._get_labeling_session('def45678-1234-5678-abcd-123456789012')

        self.assertEqual(result, mock_session2)

    @patch('server.services.labeling_service.labeling')
    def test_get_labeling_session_helper_no_match(self, mock_labeling):
        """Test _get_labeling_session when no matching session is found."""
        mock_session = Mock()
        mock_session.name = 'unrelated_session_xyz789'

        mock_labeling.get_labeling_sessions.return_value = [mock_session]

        result = self.service._get_labeling_session('judge123')

        self.assertIsNone(result)

    @patch('server.services.labeling_service.logger')
    @patch.object(LabelingService, '_get_labeling_session')
    @patch('server.services.labeling_service.labeling')
    def test_delete_labeling_session_success(self, mock_labeling, mock_get_session, mock_logger):
        """Test successful labeling session deletion."""
        mock_session = Mock()
        mock_session.mlflow_run_id = 'run123'
        mock_session.url = 'https://test.com/session'
        mock_get_session.return_value = mock_session

        result = self.service.delete_labeling_session('judge123')

        self.assertTrue(result)
        mock_labeling.delete_labeling_session.assert_called_once_with(mock_session)
        mock_logger.info.assert_called_once()

    @patch('server.services.labeling_service.logger')
    @patch.object(LabelingService, '_get_labeling_session')
    def test_delete_labeling_session_not_found(self, mock_get_session, mock_logger):
        """Test deletion when no labeling session exists."""
        mock_get_session.return_value = None

        result = self.service.delete_labeling_session('judge123')

        self.assertFalse(result)
        mock_logger.warning.assert_called_once()

    @patch('server.services.labeling_service.mlflow')
    @patch('server.services.judge_service.judge_service')
    @patch.object(LabelingService, '_get_labeling_session')
    def test_add_examples_success(self, mock_get_session, mock_judge_service, mock_mlflow):
        """Test successful addition of examples to labeling session."""
        mock_judge_service.get_judge.return_value = self.mock_judge_response

        # Mock labeling session
        mock_session = Mock()
        mock_session.mlflow_run_id = 'run123'
        mock_session.url = 'https://test.com/session'
        mock_get_session.return_value = mock_session

        # Mock MLflow traces
        mock_trace1 = Mock()
        mock_trace1.info.trace_id = 'trace1'
        mock_trace1.data.request = 'What is AI?'
        mock_trace1.data.response = 'AI is artificial intelligence'

        mock_trace2 = Mock()
        mock_trace2.info.trace_id = 'trace2'
        mock_trace2.data.request = 'Explain ML'
        mock_trace2.data.response = 'ML is machine learning'

        mock_mlflow.get_trace.side_effect = [mock_trace1, mock_trace2]

        request = TraceRequest(trace_ids=['trace1', 'trace2'])

        # Mock the environment variable setting
        with patch('mlflow.environment_variables') as mock_env_vars:
            mock_env_vars.MLFLOW_ENABLE_ASYNC_TRACE_LOGGING.set = Mock()

            result = self.service.add_examples('judge123', request)

        # Verify MLflow calls
        mock_mlflow.set_experiment.assert_called_once_with(experiment_id='exp456')
        self.assertEqual(mock_mlflow.get_trace.call_count, 2)
        mock_session.add_traces.assert_called_once()

        # Verify result
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], TraceExample)
        self.assertEqual(result[0].trace_id, 'trace1')

    @patch('server.services.judge_service.judge_service')
    def test_add_examples_judge_not_found(self, mock_judge_service):
        """Test add examples with nonexistent judge."""
        mock_judge_service.get_judge.return_value = None

        request = TraceRequest(trace_ids=['trace1'])

        with self.assertRaises(ValueError) as context:
            self.service.add_examples('nonexistent', request)

        self.assertIn('Judge with ID nonexistent not found', str(context.exception))

    @patch('server.services.judge_service.judge_service')
    def test_add_examples_no_experiment_id(self, mock_judge_service):
        """Test add examples when judge has no experiment ID."""
        judge_without_exp = JudgeResponse(
            id='judge123',
            name='Test Judge',
            instruction='Test instruction',
            experiment_id='',  # Empty experiment ID
            version=1,
        )
        mock_judge_service.get_judge.return_value = judge_without_exp

        request = TraceRequest(trace_ids=['trace1'])

        with self.assertRaises(ValueError) as context:
            self.service.add_examples('judge123', request)

        self.assertIn('No experiment ID found for judge', str(context.exception))

    @patch('server.services.labeling_service.mlflow')
    @patch('server.services.judge_service.judge_service')
    @patch.object(LabelingService, '_get_labeling_session')
    def test_add_examples_no_session(self, mock_get_session, mock_judge_service, mock_mlflow):
        """Test add examples when no labeling session exists."""
        mock_judge_service.get_judge.return_value = self.mock_judge_response
        mock_get_session.return_value = None

        request = TraceRequest(trace_ids=['trace1'])

        with self.assertRaises(ValueError) as context:
            self.service.add_examples('judge123', request)

        self.assertIn('No labeling session found for this judge', str(context.exception))

    @patch('server.services.labeling_service.logger')
    @patch('server.services.labeling_service.mlflow')
    @patch('server.services.judge_service.judge_service')
    @patch.object(LabelingService, '_get_labeling_session')
    def test_add_examples_trace_fetch_failures(
        self, mock_get_session, mock_judge_service, mock_mlflow, mock_logger
    ):
        """Test add examples with some trace fetch failures."""
        mock_judge_service.get_judge.return_value = self.mock_judge_response

        mock_session = Mock()
        mock_get_session.return_value = mock_session

        # Mock trace fetching with one success and one failure
        def mock_get_trace_side_effect(trace_id):
            if trace_id == 'trace1':
                mock_trace = Mock()
                mock_trace.info.trace_id = 'trace1'
                mock_trace.data.request = 'Test request'
                mock_trace.data.response = 'Test response'
                return mock_trace
            else:
                raise Exception('Trace not found')

        mock_mlflow.get_trace.side_effect = mock_get_trace_side_effect

        request = TraceRequest(trace_ids=['trace1', 'trace2'])

        with patch('mlflow.environment_variables') as mock_env_vars:
            mock_env_vars.MLFLOW_ENABLE_ASYNC_TRACE_LOGGING.set = Mock()
            result = self.service.add_examples('judge123', request)

        # Should have 1 successful trace
        self.assertEqual(len(result), 1)
        mock_logger.warning.assert_called_once()

    @patch('server.services.labeling_service.mlflow')
    @patch('server.services.judge_service.judge_service')
    @patch.object(LabelingService, '_get_labeling_session')
    def test_add_examples_no_valid_traces(self, mock_get_session, mock_judge_service, mock_mlflow):
        """Test add examples when no traces can be fetched."""
        mock_judge_service.get_judge.return_value = self.mock_judge_response
        mock_get_session.return_value = Mock()

        # Mock all trace fetches to fail
        mock_mlflow.get_trace.side_effect = Exception('All traces failed')

        request = TraceRequest(trace_ids=['trace1', 'trace2'])

        with self.assertRaises(ValueError) as context:
            self.service.add_examples('judge123', request)

        self.assertIn('No valid traces found', str(context.exception))

    @patch('server.services.labeling_service.mlflow')
    @patch('server.services.judge_service.judge_service')
    @patch.object(LabelingService, '_get_labeling_session')
    def test_get_examples_success(self, mock_get_session, mock_judge_service, mock_mlflow):
        """Test successful retrieval of examples."""
        mock_judge_service.get_judge.return_value = self.mock_judge_response

        mock_session = Mock()
        mock_session.mlflow_run_id = 'run123'
        mock_session.url = 'https://test.com/session'
        mock_get_session.return_value = mock_session

        # Mock search results
        mock_search_result = {'trace': ['{"trace_id": "trace1"}', '{"trace_id": "trace2"}']}
        mock_mlflow.search_traces.return_value = mock_search_result

        # Mock Trace.from_json
        mock_trace1 = Mock()
        mock_trace2 = Mock()
        with patch(
            'server.services.labeling_service.mlflow.entities.Trace.from_json',
            side_effect=[mock_trace1, mock_trace2],
        ):
            result = self.service.get_examples('judge123')

        # Verify calls
        mock_mlflow.set_experiment.assert_called_once_with(experiment_id='exp456')
        mock_mlflow.search_traces.assert_called_once_with(
            experiment_ids=['exp456'], filter_string='run_id = "run123"', max_results=1000
        )

        self.assertEqual(len(result), 2)

    @patch('server.services.judge_service.judge_service')
    def test_get_examples_judge_not_found(self, mock_judge_service):
        """Test get examples with nonexistent judge."""
        mock_judge_service.get_judge.return_value = None

        with self.assertRaises(ValueError) as context:
            self.service.get_examples('nonexistent')

        self.assertIn('Judge with ID nonexistent not found', str(context.exception))

    @patch('server.services.labeling_service.mlflow')
    @patch('server.services.judge_service.judge_service')
    @patch.object(LabelingService, '_get_labeling_session')
    def test_get_examples_no_session(self, mock_get_session, mock_judge_service, mock_mlflow):
        """Test get examples when no labeling session exists."""
        mock_judge_service.get_judge.return_value = self.mock_judge_response
        mock_get_session.return_value = None

        result = self.service.get_examples('judge123')

        self.assertEqual(result, [])
        mock_mlflow.set_experiment.assert_called_once_with(experiment_id='exp456')

    @patch('server.services.labeling_service.mlflow')
    @patch('server.services.judge_service.judge_service')
    @patch.object(LabelingService, '_get_labeling_session')
    @patch.object(LabelingService, '_get_session_counts')
    def test_get_labeling_progress_success(
        self, mock_get_counts, mock_get_session, mock_judge_service, mock_mlflow
    ):
        """Test successful labeling progress retrieval."""
        mock_judge_service.get_judge.return_value = self.mock_judge_response

        mock_session = Mock()
        mock_session.mlflow_run_id = 'run123'
        mock_session.url = 'https://databricks.com/labeling/123'
        mock_get_session.return_value = mock_session

        mock_get_counts.return_value = (10, 6)  # total_examples, labeled_examples

        result = self.service.get_labeling_progress('judge123')

        # Verify calls
        mock_judge_service.get_judge.assert_called_once_with('judge123')
        mock_mlflow.set_experiment.assert_called_once_with(experiment_id='exp456')
        mock_get_session.assert_called_once_with('judge123')
        mock_get_counts.assert_called_once_with(mock_session, 'exp456')

        # Verify result
        self.assertIsInstance(result, LabelingProgress)
        self.assertEqual(result.total_examples, 10)
        self.assertEqual(result.labeled_examples, 6)
        self.assertEqual(result.used_for_alignment, 0)
        self.assertEqual(result.labeling_session_url, 'https://databricks.com/labeling/123')

    @patch('server.services.judge_service.judge_service')
    def test_get_labeling_progress_judge_not_found(self, mock_judge_service):
        """Test labeling progress when judge is not found."""
        mock_judge_service.get_judge.return_value = None

        result = self.service.get_labeling_progress('nonexistent')

        # Should return empty progress
        self.assertEqual(result.total_examples, 0)
        self.assertEqual(result.labeled_examples, 0)
        self.assertEqual(result.used_for_alignment, 0)
        self.assertIsNone(result.labeling_session_url)

    @patch('server.services.labeling_service.mlflow')
    @patch('server.services.judge_service.judge_service')
    @patch.object(LabelingService, '_get_labeling_session')
    def test_get_labeling_progress_no_session(
        self, mock_get_session, mock_judge_service, mock_mlflow
    ):
        """Test labeling progress when no session exists."""
        mock_judge_service.get_judge.return_value = self.mock_judge_response
        mock_get_session.return_value = None

        result = self.service.get_labeling_progress('judge123')

        # Should return empty progress
        self.assertEqual(result.total_examples, 0)
        self.assertEqual(result.labeled_examples, 0)
        self.assertEqual(result.used_for_alignment, 0)
        self.assertIsNone(result.labeling_session_url)

    def test_get_session_counts_success(self):
        """Test _get_session_counts method."""
        with patch(
            'databricks.rag_eval.clients.managedevals.managed_evals_client.ManagedEvalsClient'
        ) as mock_client_class:
            # Mock the client and items
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock items with different states
            mock_item1 = Mock()
            mock_item1.state = 'COMPLETED'
            mock_item2 = Mock()
            mock_item2.state = 'IN_PROGRESS'
            mock_item3 = Mock()
            mock_item3.state = 'COMPLETED'
            mock_item4 = Mock()
            mock_item4.state = 'NOT_STARTED'

            mock_client.list_items_in_labeling_session.return_value = [
                mock_item1,
                mock_item2,
                mock_item3,
                mock_item4,
            ]

            mock_session = Mock()
            total_examples, labeled_examples = self.service._get_session_counts(
                mock_session, 'exp123'
            )

            # Verify managed evals client call
            mock_client.list_items_in_labeling_session.assert_called_once_with(mock_session)

            # Verify results: 4 total items, 2 completed items
            self.assertEqual(total_examples, 4)
            self.assertEqual(labeled_examples, 2)

    def test_get_session_counts_error(self):
        """Test _get_session_counts with managed evals client error."""
        # This will fail to import databricks.rag_eval.clients.managedevals in test environment
        mock_session = Mock()
        total_examples, labeled_examples = self.service._get_session_counts(mock_session, 'exp123')

        # Should return (0, 0) on error
        self.assertEqual(total_examples, 0)
        self.assertEqual(labeled_examples, 0)

    @patch('server.services.labeling_service.extract_categorical_options_from_instruction')
    @patch('server.services.labeling_service.mlflow')
    @patch('server.services.labeling_service.schemas')
    @patch('server.services.labeling_service.labeling')
    @patch('server.services.judge_service.judge_service')
    def test_create_labeling_session_dynamic_schema_pass_fail(
        self, mock_judge_service, mock_labeling, mock_schemas, mock_mlflow, mock_extract_options
    ):
        """Test labeling session creation with dynamic pass/fail schema."""
        # Set up judge with pass/fail instruction
        judge_with_pass_fail = JudgeResponse(
            id='judge123',
            name='Pass/Fail Judge',
            instruction='Return pass if relevant, fail if not relevant.',
            experiment_id='exp456',
            version=1,
        )
        mock_judge_service.get_judge.return_value = judge_with_pass_fail

        # Mock options extraction
        mock_extract_options.return_value = ['Pass', 'Fail']

        mock_session = Mock()
        mock_session.mlflow_run_id = 'run123'
        mock_session.url = 'https://test.com/session'
        mock_labeling.create_labeling_session.return_value = mock_session

        request = CreateLabelingSessionRequest(trace_ids=['trace1'], sme_emails=['user@test.com'])

        self.service.create_labeling_session('judge123', request)

        # Verify options extraction was called with judge instruction
        mock_extract_options.assert_called_once_with(judge_with_pass_fail.instruction)

        # Verify categorical schema was used
        schema_call = mock_schemas.create_label_schema.call_args
        input_schema = schema_call.kwargs['input']
        from mlflow.genai.label_schemas import InputCategorical
        self.assertIsInstance(input_schema, InputCategorical)
        self.assertEqual(input_schema.options, ['Pass', 'Fail'])

    @patch('server.services.labeling_service.extract_categorical_options_from_instruction')
    @patch('server.services.labeling_service.mlflow')
    @patch('server.services.labeling_service.schemas')
    @patch('server.services.labeling_service.labeling')
    @patch('server.services.judge_service.judge_service')
    def test_create_labeling_session_dynamic_schema_multi_option(
        self, mock_judge_service, mock_labeling, mock_schemas, mock_mlflow, mock_extract_options
    ):
        """Test labeling session creation with multi-option categorical schema."""
        # Set up judge with multi-option instruction
        judge_with_multi = JudgeResponse(
            id='judge123',
            name='Rating Judge',
            instruction='Rate as poor, fair, good, or excellent.',
            experiment_id='exp456',
            version=1,
        )
        mock_judge_service.get_judge.return_value = judge_with_multi

        # Mock options extraction to return multi-categorical
        mock_extract_options.return_value = ['Poor', 'Fair', 'Good', 'Excellent']

        mock_session = Mock()
        mock_session.mlflow_run_id = 'run123'
        mock_session.url = 'https://test.com/session'
        mock_labeling.create_labeling_session.return_value = mock_session

        request = CreateLabelingSessionRequest(trace_ids=['trace1'], sme_emails=['user@test.com'])

        self.service.create_labeling_session('judge123', request)

        # Verify options extraction was called
        mock_extract_options.assert_called_once_with(judge_with_multi.instruction)

        # Verify categorical schema was used with correct options
        schema_call = mock_schemas.create_label_schema.call_args
        input_schema = schema_call.kwargs['input']
        from mlflow.genai.label_schemas import InputCategorical
        self.assertIsInstance(input_schema, InputCategorical)
        self.assertEqual(input_schema.options, ['Poor', 'Fair', 'Good', 'Excellent'])

    @patch('server.services.labeling_service.extract_categorical_options_from_instruction')
    @patch('server.services.labeling_service.mlflow')
    @patch('server.services.labeling_service.schemas')
    @patch('server.services.labeling_service.labeling')
    @patch('server.services.judge_service.judge_service')
    def test_create_labeling_session_schema_analysis_failure(
        self, mock_judge_service, mock_labeling, mock_schemas, mock_mlflow, mock_extract_options
    ):
        """Test labeling session creation when schema analysis fails."""
        mock_judge_service.get_judge.return_value = self.mock_judge_response

        # Mock schema analysis failure
        mock_extract_options.side_effect = Exception('Schema analysis failed')

        mock_session = Mock()
        mock_session.mlflow_run_id = 'run123'
        mock_session.url = 'https://test.com/session'
        mock_labeling.create_labeling_session.return_value = mock_session

        request = CreateLabelingSessionRequest(trace_ids=['trace1'], sme_emails=['user@test.com'])

        # Should not raise exception, should use fallback
        result = self.service.create_labeling_session('judge123', request)

        # Verify it still creates a session
        self.assertIsInstance(result, CreateLabelingSessionResponse)

        # Verify fallback schema was used (InputCategorical with Pass/Fail)
        schema_call = mock_schemas.create_label_schema.call_args
        input_schema = schema_call.kwargs['input']
        from mlflow.genai.label_schemas import InputCategorical
        self.assertIsInstance(input_schema, InputCategorical)
        self.assertEqual(input_schema.options, ['Pass', 'Fail'])


if __name__ == '__main__':
    unittest.main()
