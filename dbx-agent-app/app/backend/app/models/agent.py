from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Agent(Base):
    """
    First-class agent entity in the registry.

    Represents a discoverable, manageable agent that links to a Collection
    (its tool set) and carries its own metadata: name, description,
    capability tags, status, and endpoint URL.
    """

    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    capabilities = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="draft")
    collection_id = Column(
        Integer,
        ForeignKey("collections.id", ondelete="SET NULL"),
        nullable=True,
    )
    app_id = Column(
        Integer,
        ForeignKey("apps.id", ondelete="CASCADE"),
        nullable=True,
        comment="Link to the backing Databricks App (if this agent is app-based)",
    )
    endpoint_url = Column(Text, nullable=True)

    # A2A Protocol fields
    auth_token = Column(Text, nullable=True)
    a2a_capabilities = Column(Text, nullable=True)  # JSON: {"streaming": true, "pushNotifications": false}
    skills = Column(Text, nullable=True)  # JSON array: [{"id":"search","name":"Search","description":"...","tags":["rag"]}]
    protocol_version = Column(String(20), nullable=True, default="0.3.0")
    system_prompt = Column(Text, nullable=True)  # Rich persona / instructions for LLM

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    collection = relationship("Collection", backref="agents")
    app = relationship("App", backref="agent", uselist=False)

    # Indexes for performance
    __table_args__ = (
        Index("idx_agent_name", "name"),
        Index("idx_agent_collection_id", "collection_id"),
    )

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name='{self.name}')>"
