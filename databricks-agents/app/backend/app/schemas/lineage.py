"""
Schemas for the lineage / knowledge graph endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class RelationshipResponse(BaseModel):
    id: int
    source_type: str
    source_id: int
    source_name: Optional[str] = None
    target_type: str
    target_id: int
    target_name: Optional[str] = None
    relationship_type: str
    metadata_json: Optional[str] = None
    discovered_at: Optional[str] = None


class LineageNode(BaseModel):
    asset_type: str
    asset_id: int
    name: str
    full_name: Optional[str] = None
    depth: int = Field(0, description="Distance from the queried asset (0 = self)")


class LineageEdge(BaseModel):
    source_type: str
    source_id: int
    target_type: str
    target_id: int
    relationship_type: str


class LineageResponse(BaseModel):
    root_type: str
    root_id: int
    root_name: str
    direction: str = Field(..., description="'upstream', 'downstream', or 'both'")
    nodes: List[LineageNode]
    edges: List[LineageEdge]


class ImpactAnalysisResponse(BaseModel):
    root_type: str
    root_id: int
    root_name: str
    affected_assets: List[LineageNode]
    total_affected: int


class LineageCrawlRequest(BaseModel):
    databricks_profile: Optional[str] = None
    include_column_lineage: bool = Field(False, description="Also crawl column-level lineage")


class LineageCrawlResponse(BaseModel):
    status: str
    message: str
    relationships_discovered: int
    new_relationships: int
    errors: List[str] = []
