"""
Discovery orchestration service.

This module coordinates the discovery of MCP servers and their tools
from various sources:
- Workspace-deployed MCP servers (Databricks Apps with MCP endpoints)
- MCP catalog managed servers (future Databricks MCP catalog)
- Custom MCP server URLs
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.config import settings
from app.services.mcp_client import (
    MCPClient,
    MCPTool,
    MCPConnectionError,
    MCPTimeoutError,
)
from app.services.tool_parser import ToolParser, NormalizedTool
from app.models import MCPServer, Tool
from app.models.agent import Agent
from app.models.app import App
from app.models.mcp_server import MCPServerKind
from app.services.a2a_client import A2AClient, A2AClientError
from app.db_adapter import DatabaseAdapter

logger = logging.getLogger(__name__)

# Common MCP endpoint paths to probe on Databricks Apps
MCP_PROBE_PATHS = ["/mcp", "/api/mcp"]
MCP_PROBE_TIMEOUT = 5.0


@dataclass
class DiscoveredServer:
    """
    Represents a discovered MCP server.

    Attributes:
        server_url: MCP server endpoint URL
        kind: Server type (managed/external/custom)
        tools: List of discovered tools
        error: Error message if discovery failed (optional)
    """

    server_url: str
    kind: str
    tools: List[NormalizedTool]
    error: Optional[str] = None


@dataclass
class DiscoveryResult:
    """
    Results from a discovery operation.

    Attributes:
        servers_discovered: Number of servers discovered
        tools_discovered: Total number of tools discovered
        servers: List of discovered servers with their tools
        errors: List of error messages encountered
    """

    servers_discovered: int
    tools_discovered: int
    servers: List[DiscoveredServer]
    errors: List[str]


@dataclass
class UpsertResult:
    """
    Results from upserting discovery data into the database.

    Attributes:
        new_servers: Number of new servers created
        updated_servers: Number of existing servers updated
        new_tools: Number of new tools created
        updated_tools: Number of existing tools updated
    """

    new_servers: int = 0
    updated_servers: int = 0
    new_tools: int = 0
    updated_tools: int = 0


@dataclass
class DiscoveredAgent:
    """An agent found during auto-discovery."""

    name: str
    endpoint_url: str
    description: Optional[str] = None
    capabilities: Optional[str] = None
    a2a_capabilities: Optional[str] = None
    skills: Optional[str] = None
    protocol_version: Optional[str] = None
    source: str = "serving_endpoint"  # "serving_endpoint" | "app"
    app_id: Optional[int] = None  # Link to backing app (if source="app")


@dataclass
class AgentDiscoveryResult:
    """Results from agent auto-discovery."""

    agents: List[DiscoveredAgent]
    errors: List[str]


@dataclass
class AgentUpsertResult:
    """Results from upserting discovered agents into the database."""

    new_agents: int = 0
    updated_agents: int = 0


# Agent card probe paths and timeout
AGENT_CARD_PATHS = ["/.well-known/agent.json", "/card"]
AGENT_CARD_PROBE_TIMEOUT = 5.0

# Foundation Model API endpoint prefixes — skip these during agent discovery
FMAPI_PREFIXES = (
    "databricks-claude-", "databricks-gpt-", "databricks-llama-",
    "databricks-meta-", "databricks-gemini-", "databricks-gemma-",
    "databricks-qwen", "databricks-gte-", "databricks-bge-",
)


class DiscoveryService:
    """
    Orchestrates discovery of MCP servers and tools.

    Coordinates scanning workspace, querying catalog, and discovering
    tools from custom server URLs.
    """

    def __init__(self, mcp_client: Optional[MCPClient] = None):
        """
        Initialize discovery service.

        Args:
            mcp_client: Optional MCP client instance (for testing)
        """
        self._mcp_client = mcp_client
        self._pending_apps: List[Dict[str, Any]] = []

    async def discover_from_url(
        self,
        server_url: str,
        kind: str = "custom",
    ) -> DiscoveredServer:
        """
        Discover tools from a single MCP server URL.

        Args:
            server_url: MCP server endpoint URL
            kind: Server type (managed/external/custom)

        Returns:
            DiscoveredServer with tools or error

        Example:
            >>> service = DiscoveryService()
            >>> server = await service.discover_from_url("https://mcp.example.com")
            >>> print(f"Found {len(server.tools)} tools")
        """
        tools = []
        error = None

        try:
            if self._mcp_client:
                # Use provided client (for testing)
                mcp_tools = await self._mcp_client.list_tools(server_url)
            else:
                # Create new client for this request
                async with MCPClient() as client:
                    mcp_tools = await client.list_tools(server_url)

            # Parse and normalize each tool
            for mcp_tool in mcp_tools:
                try:
                    normalized_tool = ToolParser.parse_tool(
                        {
                            "name": mcp_tool.name,
                            "description": mcp_tool.description,
                            "inputSchema": mcp_tool.input_schema,
                        }
                    )
                    tools.append(normalized_tool)
                except ValueError as e:
                    # Skip invalid tool but continue processing others
                    continue

        except (MCPConnectionError, MCPTimeoutError) as e:
            error = str(e)
        except Exception as e:
            error = f"Unexpected error: {str(e)}"

        return DiscoveredServer(
            server_url=server_url,
            kind=kind,
            tools=tools,
            error=error,
        )

    async def discover_from_workspace(
        self, profile: Optional[str] = None,
    ) -> DiscoveryResult:
        """
        Discover MCP servers deployed as Databricks Apps in the workspace.

        Enumerates running apps via the Databricks SDK, then probes each for
        MCP endpoints at common paths (/mcp, /api/mcp).

        Args:
            profile: Databricks CLI profile name (falls back to settings/env)

        Returns:
            DiscoveryResult with any MCP-enabled apps found
        """
        errors: List[str] = []
        servers: List[DiscoveredServer] = []
        apps_metadata: List[Dict[str, Any]] = []

        # --- 1. List workspace apps via SDK (synchronous → thread pool) ---
        try:
            app_list = await self._list_workspace_apps(profile)
        except Exception as e:
            logger.error("Workspace app listing failed: %s", e)
            return DiscoveryResult(
                servers_discovered=0,
                tools_discovered=0,
                servers=[],
                errors=[f"Failed to list workspace apps: {e}"],
            )

        if not app_list:
            return DiscoveryResult(
                servers_discovered=0, tools_discovered=0, servers=[], errors=[],
            )

        # --- 2. Register ALL running apps (regardless of MCP support) ---
        for app_info in app_list:
            app_url = app_info.get("url")
            if not app_url:
                continue
            apps_metadata.append({
                "name": app_info["name"],
                "url": app_url,
                "owner": app_info.get("owner"),
                "mcp_url": None,  # Will be set if MCP endpoint found
            })

        # --- 3. Probe each running app for MCP endpoints ---
        probe_tasks = []
        for app_info in app_list:
            app_url = app_info.get("url")
            if not app_url:
                continue
            probe_tasks.append(self._probe_app_for_mcp(app_info))

        if probe_tasks:
            probe_results = await asyncio.gather(
                *probe_tasks, return_exceptions=True,
            )
            for result in probe_results:
                if isinstance(result, Exception):
                    errors.append(str(result))
                elif result is not None:
                    discovered_server, mcp_meta = result
                    servers.append(discovered_server)
                    # Update the matching app entry with the MCP URL
                    for app_meta in apps_metadata:
                        if app_meta["name"] == mcp_meta["name"]:
                            app_meta["mcp_url"] = mcp_meta["mcp_url"]
                            break

        # Stash app metadata so upsert_discovery_results can create App rows
        self._pending_apps = apps_metadata

        total_tools = sum(len(s.tools) for s in servers)
        return DiscoveryResult(
            servers_discovered=len(servers),
            tools_discovered=total_tools,
            servers=servers,
            errors=errors,
        )

    async def discover_from_catalog(self) -> DiscoveryResult:
        """
        Discover managed MCP servers from Databricks MCP catalog.

        Queries the catalog URL (if configured) for a list of managed MCP
        servers, then discovers tools from each. Gracefully returns empty
        results when the catalog URL is not set or not responding.

        Returns:
            DiscoveryResult with managed servers (or empty if catalog unavailable)
        """
        catalog_url = settings.mcp_catalog_url
        if not catalog_url:
            logger.debug("mcp_catalog_url not configured — skipping catalog discovery")
            return DiscoveryResult(
                servers_discovered=0, tools_discovered=0, servers=[], errors=[],
            )

        errors: List[str] = []
        servers: List[DiscoveredServer] = []

        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as http:
                resp = await http.get(catalog_url)
                resp.raise_for_status()
                catalog_data = resp.json()

            # Expected shape: { "servers": [ { "url": "...", ... }, ... ] }
            server_entries = catalog_data.get("servers", [])

            discover_tasks = [
                self.discover_from_url(
                    entry["url"], kind="managed",
                )
                for entry in server_entries
                if entry.get("url")
            ]

            if discover_tasks:
                results = await asyncio.gather(*discover_tasks)
                servers = list(results)

        except Exception as e:
            logger.warning("Catalog discovery unavailable (%s): %s", catalog_url, e)
            errors.append(f"Catalog endpoint not available: {e}")

        successful = [s for s in servers if s.error is None]
        total_tools = sum(len(s.tools) for s in successful)
        errs_from_servers = [
            f"{s.server_url}: {s.error}" for s in servers if s.error
        ]

        return DiscoveryResult(
            servers_discovered=len(successful),
            tools_discovered=total_tools,
            servers=servers,
            errors=errors + errs_from_servers,
        )

    async def discover_from_urls(
        self,
        server_urls: List[str],
        kind: str = "custom",
    ) -> DiscoveryResult:
        """
        Discover tools from a list of custom MCP server URLs.

        Queries multiple servers in parallel and aggregates results.

        Args:
            server_urls: List of MCP server endpoint URLs
            kind: Server type for all URLs (default: custom)

        Returns:
            DiscoveryResult with aggregated findings

        Example:
            >>> service = DiscoveryService()
            >>> urls = ["https://mcp1.example.com", "https://mcp2.example.com"]
            >>> result = await service.discover_from_urls(urls)
            >>> print(f"Discovered {result.tools_discovered} tools from {result.servers_discovered} servers")
        """
        if not server_urls:
            return DiscoveryResult(
                servers_discovered=0,
                tools_discovered=0,
                servers=[],
                errors=[],
            )

        # Discover from all URLs in parallel
        tasks = [
            self.discover_from_url(url, kind=kind)
            for url in server_urls
        ]
        servers = await asyncio.gather(*tasks)

        # Aggregate results
        total_tools = sum(len(server.tools) for server in servers)
        successful_servers = sum(1 for server in servers if server.error is None)
        errors = [
            f"{server.server_url}: {server.error}"
            for server in servers
            if server.error
        ]

        return DiscoveryResult(
            servers_discovered=successful_servers,
            tools_discovered=total_tools,
            servers=list(servers),
            errors=errors,
        )

    async def discover_all(
        self,
        custom_urls: Optional[List[str]] = None,
        profile: Optional[str] = None,
    ) -> DiscoveryResult:
        """
        Run full discovery from all sources.

        Discovers from:
        1. Workspace-deployed apps (Databricks Apps with MCP endpoints)
        2. MCP catalog managed servers
        3. Custom URLs (if provided)

        Args:
            custom_urls: Optional list of custom MCP server URLs
            profile: Databricks CLI profile for workspace discovery

        Returns:
            Aggregated DiscoveryResult from all sources
        """
        # Run all discovery sources in parallel
        tasks = [
            self.discover_from_workspace(profile=profile),
            self.discover_from_catalog(),
        ]

        if custom_urls:
            tasks.append(self.discover_from_urls(custom_urls))

        results = await asyncio.gather(*tasks)

        # Aggregate results
        all_servers = []
        all_errors = []
        total_servers = 0
        total_tools = 0

        for result in results:
            all_servers.extend(result.servers)
            all_errors.extend(result.errors)
            total_servers += result.servers_discovered
            total_tools += result.tools_discovered

        return DiscoveryResult(
            servers_discovered=total_servers,
            tools_discovered=total_tools,
            servers=all_servers,
            errors=all_errors,
        )


    # ---- Agent auto-discovery methods ----

    async def discover_agents_all(
        self, profile: Optional[str] = None,
    ) -> AgentDiscoveryResult:
        """
        Discover agents from serving endpoints and workspace apps in parallel.

        De-duplicates by name; serving endpoint wins on collision.
        """
        tasks = [
            self._discover_agents_from_serving_endpoints(profile),
            self._discover_agents_from_apps(profile),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_agents: List[DiscoveredAgent] = []
        all_errors: List[str] = []

        for result in results:
            if isinstance(result, Exception):
                all_errors.append(f"Agent discovery error: {result}")
            else:
                all_agents.extend(result.agents)
                all_errors.extend(result.errors)

        # De-duplicate by name — serving_endpoint source wins over app
        seen: Dict[str, DiscoveredAgent] = {}
        for agent in all_agents:
            existing = seen.get(agent.name)
            if existing is None:
                seen[agent.name] = agent
            elif agent.source == "serving_endpoint":
                seen[agent.name] = agent

        return AgentDiscoveryResult(
            agents=list(seen.values()),
            errors=all_errors,
        )

    async def _discover_agents_from_serving_endpoints(
        self, profile: Optional[str] = None,
    ) -> AgentDiscoveryResult:
        """
        Discover agents from Databricks Model Serving endpoints.

        Filters to READY endpoints, constructs invocation URLs, and
        optionally fetches A2A Agent Cards for richer metadata.
        """
        agents: List[DiscoveredAgent] = []
        errors: List[str] = []

        def _list_endpoints_sync() -> tuple:
            from databricks.sdk import WorkspaceClient

            client = WorkspaceClient(profile=profile) if profile else WorkspaceClient()
            workspace_host = client.config.host.rstrip("/")

            # Extract auth token for cross-service probes
            auth_headers = client.config.authenticate()
            auth_val = auth_headers.get("Authorization", "")
            token = auth_val[7:] if auth_val.startswith("Bearer ") else None

            all_eps = list(client.serving_endpoints.list())

            results = []
            skipped = 0
            for ep in all_eps:
                ep_name = getattr(ep, "name", None)
                if not ep_name:
                    continue

                # Skip Foundation Model API endpoints (not agents)
                if ep_name.startswith(FMAPI_PREFIXES):
                    skipped += 1
                    continue

                state_obj = getattr(ep, "state", None)
                ready_val = getattr(state_obj, "ready", None) if state_obj else None
                # SDK returns an enum (EndpointStateReady.READY) — compare as string
                if not ready_val or "READY" not in str(ready_val):
                    continue

                # Extract task type
                config = getattr(ep, "config", None)
                served_entities = getattr(config, "served_entities", None) or []
                task = None
                for entity in served_entities:
                    t = getattr(entity, "task", None)
                    if t:
                        task = str(t)
                        break

                # Extract tags
                tags = {}
                for tag in getattr(ep, "tags", None) or []:
                    key = getattr(tag, "key", None)
                    value = getattr(tag, "value", None)
                    if key:
                        tags[key] = value

                results.append({
                    "name": ep_name,
                    "url": f"{workspace_host}/serving-endpoints/{ep_name}/invocations",
                    "task": task,
                    "tags": tags,
                    "workspace_host": workspace_host,
                })
            return results, token

        try:
            loop = asyncio.get_event_loop()
            result_tuple = await loop.run_in_executor(None, _list_endpoints_sync)
            endpoints, ws_token = result_tuple
            if ws_token:
                self._workspace_token = ws_token
        except Exception as e:
            logger.error("Failed to list serving endpoints: %s", e)
            return AgentDiscoveryResult(
                agents=[],
                errors=[f"Failed to list serving endpoints: {e}"],
            )

        logger.info(
            "Serving endpoints: %d candidates (from listing)",
            len(endpoints),
        )

        if not endpoints:
            return AgentDiscoveryResult(agents=[], errors=[])

        # Probe each endpoint for agent card in parallel
        probe_tasks = [
            self._probe_endpoint_for_agent(ep_info) for ep_info in endpoints
        ]
        probe_results = await asyncio.gather(*probe_tasks, return_exceptions=True)

        for result in probe_results:
            if isinstance(result, Exception):
                errors.append(str(result))
            elif result is not None:
                agents.append(result)

        logger.info(
            "Serving endpoint agent discovery: %d endpoints checked, %d agents found",
            len(endpoints), len(agents),
        )
        return AgentDiscoveryResult(agents=agents, errors=errors)

    async def _probe_endpoint_for_agent(
        self, ep_info: Dict[str, Any],
    ) -> Optional[DiscoveredAgent]:
        """
        Check if a serving endpoint is an agent.

        An endpoint qualifies if it has task=llm/v1/chat, an 'agent' tag,
        or responds to an Agent Card request.
        """
        name = ep_info["name"]
        url = ep_info["url"]
        task = ep_info.get("task")
        tags = ep_info.get("tags", {})
        workspace_host = ep_info.get("workspace_host", "")

        tag_keys_lower = {k.lower() for k in tags}
        is_agent_tagged = "agent" in tag_keys_lower
        is_chat_task = task and "chat" in task.lower()
        # MLflow-deployed agents have a MONITOR_EXPERIMENT_ID tag
        is_mlflow_agent = "monitor_experiment_id" in tag_keys_lower

        # Try fetching A2A Agent Card from the workspace app URL (if app-backed)
        token = getattr(self, "_workspace_token", None)
        agent_card = None
        try:
            async with A2AClient(timeout=AGENT_CARD_PROBE_TIMEOUT) as client:
                agent_card = await client.fetch_agent_card(
                    workspace_host + f"/serving-endpoints/{name}",
                    auth_token=token,
                )
        except A2AClientError:
            pass
        except Exception:
            pass

        if agent_card:
            return DiscoveredAgent(
                name=agent_card.get("name", name),
                endpoint_url=url,
                description=agent_card.get("description"),
                capabilities=",".join(agent_card.get("capabilities", {}).keys())
                if isinstance(agent_card.get("capabilities"), dict)
                else None,
                a2a_capabilities=json.dumps(agent_card.get("capabilities"))
                if agent_card.get("capabilities")
                else None,
                skills=json.dumps(agent_card.get("skills"))
                if agent_card.get("skills")
                else None,
                protocol_version=agent_card.get("protocolVersion"),
                source="serving_endpoint",
            )

        # No card, but if it looks like an agent based on task/tags, still register
        if is_agent_tagged or is_chat_task or is_mlflow_agent:
            tag_list = [f"{k}={v}" for k, v in tags.items() if v] if tags else []
            return DiscoveredAgent(
                name=name,
                endpoint_url=url,
                description=f"Serving endpoint ({task or 'unknown task'})",
                capabilities=",".join(tag_list) if tag_list else task,
                source="serving_endpoint",
            )

        return None

    async def _discover_agents_from_apps(
        self, profile: Optional[str] = None,
    ) -> AgentDiscoveryResult:
        """
        Discover agents from Databricks Apps that expose A2A Agent Cards.

        Reuses _list_workspace_apps() and probes each running app at
        /.well-known/agent.json and /card.
        """
        agents: List[DiscoveredAgent] = []
        errors: List[str] = []

        try:
            app_list = await self._list_workspace_apps(profile)
        except Exception as e:
            logger.error("Workspace app listing failed for agent discovery: %s", e)
            return AgentDiscoveryResult(
                agents=[],
                errors=[f"Failed to list workspace apps for agent discovery: {e}"],
            )

        if not app_list:
            return AgentDiscoveryResult(agents=[], errors=[])

        probe_tasks = []
        for app_info in app_list:
            app_url = app_info.get("url")
            if not app_url:
                continue
            probe_tasks.append(self._probe_app_for_agent(app_info))

        logger.info(f"[AGENT-DISCOVERY] Built {len(probe_tasks)} probe tasks from {len(app_list)} apps")

        if probe_tasks:
            logger.info(f"[AGENT-DISCOVERY] Probing {len(probe_tasks)} apps for agent cards")
            probe_results = await asyncio.gather(
                *probe_tasks, return_exceptions=True,
            )
            none_count = 0
            for i, result in enumerate(probe_results):
                if isinstance(result, Exception):
                    errors.append(str(result))
                    logger.warning(f"[AGENT-DISCOVERY] App {i}: Exception - {result}")
                elif result is not None:
                    agents.append(result)
                    logger.info(f"[AGENT-DISCOVERY] App {i}: Found agent '{result.name}'")
                else:
                    none_count += 1
            logger.info(f"[AGENT-DISCOVERY] Results: {len(agents)} agents, {len(errors)} errors, {none_count} None")

        logger.info(
            "App agent discovery: %d apps checked, %d agents found",
            len(app_list), len(agents),
        )
        return AgentDiscoveryResult(agents=agents, errors=errors)

    async def _probe_app_for_agent(
        self, app_info: Dict[str, Any],
    ) -> Optional[DiscoveredAgent]:
        """
        Probe a single Databricks App for an A2A Agent Card.

        Tries /.well-known/agent.json and /card with a short timeout.
        """
        app_url = app_info["url"]
        app_name = app_info["name"]

        token = getattr(self, "_workspace_token", None)
        agent_card = None
        try:
            logger.info(f"[AGENT] Probing app '{app_name}' at {app_url}")
            async with A2AClient(timeout=AGENT_CARD_PROBE_TIMEOUT) as client:
                agent_card = await client.fetch_agent_card(app_url, auth_token=token)
                logger.info(f"[AGENT] ✓ Found agent card for '{app_name}': name={agent_card.get('name', app_name)}")
        except A2AClientError as e:
            logger.info(f"[AGENT] ✗ No agent card for '{app_name}' (A2AClientError): {e}")
            return None
        except Exception as e:
            logger.error(f"[AGENT] ✗ Probe failed for '{app_name}': {type(e).__name__}: {e}", exc_info=True)
            return None

        if not agent_card:
            logger.warning(f"[AGENT] ✗ Agent card is None for '{app_name}'")
            return None

        discovered = DiscoveredAgent(
            name=agent_card.get("name", app_name),
            endpoint_url=app_url,
            description=agent_card.get("description"),
            capabilities=",".join(agent_card.get("capabilities", {}).keys())
            if isinstance(agent_card.get("capabilities"), dict)
            else None,
            a2a_capabilities=json.dumps(agent_card.get("capabilities"))
            if agent_card.get("capabilities")
            else None,
            skills=json.dumps(agent_card.get("skills"))
            if agent_card.get("skills")
            else None,
            protocol_version=agent_card.get("protocolVersion"),
            source="app",
        )
        logger.info(f"[AGENT] Created DiscoveredAgent for '{discovered.name}' from app '{app_name}'")
        return discovered

    def upsert_agent_discovery_results(
        self,
        result: AgentDiscoveryResult,
    ) -> AgentUpsertResult:
        """
        Upsert discovered agents into the database.

        Matches by unique agent name. New agents get status="discovered".
        Existing agents: factual fields are updated, but manual fields
        (auth_token, system_prompt, collection_id, status) are preserved.

        For agents from apps (source="app"), links them to their backing app via app_id.
        """
        upsert = AgentUpsertResult()

        for discovered in result.agents:
            # Look up app_id if this agent is from an app
            app_id = None
            if discovered.source == "app" and discovered.endpoint_url:
                app = DatabaseAdapter.get_app_by_url(discovered.endpoint_url)
                if app:
                    app_id = app["id"]
                    logger.info(f"[AGENT] Linking agent '{discovered.name}' to app '{app['name']}' (id={app_id})")

            # Check if agent already exists
            existing = DatabaseAdapter.get_agent_by_name(discovered.name)

            if existing:
                # Update factual fields only
                DatabaseAdapter.upsert_agent_by_name(
                    name=discovered.name,
                    endpoint_url=discovered.endpoint_url,
                    description=discovered.description,
                    capabilities=discovered.capabilities,
                    a2a_capabilities=discovered.a2a_capabilities,
                    skills=discovered.skills,
                    protocol_version=discovered.protocol_version,
                    app_id=app_id,
                )
                upsert.updated_agents += 1
            else:
                # Create new agent
                DatabaseAdapter.upsert_agent_by_name(
                    name=discovered.name,
                    endpoint_url=discovered.endpoint_url,
                    description=discovered.description,
                    capabilities=discovered.capabilities,
                    a2a_capabilities=discovered.a2a_capabilities,
                    skills=discovered.skills,
                    protocol_version=discovered.protocol_version,
                    status="discovered",
                    app_id=app_id,
                )
                upsert.new_agents += 1

        return upsert

    def upsert_discovery_results(
        self,
        discovery_result: DiscoveryResult,
    ) -> UpsertResult:
        """
        Upsert discovery results into the database.

        Creates or updates Apps, MCP servers, and tools based on discovery.
        Handles duplicates gracefully by updating existing records.

        Args:
            discovery_result: Results from discovery operation

        Returns:
            UpsertResult with counts of new/updated entities
        """
        upsert_result = UpsertResult()

        pending_apps = getattr(self, "_pending_apps", [])
        logger.info(f"[UPSERT] Starting upsert with {len(pending_apps)} pending apps")

        # Build a url→app_id map from pending app metadata (set during workspace discovery)
        url_to_app_id: Dict[str, int] = {}
        for app_meta in pending_apps:
            logger.info(f"[UPSERT] Processing app: {app_meta['name']}")
            app_id = self._upsert_app(
                name=app_meta["name"],
                url=app_meta.get("url"),
                owner=app_meta.get("owner"),
            )
            logger.info(f"[UPSERT] App '{app_meta['name']}' upserted with ID: {app_id}")
            # Map the MCP endpoint URL back to this App
            if app_meta.get("mcp_url"):
                url_to_app_id[app_meta["mcp_url"]] = app_id
            upsert_result.updated_servers += 1  # Count apps as updated

        for discovered_server in discovery_result.servers:
            # Skip servers with errors
            if discovered_server.error:
                continue

            app_id = url_to_app_id.get(discovered_server.server_url)

            # Upsert MCP server
            server_dict = self._upsert_mcp_server(
                discovered_server.server_url,
                discovered_server.kind,
                app_id=app_id,
            )
            logger.info(f"[UPSERT] MCP server upserted: {discovered_server.server_url} (id={server_dict['id']})")
            upsert_result.updated_servers += 1

            # Get the server ID
            mcp_server_id = server_dict["id"]

            # Upsert tools
            for normalized_tool in discovered_server.tools:
                tool_dict = self._upsert_tool(
                    mcp_server_id,
                    normalized_tool,
                )
                logger.info(f"[UPSERT] Tool upserted: {normalized_tool.name} (id={tool_dict['id']})")
                upsert_result.updated_tools += 1

        logger.info(f"[UPSERT] Upsert complete. Apps: {len(pending_apps)}, Servers: {upsert_result.updated_servers}, Tools: {upsert_result.updated_tools}")
        self._pending_apps = []  # Clear after upsert
        return upsert_result

    def _upsert_app(
        self,
        name: str,
        url: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> int:
        """
        Upsert a Databricks App and return its ID.

        Matches by unique app name. Creates a new row if not found,
        otherwise updates the existing one.

        Args:
            name: App name (unique key)
            url: Deployed app URL
            owner: App owner

        Returns:
            The App's primary key ID
        """
        logger.info(f"[DB] Upserting app '{name}' with url={url}, owner={owner}")
        app_dict = DatabaseAdapter.upsert_app_by_name(
            name=name, url=url, owner=owner
        )
        logger.info(f"[DB] App '{name}' upserted with id={app_dict['id']}")
        return app_dict["id"]

    def _upsert_mcp_server(
        self,
        server_url: str,
        kind: str,
        app_id: Optional[int] = None,
    ) -> Dict:
        """
        Upsert an MCP server into the database.

        Args:
            server_url: MCP server endpoint URL
            kind: Server type (managed/external/custom)
            app_id: Optional FK to parent App

        Returns:
            Server dict with ID
        """
        return DatabaseAdapter.upsert_mcp_server_by_url(
            server_url=server_url, kind=kind, app_id=app_id
        )

    def _upsert_tool(
        self,
        mcp_server_id: int,
        normalized_tool: NormalizedTool,
    ) -> Dict:
        """
        Upsert a tool into the database.

        Args:
            mcp_server_id: ID of the parent MCP server
            normalized_tool: Normalized tool specification

        Returns:
            Tool dict with ID
        """
        return DatabaseAdapter.upsert_tool_by_server_and_name(
            mcp_server_id=mcp_server_id,
            name=normalized_tool.name,
            description=normalized_tool.description,
            parameters=normalized_tool.parameters,
        )


    # ----- Private helpers for workspace discovery -----

    async def _list_workspace_apps(
        self, profile: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Enumerate Databricks Apps in the workspace via the SDK.

        Runs the synchronous SDK call in a thread pool. Returns a list of
        dicts with keys: name, url, owner, status.
        """

        def _list_sync() -> tuple:
            from databricks.sdk import WorkspaceClient

            if profile:
                client = WorkspaceClient(profile=profile)
            else:
                client = WorkspaceClient()

            # Extract the SP's auth token for cross-app requests
            auth_headers = client.config.authenticate()
            token = None
            auth_val = auth_headers.get("Authorization", "")
            if auth_val.startswith("Bearer "):
                token = auth_val[7:]

            results = []
            for app in client.apps.list():
                # Determine if app is running via compute_status (preferred)
                # or fall back to active_deployment status
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
                    "owner": getattr(app, "creator", None)
                        or getattr(app, "updater", None),
                    "compute_state": compute_state,
                    "deploy_state": deploy_state,
                })
            return results, token

        loop = asyncio.get_event_loop()
        result_tuple = await loop.run_in_executor(None, _list_sync)
        all_apps, workspace_token = result_tuple

        # Store token for cross-app probe requests
        self._workspace_token = workspace_token

        # Filter to running apps: compute is ACTIVE or deployment SUCCEEDED
        running = [
            a for a in all_apps
            if a.get("url") and (
                "ACTIVE" in (a.get("compute_state") or "")
                or "SUCCEEDED" in (a.get("deploy_state") or "")
            )
        ]

        logger.info(
            "Workspace apps: %d total, %d running",
            len(all_apps), len(running),
        )
        return running

    async def _probe_app_for_mcp(
        self, app_info: Dict[str, Any],
    ) -> Optional[tuple]:
        """
        Probe a single Databricks App for an MCP endpoint.

        Tries common MCP paths with a short timeout. Returns a tuple of
        (DiscoveredServer, app_metadata_dict) if MCP is found, else None.
        """
        app_url = app_info["url"]
        app_name = app_info["name"]

        # Build candidate URLs to probe
        candidate_urls = [f"{app_url}{path}" for path in MCP_PROBE_PATHS]

        token = getattr(self, "_workspace_token", None)
        async with MCPClient(timeout=MCP_PROBE_TIMEOUT) as client:
            for probe_url in candidate_urls:
                try:
                    mcp_tools = await client.list_tools(probe_url, auth_token=token)

                    # Parse tools
                    tools: List[NormalizedTool] = []
                    for mcp_tool in mcp_tools:
                        try:
                            tools.append(ToolParser.parse_tool({
                                "name": mcp_tool.name,
                                "description": mcp_tool.description,
                                "inputSchema": mcp_tool.input_schema,
                            }))
                        except ValueError:
                            continue

                    logger.info(
                        "MCP endpoint found: %s (%d tools)",
                        probe_url, len(tools),
                    )

                    server = DiscoveredServer(
                        server_url=probe_url,
                        kind="managed",
                        tools=tools,
                    )
                    app_meta = {
                        "name": app_name,
                        "url": app_url,
                        "owner": app_info.get("owner"),
                        "mcp_url": probe_url,
                    }
                    return (server, app_meta)

                except (MCPConnectionError, MCPTimeoutError):
                    # This path didn't respond as MCP — try next
                    continue
                except Exception as e:
                    logger.debug(
                        "Probe %s failed unexpectedly: %s", probe_url, e,
                    )
                    continue

        # No MCP endpoint found — not an error, just a non-MCP app
        return None


async def create_discovery_service() -> DiscoveryService:
    """
    Factory function to create a DiscoveryService instance.

    Returns:
        Configured DiscoveryService instance
    """
    return DiscoveryService()
