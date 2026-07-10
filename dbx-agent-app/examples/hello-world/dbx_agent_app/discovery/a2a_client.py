"""
A2A Client for agent-to-agent communication.

Implements the A2A protocol for discovering and communicating with peer agents.
"""

import json
import uuid
import logging
from typing import Dict, Any, Optional, AsyncIterator

import httpx

logger = logging.getLogger(__name__)


class A2AClientError(Exception):
    """Raised when an A2A operation fails."""
    pass


class A2AClient:
    """
    Async client for A2A protocol communication with peer agents.

    Usage:
        async with A2AClient() as client:
            card = await client.fetch_agent_card("https://app.databricksapps.com")
            result = await client.send_message("https://app.databricksapps.com/api/a2a", "Hello")
    """

    def __init__(self, timeout: float = 60.0):
        """
        Initialize A2A client.

        Args:
            timeout: Request timeout in seconds
        """
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
        """Build authentication headers."""
        headers = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        return headers

    async def fetch_agent_card(
        self,
        base_url: str,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch an agent's A2A protocol agent card.

        Tries /.well-known/agent.json first, then /card as fallback.
        Handles OAuth redirects gracefully (returns error instead of following).

        Args:
            base_url: Base URL of the agent application
            auth_token: Optional OAuth token for authenticated requests

        Returns:
            Agent card JSON data

        Raises:
            A2AClientError: If agent card cannot be fetched

        Example:
            >>> async with A2AClient() as client:
            >>>     card = await client.fetch_agent_card("https://app.databricksapps.com")
            >>>     print(card["name"], card["description"])
        """
        if not self._client:
            raise A2AClientError("Client not initialized. Use async context manager.")

        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        # Use a client that doesn't follow redirects to detect OAuth flows
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as probe_client:
            for path in ["/.well-known/agent.json", "/card"]:
                try:
                    url = base_url.rstrip("/") + path
                    response = await probe_client.get(url, headers=headers)

                    # OAuth redirect detected - app requires interactive auth
                    if response.status_code in (301, 302, 303, 307, 308):
                        logger.debug(f"OAuth redirect detected for {url}")
                        continue

                    if response.status_code == 200:
                        if not response.text or response.text.isspace():
                            logger.debug(f"Empty response body for {url}")
                            continue
                        return response.json()

                except Exception as e:
                    logger.debug(f"Agent card fetch failed for {url}: {e}")
                    continue

        raise A2AClientError(f"Could not fetch agent card from {base_url}")

    async def _jsonrpc_call(
        self,
        url: str,
        method: str,
        params: Dict[str, Any],
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a JSON-RPC 2.0 request to an agent.

        Args:
            url: A2A endpoint URL
            method: JSON-RPC method name (e.g., "message/send")
            params: Method parameters
            auth_token: Optional authentication token

        Returns:
            JSON-RPC result

        Raises:
            A2AClientError: If request fails or returns error
        """
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
                    f"A2A error: {error.get('message', 'Unknown')} "
                    f"(code: {error.get('code')})"
                )

            return result.get("result", {})

        except httpx.TimeoutException as e:
            raise A2AClientError(f"Request to {url} timed out: {e}")
        except httpx.HTTPStatusError as e:
            raise A2AClientError(
                f"HTTP error from {url}: {e.response.status_code}"
            )
        except json.JSONDecodeError as e:
            raise A2AClientError(f"Invalid JSON from {url}: {e}")

    async def send_message(
        self,
        agent_url: str,
        message: str,
        context_id: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to a peer agent using A2A protocol.

        Args:
            agent_url: Agent's A2A endpoint URL
            message: Text message to send
            context_id: Optional conversation context ID
            auth_token: Optional authentication token

        Returns:
            Agent's response

        Example:
            >>> async with A2AClient() as client:
            >>>     response = await client.send_message(
            >>>         "https://app.databricksapps.com/api/a2a",
            >>>         "What are your capabilities?"
            >>>     )
        """
        params: Dict[str, Any] = {
            "message": {
                "messageId": str(uuid.uuid4()),
                "role": "user",
                "parts": [{"text": message}],
            }
        }
        if context_id:
            params["message"]["contextId"] = context_id

        return await self._jsonrpc_call(
            agent_url, "message/send", params, auth_token
        )

    async def send_streaming_message(
        self,
        agent_url: str,
        message: str,
        auth_token: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Send a streaming message and yield SSE events.

        Args:
            agent_url: Agent's A2A endpoint URL
            message: Text message to send
            auth_token: Optional authentication token

        Yields:
            SSE events from the agent's response stream

        Example:
            >>> async with A2AClient() as client:
            >>>     async for event in client.send_streaming_message(url, "Analyze this"):
            >>>         print(event)
        """
        if not self._client:
            raise A2AClientError("Client not initialized. Use async context manager.")

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
