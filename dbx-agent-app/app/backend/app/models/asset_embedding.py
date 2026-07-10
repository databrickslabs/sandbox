"""
AssetEmbedding model — stores vector embeddings for indexed assets.

Each row links an asset (by type + ID) to its embedding vector,
enabling semantic search via cosine similarity.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.sql import func
from app.database import Base


class AssetEmbedding(Base):
    __tablename__ = "asset_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_type = Column(String(50), nullable=False)  # e.g. "table", "notebook", "app"
    asset_id = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)  # the text that was embedded
    embedding_json = Column(Text, nullable=False)  # JSON-serialized float array
    embedding_model = Column(String(100), nullable=False)
    dimension = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_asset_embedding_asset", "asset_type", "asset_id", unique=True),
        Index("ix_asset_embedding_model", "embedding_model"),
    )
