"""
Pydantic schemas for Tool entities.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ToolFilter(BaseModel):
    """Schema for filtering tools."""

    mcp_server_id: Optional[int] = Field(
        None,
        description="Filter by MCP server ID",
        example=1,
    )
    name: Optional[str] = Field(
        None,
        description="Filter by tool name (partial match)",
        example="search",
    )
    page: int = Field(
        1,
        ge=1,
        description="Page number",
        example=1,
    )
    page_size: int = Field(
        50,
        ge=1,
        le=100,
        description="Number of items per page",
        example=50,
    )


class ToolResponse(BaseModel):
    """Schema for Tool response."""

    id: int = Field(..., description="Tool ID", example=1)
    mcp_server_id: int = Field(..., description="MCP Server ID", example=1)
    name: str = Field(..., description="Tool name", example="search_transcripts")
    description: Optional[str] = Field(
        None,
        description="Human-readable description",
        example="Search expert call transcripts by keyword",
    )
    parameters: Optional[str] = Field(
        None,
        description="JSON Schema for tool parameters",
        example='{"type": "object", "properties": {"query": {"type": "string"}}}',
    )

    class Config:
        from_attributes = True
