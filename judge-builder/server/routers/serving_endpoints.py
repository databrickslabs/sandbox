"""Serving endpoints API router."""

import logging

from fastapi import APIRouter, HTTPException

from server.services.serving_endpoint_service import serving_endpoint_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def list_serving_endpoints(force_refresh: bool = False):
    """List all serving endpoints in the workspace."""
    try:
        endpoints = serving_endpoint_service.list_serving_endpoints(force_refresh=force_refresh)
        return [
            {
                "name": e.name,
                "state": e.state.config_update if e.state else None,
                "creation_timestamp": e.creation_timestamp,
            }
            for e in endpoints
        ]
    except Exception as e:
        logger.error(f"Failed to list serving endpoints: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{endpoint_name}")
async def get_serving_endpoint(endpoint_name: str):
    """Get details for a specific serving endpoint."""
    try:
        endpoint = serving_endpoint_service.get_endpoint(endpoint_name)
        return {
            "name": endpoint.name,
            "state": endpoint.state,
            "config": endpoint.config,
            "creation_timestamp": endpoint.creation_timestamp,
        }
    except Exception as e:
        logger.error(f"Failed to get endpoint {endpoint_name}: {e}")
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{endpoint_name}/validate")
async def validate_endpoint(endpoint_name: str):
    """Validate that an endpoint exists."""
    try:
        is_valid = serving_endpoint_service.validate_endpoint_name(endpoint_name)
        return {"valid": is_valid, "endpoint_name": endpoint_name}
    except Exception as e:
        logger.error(f"Failed to validate endpoint {endpoint_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
