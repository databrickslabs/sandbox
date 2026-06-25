"""
Lineage & Knowledge Graph endpoints.

Provides:
  - GET  /api/lineage/{asset_type}/{asset_id}        — upstream/downstream lineage
  - GET  /api/lineage/{asset_type}/{asset_id}/impact  — impact analysis
  - POST /api/lineage/crawl                           — trigger lineage discovery
  - GET  /api/lineage/relationships                   — list all relationships
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request

from app.schemas.lineage import (
    LineageResponse,
    LineageNode,
    LineageEdge,
    ImpactAnalysisResponse,
    LineageCrawlRequest,
    LineageCrawlResponse,
    RelationshipResponse,
)
from app.services.lineage_crawler import LineageCrawlerService
from app.services.audit import record_audit
from app.db_adapter import DatabaseAdapter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Lineage"])


@router.get("/lineage/{asset_type}/{asset_id}", response_model=LineageResponse)
async def get_lineage(
    asset_type: str,
    asset_id: int,
    direction: str = Query("both", enum=["upstream", "downstream", "both"]),
    max_depth: int = Query(3, ge=1, le=10),
):
    """
    Get upstream and/or downstream lineage for an asset.

    Returns a graph of nodes (assets) and edges (relationships)
    traversed from the given starting asset.
    """
    # Resolve asset name
    root_name = _resolve_asset_name(asset_type, asset_id)
    if not root_name:
        raise HTTPException(status_code=404, detail=f"Asset {asset_type}/{asset_id} not found")

    nodes = [LineageNode(asset_type=asset_type, asset_id=asset_id, name=root_name, depth=0)]
    edges = []
    visited = {(asset_type, asset_id)}

    if direction in ("upstream", "both"):
        _traverse(asset_type, asset_id, "upstream", max_depth, 1, nodes, edges, visited)

    if direction in ("downstream", "both"):
        _traverse(asset_type, asset_id, "downstream", max_depth, 1, nodes, edges, visited)

    return LineageResponse(
        root_type=asset_type,
        root_id=asset_id,
        root_name=root_name,
        direction=direction,
        nodes=nodes,
        edges=edges,
    )


@router.get("/lineage/{asset_type}/{asset_id}/impact", response_model=ImpactAnalysisResponse)
async def get_impact_analysis(
    asset_type: str,
    asset_id: int,
    max_depth: int = Query(5, ge=1, le=10),
):
    """
    Impact analysis: what downstream assets would be affected
    if this asset changes?

    Traverses downstream relationships recursively.
    """
    root_name = _resolve_asset_name(asset_type, asset_id)
    if not root_name:
        raise HTTPException(status_code=404, detail=f"Asset {asset_type}/{asset_id} not found")

    affected = []
    visited = {(asset_type, asset_id)}
    _traverse_impact(asset_type, asset_id, max_depth, 1, affected, visited)

    return ImpactAnalysisResponse(
        root_type=asset_type,
        root_id=asset_id,
        root_name=root_name,
        affected_assets=affected,
        total_affected=len(affected),
    )


@router.post("/lineage/crawl", response_model=LineageCrawlResponse)
async def crawl_lineage(request: LineageCrawlRequest, http_request: Request):
    """Trigger lineage discovery across all data sources."""
    service = LineageCrawlerService(databricks_profile=request.databricks_profile)
    stats = await service.crawl(include_column_lineage=request.include_column_lineage)

    result_status = "completed" if not stats.errors else "completed_with_errors"

    record_audit(http_request, "crawl", "lineage", details={
        "relationships_discovered": stats.relationships_discovered,
        "new_relationships": stats.new_relationships,
    })

    return LineageCrawlResponse(
        status=result_status,
        message=f"Discovered {stats.relationships_discovered} relationships ({stats.new_relationships} new)",
        relationships_discovered=stats.relationships_discovered,
        new_relationships=stats.new_relationships,
        errors=stats.errors,
    )


@router.get("/lineage/relationships", response_model=list[RelationshipResponse])
async def list_relationships(
    source_type: Optional[str] = None,
    target_type: Optional[str] = None,
    relationship_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
):
    """List all relationships with optional filters."""
    rels, total = DatabaseAdapter.list_asset_relationships(
        source_type=source_type,
        target_type=target_type,
        relationship_type=relationship_type,
        page=page,
        page_size=page_size,
    )
    return rels


# --- Graph traversal helpers ---

def _traverse(
    asset_type: str,
    asset_id: int,
    direction: str,
    max_depth: int,
    current_depth: int,
    nodes: list,
    edges: list,
    visited: set,
) -> None:
    """BFS-style traversal along lineage edges."""
    if current_depth > max_depth:
        return

    if direction == "upstream":
        # Find relationships where this asset is the TARGET (something feeds into it)
        rels = DatabaseAdapter.get_relationships_by_target(asset_type, asset_id)
        for rel in rels:
            neighbor = (rel["source_type"], rel["source_id"])
            edges.append(LineageEdge(
                source_type=rel["source_type"],
                source_id=rel["source_id"],
                target_type=rel["target_type"],
                target_id=rel["target_id"],
                relationship_type=rel["relationship_type"],
            ))
            if neighbor not in visited:
                visited.add(neighbor)
                name = rel.get("source_name") or _resolve_asset_name(rel["source_type"], rel["source_id"]) or ""
                nodes.append(LineageNode(
                    asset_type=rel["source_type"],
                    asset_id=rel["source_id"],
                    name=name,
                    depth=current_depth,
                ))
                _traverse(rel["source_type"], rel["source_id"], direction, max_depth, current_depth + 1, nodes, edges, visited)
    else:
        # Find relationships where this asset is the SOURCE (it feeds into something)
        rels = DatabaseAdapter.get_relationships_by_source(asset_type, asset_id)
        for rel in rels:
            neighbor = (rel["target_type"], rel["target_id"])
            edges.append(LineageEdge(
                source_type=rel["source_type"],
                source_id=rel["source_id"],
                target_type=rel["target_type"],
                target_id=rel["target_id"],
                relationship_type=rel["relationship_type"],
            ))
            if neighbor not in visited:
                visited.add(neighbor)
                name = rel.get("target_name") or _resolve_asset_name(rel["target_type"], rel["target_id"]) or ""
                nodes.append(LineageNode(
                    asset_type=rel["target_type"],
                    asset_id=rel["target_id"],
                    name=name,
                    depth=current_depth,
                ))
                _traverse(rel["target_type"], rel["target_id"], direction, max_depth, current_depth + 1, nodes, edges, visited)


def _traverse_impact(
    asset_type: str,
    asset_id: int,
    max_depth: int,
    current_depth: int,
    affected: list,
    visited: set,
) -> None:
    """Traverse downstream to find all affected assets."""
    if current_depth > max_depth:
        return

    rels = DatabaseAdapter.get_relationships_by_source(asset_type, asset_id)
    for rel in rels:
        neighbor = (rel["target_type"], rel["target_id"])
        if neighbor not in visited:
            visited.add(neighbor)
            name = rel.get("target_name") or _resolve_asset_name(rel["target_type"], rel["target_id"]) or ""
            affected.append(LineageNode(
                asset_type=rel["target_type"],
                asset_id=rel["target_id"],
                name=name,
                depth=current_depth,
            ))
            _traverse_impact(rel["target_type"], rel["target_id"], max_depth, current_depth + 1, affected, visited)


def _resolve_asset_name(asset_type: str, asset_id: int) -> Optional[str]:
    """Resolve an asset's display name by type + id."""
    catalog_types = {"table", "view", "function", "model", "volume"}
    workspace_types = {"notebook", "job", "dashboard", "pipeline", "cluster", "experiment"}

    if asset_type in catalog_types:
        asset = DatabaseAdapter.get_catalog_asset(asset_id)
        return asset["full_name"] if asset else None
    elif asset_type in workspace_types:
        asset = DatabaseAdapter.get_workspace_asset(asset_id)
        return asset["name"] if asset else None
    elif asset_type == "app":
        asset = DatabaseAdapter.get_app(asset_id)
        return asset["name"] if asset else None
    elif asset_type == "tool":
        asset = DatabaseAdapter.get_tool(asset_id)
        return asset["name"] if asset else None
    return None
