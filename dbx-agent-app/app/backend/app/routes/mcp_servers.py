"""
CRUD endpoints for MCP Servers using Databricks SQL Warehouse.
"""

import logging
from fastapi import APIRouter, HTTPException, status, Query
import math

logger = logging.getLogger(__name__)

from app.db_adapter import WarehouseDB  # Auto-switches between SQLite and Warehouse
from app.schemas.mcp_server import MCPServerCreate, MCPServerUpdate, MCPServerResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/mcp_servers", tags=["MCP Servers"])


@router.get(
    "",
    response_model=PaginatedResponse[MCPServerResponse],
    status_code=status.HTTP_200_OK,
    summary="List MCP Servers",
    description="List all MCP servers with pagination",
)
def list_mcp_servers(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    kind: str | None = Query(None, description="Filter by server kind (managed, external)"),
    app_id: int | None = Query(None, description="Filter by parent app ID"),
) -> PaginatedResponse[MCPServerResponse]:
    """List all MCP servers with pagination."""
    servers, total = WarehouseDB.list_mcp_servers(page=page, page_size=page_size, app_id=app_id, kind=kind)
    total = int(total) if total else 0  # Convert string to int from warehouse
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse(
        items=[MCPServerResponse(**server) for server in servers],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=MCPServerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create MCP Server",
    description="Create a new MCP server",
)
def create_mcp_server(server_data: MCPServerCreate) -> MCPServerResponse:
    """Create a new MCP server."""
    try:
        server = WarehouseDB.create_mcp_server(
            server_url=server_data.server_url,
            kind=server_data.kind.value if server_data.kind else 'managed',
            app_id=server_data.app_id,
            uc_connection=server_data.uc_connection,
            scopes=server_data.scopes,
        )
        return MCPServerResponse(**server)
    except Exception as e:
        logger.error("Failed to create MCP server: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to create MCP server",
        )


@router.get(
    "/{server_id}",
    response_model=MCPServerResponse,
    status_code=status.HTTP_200_OK,
    summary="Get MCP Server",
    description="Get a specific MCP server by ID",
)
def get_mcp_server(server_id: int) -> MCPServerResponse:
    """Get a specific MCP server by ID."""
    server = WarehouseDB.get_mcp_server(server_id)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP Server with id {server_id} not found",
        )
    return MCPServerResponse(**server)


@router.put(
    "/{server_id}",
    response_model=MCPServerResponse,
    status_code=status.HTTP_200_OK,
    summary="Update MCP Server",
    description="Update an existing MCP server",
)
def update_mcp_server(server_id: int, server_data: MCPServerUpdate) -> MCPServerResponse:
    """Update an existing MCP server."""
    existing = WarehouseDB.get_mcp_server(server_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP Server with id {server_id} not found",
        )

    update_dict = server_data.model_dump(exclude_unset=True)
    if 'kind' in update_dict and update_dict['kind'] is not None:
        update_dict['kind'] = update_dict['kind'].value
    server = WarehouseDB.update_mcp_server(server_id, **update_dict)
    return MCPServerResponse(**server)


@router.delete(
    "/{server_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete MCP Server",
    description="Delete an MCP server",
)
def delete_mcp_server(server_id: int) -> None:
    """Delete an MCP server."""
    existing = WarehouseDB.get_mcp_server(server_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP Server with id {server_id} not found",
        )
    WarehouseDB.delete_mcp_server(server_id)
