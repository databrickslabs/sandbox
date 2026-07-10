"""
AssetRelationship model — directed edges in the knowledge graph.

Each row represents a relationship between two assets:
  source (type + id) --[relationship_type]--> target (type + id)

Examples:
  - table A reads_from table B
  - job X writes_to table Y
  - notebook N depends_on table T
  - dashboard D reads_from table T
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.sql import func
from app.database import Base


class AssetRelationship(Base):
    __tablename__ = "asset_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Source node
    source_type = Column(String(50), nullable=False)  # e.g. "table", "job", "notebook"
    source_id = Column(Integer, nullable=False)
    source_name = Column(String(767), nullable=True)  # denormalized for fast graph queries

    # Target node
    target_type = Column(String(50), nullable=False)
    target_id = Column(Integer, nullable=False)
    target_name = Column(String(767), nullable=True)  # denormalized

    # Edge metadata
    relationship_type = Column(String(50), nullable=False)
    # reads_from, writes_to, depends_on, created_by,
    # uses_model, derived_from, scheduled_by, consumes
    metadata_json = Column(Text, nullable=True)  # extra context (column mappings, etc.)

    discovered_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_rel_source", "source_type", "source_id"),
        Index("ix_rel_target", "target_type", "target_id"),
        Index("ix_rel_type", "relationship_type"),
        Index(
            "ix_rel_unique_edge",
            "source_type", "source_id", "target_type", "target_id", "relationship_type",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AssetRelationship("
            f"{self.source_type}:{self.source_id} "
            f"--[{self.relationship_type}]--> "
            f"{self.target_type}:{self.target_id})>"
        )
