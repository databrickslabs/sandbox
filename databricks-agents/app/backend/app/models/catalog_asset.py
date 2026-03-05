from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from datetime import datetime
from app.database import Base


class CatalogAsset(Base):
    """
    Unity Catalog asset metadata.

    Represents a table, view, function, model, or volume discovered
    from a Databricks Unity Catalog. Assets are indexed by the
    CatalogCrawlerService and searchable via the Discover UI.

    Attributes:
        id: Primary key
        asset_type: One of table, view, function, model, volume
        catalog: UC catalog name
        schema_name: UC schema name
        name: Asset name (table/view/function/model/volume name)
        full_name: Three-level namespace (catalog.schema.name)
        owner: Asset owner
        comment: Asset description/comment from UC
        columns_json: JSON blob of column definitions [{name, type, comment, nullable}]
        tags_json: JSON blob of UC tags
        properties_json: JSON blob of UC properties/metadata
        data_source_format: Storage format (DELTA, PARQUET, CSV, etc.)
        table_type: MANAGED, EXTERNAL, VIEW
        created_at: When indexed
        updated_at: Last index update
        last_indexed_at: Timestamp of most recent crawl that touched this row
    """

    __tablename__ = "catalog_assets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    asset_type = Column(String(50), nullable=False)
    catalog = Column(String(255), nullable=False)
    schema_name = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    full_name = Column(String(767), nullable=False, unique=True)
    owner = Column(String(255), nullable=True)
    comment = Column(Text, nullable=True)
    columns_json = Column(Text, nullable=True)
    tags_json = Column(Text, nullable=True)
    properties_json = Column(Text, nullable=True)
    data_source_format = Column(String(50), nullable=True)
    table_type = Column(String(50), nullable=True)
    row_count = Column(Integer, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_indexed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_catalog_asset_type", "asset_type"),
        Index("idx_catalog_asset_catalog_schema", "catalog", "schema_name"),
        Index("idx_catalog_asset_full_name", "full_name"),
        Index("idx_catalog_asset_owner", "owner"),
    )

    def __repr__(self) -> str:
        return f"<CatalogAsset(id={self.id}, type='{self.asset_type}', full_name='{self.full_name}')>"
