from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from datetime import datetime
from app.database import Base


class WorkspaceAsset(Base):
    """
    Databricks workspace object metadata.

    Represents a notebook, job, dashboard, SQL query, pipeline, cluster,
    or experiment discovered from a Databricks workspace. Assets are indexed
    by the WorkspaceCrawlerService and searchable via the Discover UI.

    Attributes:
        id: Primary key
        asset_type: One of notebook, job, dashboard, sql_query, pipeline, cluster, experiment
        workspace_host: Databricks workspace URL
        path: Workspace path or resource identifier
        name: Human-readable name
        owner: Asset owner/creator
        description: Asset description
        language: For notebooks: python, sql, r, scala
        tags_json: JSON blob of tags/labels
        metadata_json: Type-specific metadata (job schedule, cluster config, etc.)
        content_preview: First 500 chars of content for search matching
        created_at: When indexed
        updated_at: Last index update
        last_indexed_at: Timestamp of most recent crawl
    """

    __tablename__ = "workspace_assets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    asset_type = Column(String(50), nullable=False)
    workspace_host = Column(String(512), nullable=False)
    path = Column(Text, nullable=False)
    name = Column(String(255), nullable=False)
    owner = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    language = Column(String(50), nullable=True)
    tags_json = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    content_preview = Column(Text, nullable=True)
    resource_id = Column(String(255), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_indexed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_workspace_asset_type", "asset_type"),
        Index("idx_workspace_asset_host", "workspace_host"),
        Index("idx_workspace_asset_owner", "owner"),
        Index("idx_workspace_asset_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<WorkspaceAsset(id={self.id}, type='{self.asset_type}', name='{self.name}')>"
