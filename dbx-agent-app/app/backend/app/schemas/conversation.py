"""
Pydantic schemas for the conversations API.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class ConversationMessageResponse(BaseModel):
    """Single message within a conversation."""

    id: int
    conversation_id: str
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
    trace_id: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ConversationListItem(BaseModel):
    """Conversation summary for list views."""

    id: str
    title: str
    user_email: Optional[str] = None
    collection_id: Optional[int] = None
    message_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Full conversation with messages."""

    id: str
    title: str
    user_email: Optional[str] = None
    collection_id: Optional[int] = None
    message_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    messages: List[ConversationMessageResponse] = []

    class Config:
        from_attributes = True


class ConversationRenameRequest(BaseModel):
    """Request to rename a conversation."""

    title: str = Field(..., min_length=1, max_length=255)
