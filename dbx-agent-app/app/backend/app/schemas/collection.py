"""
Pydantic schemas for Collection and CollectionItem entities.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List


class CollectionBase(BaseModel):
    """Base schema for Collection with common fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Collection name",
        example="Expert Research Toolkit",
    )
    description: Optional[str] = Field(
        None,
        description="Purpose description",
        example="Tools for researching expert profiles and transcripts",
    )


class CollectionCreate(CollectionBase):
    """Schema for creating a new Collection."""

    pass


class CollectionUpdate(BaseModel):
    """Schema for updating a Collection. All fields are optional."""

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Collection name",
    )
    description: Optional[str] = Field(
        None,
        description="Purpose description",
    )


class CollectionResponse(CollectionBase):
    """Schema for Collection response."""

    id: int = Field(..., description="Collection ID", example=1)

    class Config:
        from_attributes = True


class CollectionItemCountsResponse(BaseModel):
    """Schema for collection item counts."""

    total: int = Field(..., description="Total number of items", example=5)
    apps: int = Field(..., description="Number of apps", example=2)
    servers: int = Field(..., description="Number of MCP servers", example=2)
    tools: int = Field(..., description="Number of tools", example=1)


class CollectionWithItemsResponse(CollectionResponse):
    """Schema for Collection response with nested items."""

    items: List["CollectionItemResponse"] = Field(
        default_factory=list,
        description="Items in this collection",
    )

    class Config:
        from_attributes = True


class CollectionItemCreate(BaseModel):
    """
    Schema for adding an item to a collection via API.
    Exactly one of app_id, mcp_server_id, or tool_id must be set.
    collection_id comes from the URL path parameter.
    """

    app_id: Optional[int] = Field(
        None,
        description="App ID (mutually exclusive with mcp_server_id and tool_id)",
        example=1,
    )
    mcp_server_id: Optional[int] = Field(
        None,
        description="MCP Server ID (mutually exclusive with app_id and tool_id)",
        example=None,
    )
    tool_id: Optional[int] = Field(
        None,
        description="Tool ID (mutually exclusive with app_id and mcp_server_id)",
        example=None,
    )

    @field_validator("tool_id")
    @classmethod
    def validate_exactly_one_ref(cls, v, info):
        """Validate that exactly one of app_id, mcp_server_id, or tool_id is set."""
        app_id = info.data.get("app_id")
        mcp_server_id = info.data.get("mcp_server_id")
        tool_id = v

        non_null_count = sum(
            x is not None for x in [app_id, mcp_server_id, tool_id]
        )

        if non_null_count != 1:
            raise ValueError(
                "Exactly one of app_id, mcp_server_id, or tool_id must be set"
            )

        return v


class CollectionItemResponse(BaseModel):
    """Schema for CollectionItem response."""

    id: int = Field(..., description="Collection Item ID", example=1)
    collection_id: int = Field(..., description="Collection ID", example=1)
    app_id: Optional[int] = Field(None, description="App ID", example=1)
    mcp_server_id: Optional[int] = Field(None, description="MCP Server ID", example=None)
    tool_id: Optional[int] = Field(None, description="Tool ID", example=None)

    class Config:
        from_attributes = True
