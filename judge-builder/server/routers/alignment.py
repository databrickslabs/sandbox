"""Alignment API router."""

import logging
import traceback

from fastapi import APIRouter, BackgroundTasks, HTTPException

from server.models import (
    AlignmentResponse,
    AlignmentStartResponse,
    AlignmentTaskStatus,
    EvaluationResult,
    TestJudgeRequest,
    TestJudgeResponse,
    TraceRequest,
)
from server.services.alignment_service import alignment_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Track alignment status for background tasks
alignment_status: dict[str, AlignmentTaskStatus] = {}


def run_alignment_background(judge_id: str):
    """Background task to run alignment."""
    try:
        logger.info(f'Background alignment started for judge {judge_id}')
        # Status is already set to 'running' by the endpoint handler

        result = alignment_service.run_alignment(judge_id)
        alignment_status[judge_id] = AlignmentTaskStatus.completed(result)

        logger.info(f'Background alignment completed for judge {judge_id}')
    except ValueError as e:
        tb = traceback.format_exc()
        logger.error(f'Alignment validation failed for judge {judge_id}: {e}\n{tb}')
        alignment_status[judge_id] = AlignmentTaskStatus.failed(
            error_type='not_found',
            error_message=str(e),
            error_traceback=tb
        )
    except RuntimeError as e:
        tb = traceback.format_exc()
        logger.error(f'Alignment optimization failed for judge {judge_id}: {e}\n{tb}')
        alignment_status[judge_id] = AlignmentTaskStatus.failed(
            error_type='optimization_failure',
            error_message=str(e),
            error_traceback=tb
        )
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f'Alignment failed for judge {judge_id}: {e}\n{tb}')
        alignment_status[judge_id] = AlignmentTaskStatus.failed(
            error_type='unknown',
            error_message=str(e),
            error_traceback=tb
        )


@router.post('/{judge_id}/align', response_model=AlignmentStartResponse)
async def run_alignment(judge_id: str, background_tasks: BackgroundTasks):
    """Run alignment for a judge in the background."""
    # Check if alignment is already running for this judge
    if judge_id in alignment_status and alignment_status[judge_id].status == 'running':
        raise HTTPException(status_code=409, detail='Alignment is already running for this judge')

    # Set initial running status so polling works immediately
    alignment_status[judge_id] = AlignmentTaskStatus.running()
    logger.info(f'Alignment task queued for judge {judge_id}')

    # Start alignment in background
    background_tasks.add_task(run_alignment_background, judge_id)

    # Return immediately with a status response
    return AlignmentStartResponse(
        judge_id=judge_id,
        success=True,
        message='Alignment started in background. Use the status endpoint to check progress.',
    )


@router.get('/{judge_id}/align-status')
async def get_alignment_status(judge_id: str):
    """Get the status of a background alignment task."""
    if judge_id not in alignment_status:
        raise HTTPException(status_code=404, detail='No alignment task found for this judge')

    status_info = alignment_status[judge_id]

    if status_info.status == 'completed':
        # Clear the status after returning the result
        result = status_info.result
        del alignment_status[judge_id]
        return {'status': 'completed', 'result': result}
    elif status_info.status == 'failed':
        # Clear the status after returning the error
        error_type = status_info.error_type
        error_message = status_info.error_message
        del alignment_status[judge_id]

        # Return appropriate HTTP error based on error type
        if error_type == 'not_found':
            raise HTTPException(status_code=404, detail=error_message)
        elif error_type == 'optimization_failure':
            raise HTTPException(status_code=422, detail=error_message)
        else:
            raise HTTPException(status_code=500, detail=error_message)
    else:
        return {'status': 'running'}


@router.post('/{judge_id}/evaluate', response_model=EvaluationResult)
async def evaluate_judge(judge_id: str, request: TraceRequest):
    """Run judge evaluation on traces and log to MLflow."""
    try:
        return alignment_service.evaluate_judge(judge_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f'Request failed: {e}\n{traceback.format_exc()}')
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/{judge_id}/test', response_model=TestJudgeResponse)
async def test_judge(judge_id: str, request: TestJudgeRequest):
    """Test judge on a single trace (for play buttons)."""
    try:
        return alignment_service.test_judge(judge_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f'Request failed: {e}\n{traceback.format_exc()}')
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{judge_id}/alignment-comparison')
async def get_alignment_comparison(judge_id: str):
    """Get alignment comparison data including metrics and confusion matrix."""
    try:
        return alignment_service.get_alignment_comparison(judge_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f'Request failed: {e}\n{traceback.format_exc()}')
        raise HTTPException(status_code=500, detail=str(e))
