"""Cache management API router."""

import logging

from fastapi import APIRouter

from server.services.cache_service import cache_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post('/clear')
async def clear_caches():
    """Clear all caches."""
    try:
        cache_service.trace_cache.clear()
        cache_service.evaluation_cache.clear()
        return {'message': 'All caches cleared successfully'}
    except Exception as e:
        logger.error(f'Failed to clear caches: {e}')
        raise
