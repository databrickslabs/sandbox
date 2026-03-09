"""
Governance service — builds lineage graphs from UC APIs, agent cards, and system tables.

Data source strategy (layered, graceful degradation):
  1. Always available: Agent cards → tools → tool nodes + edges
  2. Cross-agent: Tool name/description matching for supervisor→sub-agent edges
  3. UC tables: Scan catalog.schema for tables, connect to agents via name/capability matching
  4. UC functions: List functions, match to agent tools by name
  5. If warehouse_id: system.access.table_lineage SQL → table-to-table lineage
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Keywords in tool descriptions that suggest data/table operations
_DATA_KEYWORDS = {
    "search", "query", "table", "data", "analyze", "analysis",
    "check", "quality", "read", "write", "insert", "update",
}


@dataclass
class LineageNode:
    id: str  # "{type}:{name}" e.g. "agent:data_tools", "table:cat.sch.tbl"
    node_type: str  # "agent", "tool", "uc_function", "table", "model"
    name: str  # display name
    full_name: str  # catalog.schema.name for UC assets, agent name for agents
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LineageEdge:
    source: str  # node id
    target: str  # node id
    relationship: str  # "uses_tool", "calls_agent", "reads_table", etc.


@dataclass
class LineageGraph:
    nodes: List[LineageNode] = field(default_factory=list)
    edges: List[LineageEdge] = field(default_factory=list)
    root_id: Optional[str] = None  # center node for agent-centric view

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [asdict(n) for n in self.nodes],
            "edges": [asdict(e) for e in self.edges],
            "root_id": self.root_id,
        }

    def _node_ids(self) -> set:
        return {n.id for n in self.nodes}

    def add_node(self, node: LineageNode) -> None:
        if node.id not in self._node_ids():
            self.nodes.append(node)

    def add_edge(self, edge: LineageEdge) -> None:
        # Deduplicate edges
        for e in self.edges:
            if e.source == edge.source and e.target == edge.target and e.relationship == edge.relationship:
                return
        self.edges.append(edge)


class GovernanceService:
    """Builds lineage graphs and governance status from UC APIs and agent cards."""

    def __init__(
        self,
        scanner: Any,
        profile: Optional[str] = None,
        catalog: Optional[str] = None,
    ):
        self._scanner = scanner
        self._profile = profile
        self._catalog = catalog  # UC catalog to scan for tables/functions
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._cache_ttl = 60.0
        self._ws_client = None
        # In-memory store: agent_name → {(source, target, relationship)}
        self._observed_edges: Dict[str, Set[Tuple[str, str, str]]] = {}

    def _cache_get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry and (time.time() - entry[0]) < self._cache_ttl:
            return entry[1]
        return None

    def _cache_set(self, key: str, value: Any) -> None:
        self._cache[key] = (time.time(), value)

    def invalidate_cache(self) -> None:
        self._cache.clear()

    # ------------------------------------------------------------------
    # Runtime / observed lineage
    # ------------------------------------------------------------------

    def ingest_trace(self, agent_name: str, trace: Dict[str, Any]) -> None:
        """Extract lineage observations from a chat trace."""
        sub_events = trace.get("sub_events", [])
        if not isinstance(sub_events, list):
            sub_events = []

        for sub in sub_events:
            if not isinstance(sub, dict):
                continue
            if sub.get("type") == "mcp_tools_call":
                tool_name = (sub.get("label") or "").replace("tools/call (", "").rstrip(")")
                if tool_name:
                    edge = (f"agent:{agent_name}", f"tool:{agent_name}:{tool_name}", "observed_uses_tool")
                    self._observed_edges.setdefault(agent_name, set()).add(edge)

        # Agent handoff: routing metadata from supervisor-style agents
        routing = trace.get("routing")
        if isinstance(routing, dict):
            sub_agent = routing.get("sub_agent")
            if sub_agent:
                edge = (f"agent:{agent_name}", f"agent:{sub_agent}", "observed_calls_agent")
                self._observed_edges.setdefault(agent_name, set()).add(edge)
                logger.info(f"Observed handoff: {agent_name} → {sub_agent}")

            # Tables accessed by the sub-agent (downstream lineage)
            tables = routing.get("tables_accessed", [])
            for table in tables:
                if isinstance(table, str):
                    edge = (f"agent:{sub_agent or agent_name}", f"table:{table}", "observed_reads_table")
                    self._observed_edges.setdefault(agent_name, set()).add(edge)
                    logger.info(f"Observed table access: {sub_agent or agent_name} → {table}")

        # Explicit target_agent in request payload (A2A delegation)
        req_payload = trace.get("request_payload", {})
        if isinstance(req_payload, dict) and "target_agent" in req_payload:
            target = req_payload["target_agent"]
            edge = (f"agent:{agent_name}", f"agent:{target}", "observed_calls_agent")
            self._observed_edges.setdefault(agent_name, set()).add(edge)

        self.invalidate_cache()

    def _merge_observed_edges(self, graph: LineageGraph, agent_name: Optional[str] = None) -> None:
        """Append observed edges into a lineage graph."""
        if agent_name:
            observed = self._observed_edges.get(agent_name, set())
        else:
            observed = set()
            for edges in self._observed_edges.values():
                observed.update(edges)

        for src, tgt, rel in observed:
            # Ensure target node exists
            if not any(n.id == tgt for n in graph.nodes):
                # Parse node type from id prefix
                if tgt.startswith("tool:"):
                    parts = tgt.split(":")
                    name = parts[-1] if len(parts) > 1 else tgt
                    graph.add_node(LineageNode(
                        id=tgt, node_type="tool", name=name, full_name=tgt.replace("tool:", ""),
                    ))
                elif tgt.startswith("agent:"):
                    name = tgt.replace("agent:", "")
                    graph.add_node(LineageNode(
                        id=tgt, node_type="agent", name=name, full_name=name,
                    ))
                elif tgt.startswith("table:"):
                    full_name = tgt.replace("table:", "")
                    name = full_name.split(".")[-1] if "." in full_name else full_name
                    graph.add_node(LineageNode(
                        id=tgt, node_type="table", name=name, full_name=full_name,
                    ))
            # Ensure source node exists too (e.g. sub-agent node)
            if not any(n.id == src for n in graph.nodes):
                if src.startswith("agent:"):
                    name = src.replace("agent:", "")
                    graph.add_node(LineageNode(
                        id=src, node_type="agent", name=name, full_name=name,
                    ))
            graph.add_edge(LineageEdge(source=src, target=tgt, relationship=rel))

    def _get_ws_client(self):
        """Get or create WorkspaceClient for UC queries."""
        if self._ws_client is None:
            try:
                from databricks.sdk import WorkspaceClient
                self._ws_client = (
                    WorkspaceClient(profile=self._profile)
                    if self._profile
                    else WorkspaceClient()
                )
            except Exception as e:
                logger.debug("WorkspaceClient not available: %s", e)
        return self._ws_client

    # ------------------------------------------------------------------
    # UC asset discovery (catalog-level)
    # ------------------------------------------------------------------

    def _discover_uc_tables(self) -> List[Dict[str, Any]]:
        """List tables across all schemas in the configured catalog."""
        cached = self._cache_get("uc_tables")
        if cached is not None:
            return cached

        tables: List[Dict[str, Any]] = []
        client = self._get_ws_client()
        if not client or not self._catalog:
            self._cache_set("uc_tables", tables)
            return tables

        try:
            for schema in client.schemas.list(catalog_name=self._catalog):
                if schema.name == "information_schema":
                    continue
                try:
                    for tbl in client.tables.list(
                        catalog_name=self._catalog, schema_name=schema.name
                    ):
                        tables.append({
                            "full_name": tbl.full_name,
                            "name": tbl.name,
                            "schema": schema.name,
                            "catalog": self._catalog,
                            "table_type": str(tbl.table_type) if tbl.table_type else "MANAGED",
                            "comment": tbl.comment or "",
                        })
                except Exception as e:
                    logger.debug("Failed listing tables in %s.%s: %s", self._catalog, schema.name, e)
        except Exception as e:
            logger.debug("Failed listing schemas in %s: %s", self._catalog, e)

        self._cache_set("uc_tables", tables)
        return tables

    def _discover_uc_functions(self) -> List[Dict[str, Any]]:
        """List functions across all schemas in the configured catalog."""
        cached = self._cache_get("uc_functions")
        if cached is not None:
            return cached

        functions: List[Dict[str, Any]] = []
        client = self._get_ws_client()
        if not client or not self._catalog:
            self._cache_set("uc_functions", functions)
            return functions

        try:
            for schema in client.schemas.list(catalog_name=self._catalog):
                if schema.name == "information_schema":
                    continue
                try:
                    for fn in client.functions.list(
                        catalog_name=self._catalog, schema_name=schema.name
                    ):
                        functions.append({
                            "full_name": fn.full_name,
                            "name": fn.name,
                            "schema": schema.name,
                            "catalog": self._catalog,
                            "comment": fn.comment or "",
                        })
                except Exception:
                    pass
        except Exception as e:
            logger.debug("Failed listing functions in %s: %s", self._catalog, e)

        self._cache_set("uc_functions", functions)
        return functions

    # ------------------------------------------------------------------
    # Agent ↔ table matching heuristics
    # ------------------------------------------------------------------

    def _match_agent_to_tables(
        self,
        agent_name: str,
        agent_capabilities: str,
        tools: List[Dict[str, Any]],
        uc_tables: List[Dict[str, Any]],
    ) -> List[Tuple[Dict[str, Any], str]]:
        """
        Match an agent to UC tables. Returns list of (table, relationship) tuples.

        Matching strategies (precise, avoids false positives):
          1. Schema name matches agent name exactly (e.g., agent "data_tools" ↔ schema "data_tools")
          2. Table name contains agent name (e.g., "research_agent_payload" contains "research")
          3. Tool description explicitly references a table name found in UC
        """
        matches: List[Tuple[Dict[str, Any], str]] = []
        seen: Set[str] = set()
        agent_lower = agent_name.lower().replace("-", "_")

        # Collect tool descriptions for keyword matching
        tool_descs = " ".join(
            (t.get("description") or "").lower() for t in tools
        )

        for tbl in uc_tables:
            tbl_full = tbl["full_name"]
            if tbl_full in seen:
                continue
            schema_lower = tbl["schema"].lower()
            tbl_name_lower = tbl["name"].lower()

            # Strategy 1: schema name matches agent name exactly
            if schema_lower == agent_lower:
                seen.add(tbl_full)
                matches.append((tbl, "reads_table"))
                continue

            # Strategy 2: table name contains agent name
            # (e.g., research_agent_payload → agent "research")
            if len(agent_lower) >= 4 and agent_lower in tbl_name_lower:
                seen.add(tbl_full)
                matches.append((tbl, "reads_table"))
                continue

            # Strategy 3: tool description explicitly mentions this table name
            # Only match if the table name is specific enough (>= 5 chars)
            if len(tbl_name_lower) >= 5 and tbl_name_lower in tool_descs:
                seen.add(tbl_full)
                matches.append((tbl, "reads_table"))
                continue

        return matches

    def _match_agent_to_functions(
        self,
        agent_name: str,
        tools: List[Dict[str, Any]],
        uc_functions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Match agent tools to UC functions by name similarity."""
        matches = []
        tool_names = {(t.get("name") or "").lower() for t in tools}

        for fn in uc_functions:
            fn_name_lower = fn["name"].lower()
            # Direct name match
            if fn_name_lower in tool_names:
                matches.append(fn)
            # Partial match — tool name contains function name or vice versa
            for tn in tool_names:
                if tn and (tn in fn_name_lower or fn_name_lower in tn):
                    matches.append(fn)
                    break

        return matches

    # ------------------------------------------------------------------
    # Agent-centric lineage
    # ------------------------------------------------------------------

    async def get_agent_lineage(self, agent_name: str) -> LineageGraph:
        """Build lineage graph centered on one agent."""
        cached = self._cache_get(f"lineage:{agent_name}")
        if cached:
            return cached

        graph = LineageGraph()

        agent = self._scanner.get_agent_by_name(agent_name)
        if not agent:
            return graph

        # Root agent node
        agent_node = LineageNode(
            id=f"agent:{agent.name}",
            node_type="agent",
            name=agent.name,
            full_name=agent.name,
            metadata={
                "endpoint_url": agent.endpoint_url,
                "app_name": agent.app_name,
                "description": agent.description or "",
                "capabilities": agent.capabilities or "",
            },
        )
        graph.add_node(agent_node)
        graph.root_id = agent_node.id

        # Fetch agent card to get tools
        tools = await self._get_agent_tools(agent.endpoint_url)
        for tool in tools:
            tool_name = tool.get("name") or tool.get("id") or "unknown"
            tool_node = LineageNode(
                id=f"tool:{agent.name}:{tool_name}",
                node_type="tool",
                name=tool_name,
                full_name=f"{agent.name}.{tool_name}",
                metadata={
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("inputSchema", tool.get("parameters", {})),
                },
            )
            graph.add_node(tool_node)
            graph.add_edge(LineageEdge(
                source=agent_node.id,
                target=tool_node.id,
                relationship="uses_tool",
            ))

        # Detect cross-agent edges (supervisor → sub-agents)
        all_agents = self._scanner.get_agents()
        other_agents = [a for a in all_agents if a.name != agent.name]
        self._detect_cross_agent_edges(graph, agent, tools, other_agents)

        # UC table discovery
        uc_tables = self._discover_uc_tables()
        if uc_tables:
            table_matches = self._match_agent_to_tables(
                agent.name, agent.capabilities or "", tools, uc_tables
            )
            for tbl, rel in table_matches:
                tbl_id = f"table:{tbl['full_name']}"
                graph.add_node(LineageNode(
                    id=tbl_id,
                    node_type="table",
                    name=tbl["name"],
                    full_name=tbl["full_name"],
                    metadata={
                        "schema": tbl["schema"],
                        "table_type": tbl.get("table_type", ""),
                        "comment": tbl.get("comment", ""),
                    },
                ))
                graph.add_edge(LineageEdge(
                    source=agent_node.id,
                    target=tbl_id,
                    relationship=rel,
                ))

        # UC function discovery
        uc_functions = self._discover_uc_functions()
        if uc_functions:
            fn_matches = self._match_agent_to_functions(agent.name, tools, uc_functions)
            for fn in fn_matches:
                fn_id = f"uc_function:{fn['full_name']}"
                graph.add_node(LineageNode(
                    id=fn_id,
                    node_type="uc_function",
                    name=fn["name"],
                    full_name=fn["full_name"],
                    metadata={"comment": fn.get("comment", "")},
                ))
                graph.add_edge(LineageEdge(
                    source=agent_node.id,
                    target=fn_id,
                    relationship="uses_function",
                ))

        # Merge runtime-observed edges
        self._merge_observed_edges(graph, agent_name=agent.name)

        self._cache_set(f"lineage:{agent_name}", graph)
        return graph

    # ------------------------------------------------------------------
    # Workspace-wide lineage
    # ------------------------------------------------------------------

    async def get_workspace_lineage(
        self, warehouse_id: Optional[str] = None
    ) -> LineageGraph:
        """Build workspace-wide graph of all agents + their connections."""
        cache_key = f"workspace:{warehouse_id or 'none'}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        graph = LineageGraph()
        all_agents = self._scanner.get_agents()

        if not all_agents:
            return graph

        # Build agent + tool nodes for every agent in parallel
        card_tasks = [self._get_agent_tools(a.endpoint_url) for a in all_agents]
        all_tools = await asyncio.gather(*card_tasks, return_exceptions=True)

        for agent, tools_result in zip(all_agents, all_tools):
            agent_node = LineageNode(
                id=f"agent:{agent.name}",
                node_type="agent",
                name=agent.name,
                full_name=agent.name,
                metadata={
                    "endpoint_url": agent.endpoint_url,
                    "app_name": agent.app_name,
                    "description": agent.description or "",
                    "capabilities": agent.capabilities or "",
                },
            )
            graph.add_node(agent_node)

            tools = tools_result if isinstance(tools_result, list) else []
            for tool in tools:
                tool_name = tool.get("name") or tool.get("id") or "unknown"
                tool_node = LineageNode(
                    id=f"tool:{agent.name}:{tool_name}",
                    node_type="tool",
                    name=tool_name,
                    full_name=f"{agent.name}.{tool_name}",
                    metadata={"description": tool.get("description", "")},
                )
                graph.add_node(tool_node)
                graph.add_edge(LineageEdge(
                    source=agent_node.id,
                    target=tool_node.id,
                    relationship="uses_tool",
                ))

        # Cross-agent edges
        for agent, tools_result in zip(all_agents, all_tools):
            tools = tools_result if isinstance(tools_result, list) else []
            others = [a for a in all_agents if a.name != agent.name]
            self._detect_cross_agent_edges(graph, agent, tools, others)

        # UC table discovery — connect each agent to relevant tables
        uc_tables = self._discover_uc_tables()
        if uc_tables:
            for agent, tools_result in zip(all_agents, all_tools):
                tools = tools_result if isinstance(tools_result, list) else []
                table_matches = self._match_agent_to_tables(
                    agent.name, agent.capabilities or "", tools, uc_tables
                )
                for tbl, rel in table_matches:
                    tbl_id = f"table:{tbl['full_name']}"
                    graph.add_node(LineageNode(
                        id=tbl_id,
                        node_type="table",
                        name=tbl["name"],
                        full_name=tbl["full_name"],
                        metadata={
                            "schema": tbl["schema"],
                            "table_type": tbl.get("table_type", ""),
                        },
                    ))
                    graph.add_edge(LineageEdge(
                        source=f"agent:{agent.name}",
                        target=tbl_id,
                        relationship=rel,
                    ))

        # UC function discovery
        uc_functions = self._discover_uc_functions()
        if uc_functions:
            for agent, tools_result in zip(all_agents, all_tools):
                tools = tools_result if isinstance(tools_result, list) else []
                fn_matches = self._match_agent_to_functions(agent.name, tools, uc_functions)
                for fn in fn_matches:
                    fn_id = f"uc_function:{fn['full_name']}"
                    graph.add_node(LineageNode(
                        id=fn_id,
                        node_type="uc_function",
                        name=fn["name"],
                        full_name=fn["full_name"],
                        metadata={"comment": fn.get("comment", "")},
                    ))
                    graph.add_edge(LineageEdge(
                        source=f"agent:{agent.name}",
                        target=fn_id,
                        relationship="uses_function",
                    ))

        # Merge runtime-observed edges (all agents)
        self._merge_observed_edges(graph, agent_name=None)

        # System table lineage (if warehouse_id)
        if warehouse_id:
            await self._enrich_with_system_tables(graph, warehouse_id)

        self._cache_set(cache_key, graph)
        return graph

    # ------------------------------------------------------------------
    # Governance status
    # ------------------------------------------------------------------

    async def get_governance_status(self, agent_name: str) -> Dict[str, Any]:
        """Governance status for an agent — based on Apps API and declared resources."""
        cached = self._cache_get(f"governance:{agent_name}")
        if cached:
            return cached

        agent = self._scanner.get_agent_by_name(agent_name)
        status: Dict[str, Any] = {
            "app_running": False,
            "app_name": None,
            "declared_resources": [],
            "connected_tables": [],
            "connected_table_count": 0,
        }

        if agent:
            status["app_name"] = agent.app_name
            status["app_running"] = True  # scanner only lists running apps

            # Query Apps API for all declared resources
            client = self._get_ws_client()
            if client and agent.app_name:
                try:
                    app = client.apps.get(name=agent.app_name)
                    resources = getattr(app, "resources", None) or []
                    for r in resources:
                        res_info: Dict[str, Any] = {"name": getattr(r, "name", "")}
                        # Check each resource type
                        for rtype in ("uc_securable", "sql_warehouse", "job", "secret", "serving_endpoint", "database"):
                            obj = getattr(r, rtype, None)
                            if obj:
                                res_info["type"] = rtype
                                # Extract all non-None fields from the resource object
                                for field in dir(obj):
                                    if field.startswith("_"):
                                        continue
                                    val = getattr(obj, field, None)
                                    if val is not None and not callable(val):
                                        res_info[field] = str(val)
                                break
                        status["declared_resources"].append(res_info)
                except Exception as e:
                    logger.debug("Could not fetch app resources for %s: %s", agent.app_name, e)

            # UC table connections (heuristic matching)
            uc_tables = self._discover_uc_tables()
            if uc_tables:
                tools = []
                try:
                    tools = await self._get_agent_tools(agent.endpoint_url)
                except Exception:
                    pass
                table_matches = self._match_agent_to_tables(
                    agent.name, agent.capabilities or "", tools, uc_tables
                )
                status["connected_tables"] = [
                    {"full_name": tbl["full_name"], "schema": tbl["schema"], "relationship": rel}
                    for tbl, rel in table_matches
                ]
                status["connected_table_count"] = len(table_matches)

        self._cache_set(f"governance:{agent_name}", status)
        return status

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_agent_tools(self, endpoint_url: str) -> List[Dict[str, Any]]:
        """Fetch tool list from an agent's card or MCP tools/list."""
        try:
            card = await self._scanner.get_agent_card(endpoint_url)
            tools = card.get("skills") or card.get("tools") or []
            if tools:
                return tools
        except Exception:
            pass

        # Fallback: try MCP tools/list
        try:
            import uuid
            resp = await self._scanner.proxy_mcp(endpoint_url, {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/list",
                "params": {},
            })
            result = resp.get("result", resp) if isinstance(resp, dict) else {}
            return result.get("tools", []) if isinstance(result, dict) else []
        except Exception:
            return []

    def _detect_cross_agent_edges(
        self,
        graph: LineageGraph,
        agent: Any,
        tools: List[Dict[str, Any]],
        other_agents: List[Any],
    ) -> None:
        """Detect agent-to-agent calls by scanning tool names, descriptions, and capabilities."""
        existing_ids = graph._node_ids()

        # Also check agent capabilities for sub-agent references
        capabilities = set()
        if agent.capabilities:
            capabilities = {c.strip().lower() for c in agent.capabilities.split(",") if c.strip()}

        for other in other_agents:
            other_name_variants = {
                other.name.lower(),
                other.name.lower().replace("-", "_"),
                other.name.lower().replace("_", "-"),
            }

            found = False

            # Check tool names and descriptions
            for tool in tools:
                tool_name = (tool.get("name") or tool.get("id") or "").lower()
                tool_desc = (tool.get("description") or "").lower()

                for variant in other_name_variants:
                    if variant in tool_name or variant in tool_desc:
                        found = True
                        break
                if found:
                    break

            # Check capabilities for sub-agent references
            if not found:
                for variant in other_name_variants:
                    if variant in capabilities:
                        found = True
                        break

            if found:
                other_id = f"agent:{other.name}"
                if other_id not in existing_ids:
                    graph.add_node(LineageNode(
                        id=other_id,
                        node_type="agent",
                        name=other.name,
                        full_name=other.name,
                        metadata={
                            "endpoint_url": other.endpoint_url,
                            "app_name": other.app_name,
                        },
                    ))
                    existing_ids.add(other_id)

                graph.add_edge(LineageEdge(
                    source=f"agent:{agent.name}",
                    target=other_id,
                    relationship="calls_agent",
                ))

    async def _enrich_with_system_tables(
        self, graph: LineageGraph, warehouse_id: str
    ) -> None:
        """Query system.access.table_lineage to add table-to-table edges."""
        try:
            client = self._get_ws_client()
            if not client:
                return

            stmt = client.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=(
                    "SELECT source_table_full_name, target_table_full_name "
                    "FROM system.access.table_lineage "
                    "WHERE source_table_full_name IS NOT NULL "
                    "AND target_table_full_name IS NOT NULL "
                    "LIMIT 100"
                ),
                wait_timeout="30s",
            )

            if stmt.result and stmt.result.data_array:
                for row in stmt.result.data_array:
                    if len(row) >= 2 and row[0] and row[1]:
                        src_name = row[0]
                        tgt_name = row[1]

                        src_id = f"table:{src_name}"
                        tgt_id = f"table:{tgt_name}"

                        graph.add_node(LineageNode(
                            id=src_id,
                            node_type="table",
                            name=src_name.split(".")[-1],
                            full_name=src_name,
                        ))
                        graph.add_node(LineageNode(
                            id=tgt_id,
                            node_type="table",
                            name=tgt_name.split(".")[-1],
                            full_name=tgt_name,
                        ))
                        graph.add_edge(LineageEdge(
                            source=src_id,
                            target=tgt_id,
                            relationship="writes_to",
                        ))
        except Exception as e:
            logger.debug("System table lineage query failed: %s", e)
