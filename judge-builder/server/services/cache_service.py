"""Caching service to reduce MLflow service pressure."""

import hashlib
import logging
from typing import Any, Dict, List, Optional

import mlflow
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class CacheService:
    """Service for caching MLflow traces and evaluation results."""

    def __init__(self):
        # Cache for MLflow trace objects (trace_id -> trace)
        # TTL of 30 minutes for traces
        self.trace_cache: TTLCache = TTLCache(maxsize=1000, ttl=1800)

        # Cache for evaluation run IDs (cache_key -> mlflow_run_id)
        # TTL of 1 hour for evaluations
        self.evaluation_cache: TTLCache = TTLCache(maxsize=500, ttl=3600)

    def compute_dataset_version(self, trace_ids: List[str]) -> str:
        """Compute dataset version from trace IDs.

        Args:
            trace_ids: List of trace IDs

        Returns:
            8-character hash representing the dataset version
        """
        # Sort trace IDs alphabetically for consistent hashing
        sorted_trace_ids = sorted(trace_ids)

        # Create hash from sorted trace IDs
        hash_input = ''.join(sorted_trace_ids)
        hash_obj = hashlib.sha256(hash_input.encode())

        # Return first 8 characters of hex digest
        return hash_obj.hexdigest()[:8]

    def get_trace(self, trace_id: str) -> Optional[Any]:
        """Get trace from cache or fetch from MLflow.

        Args:
            trace_id: MLflow trace ID

        Returns:
            MLflow trace object or None if not found
        """
        # Check cache first
        if trace_id in self.trace_cache:
            logger.debug(f'Cache hit for trace {trace_id}')
            return self.trace_cache[trace_id]

        try:
            # Fetch from MLflow
            logger.debug(f'Cache miss for trace {trace_id}, fetching from MLflow')
            trace = mlflow.get_trace(trace_id)

            # Store in cache
            self.trace_cache[trace_id] = trace
            logger.debug(f'Cached trace {trace_id}')

            return trace
        except Exception as e:
            logger.warning(f'Failed to fetch trace {trace_id}: {e}')
            return None

    def get_traces(self, trace_ids: List[str]) -> List['mlflow.entities.Trace']:
        """Get multiple traces from cache or fetch from MLflow.

        Args:
            trace_ids: List of MLflow trace IDs

        Returns:
            List of MLflow trace objects (excludes any that couldn't be fetched)
        """
        traces = []
        for trace_id in trace_ids:
            trace = self.get_trace(trace_id)
            if trace:
                traces.append(trace)
            else:
                logger.warning(f'Could not fetch trace {trace_id} from cache')
        return traces

    def get_evaluation_run_id(
        self, judge_id: str, judge_version: int, trace_ids: List[str], experiment_id: Optional[str] = None
    ) -> Optional[str]:
        """Get cached evaluation run ID for judge and dataset.

        Args:
            judge_id: Judge identifier
            judge_version: Judge version
            trace_ids: List of trace IDs in dataset
            experiment_id: MLflow experiment ID (required for cache miss lookup)

        Returns:
            MLflow run ID if cached or found, None otherwise
        """
        dataset_version = self.compute_dataset_version(trace_ids)
        cache_key = f'{judge_id}:{judge_version}:{dataset_version}'

        if cache_key in self.evaluation_cache:
            run_id = self.evaluation_cache[cache_key]
            logger.debug(f'Cache hit for evaluation {cache_key}')
            return run_id

        logger.debug(f'Cache miss for evaluation {cache_key}')

        # If experiment_id provided, try to find the run in MLflow
        if experiment_id:
            run_id = self.find_evaluation_run(judge_id, judge_version, experiment_id, dataset_version)
            if run_id:
                logger.debug(f'Found evaluation run in MLflow: {run_id}')
                return run_id

        logger.debug(f'No evaluation run found for {cache_key}')
        return None

    def find_evaluation_run(self, judge_id: str, judge_version: int, experiment_id: str, dataset_version: str) -> Optional[str]:
        """Find existing evaluation run in MLflow by searching for runs with matching tags."""
        from server.utils.naming_utils import sanitize_judge_name

        try:
            # Method 1: Search for runs with judge tags
            runs = mlflow.search_runs(
                experiment_ids=[experiment_id],
                filter_string=f"tags.judge_id = '{judge_id}' and tags.judge_version = '{judge_version}' and tags.dataset_version = '{dataset_version}'",
                output_format='list'
            )

            if runs:
                run_id = runs[0].info.run_id
                # Cache the found run
                self.evaluation_cache[f'{judge_id}:{judge_version}:{dataset_version}'] = run_id
                return run_id

            # Method 2: Fallback - search by run name pattern if tag search fails
            # Get judge metadata to find judge name
            from server.services.judge_service import judge_service
            judge = judge_service.get_judge(judge_id)
            if not judge:
                return None

            sanitized_name = sanitize_judge_name(judge.name)
            run_name_pattern = f'evaluation_{sanitized_name}_v{judge_version}_{dataset_version}'

            # Search for runs by name pattern
            all_runs = mlflow.search_runs(
                experiment_ids=[experiment_id],
                output_format='list',
                max_results=100  # Limit to avoid performance issues
            )

            for run in all_runs:
                if run.info.run_name and run.info.run_name == run_name_pattern:
                    run_id = run.info.run_id
                    # Cache the found run
                    self.evaluation_cache[f'{judge_id}:{judge_version}:{dataset_version}'] = run_id
                    return run_id

            return None

        except Exception as e:
            logger.error(f'Failed to find evaluation run: {e}')
            return None

    def cache_evaluation_run_id(
        self, judge_id: str, judge_version: int, trace_ids: List[str], run_id: str
    ) -> None:
        """Cache evaluation run ID for judge and dataset.

        Args:
            judge_id: Judge identifier
            judge_version: Judge version
            trace_ids: List of trace IDs in dataset
            run_id: MLflow run ID to cache
        """
        dataset_version = self.compute_dataset_version(trace_ids)
        cache_key = f'{judge_id}:{judge_version}:{dataset_version}'

        self.evaluation_cache[cache_key] = run_id
        logger.debug(f'Cached evaluation {cache_key} (dataset with {len(trace_ids)} traces)')

    def invalidate_trace(self, trace_id: str) -> None:
        """Invalidate cached trace.

        Args:
            trace_id: Trace ID to invalidate
        """
        if trace_id in self.trace_cache:
            del self.trace_cache[trace_id]
            logger.debug(f'Invalidated trace cache for {trace_id}')

    def invalidate_traces(self, trace_ids: List[str]) -> None:
        """Invalidate multiple cached traces.

        Args:
            trace_ids: List of trace IDs to invalidate
        """
        invalidated_count = 0
        for trace_id in trace_ids:
            if trace_id in self.trace_cache:
                del self.trace_cache[trace_id]
                invalidated_count += 1

        logger.debug(f'Invalidated {invalidated_count} traces from cache')

    def invalidate_judge_evaluations(self, judge_id: str) -> None:
        """Invalidate all cached evaluations for a judge.

        Args:
            judge_id: Judge ID to invalidate evaluations for
        """
        keys_to_remove = [
            key for key in self.evaluation_cache.keys() if key.startswith(f'{judge_id}:')
        ]

        for key in keys_to_remove:
            del self.evaluation_cache[key]
            logger.debug(f'Invalidated evaluation cache for {key}')

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics
        """
        return {
            'trace_cache': {
                'size': len(self.trace_cache),
                'maxsize': self.trace_cache.maxsize,
                'ttl': self.trace_cache.ttl,
                'hits': getattr(self.trace_cache, 'hits', 0),
                'misses': getattr(self.trace_cache, 'misses', 0),
            },
            'evaluation_cache': {
                'size': len(self.evaluation_cache),
                'maxsize': self.evaluation_cache.maxsize,
                'ttl': self.evaluation_cache.ttl,
                'hits': getattr(self.evaluation_cache, 'hits', 0),
                'misses': getattr(self.evaluation_cache, 'misses', 0),
            },
        }


# Global cache service instance
cache_service = CacheService()
