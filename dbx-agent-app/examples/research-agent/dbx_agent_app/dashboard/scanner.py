"""
Dashboard scanner — wraps AgentDiscovery + A2AClient with caching and MCP proxy.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

import httpx

from ..discovery import AgentDiscovery, DiscoveredAgent, A2AClient, A2AClientError

logger = logging.getLogger(__name__)


class DashboardScanner:
    """
    Thin wrapper around AgentDiscovery that adds result caching
    and MCP JSON-RPC proxying for the dashboard UI.
    """

    def __init__(self, profile: Optional[str] = None):
        self._discovery = AgentDiscovery(profile=profile)
        self._agents: List[DiscoveredAgent] = []
        self._scan_lock = asyncio.Lock()
        self._scanned = False

    async def scan(self) -> List[DiscoveredAgent]:
        """Run workspace discovery and cache results. Thread-safe via asyncio.Lock."""
        async with self._scan_lock:
            result = await self._discovery.discover_agents()
            self._agents = result.agents
            self._scanned = True
            if result.errors:
                for err in result.errors:
                    logger.warning("Discovery error: %s", err)
            return self._agents

    def get_agents(self) -> List[DiscoveredAgent]:
        """Return cached agent list from the last scan."""
        return list(self._agents)

    def get_agent_by_name(self, name: str) -> Optional[DiscoveredAgent]:
        """Look up a cached agent by name."""
        for agent in self._agents:
            if agent.name == name or agent.app_name == name:
                return agent
        return None

    @property
    def workspace_token(self) -> Optional[str]:
        """Auth token extracted during discovery, used for cross-app requests."""
        return self._discovery._workspace_token

    async def get_agent_card(self, endpoint_url: str) -> Dict[str, Any]:
        """Fetch the full agent card JSON from a remote agent."""
        async with A2AClient(timeout=10.0) as client:
            return await client.fetch_agent_card(
                endpoint_url, auth_token=self.workspace_token
            )

    async def proxy_mcp(self, endpoint_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Forward a JSON-RPC request to an agent's MCP endpoint.

        Args:
            endpoint_url: Agent base URL
            payload: Complete JSON-RPC 2.0 request body

        Returns:
            JSON-RPC response from the agent
        """
        mcp_url = endpoint_url.rstrip("/") + "/api/mcp"
        headers = {"Content-Type": "application/json"}
        if self.workspace_token:
            headers["Authorization"] = f"Bearer {self.workspace_token}"

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
            response = await http.post(mcp_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
