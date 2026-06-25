from sqlalchemy import Column, Integer, String, Text, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Collection(Base):
    """
    Curated collections of tools/agents/servers.

    Collections are user-defined groupings of MCP resources (apps, servers, tools).
    They serve as the basis for generating supervisors and orchestrating multi-agent
    workflows. A collection can contain any combination of apps, servers, or individual tools.

    Attributes:
        id: Primary key
        name: Collection name (e.g., "Expert Research Toolkit")
        description: Human-readable description of the collection's purpose
    """

    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # Relationships
    items = relationship(
        "CollectionItem",
        back_populates="collection",
        cascade="all, delete-orphan",
    )

    # Indexes for performance
    __table_args__ = (Index("idx_collection_name", "name"),)

    def __repr__(self) -> str:
        return f"<Collection(id={self.id}, name='{self.name}')>"
