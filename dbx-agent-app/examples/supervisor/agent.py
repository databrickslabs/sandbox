"""Multi-Agent Supervisor — Routes queries to independently deployed sub-agents via /invocations.

Uses SDK types (AgentRequest/AgentResponse) instead of mlflow.pyfunc.ResponsesAgent.
"""

# IMPORTANT: Clean up auth environment BEFORE any Databricks SDK imports
# In Databricks Apps, both OAuth and PAT token may be present
import os
if os.environ.get("DATABRICKS_CLIENT_ID"):
    os.environ.pop("DATABRICKS_TOKEN", None)

import json
import time
import logging
from datetime import datetime, timezone
from uuid import uuid4
from typing import Dict, Any

import httpx

from dbx_agent_app import AgentRequest, AgentResponse, UserContext
from databricks_langchain import ChatDatabricks
from databricks.sdk import WorkspaceClient
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


class SupervisorAgent:
    """
    Multi-agent supervisor that routes queries to independently deployed sub-agents.

    Each sub-agent is a separate Databricks App with an /invocations endpoint
    (Databricks Responses Agent protocol). The supervisor uses LLM function
    calling to pick the right sub-agent, then calls it over HTTP at /invocations.
    """

    # Map tool names to sub-agent endpoint keys
    TOOL_TO_SUBAGENT = {
        "call_research": "research",
        "call_expert_finder": "expert_finder",
        "call_analytics": "analytics",
        "call_compliance_check": "compliance",
    }

    # Sub-agent configuration: env var for URL + tool name to invoke
    SUBAGENT_CONFIG = {
        "research":      {"url_env": "RESEARCH_URL",      "tool": "search"},
        "expert_finder": {"url_env": "EXPERT_FINDER_URL",  "tool": "search"},
        "analytics":     {"url_env": "ANALYTICS_URL",      "tool": "query"},
        "compliance":    {"url_env": "COMPLIANCE_URL",      "tool": "check"},
    }

    def __init__(self, config=None):
        """Initialize supervisor with LLM routing and sub-agent config."""
        self.config = config or {}

        # Workspace client for auth token generation
        self.workspace = WorkspaceClient()

        # Per-request user context (set in predict, used in tool calls)
        self._current_user_context: UserContext | None = None

        # Observability state — reset per call
        self._last_tables_accessed = []
        self._last_sql_queries = []
        self._last_keywords = []
        self._last_data_source = "live"
        self._last_routing = None

        # Initialize LLM with function calling
        self.llm = ChatDatabricks(
            endpoint=self.config.get("endpoint", "databricks-claude-sonnet-4-5"),
            temperature=0.1,
            max_tokens=4096,
        )

        # Create tools for sub-agents
        self.tools = self._create_subagent_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    # ------------------------------------------------------------------
    # Sub-agent client — calls deployed agents via /invocations
    # ------------------------------------------------------------------

    def _call_subagent_invocations(
        self, endpoint_name: str, query: str, user_context: UserContext | None = None,
    ) -> dict:
        """Call a sub-agent via /invocations (Databricks Responses Agent protocol)."""
        config = self.SUBAGENT_CONFIG[endpoint_name]
        agent_url = os.environ.get(config["url_env"])

        if not agent_url:
            logger.warning("No URL configured for sub-agent %s (env: %s)",
                           endpoint_name, config["url_env"])
            return self._fallback_response(endpoint_name, query)

        invocations_url = f"{agent_url.rstrip('/')}/invocations"

        # Authenticate using workspace OAuth (service principal)
        auth_headers = {}
        try:
            header_factory = self.workspace.config.authenticate()
            if callable(header_factory):
                auth_headers = header_factory()
            elif isinstance(header_factory, dict):
                auth_headers = header_factory
        except Exception as e:
            logger.warning("Auth header generation failed: %s", e)

        # Forward user identity so sub-agents can execute as the calling user
        if user_context is not None:
            auth_headers.update(user_context.as_forwarded_headers())

        payload = {
            "input": [{"role": "user", "content": query}],
        }

        start = time.monotonic()
        try:
            resp = httpx.post(
                invocations_url,
                json=payload,
                headers={**auth_headers, "Content-Type": "application/json"},
                timeout=50.0,
            )
            resp.raise_for_status()
        except Exception as e:
            logger.error("/invocations call to %s failed: %s", endpoint_name, e, exc_info=True)
            return self._fallback_response(endpoint_name, query)
        call_duration = round((time.monotonic() - start) * 1000, 1)

        response_data = resp.json()

        # Extract response text from Responses Agent protocol output
        response_text = ""
        output_items = response_data.get("output", [])
        for item in output_items:
            if isinstance(item, dict):
                content = item.get("content", [])
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "output_text":
                        response_text = part.get("text", "")
                        break
                if response_text:
                    break

        # Extract structured metadata if the sub-agent passed it through
        metadata = response_data.get("_metadata") or {}

        if isinstance(metadata, dict) and "response" in metadata:
            metadata["_network_ms"] = call_duration
            metadata["_agent_url"] = agent_url
            return metadata

        return {
            "response": response_text,
            "data_source": metadata.get("data_source", "live"),
            "tables_accessed": metadata.get("tables_accessed", []),
            "keywords_extracted": metadata.get("keywords_extracted", []),
            "sql_queries": metadata.get("sql_queries", []),
            "timing": metadata.get("timing", {"sql_total_ms": 0, "total_ms": call_duration}),
            "_network_ms": call_duration,
            "_agent_url": agent_url,
        }

    def _fallback_response(self, endpoint_name: str, query: str) -> dict:
        """Return a fallback response when MCP call fails or URL is not configured."""
        catalog = self.config.get("catalog", "serverless_dxukih_catalog")
        schema = self.config.get("schema", "agents")
        fqn = lambda t: f"{catalog}.{schema}.{t}"

        demo_responses = {
            "research": {
                "response": f'Based on analysis of expert transcripts:\n\n**Key Insights on "{query}":**\n\n'
                    '1. **Dr. Sarah Chen** (Healthcare Technology, Interview #T-2025-1247):\n'
                    '   "We\'re seeing 40% year-over-year growth in AI implementation."\n\n'
                    '2. **Michael Torres** (Supply Chain, Interview #T-2025-1189):\n'
                    '   "Leaders prioritize real-time visibility and transparency."\n\n'
                    '*Demo fallback -- sub-agent not reachable*',
                "tables_accessed": [fqn("expert_transcripts")],
            },
            "expert_finder": {
                "response": f'**Found 5 experts for "{query}":**\n\n'
                    '**1. Dr. Sarah Chen** - Healthcare Technology\n'
                    '   - 23 interviews | Rating: 4.9\n\n'
                    '**2. Michael Torres** - Supply Chain Analytics\n'
                    '   - 18 interviews | Rating: 4.8\n\n'
                    '*Demo fallback -- sub-agent not reachable*',
                "tables_accessed": [fqn("experts")],
            },
            "analytics": {
                "response": f'**Analytics Results:**\n\nQuery: {query}\n\n'
                    '- Total calls (last 90 days): 2,847\n'
                    '- Average duration: 52 minutes\n'
                    '- Month-over-month growth: +18%\n\n'
                    '*Demo fallback -- sub-agent not reachable*',
                "tables_accessed": [fqn("call_metrics"), fqn("engagement_summary")],
            },
            "compliance": {
                "response": '**Compliance Check Complete**\n\n**Status: CLEARED**\n\n'
                    'Checks:\n- Conflict of Interest: Clear\n- Restricted List: Clear\n'
                    '- NDA Status: Active\n\n'
                    '*Demo fallback -- sub-agent not reachable*',
                "tables_accessed": [fqn("restricted_list"), fqn("nda_registry")],
            },
        }

        demo = demo_responses.get(endpoint_name, demo_responses["research"])
        return {
            "response": demo["response"],
            "data_source": "demo_fallback",
            "tables_accessed": demo["tables_accessed"],
            "keywords_extracted": [],
            "sql_queries": [],
            "timing": {"sql_total_ms": 0, "total_ms": 0},
            "_network_ms": 0,
            "_agent_url": None,
        }

    # ------------------------------------------------------------------
    # Sub-agent dispatch (wraps invocations call with observability)
    # ------------------------------------------------------------------

    def _call_subagent(self, endpoint_name: str, query: str) -> str:
        """Call a sub-agent via /invocations and update observability state."""
        self._last_tables_accessed = []
        self._last_sql_queries = []
        self._last_keywords = []
        self._last_data_source = "live"
        self._last_subagent_duration_ms = 0
        self._last_network_ms = 0
        self._last_agent_url = None

        result = self._call_subagent_invocations(
            endpoint_name, query, self._current_user_context
        )

        self._last_tables_accessed = result.get("tables_accessed", [])
        self._last_sql_queries = result.get("sql_queries", [])
        self._last_keywords = result.get("keywords_extracted", [])
        self._last_data_source = result.get("data_source", "live")
        self._last_subagent_duration_ms = result.get("timing", {}).get("total_ms", 0)
        self._last_network_ms = result.get("_network_ms", 0)
        self._last_agent_url = result.get("_agent_url")

        return result.get("response", str(result))

    # ------------------------------------------------------------------
    # Tool definitions
    # ------------------------------------------------------------------

    def _create_subagent_tools(self):
        """Create sync tools that route to sub-agent /invocations endpoints."""

        @tool
        def call_research(query: str) -> str:
            """
            Search expert interview transcripts for insights and opinions.

            Use for:
            - Questions about what experts have said
            - Industry insights, trends, expert opinions
            - "What do experts think about..."
            - Summarizing expert perspectives
            """
            return self._call_subagent("research", query)

        @tool
        def call_expert_finder(query: str) -> str:
            """
            Find experts who have knowledge on specific topics.

            Use for:
            - "Find experts who know about..."
            - "Who has discussed..."
            - Identifying advisors with specific expertise
            """
            return self._call_subagent("expert_finder", query)

        @tool
        def call_analytics(query: str) -> str:
            """
            Query business metrics, usage data, and operational analytics.

            Use for:
            - Questions with numbers, counts, percentages
            - "How many...", "What percentage...", "Show me usage..."
            - Trends over time, comparisons
            """
            return self._call_subagent("analytics", query)

        @tool
        def call_compliance_check(query: str) -> str:
            """
            Check engagements for compliance and conflicts of interest.

            Use for:
            - "Check if this engagement is compliant..."
            - "Any conflicts with..."
            - Conflict of interest screening
            """
            return self._call_subagent("compliance", query)

        return [call_research, call_expert_finder, call_analytics, call_compliance_check]

    # ------------------------------------------------------------------
    # Predict
    # ------------------------------------------------------------------

    def predict(self, request: AgentRequest) -> AgentResponse:
        """Route query to appropriate sub-agent via /invocations."""
        # Capture user context for forwarding to sub-agents during tool calls
        self._current_user_context = request.user_context

        # Convert SDK request to LangChain messages
        messages = []
        for item in request.input:
            if item.role == "user":
                messages.append(HumanMessage(content=item.content))
            elif item.role == "assistant":
                messages.append(AIMessage(content=item.content))

        # System prompt for routing
        system_msg = SystemMessage(content="""You are a multi-agent supervisor for an expert network platform.

Your role is to route user queries to the appropriate specialized sub-agent:

**Available Sub-Agents:**

1. **call_research**: Expert interview transcript research
   - Use for: qualitative insights, expert opinions, "what do experts say about..."

2. **call_expert_finder**: Find experts by topic/domain
   - Use for: "find experts who...", "who knows about...", expert recommendations

3. **call_analytics**: Business metrics and SQL queries
   - Use for: numbers, counts, trends, "how many...", quantitative questions

4. **call_compliance_check**: Compliance and conflict checks
   - Use for: policy adherence, conflicts of interest, engagement approval

**Routing Guidelines:**
- Choose ONE sub-agent that best matches the query intent
- Call the tool with the full user query
- Return the sub-agent's response directly
- If unclear, prefer call_research for general questions

**DO NOT:**
- Try to answer queries yourself
- Call multiple tools (pick the best one)
- Modify or summarize the sub-agent's response""")

        llm_start = time.monotonic()
        response = self.llm_with_tools.invoke([system_msg] + messages)
        llm_duration_ms = round((time.monotonic() - llm_start) * 1000, 1)

        self._last_routing = None
        call_timestamp = datetime.now(timezone.utc).isoformat()

        # Check if tool was called
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_call = response.tool_calls[0]
            tool_name = tool_call['name']
            tool_args = tool_call['args']

            for t in self.tools:
                if t.name == tool_name:
                    result = t.invoke(tool_args)

                    sub_agent = self.TOOL_TO_SUBAGENT.get(tool_name, tool_name)
                    total_sql_ms = sum(
                        q.get("duration_ms", 0) for q in self._last_sql_queries
                        if "duration_ms" in q
                    )
                    network_ms = getattr(self, "_last_network_ms", 0)
                    subagent_ms = getattr(self, "_last_subagent_duration_ms", 0)
                    agent_url = getattr(self, "_last_agent_url", None)

                    self._last_routing = {
                        "tool": tool_name,
                        "sub_agent": sub_agent,
                        "timestamp": call_timestamp,
                        "data_source": self._last_data_source,
                        "tables_accessed": self._last_tables_accessed,
                        "keywords_extracted": self._last_keywords,
                        "routing_decision": {
                            "model": self.config.get("endpoint", "databricks-claude-sonnet-4-5"),
                            "latency_ms": llm_duration_ms,
                            "tool_selected": tool_name,
                            "tool_args": tool_args,
                        },
                        "sql_queries": self._last_sql_queries,
                        "timing": {
                            "routing_ms": llm_duration_ms,
                            "network_ms": network_ms,
                            "sql_total_ms": total_sql_ms,
                            "subagent_ms": subagent_ms,
                            "total_ms": round(llm_duration_ms + network_ms, 1),
                        },
                        "agent_endpoint": agent_url,
                    }

                    return AgentResponse.text(result)

        # No tool called — return LLM response directly
        self._last_routing = {
            "tool": None,
            "sub_agent": None,
            "timestamp": call_timestamp,
            "data_source": "llm_direct",
            "tables_accessed": [],
            "keywords_extracted": [],
            "routing_decision": {
                "model": self.config.get("endpoint", "databricks-claude-sonnet-4-5"),
                "latency_ms": llm_duration_ms,
                "tool_selected": None,
                "reason": "LLM did not select a tool",
            },
            "sql_queries": [],
            "timing": {
                "routing_ms": llm_duration_ms,
                "network_ms": 0,
                "sql_total_ms": 0,
                "subagent_ms": 0,
                "total_ms": llm_duration_ms,
            },
            "agent_endpoint": None,
        }
        return AgentResponse.text(response.content)
