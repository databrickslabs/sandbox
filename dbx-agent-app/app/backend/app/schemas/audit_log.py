"""
Pydantic schemas for the audit log API.
"""

from pydantic import BaseModel, Field
from typing import Optional


class AuditLogResponse(BaseModel):
    """Single audit log entry."""

    id: int
    timestamp: str = Field(..., description="ISO timestamp of the action")
    user_email: str = Field(..., description="Email of the user who performed the action")
    action: str = Field(..., description="Action type (create, update, delete, crawl, clear)")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: Optional[str] = Field(None, description="ID of the affected resource")
    resource_name: Optional[str] = Field(None, description="Human-readable name of the resource")
    details: Optional[str] = Field(None, description="JSON string with extra context")
    ip_address: Optional[str] = Field(None, description="Client IP address")

    class Config:
        from_attributes = True
