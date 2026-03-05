"""Experiment service for MLflow integration."""

import logging
from typing import List, Optional

import mlflow
from mlflow.entities import Experiment, ViewType

from server.models import TraceExample
from server.utils.parsing_utils import extract_text_from_data

from .base_service import BaseService

logger = logging.getLogger(__name__)


class ExperimentService(BaseService):
    """Experiment and trace operations."""

    def list_experiments(
        self, filter_string: Optional[str] = None, max_results: int = 100
    ) -> List[Experiment]:
        """List active MLflow experiments."""
        return mlflow.search_experiments(
            view_type=ViewType.ACTIVE_ONLY,
            filter_string=filter_string,
            order_by=['last_update_time DESC'],
            max_results=max_results,
        )

    def get_experiment(self, experiment_id: str) -> Experiment:
        """Get experiment by ID."""
        return self.client.get_experiment(experiment_id)

    def get_experiment_traces(self, experiment_id: str, run_id: Optional[str] = None, max_results: int = 1000):
        """Get traces from MLflow experiment."""
        search_params = {'experiment_ids': [experiment_id], 'max_results': max_results}
        if run_id:
            search_params['run_id'] = run_id

        traces_df = mlflow.search_traces(**search_params)

        trace_examples = []
        for _, row in traces_df.iterrows():
            trace_examples.append(
                TraceExample(
                    trace_id=row['trace_id'],
                    request=extract_text_from_data(row['request'], 'request'),
                    response=extract_text_from_data(row['response'], 'response'),
                    assessments=row.get('assessments', [])
                )
            )

        logger.debug(f'Retrieved {len(trace_examples)} traces from experiment {experiment_id}')
        return trace_examples


# Global service instance
experiment_service = ExperimentService()
