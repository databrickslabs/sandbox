"""
Schemas for the unified semantic search endpoint.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query")
    types: Optional[List[str]] = Field(
        None,
        description="Filter by asset types (e.g. ['table', 'notebook', 'app']). None = all types.",
    )
    catalogs: Optional[List[str]] = Field(
        None,
        description="Filter catalog assets to specific catalogs",
    )
    owner: Optional[str] = Field(None, description="Filter by owner")
    limit: int = Field(20, ge=1, le=100, description="Max results to return")


class SearchResultItem(BaseModel):
    asset_type: str = Field(..., description="Type of asset (table, notebook, app, etc.)")
    asset_id: int = Field(..., description="ID of the asset in its source table")
    name: str
    description: Optional[str] = None
    full_name: Optional[str] = None  # for catalog assets
    path: Optional[str] = None  # for workspace assets
    owner: Optional[str] = None
    score: float = Field(..., description="Relevance score (0-1)")
    match_type: str = Field(..., description="'semantic', 'keyword', or 'hybrid'")
    snippet: Optional[str] = Field(None, description="Highlighted text snippet")


class SearchResponse(BaseModel):
    query: str
    total: int
    results: List[SearchResultItem]
    search_mode: str = Field(..., description="'semantic', 'keyword', or 'hybrid'")


class EmbedStatusResponse(BaseModel):
    total_assets: int
    embedded_assets: int
    pending_assets: int
    embedding_model: str
    dimension: int
