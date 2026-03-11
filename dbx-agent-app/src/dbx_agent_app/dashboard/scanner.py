"""
Dashboard scanner — wraps AgentDiscovery + A2AClient with caching and MCP proxy.
"""

import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from typing import AsyncIterator, Dict, Any, List, Optional

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
            # Deduplicate by agent name (multiple apps may share the same agent name)
            seen: dict[str, DiscoveredAgent] = {}
            for agent in result.agents:
                if agent.name not in seen:
                    seen[agent.name] = agent
                else:
                    logger.debug("Skipping duplicate agent '%s' from app '%s'", agent.name, agent.app_name)
            self._agents = list(seen.values())
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

    async def proxy_mcp(
        self,
        endpoint_url: str,
        payload: Dict[str, Any],
        *,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Forward a JSON-RPC request to an agent's MCP endpoint.

        Args:
            endpoint_url: Agent base URL
            payload: Complete JSON-RPC 2.0 request body
            auth_token: Override token (e.g. user's forwarded access token)

        Returns:
            JSON-RPC response from the agent
        """
        mcp_url = endpoint_url.rstrip("/") + "/api/mcp"
        headers = {"Content-Type": "application/json"}
        token = auth_token or self.workspace_token
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
            response = await http.post(mcp_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    async def send_a2a_message(
        self,
        endpoint_url: str,
        message: str,
        context_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to an agent. Tries A2A message/send first,
        then falls back to MCP tools/call if A2A is unavailable.

        Returns response dict with 'parts' list and '_trace' timing metadata.
        """
        # Try A2A message/send first
        a2a_url = endpoint_url.rstrip("/") + "/api/a2a"
        request_sent_at = datetime.now(timezone.utc).isoformat()
        t0 = time.monotonic()
        try:
            async with A2AClient(timeout=60.0) as client:
                result = await client.send_message(
                    a2a_url, message, context_id=context_id, auth_token=self.workspace_token
                )
            latency_ms = round((time.monotonic() - t0) * 1000, 1)
            result["_trace"] = {
                "request_sent_at": request_sent_at,
                "response_received_at": datetime.now(timezone.utc).isoformat(),
                "latency_ms": latency_ms,
                "protocol": "a2a",
                "request_payload": {"message": message, "context_id": context_id},
                "response_payload": {k: v for k, v in result.items() if k != "_trace"},
            }
            return result
        except A2AClientError as e:
            logger.info("A2A message/send failed (%s), trying /invocations", e)

        # Fallback 1: try /invocations (standard Databricks protocol)
        try:
            return await self.call_invocations(endpoint_url, message)
        except Exception as e:
            logger.info("/invocations failed (%s), falling back to MCP", e)

        # Fallback 2: get tools list, pick the first tool, call it via MCP
        return await self._mcp_chat_fallback_traced(endpoint_url, message)

    async def _mcp_chat_fallback_traced(
        self,
        endpoint_url: str,
        message: str,
    ) -> Dict[str, Any]:
        """
        Fallback chat via MCP with per-RPC timing sub-events.

        Returns a dict shaped like an A2A response with 'parts' and '_trace'.
        """
        import json as _json
        import uuid

        request_sent_at = datetime.now(timezone.utc).isoformat()
        t_total = time.monotonic()
        sub_events: List[Dict[str, Any]] = []

        # --- tools/list ---
        list_req = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": {},
        }
        t0 = time.monotonic()
        tools_resp = await self.proxy_mcp(endpoint_url, list_req)
        list_dur = round((time.monotonic() - t0) * 1000, 1)
        sub_events.append({
            "type": "mcp_tools_list",
            "label": "tools/list",
            "duration_ms": list_dur,
            "request": list_req,
            "response": tools_resp,
        })

        tools = []
        if isinstance(tools_resp, dict):
            result = tools_resp.get("result", tools_resp)
            tools = result.get("tools", []) if isinstance(result, dict) else []

        if not tools:
            total_ms = round((time.monotonic() - t_total) * 1000, 1)
            resp: Dict[str, Any] = {
                "parts": [{"text": "This agent has no tools available via MCP."}],
            }
            resp["_trace"] = {
                "request_sent_at": request_sent_at,
                "response_received_at": datetime.now(timezone.utc).isoformat(),
                "latency_ms": total_ms,
                "protocol": "mcp_fallback",
                "request_payload": {"message": message},
                "response_payload": resp,
                "sub_events": sub_events,
            }
            return resp

        # Pick the first tool and pass the message as the first string param
        tool = tools[0]
        tool_name = tool.get("name", "unknown")
        input_schema = tool.get("inputSchema", {})
        properties = input_schema.get("properties", {})

        args: Dict[str, Any] = {}
        for param_name, param_def in properties.items():
            param_type = param_def.get("type", "string") if isinstance(param_def, dict) else "string"
            if param_type == "string":
                args[param_name] = message
                break

        if not args:
            first_param = next(iter(properties), None)
            if first_param:
                args[first_param] = message

        # --- tools/call ---
        call_req = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": args},
        }
        t0 = time.monotonic()
        call_resp = await self.proxy_mcp(endpoint_url, call_req)
        call_dur = round((time.monotonic() - t0) * 1000, 1)
        sub_events.append({
            "type": "mcp_tools_call",
            "label": f"tools/call ({tool_name})",
            "duration_ms": call_dur,
            "request": call_req,
            "response": call_resp,
        })

        # Extract result text
        call_result = call_resp.get("result", call_resp) if isinstance(call_resp, dict) else call_resp
        content = call_result.get("content", []) if isinstance(call_result, dict) else []

        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))

        if not text_parts:
            text_parts = [_json.dumps(call_result, indent=2)]

        # Extract _routing metadata from tool response (agent handoff tracking)
        routing = None
        inner_result = call_result.get("result", {}) if isinstance(call_result, dict) else {}
        if isinstance(inner_result, dict) and "_routing" in inner_result:
            routing = inner_result["_routing"]

        total_ms = round((time.monotonic() - t_total) * 1000, 1)
        resp = {
            "parts": [{"text": "\n".join(text_parts)}],
            "tool_used": tool_name,
            "tool_args": args,
        }
        trace: Dict[str, Any] = {
            "request_sent_at": request_sent_at,
            "response_received_at": datetime.now(timezone.utc).isoformat(),
            "latency_ms": total_ms,
            "protocol": "mcp_fallback",
            "request_payload": {"message": message},
            "response_payload": {k: v for k, v in resp.items() if k != "_trace"},
            "sub_events": sub_events,
        }
        if routing:
            trace["routing"] = routing
        resp["_trace"] = trace
        return resp

    # Pattern: *Routed to **agent_name*** (123ms)
    _ROUTING_RE = re.compile(
        r"\*Routed to \*\*(\w+)\*\*\*\s*\((\d+)ms\)",
    )

    @staticmethod
    def _extract_routing_from_text(parts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Parse routing hints from supervisor-style response text."""
        text = ""
        for p in parts:
            if isinstance(p, dict) and p.get("text"):
                text = p["text"]
                break
        if not text:
            return None

        m = DashboardScanner._ROUTING_RE.search(text)
        if not m:
            return None

        sub_agent = m.group(1)
        subagent_ms = int(m.group(2))

        # Extract UC-style table references (catalog.schema.table)
        tables = list(dict.fromkeys(
            re.findall(r"\b\w+\.\w+\.\w+\b", text)
        ))
        # Filter to likely UC tables (exclude common false positives)
        tables = [t for t in tables if not t.startswith(("e.g.", "i.e."))]

        return {
            "sub_agent": sub_agent,
            "tables_accessed": tables,
            "timing": {"subagent_ms": subagent_ms},
            "data_source": "text_parsed",
        }

    async def call_invocations(
        self,
        endpoint_url: str,
        message: str,
    ) -> Dict[str, Any]:
        """
        Call an agent via the Databricks /invocations protocol.

        Sends: {"input": [{"role": "user", "content": message}]}
        Returns: The agent's response dict with _trace metadata.
        """
        invocations_url = endpoint_url.rstrip("/") + "/invocations"
        headers = {"Content-Type": "application/json"}
        if self.workspace_token:
            headers["Authorization"] = f"Bearer {self.workspace_token}"

        payload = {"input": [{"role": "user", "content": message}]}

        request_sent_at = datetime.now(timezone.utc).isoformat()
        t0 = time.monotonic()

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as http:
            response = await http.post(invocations_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

        latency_ms = round((time.monotonic() - t0) * 1000, 1)

        # Extract text from Responses Agent protocol format
        parts = []
        for output_item in result.get("output", []):
            if isinstance(output_item, dict):
                for content_item in output_item.get("content", []):
                    if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                        parts.append({"text": content_item.get("text", "")})

        if not parts:
            import json as _json
            parts = [{"text": _json.dumps(result, indent=2)}]

        trace: Dict[str, Any] = {
            "request_sent_at": request_sent_at,
            "response_received_at": datetime.now(timezone.utc).isoformat(),
            "latency_ms": latency_ms,
            "protocol": "invocations",
            "request_payload": payload,
            "response_payload": result,
        }

        # Build routing from structured _metadata (from trace_sql/trace_table/trace_subagent)
        agent_meta = result.get("_metadata", {})
        routing: Dict[str, Any] = {}

        if isinstance(agent_meta, dict) and agent_meta:
            if agent_meta.get("tables_accessed"):
                routing["tables_accessed"] = agent_meta["tables_accessed"]
            if agent_meta.get("sub_agents"):
                routing["sub_agent"] = agent_meta["sub_agents"][0]
            if agent_meta.get("sql_queries"):
                routing["sql_queries"] = agent_meta["sql_queries"]
            if agent_meta.get("llm_calls"):
                routing["llm_calls"] = agent_meta["llm_calls"]
            routing["data_source"] = "agent_metadata"

        # Fallback: parse routing hints from response text
        if not routing:
            text_routing = self._extract_routing_from_text(parts)
            if text_routing:
                routing = text_routing

        if routing:
            trace["routing"] = routing

        return {"parts": parts, "_trace": trace}

    async def stream_a2a_message(
        self,
        endpoint_url: str,
        message: str,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Send a streaming A2A message and yield SSE events.

        Args:
            endpoint_url: Agent base URL
            message: Text message to send

        Yields:
            SSE event dicts from the agent's response stream
        """
        a2a_url = endpoint_url.rstrip("/") + "/api/a2a"
        async with A2AClient(timeout=60.0) as client:
            async for event in client.send_streaming_message(
                a2a_url, message, auth_token=self.workspace_token
            ):
                yield event
