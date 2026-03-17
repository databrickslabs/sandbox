"""
Pydantic schemas for MCPServer entities.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from enum import Enum


class MCPServerKindSchema(str, Enum):
    """MCP Server types."""

    MANAGED = "managed"
    EXTERNAL = "external"
    CUSTOM = "custom"


class MCPServerBase(BaseModel):
    """Base schema for MCPServer with common fields."""

    app_id: Optional[int] = Field(
        None,
        description="Foreign key to parent App (nullable for standalone servers)",
        example=1,
    )
    server_url: str = Field(
        ...,
        description="MCP server endpoint URL",
        example="https://api.guidepoint.com/mcp",
    )
    kind: MCPServerKindSchema = Field(
        ...,
        description="Server type (managed/external/custom)",
        example="custom",
    )
    uc_connection: Optional[str] = Field(
        None,
        max_length=255,
        description="Unity Catalog connection name (for governance)",
        example="guidepoint_connection",
    )
    scopes: Optional[str] = Field(
        None,
        description="Comma-separated OAuth scopes required",
        example="read:experts,read:transcripts",
    )


class MCPServerCreate(MCPServerBase):
    """Schema for creating a new MCPServer."""

    pass


class MCPServerUpdate(BaseModel):
    """Schema for updating an MCPServer. All fields are optional."""

    app_id: Optional[int] = Field(
        None,
        description="Foreign key to parent App",
    )
    server_url: Optional[str] = Field(
        None,
        description="MCP server endpoint URL",
    )
    kind: Optional[MCPServerKindSchema] = Field(
        None,
        description="Server type",
    )
    uc_connection: Optional[str] = Field(
        None,
        max_length=255,
        description="Unity Catalog connection name",
    )
    scopes: Optional[str] = Field(
        None,
        description="Comma-separated OAuth scopes",
    )


class MCPServerResponse(MCPServerBase):
    """Schema for MCPServer response."""

    id: int = Field(..., description="MCP Server ID", example=1)

    class Config:
        from_attributes = True
