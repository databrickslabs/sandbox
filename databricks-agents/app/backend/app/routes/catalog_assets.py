"""
CRUD and search endpoints for Unity Catalog assets.
"""

import logging
import math
from fastapi import APIRouter, HTTPException, Query, Request, status, BackgroundTasks

from app.db_adapter import WarehouseDB
from app.schemas.catalog_asset import (
    CatalogAssetResponse,
    CatalogCrawlRequest,
    CatalogCrawlResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.audit import record_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/catalog-assets", tags=["Catalog Assets"])


@router.get(
    "",
    response_model=PaginatedResponse[CatalogAssetResponse],
    status_code=status.HTTP_200_OK,
    summary="List Catalog Assets",
    description="List indexed Unity Catalog assets with filtering and pagination",
)
def list_catalog_assets(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    asset_type: str = Query(None, description="Filter by type (table, view, function, model, volume)"),
    catalog: str = Query(None, description="Filter by catalog name"),
    schema_name: str = Query(None, description="Filter by schema name"),
    search: str = Query(None, description="Search by name, comment, or column names"),
    owner: str = Query(None, description="Filter by owner"),
) -> PaginatedResponse[CatalogAssetResponse]:
    """List catalog assets with optional filters."""
    assets, total = WarehouseDB.list_catalog_assets(
        page=page,
        page_size=page_size,
        asset_type=asset_type,
        catalog=catalog,
        schema_name=schema_name,
        search=search,
        owner=owner,
    )
    total = int(total) if total else 0  # Convert string to int from warehouse
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse(
        items=[CatalogAssetResponse(**a) for a in assets],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{asset_id}",
    response_model=CatalogAssetResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Catalog Asset",
    description="Get a specific catalog asset by ID",
)
def get_catalog_asset(asset_id: int) -> CatalogAssetResponse:
    """Get a specific catalog asset."""
    asset = WarehouseDB.get_catalog_asset(asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Catalog asset with id {asset_id} not found",
        )
    return CatalogAssetResponse(**asset)


@router.post(
    "/crawl",
    response_model=CatalogCrawlResponse,
    status_code=status.HTTP_200_OK,
    summary="Crawl Unity Catalog",
    description="Trigger a crawl of Unity Catalog to index tables, views, functions, models, and volumes",
)
def crawl_catalog(request: CatalogCrawlRequest = None, http_request: Request = None) -> CatalogCrawlResponse:
    """
    Trigger a Unity Catalog crawl.

    This synchronously crawls the UC hierarchy and indexes all discovered assets.
    For large catalogs, consider running via background task.
    """
    if request is None:
        request = CatalogCrawlRequest()

    try:
        from app.services.catalog_crawler import CatalogCrawlerService

        service = CatalogCrawlerService(profile=request.databricks_profile)
        stats = service.crawl(
            catalogs=request.catalogs,
            include_columns=request.include_columns,
        )

        if stats.errors and stats.assets_discovered == 0:
            result_status = "failed"
            message = f"Catalog crawl failed with {len(stats.errors)} errors"
        elif stats.errors:
            result_status = "partial"
            message = f"Catalog crawl completed with {len(stats.errors)} errors"
        else:
            result_status = "success"
            message = f"Crawled {stats.catalogs_crawled} catalogs, {stats.schemas_crawled} schemas, {stats.assets_discovered} assets"

        if http_request:
            record_audit(http_request, "crawl", "catalog_asset", details={
                "catalogs_crawled": stats.catalogs_crawled,
                "assets_discovered": stats.assets_discovered,
                "new_assets": stats.new_assets,
            })

        return CatalogCrawlResponse(
            status=result_status,
            message=message,
            catalogs_crawled=stats.catalogs_crawled,
            schemas_crawled=stats.schemas_crawled,
            assets_discovered=stats.assets_discovered,
            new_assets=stats.new_assets,
            updated_assets=stats.updated_assets,
            errors=stats.errors,
        )
    except Exception as e:
        logger.error("Catalog crawl failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Catalog crawl failed: {e}",
        )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear Catalog Assets",
    description="Delete all indexed catalog assets (useful for re-indexing)",
)
def clear_catalog_assets(http_request: Request) -> None:
    """Delete all catalog assets."""
    WarehouseDB.clear_catalog_assets()
    record_audit(http_request, "clear", "catalog_asset")
