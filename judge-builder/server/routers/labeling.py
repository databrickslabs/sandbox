"""Labeling API router."""

import logging
import traceback

from fastapi import APIRouter, HTTPException

from server.models import (
    CreateLabelingSessionRequest,
    CreateLabelingSessionResponse,
    LabelingProgress,
    TraceRequest,
)
from server.services.labeling_service import labeling_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post('/{judge_id}/examples')
async def add_examples(judge_id: str, request: TraceRequest):
    """Add examples to a judge."""
    try:
        traces = labeling_service.add_examples(judge_id, request)
        return {'traces': traces, 'count': len(traces)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f'Request failed: {e}\n{traceback.format_exc()}')
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{judge_id}/examples')
async def get_examples(judge_id: str, include_judge_results: bool = False):
    """Get examples for a judge."""
    try:
        traces = labeling_service.get_examples(judge_id, include_judge_results=include_judge_results)
        return {'traces': traces, 'count': len(traces)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f'Request failed: {e}\n{traceback.format_exc()}')
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{judge_id}/labeling-progress', response_model=LabelingProgress)
async def get_labeling_progress(judge_id: str):
    """Get labeling progress for a judge."""
    try:
        return labeling_service.get_labeling_progress(judge_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f'Request failed: {e}\n{traceback.format_exc()}')
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/{judge_id}/labeling', response_model=CreateLabelingSessionResponse)
async def create_labeling_session(judge_id: str, request: CreateLabelingSessionRequest):
    """Create a new labeling session for a judge."""
    try:
        return labeling_service.create_labeling_session(judge_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        logger.error(f'Request failed: {e}\n{traceback.format_exc()}')
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{judge_id}/labeling')
async def get_labeling_session(judge_id: str):
    """Get the labeling session for a judge."""
    try:
        session = labeling_service.get_labeling_session(judge_id)
        if not session:
            raise HTTPException(status_code=404, detail='No labeling session found for this judge')
        return {
            'session_id': session.mlflow_run_id,
            'session_name': session.name,
            'labeling_url': getattr(session, 'url', None),
            'assigned_users': getattr(session, 'assigned_users', []),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f'Request failed: {e}\n{traceback.format_exc()}')
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/{judge_id}/labeling')
async def delete_labeling_session(judge_id: str):
    """Delete the labeling session for a judge."""
    try:
        success = labeling_service.delete_labeling_session(judge_id)
        if not success:
            raise HTTPException(status_code=404, detail='Labeling session not found')
        return {'message': 'Labeling session deleted successfully'}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            f'Failed to delete labeling session for judge {judge_id}: {e}\n{traceback.format_exc()}'
        )
        raise HTTPException(status_code=500, detail=str(e))
