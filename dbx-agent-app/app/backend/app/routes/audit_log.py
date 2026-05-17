"""
Read-only endpoints for the audit log.
"""

import logging
import math
from typing import Optional
from fastapi import APIRouter, Query, status

from app.db_adapter import WarehouseDB
from app.schemas.audit_log import AuditLogResponse
from app.schemas.common import PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit-log", tags=["Audit Log"])


@router.get(
    "",
    response_model=PaginatedResponse[AuditLogResponse],
    status_code=status.HTTP_200_OK,
    summary="List Audit Log Entries",
    description="Query audit log entries with optional filters and pagination",
)
def list_audit_log(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    date_from: Optional[str] = Query(None, description="Start date (ISO format)"),
    date_to: Optional[str] = Query(None, description="End date (ISO format)"),
) -> PaginatedResponse[AuditLogResponse]:
    """List audit log entries with optional filters."""
    entries, total = WarehouseDB.list_audit_logs(
        page=page,
        page_size=page_size,
        user_email=user_email,
        action=action,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
    )
    total = int(total) if total else 0  # Convert string to int from warehouse
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse(
        items=[AuditLogResponse(**e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
