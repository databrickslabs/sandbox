from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Tool(Base):
    """
    Individual tools/functions from MCP servers.

    Represents a single tool exposed by an MCP server. Tools are discovered
    by querying the MCP server's tool listing endpoint. Each tool has a name,
    description, and parameter schema (JSON Schema format).

    Attributes:
        id: Primary key
        mcp_server_id: Foreign key to parent MCP server
        name: Tool name (e.g., "search_transcripts")
        description: Human-readable description
        parameters: JSON Schema for tool parameters (stored as text)
    """

    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mcp_server_id = Column(
        Integer,
        ForeignKey("mcp_servers.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    parameters = Column(Text, nullable=True)  # JSON Schema as text

    # Relationships
    mcp_server = relationship("MCPServer", back_populates="tools")
    collection_items = relationship(
        "CollectionItem",
        back_populates="tool",
        cascade="all, delete-orphan",
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_tool_mcp_server_id", "mcp_server_id"),
        Index("idx_tool_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<Tool(id={self.id}, name='{self.name}', server_id={self.mcp_server_id})>"
