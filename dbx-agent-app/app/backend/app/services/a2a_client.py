"""
A2A Client — outbound calls to peer agents following the A2A protocol.

Follows the same httpx async + context manager pattern as mcp_client.py.
VERSION: 2026-02-25-v2 (OAuth fix)
"""

import json
import uuid
import logging
from typing import Dict, Any, Optional, AsyncIterator

import httpx

logger = logging.getLogger(__name__)
logger.info("[A2A-CLIENT] Module loaded - VERSION: 2026-02-25-v2 with OAuth redirect fix")


class A2AClientError(Exception):
    """Raised when an A2A call fails."""
    pass


class A2AClient:
    """
    Async client for sending A2A JSON-RPC requests to peer agents.

    Usage:
        async with A2AClient() as client:
            result = await client.send_message(agent_url, "Search for AI experts")
    """

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    def _auth_headers(self, auth_token: Optional[str] = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        return headers

    async def _jsonrpc_call(
        self,
        url: str,
        method: str,
        params: Dict[str, Any],
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a JSON-RPC 2.0 request and return the result."""
        if not self._client:
            raise A2AClientError("Client not initialized. Use async context manager.")

        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params,
        }

        try:
            response = await self._client.post(
                url,
                json=payload,
                headers=self._auth_headers(auth_token),
            )
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                error = result["error"]
                raise A2AClientError(
                    f"A2A error: {error.get('message', 'Unknown')} (code: {error.get('code')})"
                )

            return result.get("result", {})

        except httpx.TimeoutException as e:
            raise A2AClientError(f"A2A request to {url} timed out: {e}")
        except httpx.HTTPStatusError as e:
            raise A2AClientError(f"A2A HTTP error from {url}: {e.response.status_code}")
        except json.JSONDecodeError as e:
            raise A2AClientError(f"Invalid JSON from {url}: {e}")

    async def send_message(
        self,
        agent_url: str,
        message: str,
        context_id: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a message/send request to a peer agent."""
        params: Dict[str, Any] = {
            "message": {
                "messageId": str(uuid.uuid4()),
                "role": "user",
                "parts": [{"text": message}],
            }
        }
        if context_id:
            params["message"]["contextId"] = context_id

        return await self._jsonrpc_call(agent_url, "message/send", params, auth_token)

    async def send_streaming_message(
        self,
        agent_url: str,
        message: str,
        auth_token: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Send a streaming message and yield SSE events."""
        if not self._client:
            raise A2AClientError("Client not initialized. Use async context manager.")

        # Streaming endpoint is /stream relative to the agent's A2A URL
        stream_url = agent_url.rstrip("/") + "/stream"

        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": message}],
                }
            },
        }

        async with self._client.stream(
            "POST",
            stream_url,
            json=payload,
            headers=self._auth_headers(auth_token),
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        yield json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue

    async def get_task(
        self,
        agent_url: str,
        task_id: str,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get a task by ID from a peer agent."""
        return await self._jsonrpc_call(
            agent_url, "tasks/get", {"id": task_id}, auth_token
        )

    async def cancel_task(
        self,
        agent_url: str,
        task_id: str,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cancel a task on a peer agent."""
        return await self._jsonrpc_call(
            agent_url, "tasks/cancel", {"id": task_id}, auth_token
        )

    async def fetch_agent_card(
        self, base_url: str, auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch an agent's Agent Card from /.well-known/agent.json or /card."""
        if not self._client:
            raise A2AClientError("Client not initialized. Use async context manager.")

        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        # Try well-known path first, then /card
        # Use a fresh client that does NOT follow redirects to avoid OAuth session contamination
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as probe_client:
            for path in ["/.well-known/agent.json", "/card"]:
                try:
                    url = base_url.rstrip("/") + path
                    response = await probe_client.get(url, headers=headers)

                    # Explicit handling of OAuth redirects (3xx status codes)
                    if response.status_code in (301, 302, 303, 307, 308):
                        # OAuth redirect detected - app doesn't support SP auth
                        logger.debug(f"OAuth redirect detected for {url} (status {response.status_code})")
                        continue

                    if response.status_code == 200:
                        # Check if response body is empty
                        if not response.text or response.text.isspace():
                            logger.debug(f"Empty response body for {url}")
                            continue
                        return response.json()
                except Exception as e:
                    logger.warning(f"Agent card fetch failed for {url}: {type(e).__name__}: {e}")
                    continue

        raise A2AClientError(f"Could not fetch Agent Card from {base_url}")
