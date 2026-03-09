from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class MCPServerKind(str, enum.Enum):
    """
    MCP Server types.

    - managed: Servers from Databricks MCP catalog (official)
    - external: Third-party MCP servers (GitHub, npm, etc.)
    - custom: User-deployed MCP servers (private)
    """

    MANAGED = "managed"
    EXTERNAL = "external"
    CUSTOM = "custom"


class MCPServer(Base):
    """
    MCP (Model Context Protocol) server configurations.

    Represents an MCP server that provides tools/functions to agents.
    Servers can be managed (Databricks catalog), external (third-party),
    or custom (user-deployed).

    Attributes:
        id: Primary key
        app_id: Foreign key to parent App (nullable for standalone servers)
        server_url: MCP server endpoint URL
        kind: Server type (managed/external/custom)
        uc_connection: Unity Catalog connection name (for governance)
        scopes: Comma-separated OAuth scopes required
    """

    __tablename__ = "mcp_servers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    app_id = Column(
        Integer,
        ForeignKey("apps.id", ondelete="CASCADE"),
        nullable=True,
    )
    server_url = Column(Text, nullable=False)
    kind = Column(
        SQLEnum(MCPServerKind),
        nullable=False,
        default=MCPServerKind.CUSTOM,
    )
    uc_connection = Column(String(255), nullable=True)
    scopes = Column(Text, nullable=True)

    # Relationships
    app = relationship("App", back_populates="mcp_servers")
    tools = relationship(
        "Tool",
        back_populates="mcp_server",
        cascade="all, delete-orphan",
    )
    collection_items = relationship(
        "CollectionItem",
        back_populates="mcp_server",
        cascade="all, delete-orphan",
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_mcp_server_app_id", "app_id"),
        Index("idx_mcp_server_kind", "kind"),
    )

    def __repr__(self) -> str:
        return f"<MCPServer(id={self.id}, url='{self.server_url}', kind='{self.kind.value}')>"
