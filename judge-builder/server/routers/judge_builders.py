"""Judge Builders API router."""

import logging
import traceback
from typing import List

from fastapi import APIRouter, HTTPException

from server.models import (
    JudgeCreateRequest,
    JudgeResponse,
)
from server.services.judge_builder_service import judge_builder_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get('/', response_model=List[JudgeResponse])
async def list_judge_builders():
    """List all judge builders."""
    try:
        return judge_builder_service.list_judge_builders()
    except Exception as e:
        logger.error(f'Failed to list judge builders: {e}\n{traceback.format_exc()}')
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/', response_model=JudgeResponse)
async def create_judge_builder(request: JudgeCreateRequest):
    """Create a new judge builder."""
    try:
        logger.info(f'Creating judge builder: {request.name}')
        return judge_builder_service.create_judge_builder(request)
    except Exception as e:
        logger.error(f'Failed to create judge builder: {e}\n{traceback.format_exc()}')
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{judge_id}', response_model=JudgeResponse)
async def get_judge_builder(judge_id: str):
    """Get a judge builder by ID."""
    judge = judge_builder_service.get_judge_builder(judge_id)
    if not judge:
        raise HTTPException(status_code=404, detail='Judge builder not found')
    return judge


@router.delete('/{judge_id}')
async def delete_judge_builder(judge_id: str):
    """Delete a judge builder."""
    try:
        deletion_success, warnings = judge_builder_service.delete_judge_builder(judge_id)

        # Always return success so frontend refreshes the judge list
        # Surface warnings as different message types
        if deletion_success and not warnings:
            return {'message': 'Judge builder deleted successfully', 'refresh_needed': False}
        elif deletion_success and warnings:
            return {
                'message': 'Judge builder deleted with some cleanup issues',
                'refresh_needed': False,
                'warning': f'Some resources could not be cleaned up: {"; ".join(warnings)}',
                'warnings': warnings
            }
        else:
            return {
                'message': 'Judge builder deletion failed',
                'refresh_needed': True,
                'error': '; '.join(warnings) if warnings else 'Unknown error',
                'warnings': warnings
            }

    except Exception as e:
        logger.error(f'Unexpected error deleting judge builder {judge_id}: {e}\n{traceback.format_exc()}')
        return {
            'message': 'Judge builder deletion failed',
            'refresh_needed': True,
            'error': str(e)
        }
