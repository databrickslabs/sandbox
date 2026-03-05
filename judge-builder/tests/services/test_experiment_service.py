"""Unit tests for ExperimentService with mocked MLflow calls."""

import unittest
from unittest import TestCase
from unittest.mock import Mock, patch

from mlflow.entities import Experiment, ViewType

from server.services.experiment_service import ExperimentService


class TestExperimentService(TestCase):
    """Test cases for ExperimentService class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.service = ExperimentService()

    @patch('server.services.experiment_service.mlflow')
    def test_list_experiments_basic(self, mock_mlflow):
        """Test basic experiment listing."""
        # Mock experiment objects
        mock_exp1 = Mock(spec=Experiment)
        mock_exp1.experiment_id = 'exp1'
        mock_exp1.name = 'Experiment 1'

        mock_exp2 = Mock(spec=Experiment)
        mock_exp2.experiment_id = 'exp2'
        mock_exp2.name = 'Experiment 2'

        mock_mlflow.search_experiments.return_value = [mock_exp1, mock_exp2]

        result = self.service.list_experiments()

        # Verify MLflow call
        mock_mlflow.search_experiments.assert_called_once_with(
            view_type=ViewType.ACTIVE_ONLY,
            filter_string=None,
            order_by=['last_update_time DESC'],
            max_results=100,
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].experiment_id, 'exp1')
        self.assertEqual(result[1].experiment_id, 'exp2')

    @patch('server.services.experiment_service.mlflow')
    def test_list_experiments_with_filter(self, mock_mlflow):
        """Test experiment listing with filter string."""
        mock_exp = Mock(spec=Experiment)
        mock_exp.experiment_id = 'filtered_exp'
        mock_exp.name = 'Filtered Experiment'

        mock_mlflow.search_experiments.return_value = [mock_exp]

        filter_string = "name LIKE '%test%'"
        result = self.service.list_experiments(filter_string=filter_string)

        mock_mlflow.search_experiments.assert_called_once_with(
            view_type=ViewType.ACTIVE_ONLY,
            filter_string=filter_string,
            order_by=['last_update_time DESC'],
            max_results=100,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].experiment_id, 'filtered_exp')

    @patch('server.services.experiment_service.mlflow')
    def test_list_experiments_custom_max_results(self, mock_mlflow):
        """Test experiment listing with custom max_results."""
        mock_mlflow.search_experiments.return_value = []

        self.service.list_experiments(max_results=50)

        mock_mlflow.search_experiments.assert_called_once_with(
            view_type=ViewType.ACTIVE_ONLY,
            filter_string=None,
            order_by=['last_update_time DESC'],
            max_results=50,
        )

    @patch('server.services.experiment_service.mlflow')
    def test_list_experiments_empty_result(self, mock_mlflow):
        """Test experiment listing when no experiments exist."""
        mock_mlflow.search_experiments.return_value = []

        result = self.service.list_experiments()

        self.assertEqual(result, [])

    def test_get_experiment_basic(self):
        """Test getting a single experiment by ID."""
        # Mock the client
        mock_experiment = Mock(spec=Experiment)
        mock_experiment.experiment_id = 'exp123'
        mock_experiment.name = 'Test Experiment'

        self.service.client = Mock()
        self.service.client.get_experiment.return_value = mock_experiment

        result = self.service.get_experiment('exp123')

        self.service.client.get_experiment.assert_called_once_with('exp123')
        self.assertEqual(result.experiment_id, 'exp123')
        self.assertEqual(result.name, 'Test Experiment')

    def test_get_experiment_client_error(self):
        """Test get experiment when client raises an error."""
        self.service.client = Mock()
        self.service.client.get_experiment.side_effect = Exception('Experiment not found')

        with self.assertRaises(Exception) as context:
            self.service.get_experiment('nonexistent')

        self.assertIn('Experiment not found', str(context.exception))

    @patch('server.services.experiment_service.mlflow')
    def test_get_experiment_traces_basic(self, mock_mlflow):
        """Test getting traces from an experiment."""
        mock_traces = {
            'trace': [
                {'trace_id': 'trace1', 'request': 'Question 1'},
                {'trace_id': 'trace2', 'request': 'Question 2'},
            ]
        }
        mock_mlflow.search_traces.return_value = mock_traces

        result = self.service.get_experiment_traces('exp123')

        mock_mlflow.search_traces.assert_called_once_with(experiment_ids=['exp123'])

        self.assertEqual(result, mock_traces)

    @patch('server.services.experiment_service.mlflow')
    def test_get_experiment_traces_with_run_id(self, mock_mlflow):
        """Test getting traces from an experiment filtered by run ID."""
        mock_traces = {'trace': [{'trace_id': 'trace1', 'run_id': 'run123'}]}
        mock_mlflow.search_traces.return_value = mock_traces

        result = self.service.get_experiment_traces('exp123', run_id='run123')

        mock_mlflow.search_traces.assert_called_once_with(
            experiment_ids=['exp123'], run_id='run123'
        )

        self.assertEqual(result, mock_traces)

    @patch('server.services.experiment_service.mlflow')
    def test_get_experiment_traces_empty_result(self, mock_mlflow):
        """Test getting traces when no traces exist."""
        mock_mlflow.search_traces.return_value = {'trace': []}

        result = self.service.get_experiment_traces('exp123')

        self.assertEqual(result['trace'], [])

    @patch('server.services.experiment_service.mlflow')
    def test_get_experiment_traces_mlflow_error(self, mock_mlflow):
        """Test get experiment traces when MLflow raises an error."""
        mock_mlflow.search_traces.side_effect = Exception('MLflow connection error')

        with self.assertRaises(Exception) as context:
            self.service.get_experiment_traces('exp123')

        self.assertIn('MLflow connection error', str(context.exception))

    @patch('server.services.experiment_service.mlflow')
    def test_list_experiments_with_all_parameters(self, mock_mlflow):
        """Test experiment listing with all optional parameters."""
        mock_exp = Mock(spec=Experiment)
        mock_exp.experiment_id = 'exp_all_params'
        mock_exp.name = 'All Parameters Experiment'

        mock_mlflow.search_experiments.return_value = [mock_exp]

        result = self.service.list_experiments(filter_string="name LIKE '%param%'", max_results=25)

        mock_mlflow.search_experiments.assert_called_once_with(
            view_type=ViewType.ACTIVE_ONLY,
            filter_string="name LIKE '%param%'",
            order_by=['last_update_time DESC'],
            max_results=25,
        )

        self.assertEqual(len(result), 1)

    def test_experiment_service_inheritance(self):
        """Test that ExperimentService properly inherits from BaseService."""
        # Should have BaseService properties and methods
        self.assertTrue(hasattr(self.service, 'client'))

        # Should be an instance of both ExperimentService and BaseService
        from server.services.base_service import BaseService

        self.assertIsInstance(self.service, BaseService)
        self.assertIsInstance(self.service, ExperimentService)

    @patch('server.services.experiment_service.mlflow')
    def test_search_experiments_order_by_parameter(self, mock_mlflow):
        """Test that search_experiments uses correct order_by parameter."""
        mock_mlflow.search_experiments.return_value = []

        self.service.list_experiments()

        call_args = mock_mlflow.search_experiments.call_args
        self.assertIn('order_by', call_args.kwargs)
        self.assertEqual(call_args.kwargs['order_by'], ['last_update_time DESC'])

    @patch('server.services.experiment_service.mlflow')
    def test_search_experiments_view_type_active_only(self, mock_mlflow):
        """Test that search_experiments uses ViewType.ACTIVE_ONLY."""
        mock_mlflow.search_experiments.return_value = []

        self.service.list_experiments()

        call_args = mock_mlflow.search_experiments.call_args
        self.assertIn('view_type', call_args.kwargs)
        self.assertEqual(call_args.kwargs['view_type'], ViewType.ACTIVE_ONLY)

    @patch('server.services.experiment_service.mlflow')
    def test_get_experiment_traces_parameter_construction(self, mock_mlflow):
        """Test that get_experiment_traces constructs parameters correctly."""
        mock_mlflow.search_traces.return_value = {'trace': []}

        # Test without run_id
        self.service.get_experiment_traces('exp123')

        call_args = mock_mlflow.search_traces.call_args
        expected_params = {'experiment_ids': ['exp123']}
        self.assertEqual(call_args.kwargs, expected_params)

        # Reset mock
        mock_mlflow.search_traces.reset_mock()

        # Test with run_id
        self.service.get_experiment_traces('exp123', run_id='run456')

        call_args = mock_mlflow.search_traces.call_args
        expected_params = {'experiment_ids': ['exp123'], 'run_id': 'run456'}
        self.assertEqual(call_args.kwargs, expected_params)


if __name__ == '__main__':
    unittest.main()
