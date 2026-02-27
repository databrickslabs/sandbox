"""
A2A Push Notification Service — fires HTTP POST to registered webhooks on task state transitions.
"""

import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


async def send_push_notification(
    webhook_url: str,
    task_id: str,
    status: str,
    webhook_token: Optional[str] = None,
    artifacts: Optional[str] = None,
) -> bool:
    """
    Fire a push notification to a registered webhook URL.

    Returns True on success, False on failure (best-effort, never raises).
    """
    headers = {"Content-Type": "application/json"}
    if webhook_token:
        headers["Authorization"] = f"Bearer {webhook_token}"

    payload = {
        "taskId": task_id,
        "status": status,
    }

    if artifacts:
        try:
            payload["artifacts"] = json.loads(artifacts) if isinstance(artifacts, str) else artifacts
        except (json.JSONDecodeError, TypeError):
            pass

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info("Push notification sent: task=%s status=%s url=%s", task_id, status, webhook_url)
            return True
    except Exception as e:
        logger.warning("Push notification failed: task=%s url=%s error=%s", task_id, webhook_url, e)
        return False
