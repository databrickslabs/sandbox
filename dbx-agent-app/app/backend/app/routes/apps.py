"""
CRUD endpoints for Apps using Databricks SQL Warehouse.
"""

import logging
from fastapi import APIRouter, HTTPException, status, Query
import math

logger = logging.getLogger(__name__)

from app.db_adapter import WarehouseDB  # Auto-switches between SQLite and Warehouse
from app.schemas.app import AppCreate, AppUpdate, AppResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/apps", tags=["Apps"])


@router.get(
    "",
    response_model=PaginatedResponse[AppResponse],
    status_code=status.HTTP_200_OK,
    summary="List Apps",
    description="List all registered apps with pagination",
)
def list_apps(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    owner: str | None = Query(None, description="Filter by owner"),
) -> PaginatedResponse[AppResponse]:
    """List all apps with pagination."""
    logger.info(f"[READ] Listing apps (page={page}, page_size={page_size}, owner={owner})")
    apps, total = WarehouseDB.list_apps(page=page, page_size=page_size, owner=owner)
    logger.info(f"[READ] Found {total} apps total, returning {len(apps)} on this page")
    total = int(total) if total else 0  # Convert string to int from warehouse
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse(
        items=[AppResponse(**app) for app in apps],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=AppResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create App",
    description="Register a new Databricks App",
)
def create_app(app_data: AppCreate) -> AppResponse:
    """Create a new app."""
    try:
        app = WarehouseDB.create_app(
            name=app_data.name,
            owner=app_data.owner,
            url=app_data.url,
            tags=app_data.tags,
            manifest_url=app_data.manifest_url,
        )
        return AppResponse(**app)
    except Exception as e:
        logger.error("Failed to create app: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to create app",
        )


@router.get(
    "/{app_id}",
    response_model=AppResponse,
    status_code=status.HTTP_200_OK,
    summary="Get App",
    description="Get a specific app by ID",
)
def get_app(app_id: int) -> AppResponse:
    """Get a specific app by ID."""
    app = WarehouseDB.get_app(app_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App with id {app_id} not found",
        )
    return AppResponse(**app)


@router.put(
    "/{app_id}",
    response_model=AppResponse,
    status_code=status.HTTP_200_OK,
    summary="Update App",
    description="Update an existing app",
)
def update_app(app_id: int, app_data: AppUpdate) -> AppResponse:
    """Update an existing app."""
    existing = WarehouseDB.get_app(app_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App with id {app_id} not found",
        )

    update_dict = app_data.model_dump(exclude_unset=True)
    app = WarehouseDB.update_app(app_id, **update_dict)
    return AppResponse(**app)


@router.delete(
    "/{app_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete App",
    description="Delete an app from the registry",
)
def delete_app(app_id: int) -> None:
    """Delete an app."""
    existing = WarehouseDB.get_app(app_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App with id {app_id} not found",
        )
    WarehouseDB.delete_app(app_id)
