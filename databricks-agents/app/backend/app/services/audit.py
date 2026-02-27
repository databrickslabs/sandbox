"""
Audit logging helper — fire-and-forget recording of mutating API actions.

Usage in route handlers:
    from app.services.audit import record_audit

    record_audit(
        request=request,
        action="create",
        resource_type="agent",
        resource_id=str(agent["id"]),
        resource_name=agent["name"],
    )
"""

import json
import logging
from typing import Optional, Any
from fastapi import Request

logger = logging.getLogger(__name__)


def record_audit(
    request: Request,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    resource_name: Optional[str] = None,
    details: Optional[Any] = None,
) -> None:
    """
    Record an audit log entry. Fire-and-forget — failures are logged
    as warnings but never raised to the caller.

    Args:
        request: The FastAPI Request object (used for user identity + IP).
        action: The mutation type (create, update, delete, crawl, clear).
        resource_type: The kind of resource (agent, collection, etc.).
        resource_id: The ID of the affected resource (stringified).
        resource_name: Human-readable name for the resource.
        details: Extra context dict (will be JSON-serialized).
    """
    try:
        from app.db_adapter import DatabaseAdapter

        user_email = getattr(request.state, "user_email", None) or "local-dev"
        ip_address = request.client.host if request.client else None

        details_str = None
        if details is not None:
            details_str = json.dumps(details) if not isinstance(details, str) else details

        DatabaseAdapter.create_audit_log(
            user_email=user_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details_str,
            ip_address=ip_address,
        )
    except Exception as e:
        logger.warning("Failed to record audit log: %s", e)
