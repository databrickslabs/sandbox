"""
CRUD endpoints for Collections using Databricks SQL Warehouse.
"""

import logging
from fastapi import APIRouter, HTTPException, Request, status, Query
from typing import List
import math

logger = logging.getLogger(__name__)

from app.db_adapter import WarehouseDB  # Auto-switches between SQLite and Warehouse
from app.schemas.collection import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionItemCreate,
    CollectionItemResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.audit import record_audit

router = APIRouter(prefix="/collections", tags=["Collections"])


@router.get(
    "",
    response_model=PaginatedResponse[CollectionResponse],
    status_code=status.HTTP_200_OK,
    summary="List Collections",
    description="List all collections with pagination",
)
def list_collections(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[CollectionResponse]:
    """List all collections with pagination."""
    collections, total = WarehouseDB.list_collections(page=page, page_size=page_size)
    total = int(total) if total else 0  # Convert string to int from warehouse
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse(
        items=[CollectionResponse(**c) for c in collections],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Collection",
    description="Create a new collection",
)
def create_collection(collection_data: CollectionCreate, request: Request) -> CollectionResponse:
    """Create a new collection."""
    try:
        collection = WarehouseDB.create_collection(
            name=collection_data.name,
            description=collection_data.description,
        )
        record_audit(request, "create", "collection", str(collection["id"]), collection["name"])
        return CollectionResponse(**collection)
    except Exception as e:
        logger.error("Failed to create collection: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to create collection",
        )


@router.get(
    "/{collection_id}",
    response_model=CollectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Collection",
    description="Get a specific collection by ID",
)
def get_collection(collection_id: int) -> CollectionResponse:
    """Get a specific collection by ID."""
    collection = WarehouseDB.get_collection(collection_id)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with id {collection_id} not found",
        )
    return CollectionResponse(**collection)


@router.put(
    "/{collection_id}",
    response_model=CollectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Collection",
    description="Update an existing collection",
)
def update_collection(collection_id: int, collection_data: CollectionUpdate, request: Request) -> CollectionResponse:
    """Update an existing collection."""
    existing = WarehouseDB.get_collection(collection_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with id {collection_id} not found",
        )

    update_dict = collection_data.model_dump(exclude_unset=True)

    # Check for duplicate name
    if 'name' in update_dict and update_dict['name'] != existing.get('name'):
        all_collections, _ = WarehouseDB.list_collections(page=1, page_size=10000)
        for c in all_collections:
            if c['name'] == update_dict['name'] and c['id'] != collection_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="A collection with this name already exists",
                )

    collection = WarehouseDB.update_collection(collection_id, **update_dict)
    record_audit(request, "update", "collection", str(collection_id), collection["name"])
    return CollectionResponse(**collection)


@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Collection",
    description="Delete a collection (cascades to collection items)",
)
def delete_collection(collection_id: int, request: Request) -> None:
    """Delete a collection."""
    existing = WarehouseDB.get_collection(collection_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with id {collection_id} not found",
        )
    WarehouseDB.delete_collection(collection_id)
    record_audit(request, "delete", "collection", str(collection_id), existing["name"])


# Collection Items endpoints


@router.get(
    "/{collection_id}/items",
    response_model=List[CollectionItemResponse],
    status_code=status.HTTP_200_OK,
    summary="List Collection Items",
    description="List all items in a collection",
)
def list_collection_items(collection_id: int) -> List[CollectionItemResponse]:
    """List all items in a specific collection."""
    # list_collection_items returns [] for non-existent collections,
    # so check existence only when empty to distinguish "no items" from "not found"
    items = WarehouseDB.list_collection_items(collection_id)
    if not items:
        collection = WarehouseDB.get_collection(collection_id)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection with id {collection_id} not found",
            )
    return [CollectionItemResponse(**item) for item in items]


@router.post(
    "/{collection_id}/items",
    response_model=CollectionItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Item to Collection",
    description="Add an app, MCP server, or tool to a collection",
)
def add_collection_item(collection_id: int, item_data: CollectionItemCreate, request: Request) -> CollectionItemResponse:
    """Add an item to a collection."""
    # Verify collection exists
    collection = WarehouseDB.get_collection(collection_id)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with id {collection_id} not found",
        )

    # Validate exactly one reference is set
    refs = [item_data.app_id, item_data.mcp_server_id, item_data.tool_id]
    if sum(r is not None for r in refs) != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Exactly one of app_id, mcp_server_id, or tool_id must be set",
        )

    # Check for duplicate item in collection
    existing_items = WarehouseDB.list_collection_items(collection_id)
    for existing in existing_items:
        if (item_data.app_id and existing.get('app_id') == item_data.app_id) or \
           (item_data.mcp_server_id and existing.get('mcp_server_id') == item_data.mcp_server_id) or \
           (item_data.tool_id and existing.get('tool_id') == item_data.tool_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Item already exists in this collection",
            )

    # Validate referenced entity exists
    if item_data.app_id and not WarehouseDB.get_app(item_data.app_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"App with id {item_data.app_id} does not exist",
        )
    if item_data.mcp_server_id and not WarehouseDB.get_mcp_server(item_data.mcp_server_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"MCP Server with id {item_data.mcp_server_id} does not exist",
        )
    if item_data.tool_id and not WarehouseDB.get_tool(item_data.tool_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tool with id {item_data.tool_id} does not exist",
        )

    try:
        item = WarehouseDB.add_collection_item(
            collection_id=collection_id,
            app_id=item_data.app_id,
            mcp_server_id=item_data.mcp_server_id,
            tool_id=item_data.tool_id,
        )
        record_audit(request, "add_item", "collection", str(collection_id), collection["name"],
                      details={"item_id": item["id"]})
        return CollectionItemResponse(**item)
    except Exception as e:
        logger.error("Failed to add collection item: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to add item to collection",
        )


@router.delete(
    "/{collection_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Item from Collection",
    description="Remove an item from a collection",
)
def remove_collection_item(collection_id: int, item_id: int, request: Request) -> None:
    """Remove an item from a collection."""
    # Verify collection exists
    collection = WarehouseDB.get_collection(collection_id)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with id {collection_id} not found",
        )

    # Verify item exists and belongs to this collection
    item = WarehouseDB.get_collection_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found",
        )
    if item['collection_id'] != collection_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} does not belong to collection {collection_id}",
        )

    WarehouseDB.delete_collection_item(item_id)
    record_audit(request, "remove_item", "collection", str(collection_id), collection["name"],
                  details={"item_id": item_id})
