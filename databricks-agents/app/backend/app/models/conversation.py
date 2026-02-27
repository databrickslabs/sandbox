from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from datetime import datetime
from app.database import Base


class Conversation(Base):
    """
    Persistent chat conversation.

    Stores conversation metadata for the chat interface. Each conversation
    contains an ordered list of messages and is optionally scoped to a
    tool collection.

    Attributes:
        id: UUID string primary key (generated client- or server-side)
        title: Auto-generated from first user message, renamable
        user_email: Owner of the conversation
        collection_id: Optional FK to the tool collection used
        created_at: When the conversation started
        updated_at: Last message timestamp
    """

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False, default="New conversation")
    user_email = Column(String(255), nullable=True)
    collection_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_conversation_user", "user_email"),
        Index("idx_conversation_updated", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<Conversation(id='{self.id}', title='{self.title}')>"


class ConversationMessage(Base):
    """
    Individual message within a conversation.

    Stores each user/assistant message with optional trace linkage
    for the inspector panel.

    Attributes:
        id: Auto-increment primary key
        conversation_id: FK to parent conversation
        role: 'user' or 'assistant'
        content: Message text
        trace_id: Optional link to MLflow trace
        created_at: Message timestamp
    """

    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    trace_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_conv_msg_conversation", "conversation_id"),
        Index("idx_conv_msg_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ConversationMessage(id={self.id}, conversation_id='{self.conversation_id}', role='{self.role}')>"
