"""Core agent components: @app_agent decorator, helpers, and types."""

from .helpers import add_agent_card, add_mcp_endpoints
from .app_agent import app_agent, AppAgent
from .trace_context import trace_sql, trace_table, trace_subagent, trace_llm
from .tracing import update_trace
from .types import AgentRequest, AgentResponse, InputItem, OutputItem, OutputTextContent, StreamEvent, UserContext

__all__ = [
    # Primary API: @app_agent decorator
    "app_agent",
    "AppAgent",
    # Wire protocol types
    "AgentRequest",
    "AgentResponse",
    "InputItem",
    "OutputItem",
    "OutputTextContent",
    "StreamEvent",
    "UserContext",
    # Tracing
    "update_trace",
    "trace_sql",
    "trace_table",
    "trace_subagent",
    "trace_llm",
    # Helpers
    "add_agent_card",
    "add_mcp_endpoints",
]
