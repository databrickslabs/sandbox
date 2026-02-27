"""
CRUD and search endpoints for Databricks workspace assets.
"""

import logging
import math
from fastapi import APIRouter, HTTPException, Query, Request, status

from app.db_adapter import WarehouseDB
from app.schemas.workspace_asset import (
    WorkspaceAssetResponse,
    WorkspaceCrawlRequest,
    WorkspaceCrawlResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.audit import record_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspace-assets", tags=["Workspace Assets"])


@router.get(
    "",
    response_model=PaginatedResponse[WorkspaceAssetResponse],
    status_code=status.HTTP_200_OK,
    summary="List Workspace Assets",
    description="List indexed workspace assets with filtering and pagination",
)
def list_workspace_assets(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    asset_type: str = Query(None, description="Filter by type (notebook, job, dashboard, pipeline, cluster, experiment)"),
    search: str = Query(None, description="Search by name, description, or content preview"),
    owner: str = Query(None, description="Filter by owner"),
    workspace_host: str = Query(None, description="Filter by workspace host"),
) -> PaginatedResponse[WorkspaceAssetResponse]:
    """List workspace assets with optional filters."""
    assets, total = WarehouseDB.list_workspace_assets(
        page=page,
        page_size=page_size,
        asset_type=asset_type,
        search=search,
        owner=owner,
        workspace_host=workspace_host,
    )
    total = int(total) if total else 0  # Convert string to int from warehouse
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse(
        items=[WorkspaceAssetResponse(**a) for a in assets],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{asset_id}",
    response_model=WorkspaceAssetResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Workspace Asset",
    description="Get a specific workspace asset by ID",
)
def get_workspace_asset(asset_id: int) -> WorkspaceAssetResponse:
    """Get a specific workspace asset."""
    asset = WarehouseDB.get_workspace_asset(asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace asset with id {asset_id} not found",
        )
    return WorkspaceAssetResponse(**asset)


@router.post(
    "/crawl",
    response_model=WorkspaceCrawlResponse,
    status_code=status.HTTP_200_OK,
    summary="Crawl Workspace",
    description="Trigger a crawl of the Databricks workspace to index notebooks, jobs, dashboards, etc.",
)
def crawl_workspace(request: WorkspaceCrawlRequest = None, http_request: Request = None) -> WorkspaceCrawlResponse:
    """
    Trigger a workspace crawl.

    Indexes notebooks, jobs, dashboards, pipelines, clusters, and experiments.
    """
    if request is None:
        request = WorkspaceCrawlRequest()

    try:
        from app.services.workspace_crawler import WorkspaceCrawlerService

        service = WorkspaceCrawlerService(profile=request.databricks_profile)
        stats = service.crawl(
            asset_types=request.asset_types,
            root_path=request.root_path or "/",
        )

        if stats.errors and stats.assets_discovered == 0:
            result_status = "failed"
            message = f"Workspace crawl failed with {len(stats.errors)} errors"
        elif stats.errors:
            result_status = "partial"
            message = f"Workspace crawl completed with {len(stats.errors)} errors"
        else:
            result_status = "success"
            message = f"Discovered {stats.assets_discovered} assets across {len(stats.by_type)} types"

        if http_request:
            record_audit(http_request, "crawl", "workspace_asset", details={
                "assets_discovered": stats.assets_discovered,
                "new_assets": stats.new_assets,
            })

        return WorkspaceCrawlResponse(
            status=result_status,
            message=message,
            assets_discovered=stats.assets_discovered,
            new_assets=stats.new_assets,
            updated_assets=stats.updated_assets,
            by_type=stats.by_type,
            errors=stats.errors,
        )
    except Exception as e:
        logger.error("Workspace crawl failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workspace crawl failed: {e}",
        )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear Workspace Assets",
    description="Delete all indexed workspace assets (useful for re-indexing)",
)
def clear_workspace_assets(http_request: Request) -> None:
    """Delete all workspace assets."""
    WarehouseDB.clear_workspace_assets()
    record_audit(http_request, "clear", "workspace_asset")
