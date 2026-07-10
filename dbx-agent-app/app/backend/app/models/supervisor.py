from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Supervisor(Base):
    """
    Generated supervisors metadata tracking.

    Tracks supervisors that have been generated from collections,
    including when they were generated and where they are deployed.

    Attributes:
        id: Primary key
        collection_id: Reference to the collection used for generation
        app_name: Generated app name
        generated_at: Timestamp when supervisor was generated
        deployed_url: URL where the supervisor is deployed (optional)
    """

    __tablename__ = "supervisors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    collection_id = Column(
        Integer,
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
    )
    app_name = Column(String(255), nullable=False)
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deployed_url = Column(Text, nullable=True)

    # Relationships
    collection = relationship("Collection", backref="supervisors")

    # Indexes for performance
    __table_args__ = (
        Index("idx_supervisor_collection_id", "collection_id"),
        Index("idx_supervisor_app_name", "app_name"),
    )

    def __repr__(self) -> str:
        return f"<Supervisor(id={self.id}, app_name='{self.app_name}')>"
