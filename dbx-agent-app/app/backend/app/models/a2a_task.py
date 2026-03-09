from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from datetime import datetime
from app.database import Base


class A2ATask(Base):
    """
    A2A Task entity — tracks agent-to-agent task lifecycle.

    Each task corresponds to a message/send call and tracks its state
    through submitted → working → completed/failed/canceled.
    """

    __tablename__ = "a2a_tasks"

    id = Column(String(36), primary_key=True)
    agent_id = Column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    context_id = Column(String(36), nullable=True)
    status = Column(String(32), nullable=False, default="submitted")
    messages = Column(Text, nullable=True)       # JSON array of A2A Message objects
    artifacts = Column(Text, nullable=True)      # JSON array of A2A Artifact objects
    metadata_json = Column(Text, nullable=True)  # Task-level metadata
    webhook_url = Column(Text, nullable=True)    # Push notification URL
    webhook_token = Column(Text, nullable=True)  # Push notification auth token
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_a2a_task_agent_id", "agent_id"),
        Index("idx_a2a_task_context_id", "context_id"),
        Index("idx_a2a_task_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<A2ATask(id={self.id}, agent_id={self.agent_id}, status='{self.status}')>"
