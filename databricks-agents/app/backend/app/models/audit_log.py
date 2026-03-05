from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from datetime import datetime
from app.database import Base


class AuditLog(Base):
    """
    Append-only audit log for tracking mutating API actions.

    Records who did what, when, to which resource — supporting
    enterprise compliance and operational visibility.
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    user_email = Column(String(255), nullable=False)
    action = Column(String(50), nullable=False)  # create, update, delete, crawl, clear
    resource_type = Column(String(50), nullable=False)  # agent, collection, catalog_asset, etc.
    resource_id = Column(String(100), nullable=True)  # String to support both int IDs and UUIDs
    resource_name = Column(String(255), nullable=True)
    details = Column(Text, nullable=True)  # JSON text for extra context
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6

    __table_args__ = (
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_user_email", "user_email"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_resource_type", "resource_type"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action='{self.action}', resource='{self.resource_type}/{self.resource_id}')>"
