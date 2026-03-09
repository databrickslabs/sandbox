"""
Agent discovery for Databricks Apps.

Discovers agent-enabled Databricks Apps by scanning workspace apps
and probing for A2A protocol agent cards.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from databricks.sdk import WorkspaceClient

from .a2a_client import A2AClient, A2AClientError

logger = logging.getLogger(__name__)

# Agent card probe paths and timeout
AGENT_CARD_PATHS = ["/.well-known/agent.json", "/card"]
AGENT_CARD_PROBE_TIMEOUT = 5.0


@dataclass
class DiscoveredAgent:
    """
    An agent discovered from a Databricks App.

    Attributes:
        name: Agent name (from agent card or app name)
        endpoint_url: Agent's base URL
        description: Agent description (from agent card)
        capabilities: Comma-separated list of capabilities
        protocol_version: A2A protocol version
        app_name: Name of the backing Databricks App
    """
    name: str
    endpoint_url: str
    app_name: str
    description: Optional[str] = None
    capabilities: Optional[str] = None
    protocol_version: Optional[str] = None


@dataclass
class AgentDiscoveryResult:
    """
    Results from agent discovery operation.

    Attributes:
        agents: List of discovered agents
        errors: List of error messages encountered during discovery
    """
    agents: List[DiscoveredAgent]
    errors: List[str]


class AgentDiscovery:
    """
    Discovers agent-enabled Databricks Apps in a workspace.

    Scans running Databricks Apps and probes for A2A protocol agent cards
    to identify which apps are agents.

    Usage:
        discovery = AgentDiscovery(profile="my-profile")
        result = await discovery.discover_agents()
        for agent in result.agents:
            print(f"Found agent: {agent.name} at {agent.endpoint_url}")
    """

    def __init__(self, profile: Optional[str] = None):
        """
        Initialize agent discovery.

        Args:
            profile: Databricks CLI profile name (uses default if not specified)
        """
        self.profile = profile
        self._workspace_token: Optional[str] = None

    async def discover_agents(self) -> AgentDiscoveryResult:
        """
        Discover all agent-enabled Databricks Apps in the workspace.

        Returns:
            AgentDiscoveryResult with discovered agents and any errors

        Example:
            >>> discovery = AgentDiscovery(profile="my-profile")
            >>> result = await discovery.discover_agents()
            >>> print(f"Found {len(result.agents)} agents")
        """
        agents: List[DiscoveredAgent] = []
        errors: List[str] = []

        try:
            app_list = await self._list_workspace_apps()
        except Exception as e:
            logger.error("Workspace app listing failed: %s", e)
            return AgentDiscoveryResult(
                agents=[],
                errors=[f"Failed to list workspace apps: {e}"],
            )

        if not app_list:
            return AgentDiscoveryResult(agents=[], errors=[])

        # Probe each running app for agent card in parallel
        probe_tasks = [
            self._probe_app_for_agent(app_info)
            for app_info in app_list
            if app_info.get("url")
        ]

        if probe_tasks:
            probe_results = await asyncio.gather(
                *probe_tasks, return_exceptions=True
            )

            for result in probe_results:
                if isinstance(result, Exception):
                    errors.append(str(result))
                elif result is not None:
                    agents.append(result)

        logger.info(
            "Agent discovery: %d apps checked, %d agents found",
            len(app_list), len(agents)
        )

        return AgentDiscoveryResult(agents=agents, errors=errors)

    async def _list_workspace_apps(self) -> List[Dict[str, Any]]:
        """
        Enumerate Databricks Apps in the workspace.

        Returns:
            List of running apps with name, url, owner
        """
        def _list_sync() -> tuple:
            client = (
                WorkspaceClient(profile=self.profile)
                if self.profile
                else WorkspaceClient()
            )

            # Extract auth token for cross-app requests
            auth_headers = client.config.authenticate()
            auth_val = auth_headers.get("Authorization", "")
            token = auth_val[7:] if auth_val.startswith("Bearer ") else None

            results = []
            for app in client.apps.list():
                # Check if app is running via compute_status or deployment status
                compute_state = None
                cs = getattr(app, "compute_status", None)
                if cs:
                    compute_state = str(getattr(cs, "state", ""))

                deploy_state = None
                dep = getattr(app, "active_deployment", None)
                if dep:
                    dep_status = getattr(dep, "status", None)
                    if dep_status:
                        deploy_state = str(getattr(dep_status, "state", ""))

                app_url = getattr(app, "url", None) or ""
                app_url = app_url.rstrip("/") if app_url else ""

                results.append({
                    "name": app.name,
                    "url": app_url,
                    "owner": getattr(app, "creator", None) or getattr(app, "updater", None),
                    "compute_state": compute_state,
                    "deploy_state": deploy_state,
                })

            return results, token

        loop = asyncio.get_event_loop()
        result_tuple = await loop.run_in_executor(None, _list_sync)
        all_apps, workspace_token = result_tuple

        # Store token for probing
        self._workspace_token = workspace_token

        # Filter to running apps
        running = [
            a for a in all_apps
            if a.get("url") and (
                "ACTIVE" in (a.get("compute_state") or "")
                or "SUCCEEDED" in (a.get("deploy_state") or "")
            )
        ]

        logger.info(
            "Workspace apps: %d total, %d running",
            len(all_apps), len(running)
        )

        return running

    async def _probe_app_for_agent(
        self,
        app_info: Dict[str, Any],
    ) -> Optional[DiscoveredAgent]:
        """
        Probe a Databricks App for an A2A agent card.

        Args:
            app_info: App metadata from workspace listing

        Returns:
            DiscoveredAgent if agent card found, None otherwise
        """
        app_url = app_info["url"]
        app_name = app_info["name"]

        token = self._workspace_token
        agent_card = None

        try:
            logger.debug(f"Probing app '{app_name}' at {app_url}")
            async with A2AClient(timeout=AGENT_CARD_PROBE_TIMEOUT) as client:
                agent_card = await client.fetch_agent_card(app_url, auth_token=token)
                logger.info(f"Found agent card for '{app_name}'")
        except A2AClientError as e:
            logger.debug(f"No agent card for '{app_name}': {e}")
            return None
        except Exception as e:
            logger.warning(f"Probe failed for '{app_name}': {e}")
            return None

        if not agent_card:
            return None

        # Extract capabilities
        capabilities_list = []
        caps = agent_card.get("capabilities")
        if isinstance(caps, dict):
            capabilities_list = list(caps.keys())
        elif isinstance(caps, list):
            capabilities_list = caps

        return DiscoveredAgent(
            name=agent_card.get("name", app_name),
            endpoint_url=app_url,
            app_name=app_name,
            description=agent_card.get("description"),
            capabilities=",".join(capabilities_list) if capabilities_list else None,
            protocol_version=agent_card.get("protocolVersion"),
        )
