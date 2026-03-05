"""Unit tests for cache service."""

import hashlib
from unittest.mock import Mock, patch

import pytest

from server.services.cache_service import CacheService


@pytest.fixture
def cache_service():
    """Create a cache service instance for testing."""
    return CacheService()


@pytest.fixture
def mock_trace():
    """Create a mock trace object."""
    trace = Mock()
    trace.info.trace_id = 'trace-123'
    trace.data.request = {'request': 'test request'}
    trace.data.response = {'response': 'test response'}
    return trace


class TestCacheService:
    """Test cases for CacheService."""

    def test_compute_dataset_version(self, cache_service):
        """Test dataset version computation."""
        trace_ids = ['trace-1', 'trace-2', 'trace-3']
        expected_hash = hashlib.sha256(''.join(sorted(trace_ids)).encode()).hexdigest()[:8]

        result = cache_service.compute_dataset_version(trace_ids)

        assert result == expected_hash

    def test_compute_dataset_version_empty_list(self, cache_service):
        """Test dataset version computation with empty list."""
        trace_ids = []
        expected_hash = hashlib.sha256(''.encode()).hexdigest()[:8]

        result = cache_service.compute_dataset_version(trace_ids)

        assert result == expected_hash

    def test_compute_dataset_version_order_independent(self, cache_service):
        """Test that dataset version is independent of trace ID order."""
        trace_ids_1 = ['trace-1', 'trace-2', 'trace-3']
        trace_ids_2 = ['trace-3', 'trace-1', 'trace-2']

        result_1 = cache_service.compute_dataset_version(trace_ids_1)
        result_2 = cache_service.compute_dataset_version(trace_ids_2)

        assert result_1 == result_2

    def test_cache_evaluation_run_id(self, cache_service):
        """Test caching evaluation run ID."""
        judge_id = 'judge-123'
        judge_version = 1
        trace_ids = ['trace-1', 'trace-2']
        run_id = 'run-123'

        cache_service.cache_evaluation_run_id(judge_id, judge_version, trace_ids, run_id)

        # Check that the run ID was cached
        dataset_version = cache_service.compute_dataset_version(trace_ids)
        cache_key = f'{judge_id}:{judge_version}:{dataset_version}'
        assert cache_service.evaluation_cache[cache_key] == run_id

    def test_get_evaluation_run_id_cache_hit(self, cache_service):
        """Test getting evaluation run ID from cache."""
        judge_id = 'judge-123'
        judge_version = 1
        trace_ids = ['trace-1', 'trace-2']
        run_id = 'run-123'

        # First cache the run ID
        cache_service.cache_evaluation_run_id(judge_id, judge_version, trace_ids, run_id)

        # Then retrieve it
        result = cache_service.get_evaluation_run_id(judge_id, judge_version, trace_ids)

        assert result == run_id

    def test_get_evaluation_run_id_cache_miss_no_experiment(self, cache_service):
        """Test getting evaluation run ID with cache miss and no experiment ID."""
        judge_id = 'judge-123'
        judge_version = 1
        trace_ids = ['trace-1', 'trace-2']

        result = cache_service.get_evaluation_run_id(judge_id, judge_version, trace_ids)

        assert result is None

    @patch('server.services.cache_service.cache_service.find_evaluation_run')
    def test_get_evaluation_run_id_cache_miss_with_experiment(self, mock_find, cache_service):
        """Test getting evaluation run ID with cache miss but experiment ID provided."""
        judge_id = 'judge-123'
        judge_version = 1
        trace_ids = ['trace-1', 'trace-2']
        experiment_id = 'exp-123'
        mock_find.return_value = 'found-run-123'

        result = cache_service.get_evaluation_run_id(judge_id, judge_version, trace_ids, experiment_id)

        assert result == 'found-run-123'
        mock_find.assert_called_once()

    def test_cache_trace(self, cache_service, mock_trace):
        """Test caching a trace."""
        cache_service.cache_trace(mock_trace)

        cached_trace = cache_service.trace_cache['trace-123']
        assert cached_trace == mock_trace

    def test_get_trace_cache_hit(self, cache_service, mock_trace):
        """Test getting trace from cache."""
        # First cache the trace
        cache_service.cache_trace(mock_trace)

        # Then retrieve it
        result = cache_service.get_trace('trace-123')

        assert result == mock_trace

    @patch('server.services.cache_service.mlflow.get_trace')
    def test_get_trace_cache_miss(self, mock_mlflow_get, cache_service, mock_trace):
        """Test getting trace with cache miss."""
        mock_mlflow_get.return_value = mock_trace

        result = cache_service.get_trace('trace-123')

        assert result == mock_trace
        mock_mlflow_get.assert_called_once_with('trace-123')
        # Should also be cached now
        assert cache_service.trace_cache['trace-123'] == mock_trace

    @patch('server.services.cache_service.mlflow.get_trace')
    def test_get_trace_mlflow_error(self, mock_mlflow_get, cache_service):
        """Test getting trace when MLflow raises exception."""
        mock_mlflow_get.side_effect = Exception('MLflow error')

        result = cache_service.get_trace('trace-123')

        assert result is None

    @patch('server.services.cache_service.mlflow.search_runs')
    def test_find_evaluation_run_found(self, mock_search_runs, cache_service):
        """Test finding evaluation run in MLflow."""
        judge_id = 'judge-123'
        judge_version = 1
        experiment_id = 'exp-123'
        dataset_version = 'abc123'

        # Mock MLflow response
        mock_run = Mock()
        mock_run.info.run_id = 'found-run-123'
        mock_search_runs.return_value = [mock_run]

        result = cache_service.find_evaluation_run(judge_id, judge_version, experiment_id, dataset_version)

        assert result == 'found-run-123'
        mock_search_runs.assert_called_once()

        # Should also cache the result
        cache_key = f'{judge_id}:{judge_version}:{dataset_version}'
        assert cache_service.evaluation_cache[cache_key] == 'found-run-123'

    @patch('server.services.cache_service.mlflow.search_runs')
    def test_find_evaluation_run_not_found(self, mock_search_runs, cache_service):
        """Test finding evaluation run when not found in MLflow."""
        mock_search_runs.return_value = []

        result = cache_service.find_evaluation_run('judge-123', 1, 'exp-123', 'abc123')

        assert result is None

    @patch('server.services.cache_service.mlflow.search_runs')
    def test_find_evaluation_run_mlflow_error(self, mock_search_runs, cache_service):
        """Test finding evaluation run when MLflow raises exception."""
        mock_search_runs.side_effect = Exception('MLflow error')

        result = cache_service.find_evaluation_run('judge-123', 1, 'exp-123', 'abc123')

        assert result is None

    def test_ttl_expiration(self, cache_service):
        """Test that cache entries expire after TTL."""
        import time

        # Set a very short TTL for testing
        original_ttl = cache_service.trace_cache_ttl
        cache_service.trace_cache_ttl = 0.1  # 100ms

        try:
            # Cache a trace
            mock_trace = Mock()
            mock_trace.info.trace_id = 'trace-123'
            cache_service.cache_trace(mock_trace)

            # Should be in cache immediately
            assert 'trace-123' in cache_service.trace_cache

            # Wait for TTL to expire
            time.sleep(0.2)

            # Should be removed after cleanup
            cache_service._cleanup_expired_traces()
            assert 'trace-123' not in cache_service.trace_cache

        finally:
            # Restore original TTL
            cache_service.trace_cache_ttl = original_ttl

    def test_cleanup_expired_traces(self, cache_service):
        """Test cleanup of expired traces."""
        import time

        # Set a very short TTL
        original_ttl = cache_service.trace_cache_ttl
        cache_service.trace_cache_ttl = 0.1

        try:
            # Add multiple traces
            for i in range(3):
                mock_trace = Mock()
                mock_trace.info.trace_id = f'trace-{i}'
                cache_service.cache_trace(mock_trace)

            assert len(cache_service.trace_cache) == 3

            # Wait for expiration
            time.sleep(0.2)

            # Add one more trace (should not be expired)
            fresh_trace = Mock()
            fresh_trace.info.trace_id = 'fresh-trace'
            cache_service.cache_trace(fresh_trace)

            # Cleanup
            cache_service._cleanup_expired_traces()

            # Only the fresh trace should remain
            assert len(cache_service.trace_cache) == 1
            assert 'fresh-trace' in cache_service.trace_cache

        finally:
            cache_service.trace_cache_ttl = original_ttl
