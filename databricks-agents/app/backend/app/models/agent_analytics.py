from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from datetime import datetime
from app.database import Base


class AgentAnalytics(Base):
    """Tracks per-invocation performance metrics for agents."""

    __tablename__ = "agent_analytics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    task_description = Column(Text, nullable=True)
    success = Column(Integer, default=1)  # 0 or 1
    latency_ms = Column(Integer, nullable=True)
    quality_score = Column(Integer, nullable=True)  # 1-5, from LLM evaluation
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_analytics_agent_id", "agent_id"),
        Index("idx_analytics_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AgentAnalytics(id={self.id}, agent_id={self.agent_id}, success={self.success})>"
