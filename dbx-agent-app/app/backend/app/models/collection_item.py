from sqlalchemy import Column, Integer, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class CollectionItem(Base):
    """
    Many-to-many join table for collection membership.

    Represents an item in a collection. Each item can be one of:
    - An App (app_id set, others null)
    - An MCP Server (mcp_server_id set, others null)
    - A Tool (tool_id set, others null)

    Exactly one of the foreign keys must be non-null (enforced by check constraint).

    Attributes:
        id: Primary key
        collection_id: Foreign key to parent collection
        app_id: Foreign key to App (nullable)
        mcp_server_id: Foreign key to MCP Server (nullable)
        tool_id: Foreign key to Tool (nullable)
    """

    __tablename__ = "collection_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    collection_id = Column(
        Integer,
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
    )
    app_id = Column(
        Integer,
        ForeignKey("apps.id", ondelete="CASCADE"),
        nullable=True,
    )
    mcp_server_id = Column(
        Integer,
        ForeignKey("mcp_servers.id", ondelete="CASCADE"),
        nullable=True,
    )
    tool_id = Column(
        Integer,
        ForeignKey("tools.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Relationships
    collection = relationship("Collection", back_populates="items")
    app = relationship("App", back_populates="collection_items")
    mcp_server = relationship("MCPServer", back_populates="collection_items")
    tool = relationship("Tool", back_populates="collection_items")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_collection_item_collection_id", "collection_id"),
        Index("idx_collection_item_app_id", "app_id"),
        Index("idx_collection_item_mcp_server_id", "mcp_server_id"),
        Index("idx_collection_item_tool_id", "tool_id"),
        # Ensure exactly one of the foreign keys is set
        CheckConstraint(
            "(app_id IS NOT NULL AND mcp_server_id IS NULL AND tool_id IS NULL) OR "
            "(app_id IS NULL AND mcp_server_id IS NOT NULL AND tool_id IS NULL) OR "
            "(app_id IS NULL AND mcp_server_id IS NULL AND tool_id IS NOT NULL)",
            name="chk_collection_item_exactly_one_ref",
        ),
    )

    def __repr__(self) -> str:
        ref = (
            f"app_id={self.app_id}"
            if self.app_id
            else f"server_id={self.mcp_server_id}"
            if self.mcp_server_id
            else f"tool_id={self.tool_id}"
        )
        return f"<CollectionItem(id={self.id}, collection_id={self.collection_id}, {ref})>"
