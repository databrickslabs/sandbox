"""
Conversation CRUD routes.

Provides endpoints to list, get, rename, and delete persisted chat conversations.
"""

import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, Query, status

from app.db_adapter import DatabaseAdapter
from app.schemas.conversation import (
    ConversationListItem,
    ConversationResponse,
    ConversationRenameRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=Dict)
async def list_conversations(
    user_email: str = Query(None, description="Filter by user email"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """List conversations, newest first."""
    items, total = DatabaseAdapter.list_conversations(
        user_email=user_email, page=page, page_size=page_size
    )
    return {
        "conversations": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    """Get a conversation with all its messages."""
    conv = DatabaseAdapter.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )
    return conv


@router.patch("/{conversation_id}", response_model=ConversationListItem)
async def rename_conversation(conversation_id: str, body: ConversationRenameRequest):
    """Rename a conversation."""
    conv = DatabaseAdapter.update_conversation_title(conversation_id, body.title)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )
    return conv


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    deleted = DatabaseAdapter.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )
