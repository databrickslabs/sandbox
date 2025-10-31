"""Experiments API router."""

import logging
import traceback

from fastapi import APIRouter, HTTPException

# from server.models import ExperimentInfo  # Using MLflow entities directly
from server.services.experiment_service import experiment_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get('/')
async def list_experiments():
    """List available MLflow experiments."""
    try:
        return experiment_service.list_experiments()
    except Exception as e:
        logger.error(f'Failed to list experiments: {e}\n{traceback.format_exc()}')
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{experiment_id}')
async def get_experiment(experiment_id: str):
    """Get experiment by ID."""
    try:
        return experiment_service.get_experiment(experiment_id)
    except ValueError as e:
        logger.error(f'Experiment not found {experiment_id}: {e}\n{traceback.format_exc()}')
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f'Failed to get experiment {experiment_id}: {e}\n{traceback.format_exc()}')
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{experiment_id}/traces')
async def get_experiment_traces(experiment_id: str, run_id: str = None):
    """Get traces from experiment."""
    try:
        traces = experiment_service.get_experiment_traces(experiment_id, run_id)
        return {'traces': traces, 'count': len(traces)}
    except ValueError as e:
        logger.error(
            f'Failed to get traces for experiment {experiment_id}: {e}\n{traceback.format_exc()}'
        )
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            f'Failed to get traces for experiment {experiment_id}: {e}\n{traceback.format_exc()}'
        )
        raise HTTPException(status_code=500, detail=str(e))
