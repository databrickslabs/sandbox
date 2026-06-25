"""
Pydantic schemas for CatalogAsset entities.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ColumnInfo(BaseModel):
    """Schema for a single column in a UC table/view."""

    name: str = Field(..., description="Column name")
    type: str = Field(..., description="Column data type")
    comment: Optional[str] = Field(None, description="Column description")
    nullable: bool = Field(True, description="Whether column allows nulls")
    position: Optional[int] = Field(None, description="Column ordinal position")


class CatalogAssetResponse(BaseModel):
    """Response schema for a catalog asset."""

    id: int = Field(..., description="Asset ID")
    asset_type: str = Field(..., description="Asset type (table, view, function, model, volume)")
    catalog: str = Field(..., description="UC catalog name")
    schema_name: str = Field(..., description="UC schema name")
    name: str = Field(..., description="Asset name")
    full_name: str = Field(..., description="Three-level namespace (catalog.schema.name)")
    owner: Optional[str] = Field(None, description="Asset owner")
    comment: Optional[str] = Field(None, description="Asset description")
    columns_json: Optional[str] = Field(None, description="JSON array of column definitions")
    tags_json: Optional[str] = Field(None, description="JSON array of UC tags")
    properties_json: Optional[str] = Field(None, description="JSON object of UC properties")
    data_source_format: Optional[str] = Field(None, description="Storage format (DELTA, PARQUET, etc.)")
    table_type: Optional[str] = Field(None, description="Table type (MANAGED, EXTERNAL, VIEW)")
    row_count: Optional[int] = Field(None, description="Approximate row count")
    created_at: Optional[str] = Field(None, description="When first indexed")
    updated_at: Optional[str] = Field(None, description="Last index update")
    last_indexed_at: Optional[str] = Field(None, description="Most recent crawl timestamp")

    class Config:
        from_attributes = True


class CatalogCrawlRequest(BaseModel):
    """Request to trigger a catalog crawl."""

    catalogs: Optional[List[str]] = Field(
        None,
        description="Specific catalogs to crawl. If empty, crawls all accessible catalogs.",
    )
    include_columns: bool = Field(
        True,
        description="Whether to fetch column metadata for tables/views",
    )
    databricks_profile: Optional[str] = Field(
        None,
        description="Databricks CLI profile to use for authentication",
    )


class CatalogCrawlResponse(BaseModel):
    """Response from catalog crawl."""

    status: str = Field(..., description="Crawl status (success/partial/failed)")
    message: str = Field(..., description="Human-readable status message")
    catalogs_crawled: int = Field(0, description="Number of catalogs crawled")
    schemas_crawled: int = Field(0, description="Number of schemas crawled")
    assets_discovered: int = Field(0, description="Total assets discovered")
    new_assets: int = Field(0, description="New assets added")
    updated_assets: int = Field(0, description="Existing assets updated")
    errors: List[str] = Field(default_factory=list, description="Errors encountered")
