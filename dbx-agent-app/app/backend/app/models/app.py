from sqlalchemy import Column, Integer, String, Text, Index
from sqlalchemy.orm import relationship
from app.database import Base


class App(Base):
    """
    Databricks Apps metadata.

    Represents a Databricks App that may host one or more MCP servers.
    Apps are discovered from the workspace and registered in the catalog.

    Attributes:
        id: Primary key
        name: App name (e.g., "sgp-research-app")
        owner: App owner (username or service principal)
        url: Deployed app URL
        tags: Comma-separated tags for filtering
        manifest_url: URL to app.yaml or manifest file
    """

    __tablename__ = "apps"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    owner = Column(String(255), nullable=True)
    url = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    manifest_url = Column(Text, nullable=True)

    # Relationships
    mcp_servers = relationship(
        "MCPServer",
        back_populates="app",
        cascade="all, delete-orphan",
    )
    collection_items = relationship(
        "CollectionItem",
        back_populates="app",
        cascade="all, delete-orphan",
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_app_name", "name"),
        Index("idx_app_owner", "owner"),
    )

    def __repr__(self) -> str:
        return f"<App(id={self.id}, name='{self.name}', owner='{self.owner}')>"
