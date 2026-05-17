"""
Pydantic schemas for App entities.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime


class AppBase(BaseModel):
    """Base schema for App with common fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="App name",
        example="sgp-research-app",
    )
    owner: Optional[str] = Field(
        None,
        max_length=255,
        description="App owner (username or service principal)",
        example="stuart.gano@example.com",
    )
    url: Optional[str] = Field(
        None,
        description="Deployed app URL",
        example="https://my-workspace.cloud.databricks.com/apps/sgp-research-app",
    )
    tags: Optional[str] = Field(
        None,
        description="Comma-separated tags",
        example="research,guidepoint,mcp",
    )
    manifest_url: Optional[str] = Field(
        None,
        description="URL to app.yaml or manifest file",
        example="https://github.com/org/repo/blob/main/app.yaml",
    )


class AppCreate(AppBase):
    """Schema for creating a new App."""

    pass


class AppUpdate(BaseModel):
    """Schema for updating an App. All fields are optional."""

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="App name",
    )
    owner: Optional[str] = Field(
        None,
        max_length=255,
        description="App owner",
    )
    url: Optional[str] = Field(
        None,
        description="Deployed app URL",
    )
    tags: Optional[str] = Field(
        None,
        description="Comma-separated tags",
    )
    manifest_url: Optional[str] = Field(
        None,
        description="URL to app.yaml or manifest file",
    )


class AppResponse(AppBase):
    """Schema for App response."""

    id: int = Field(..., description="App ID", example=1)

    class Config:
        from_attributes = True
