"""
Unified search endpoint — semantic + keyword search across all asset types.
"""

import logging
from fastapi import APIRouter, HTTPException

from app.schemas.search import (
    SearchRequest,
    SearchResponse,
    EmbedStatusResponse,
)
from app.services.search import SearchService
from app.services.embedding import EmbeddingService
from app.db_adapter import DatabaseAdapter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Search"])


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Unified semantic search across all indexed assets.

    Combines vector similarity with keyword matching for hybrid ranking.
    """
    service = SearchService()
    results, search_mode = await service.search(
        query=request.query,
        types=request.types,
        catalogs=request.catalogs,
        owner=request.owner,
        limit=request.limit,
    )

    return SearchResponse(
        query=request.query,
        total=len(results),
        results=results,
        search_mode=search_mode,
    )


@router.post("/search/embed-all", response_model=EmbedStatusResponse)
async def embed_all_assets():
    """
    Generate embeddings for all un-embedded assets.

    This is typically called after a crawl to ensure all new assets
    have embeddings for semantic search.
    """
    service = EmbeddingService()
    counts = await service.embed_all_assets()

    total_embedded = sum(counts.values())
    logger.info("Embedded %d new assets: %s", total_embedded, counts)

    stats = DatabaseAdapter.get_embedding_stats()

    return EmbedStatusResponse(
        total_assets=stats["total_assets"],
        embedded_assets=stats["embedded_assets"],
        pending_assets=stats["pending_assets"],
        embedding_model=service._model if service._use_fmapi else "keyword-hash",
        dimension=service._dimension if service._use_fmapi else 256,
    )


@router.get("/search/embed-status", response_model=EmbedStatusResponse)
async def embed_status():
    """Get the current embedding coverage status."""
    service = EmbeddingService()
    stats = DatabaseAdapter.get_embedding_stats()

    return EmbedStatusResponse(
        total_assets=stats["total_assets"],
        embedded_assets=stats["embedded_assets"],
        pending_assets=stats["pending_assets"],
        embedding_model=service._model if service._use_fmapi else "keyword-hash",
        dimension=service._dimension if service._use_fmapi else 256,
    )
