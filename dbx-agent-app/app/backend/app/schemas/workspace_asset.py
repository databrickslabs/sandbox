"""
Pydantic schemas for WorkspaceAsset entities.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class WorkspaceAssetResponse(BaseModel):
    """Response schema for a workspace asset."""

    id: int = Field(..., description="Asset ID")
    asset_type: str = Field(..., description="Asset type (notebook, job, dashboard, etc.)")
    workspace_host: str = Field(..., description="Databricks workspace URL")
    path: str = Field(..., description="Workspace path or resource identifier")
    name: str = Field(..., description="Human-readable name")
    owner: Optional[str] = Field(None, description="Asset owner/creator")
    description: Optional[str] = Field(None, description="Asset description")
    language: Optional[str] = Field(None, description="Language (for notebooks)")
    tags_json: Optional[str] = Field(None, description="JSON array of tags")
    metadata_json: Optional[str] = Field(None, description="Type-specific metadata JSON")
    content_preview: Optional[str] = Field(None, description="Content preview for search")
    resource_id: Optional[str] = Field(None, description="Databricks resource ID")
    created_at: Optional[str] = Field(None, description="When first indexed")
    updated_at: Optional[str] = Field(None, description="Last index update")
    last_indexed_at: Optional[str] = Field(None, description="Most recent crawl timestamp")

    class Config:
        from_attributes = True


class WorkspaceCrawlRequest(BaseModel):
    """Request to trigger a workspace crawl."""

    asset_types: Optional[List[str]] = Field(
        None,
        description="Specific types to crawl (notebook, job, dashboard, pipeline, cluster, experiment). If empty, crawls all.",
    )
    root_path: Optional[str] = Field(
        "/",
        description="Root path to start notebook crawl from",
    )
    databricks_profile: Optional[str] = Field(
        None,
        description="Databricks CLI profile to use for authentication",
    )


class WorkspaceCrawlResponse(BaseModel):
    """Response from workspace crawl."""

    status: str = Field(..., description="Crawl status (success/partial/failed)")
    message: str = Field(..., description="Human-readable status message")
    assets_discovered: int = Field(0, description="Total assets discovered")
    new_assets: int = Field(0, description="New assets added")
    updated_assets: int = Field(0, description="Existing assets updated")
    by_type: dict = Field(default_factory=dict, description="Counts per asset type")
    errors: List[str] = Field(default_factory=list, description="Errors encountered")
