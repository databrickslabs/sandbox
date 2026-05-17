"""
Read-only endpoints for Tools using Databricks SQL Warehouse.
"""

from fastapi import APIRouter, HTTPException, status, Query
import math

from app.db_adapter import WarehouseDB  # Auto-switches between SQLite and Warehouse
from app.schemas.tool import ToolResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.get(
    "",
    response_model=PaginatedResponse[ToolResponse],
    status_code=status.HTTP_200_OK,
    summary="List Tools",
    description="List all tools with pagination",
)
def list_tools(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    mcp_server_id: int | None = Query(None, description="Filter by MCP server ID"),
    name: str | None = Query(None, description="Filter by tool name (substring match)"),
    search: str | None = Query(None, description="Full-text search on name and description"),
    tags: str | None = Query(None, description="Filter by parent app tags (comma-separated)"),
    owner: str | None = Query(None, description="Filter by parent app owner (substring match)"),
) -> PaginatedResponse[ToolResponse]:
    """List all tools with optional filtering and pagination."""
    tools, total = WarehouseDB.list_tools(
        page=page,
        page_size=page_size,
        mcp_server_id=mcp_server_id,
        name=name,
        search=search,
        tags=tags,
        owner=owner,
    )
    total = int(total) if total else 0  # Convert string to int from warehouse
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse(
        items=[ToolResponse(**tool) for tool in tools],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{tool_id}",
    response_model=ToolResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Tool",
    description="Get a specific tool by ID",
)
def get_tool(tool_id: int) -> ToolResponse:
    """Get a specific tool by ID."""
    tool = WarehouseDB.get_tool(tool_id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool with id {tool_id} not found",
        )
    return ToolResponse(**tool)
