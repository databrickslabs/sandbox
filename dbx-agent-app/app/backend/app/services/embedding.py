"""
Embedding Service — generates vector embeddings for indexed assets.

Dual-path:
  - Production: Databricks Foundation Model API (databricks-bge-large-en)
  - Dev/local: Simple keyword-based pseudo-embeddings using TF-IDF-style hashing

Embeddings are stored in the AssetEmbedding table and used by SearchService
for cosine-similarity ranking.
"""

import json
import logging
import math
import hashlib
from typing import List, Optional, Dict, Any

import httpx

from app.config import settings
from app.db_adapter import DatabaseAdapter

logger = logging.getLogger(__name__)

# Default embedding dimension for the keyword fallback
KEYWORD_EMBED_DIM = 256


class EmbeddingService:
    """Generates and stores embeddings for asset text content."""

    def __init__(self):
        self._use_fmapi = bool(settings.databricks_host)
        self._model = settings.embedding_model
        self._dimension = settings.embedding_dimension

    def _build_text(self, asset_type: str, asset: Dict[str, Any]) -> str:
        """Build searchable text from an asset dict (type-specific)."""
        parts: List[str] = []

        # Name is always primary
        if asset.get("name"):
            parts.append(asset["name"])

        # Full name for catalog assets
        if asset.get("full_name"):
            parts.append(asset["full_name"])

        # Description / comment
        for key in ("comment", "description"):
            if asset.get(key):
                parts.append(asset[key])

        # Owner
        if asset.get("owner"):
            parts.append(f"owner: {asset['owner']}")

        # Column names for tables/views
        if asset.get("columns_json"):
            try:
                columns = json.loads(asset["columns_json"])
                col_names = [c.get("name", "") for c in columns if c.get("name")]
                if col_names:
                    parts.append("columns: " + ", ".join(col_names[:50]))
            except (json.JSONDecodeError, TypeError):
                pass

        # Workspace asset path
        if asset.get("path"):
            parts.append(asset["path"])

        # Content preview
        if asset.get("content_preview"):
            parts.append(asset["content_preview"][:500])

        # Agent-specific fields
        if asset.get("capabilities"):
            parts.append(f"capabilities: {asset['capabilities']}")
        if asset.get("skills"):
            try:
                skills = json.loads(asset["skills"])
                skill_names = [s.get("name", "") for s in skills if s.get("name")]
                if skill_names:
                    parts.append("skills: " + ", ".join(skill_names))
            except (json.JSONDecodeError, TypeError):
                pass

        # Type context
        parts.append(f"type: {asset_type}")

        return " ".join(parts)

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single text string."""
        if self._use_fmapi:
            return await self._embed_via_fmapi(text)
        return self._embed_keyword(text)

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Batch-embed multiple text strings."""
        if self._use_fmapi:
            return await self._embed_batch_fmapi(texts)
        return [self._embed_keyword(t) for t in texts]

    async def embed_asset(self, asset_type: str, asset_id: int, asset: Dict[str, Any]) -> None:
        """Generate and store embedding for a single asset."""
        text = self._build_text(asset_type, asset)
        if not text.strip():
            return

        embedding = await self.embed_text(text)
        dim = len(embedding)
        model = self._model if self._use_fmapi else "keyword-hash"

        existing = DatabaseAdapter.get_asset_embedding(asset_type, asset_id)
        if existing:
            DatabaseAdapter.update_asset_embedding(
                existing["id"],
                text_content=text,
                embedding_json=json.dumps(embedding),
                embedding_model=model,
                dimension=dim,
            )
        else:
            DatabaseAdapter.create_asset_embedding(
                asset_type=asset_type,
                asset_id=asset_id,
                text_content=text,
                embedding_json=json.dumps(embedding),
                embedding_model=model,
                dimension=dim,
            )

    async def embed_all_assets(self) -> Dict[str, int]:
        """Embed all un-embedded assets. Returns counts by type."""
        counts: Dict[str, int] = {}

        # Catalog assets
        catalog_assets, total = DatabaseAdapter.list_catalog_assets(page=1, page_size=5000)
        for asset in catalog_assets:
            existing = DatabaseAdapter.get_asset_embedding(asset["asset_type"], asset["id"])
            if not existing:
                await self.embed_asset(asset["asset_type"], asset["id"], asset)
                counts[asset["asset_type"]] = counts.get(asset["asset_type"], 0) + 1

        # Workspace assets
        workspace_assets, total = DatabaseAdapter.list_workspace_assets(page=1, page_size=5000)
        for asset in workspace_assets:
            existing = DatabaseAdapter.get_asset_embedding(asset["asset_type"], asset["id"])
            if not existing:
                await self.embed_asset(asset["asset_type"], asset["id"], asset)
                counts[asset["asset_type"]] = counts.get(asset["asset_type"], 0) + 1

        # Apps
        apps, total = DatabaseAdapter.list_apps(page=1, page_size=500)
        for app in apps:
            existing = DatabaseAdapter.get_asset_embedding("app", app["id"])
            if not existing:
                await self.embed_asset("app", app["id"], app)
                counts["app"] = counts.get("app", 0) + 1

        # Tools
        tools, total = DatabaseAdapter.list_tools(page=1, page_size=500)
        for tool in tools:
            existing = DatabaseAdapter.get_asset_embedding("tool", tool["id"])
            if not existing:
                await self.embed_asset("tool", tool["id"], tool)
                counts["tool"] = counts.get("tool", 0) + 1

        # Agents
        agents, total = DatabaseAdapter.list_agents(page=1, page_size=500)
        for agent in agents:
            existing = DatabaseAdapter.get_asset_embedding("agent", agent["id"])
            if not existing:
                await self.embed_asset("agent", agent["id"], agent)
                counts["agent"] = counts.get("agent", 0) + 1

        return counts

    # --- Databricks FMAPI ---

    async def _embed_via_fmapi(self, text: str) -> List[float]:
        """Call Databricks Foundation Model API for a single embedding."""
        results = await self._embed_batch_fmapi([text])
        return results[0]

    async def _embed_batch_fmapi(self, texts: List[str]) -> List[List[float]]:
        """Batch call to Databricks FMAPI embedding endpoint."""
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient()
        workspace_url = w.config.host.rstrip("/")
        url = f"{workspace_url}/serving-endpoints/{self._model}/invocations"

        headers = {"Content-Type": "application/json"}
        headers.update(w.config.authenticate())

        payload = {"input": texts}

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.error("FMAPI embedding error %d: %s", resp.status_code, resp.text)
                raise ValueError(f"Embedding API error ({resp.status_code}): {resp.text}")
            data = resp.json()

        # Standard OpenAI-compatible response format
        embeddings = []
        for item in sorted(data.get("data", []), key=lambda x: x.get("index", 0)):
            embeddings.append(item["embedding"])

        return embeddings

    # --- Keyword fallback ---

    def _embed_keyword(self, text: str) -> List[float]:
        """
        Generate a pseudo-embedding using deterministic hash-based feature extraction.
        Produces a fixed-size vector from word-level hashing — good enough for
        keyword-overlap similarity without any ML dependencies.
        """
        dim = KEYWORD_EMBED_DIM
        vector = [0.0] * dim
        words = text.lower().split()

        for word in words:
            # Hash each word to a bucket
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = h % dim
            # Use a second hash for sign (simulates random projections)
            sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
            vector[idx] += sign

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector
