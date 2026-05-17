"""
Search Service — unified semantic + keyword search across all asset types.

Combines:
  1. Vector similarity (cosine) from stored embeddings
  2. Keyword matching (ILIKE) from the database
  3. Relevance ranking with quality/recency signals

Returns a single ranked list of SearchResultItem objects.
"""

import json
import logging
import math
from typing import List, Dict, Any, Optional, Tuple

from app.db_adapter import DatabaseAdapter
from app.services.embedding import EmbeddingService
from app.schemas.search import SearchResultItem

logger = logging.getLogger(__name__)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SearchService:
    """Unified search across all asset types."""

    def __init__(self):
        self._embedding_service = EmbeddingService()

    async def search(
        self,
        query: str,
        types: Optional[List[str]] = None,
        catalogs: Optional[List[str]] = None,
        owner: Optional[str] = None,
        limit: int = 20,
    ) -> Tuple[List[SearchResultItem], str]:
        """
        Execute a unified search.

        Returns (results, search_mode) where search_mode is
        'semantic', 'keyword', or 'hybrid'.
        """
        # Try semantic search first
        semantic_results = await self._semantic_search(query, types, limit * 2)

        # Also run keyword search
        keyword_results = self._keyword_search(query, types, catalogs, owner, limit * 2)

        if semantic_results and keyword_results:
            merged = self._merge_results(semantic_results, keyword_results, limit)
            return merged, "hybrid"
        elif semantic_results:
            return semantic_results[:limit], "semantic"
        else:
            return keyword_results[:limit], "keyword"

    async def _semantic_search(
        self,
        query: str,
        types: Optional[List[str]],
        limit: int,
    ) -> List[SearchResultItem]:
        """Search by embedding similarity."""
        # Get all embeddings (for small-scale, load into memory)
        embeddings = DatabaseAdapter.list_all_asset_embeddings()
        if not embeddings:
            return []

        # Embed the query
        query_vec = await self._embedding_service.embed_text(query)

        # Compute similarities
        scored: List[Tuple[float, Dict]] = []
        for emb in embeddings:
            if types and emb["asset_type"] not in types:
                continue

            asset_vec = json.loads(emb["embedding_json"])
            sim = _cosine_similarity(query_vec, asset_vec)
            if sim > 0.05:  # threshold to cut noise
                scored.append((sim, emb))

        # Sort by similarity descending
        scored.sort(key=lambda x: x[0], reverse=True)

        results: List[SearchResultItem] = []
        for sim, emb in scored[:limit]:
            asset = self._load_asset(emb["asset_type"], emb["asset_id"])
            if not asset:
                continue

            results.append(SearchResultItem(
                asset_type=emb["asset_type"],
                asset_id=emb["asset_id"],
                name=asset.get("name", ""),
                description=asset.get("comment") or asset.get("description"),
                full_name=asset.get("full_name"),
                path=asset.get("path"),
                owner=asset.get("owner"),
                score=round(sim, 4),
                match_type="semantic",
                snippet=self._make_snippet(emb.get("text_content", ""), query),
            ))

        return results

    def _keyword_search(
        self,
        query: str,
        types: Optional[List[str]],
        catalogs: Optional[List[str]] = None,
        owner: Optional[str] = None,
        limit: int = 40,
    ) -> List[SearchResultItem]:
        """Search by keyword matching across all asset tables."""
        results: List[SearchResultItem] = []
        per_type_limit = max(limit // 3, 10)

        # Catalog assets
        if not types or any(t in ("table", "view", "function", "model", "volume") for t in types):
            asset_type_filter = None
            if types:
                catalog_types = [t for t in types if t in ("table", "view", "function", "model", "volume")]
                if len(catalog_types) == 1:
                    asset_type_filter = catalog_types[0]

            catalog_filter = catalogs[0] if catalogs and len(catalogs) == 1 else None

            assets, _ = DatabaseAdapter.list_catalog_assets(
                page=1, page_size=per_type_limit,
                asset_type=asset_type_filter,
                catalog=catalog_filter,
                search=query,
                owner=owner,
            )
            for asset in assets:
                score = self._keyword_score(query, asset)
                results.append(SearchResultItem(
                    asset_type=asset["asset_type"],
                    asset_id=asset["id"],
                    name=asset["name"],
                    description=asset.get("comment"),
                    full_name=asset.get("full_name"),
                    owner=asset.get("owner"),
                    score=round(score, 4),
                    match_type="keyword",
                    snippet=asset.get("comment", "")[:200] if asset.get("comment") else None,
                ))

        # Workspace assets
        if not types or any(t in ("notebook", "job", "dashboard", "pipeline", "cluster", "experiment") for t in types):
            ws_type_filter = None
            if types:
                ws_types = [t for t in types if t in ("notebook", "job", "dashboard", "pipeline", "cluster", "experiment")]
                if len(ws_types) == 1:
                    ws_type_filter = ws_types[0]

            assets, _ = DatabaseAdapter.list_workspace_assets(
                page=1, page_size=per_type_limit,
                asset_type=ws_type_filter,
                search=query,
                owner=owner,
            )
            for asset in assets:
                score = self._keyword_score(query, asset)
                results.append(SearchResultItem(
                    asset_type=asset["asset_type"],
                    asset_id=asset["id"],
                    name=asset["name"],
                    description=asset.get("description"),
                    path=asset.get("path"),
                    owner=asset.get("owner"),
                    score=round(score, 4),
                    match_type="keyword",
                    snippet=asset.get("description", "")[:200] if asset.get("description") else None,
                ))

        # Apps
        if not types or "app" in types:
            apps, _ = DatabaseAdapter.list_apps(page=1, page_size=per_type_limit)
            for app in apps:
                if query.lower() in (app.get("name", "") or "").lower():
                    score = self._keyword_score(query, app)
                    results.append(SearchResultItem(
                        asset_type="app",
                        asset_id=app["id"],
                        name=app["name"],
                        description=None,
                        owner=app.get("owner"),
                        score=round(score, 4),
                        match_type="keyword",
                    ))

        # Tools
        if not types or "tool" in types:
            tools, _ = DatabaseAdapter.list_tools(page=1, page_size=per_type_limit)
            for tool in tools:
                searchable = f"{tool.get('name', '')} {tool.get('description', '')}".lower()
                if query.lower() in searchable:
                    score = self._keyword_score(query, tool)
                    results.append(SearchResultItem(
                        asset_type="tool",
                        asset_id=tool["id"],
                        name=tool["name"],
                        description=tool.get("description"),
                        score=round(score, 4),
                        match_type="keyword",
                    ))

        # Agents
        if not types or "agent" in types:
            agents, _ = DatabaseAdapter.list_agents(page=1, page_size=per_type_limit)
            for agent in agents:
                searchable = f"{agent.get('name', '')} {agent.get('description', '')} {agent.get('capabilities', '')}".lower()
                if query.lower() in searchable:
                    score = self._keyword_score(query, agent)
                    results.append(SearchResultItem(
                        asset_type="agent",
                        asset_id=agent["id"],
                        name=agent["name"],
                        description=agent.get("description"),
                        score=round(score, 4),
                        match_type="keyword",
                    ))

        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def _keyword_score(self, query: str, asset: Dict[str, Any]) -> float:
        """Simple keyword relevance score (0-1)."""
        query_lower = query.lower()
        query_words = query_lower.split()
        score = 0.0

        name = (asset.get("name", "") or "").lower()
        full_name = (asset.get("full_name", "") or "").lower()
        desc = (asset.get("comment") or asset.get("description") or "").lower()

        # Exact name match — highest signal
        if query_lower == name:
            score += 1.0
        elif query_lower in name:
            score += 0.7
        elif query_lower in full_name:
            score += 0.5

        # Word-level matches in name
        for word in query_words:
            if len(word) < 3:
                continue
            if word in name:
                score += 0.3
            if word in desc:
                score += 0.1

        # Quality boost: assets with descriptions rank higher
        if desc:
            score += 0.05

        # Owner match
        if asset.get("owner") and query_lower in (asset["owner"] or "").lower():
            score += 0.2

        return min(score, 1.0)

    def _merge_results(
        self,
        semantic: List[SearchResultItem],
        keyword: List[SearchResultItem],
        limit: int,
    ) -> List[SearchResultItem]:
        """Merge semantic and keyword results with deduplication."""
        seen = set()
        merged: List[SearchResultItem] = []

        # Build lookup of keyword scores
        kw_scores: Dict[str, float] = {}
        for r in keyword:
            key = f"{r.asset_type}:{r.asset_id}"
            kw_scores[key] = r.score

        # Semantic results get boosted if they also match keywords
        for r in semantic:
            key = f"{r.asset_type}:{r.asset_id}"
            if key in seen:
                continue
            seen.add(key)

            kw_boost = kw_scores.get(key, 0.0) * 0.3
            merged.append(SearchResultItem(
                asset_type=r.asset_type,
                asset_id=r.asset_id,
                name=r.name,
                description=r.description,
                full_name=r.full_name,
                path=r.path,
                owner=r.owner,
                score=round(min(r.score + kw_boost, 1.0), 4),
                match_type="hybrid" if kw_boost > 0 else "semantic",
                snippet=r.snippet,
            ))

        # Add keyword-only results not covered by semantic
        for r in keyword:
            key = f"{r.asset_type}:{r.asset_id}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(r)

        merged.sort(key=lambda r: r.score, reverse=True)
        return merged[:limit]

    def _load_asset(self, asset_type: str, asset_id: int) -> Optional[Dict]:
        """Load full asset dict by type + id."""
        catalog_types = {"table", "view", "function", "model", "volume"}
        workspace_types = {"notebook", "job", "dashboard", "pipeline", "cluster", "experiment"}

        if asset_type in catalog_types:
            return DatabaseAdapter.get_catalog_asset(asset_id)
        elif asset_type in workspace_types:
            return DatabaseAdapter.get_workspace_asset(asset_id)
        elif asset_type == "app":
            return DatabaseAdapter.get_app(asset_id)
        elif asset_type == "tool":
            return DatabaseAdapter.get_tool(asset_id)
        elif asset_type == "agent":
            return DatabaseAdapter.get_agent(asset_id)
        elif asset_type == "server":
            return DatabaseAdapter.get_mcp_server(asset_id)
        return None

    async def match_agents(
        self, task_description: str, limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find agents whose capabilities match a task description.

        Returns a list of {"agent": {...}, "score": float} dicts,
        sorted by cosine similarity descending.
        """
        query_vec = await self._embedding_service.embed_text(task_description)

        embeddings = DatabaseAdapter.list_all_asset_embeddings()
        agent_embeddings = [e for e in embeddings if e["asset_type"] == "agent"]

        scored: List[Dict[str, Any]] = []
        for emb in agent_embeddings:
            asset_vec = json.loads(emb["embedding_json"])
            sim = _cosine_similarity(query_vec, asset_vec)
            if sim > 0.1:
                agent = DatabaseAdapter.get_agent(emb["asset_id"])
                if agent and agent.get("status") == "active" and agent.get("endpoint_url"):
                    scored.append({"agent": agent, "score": sim})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    def _make_snippet(self, text: str, query: str, max_len: int = 200) -> Optional[str]:
        """Extract a relevant snippet around the query match."""
        if not text:
            return None

        query_lower = query.lower()
        text_lower = text.lower()
        idx = text_lower.find(query_lower)

        if idx >= 0:
            start = max(0, idx - 50)
            end = min(len(text), idx + len(query) + 150)
            snippet = text[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(text):
                snippet = snippet + "..."
            return snippet

        # No exact match — return beginning
        return text[:max_len] + ("..." if len(text) > max_len else "")
