"""
Lightweight trace context for agent instrumentation.

Agents call trace_sql(), trace_table(), trace_subagent() during request handling.
The @app_agent framework collects these and includes them as _metadata in the response.

Usage in agent code:
    from dbx_agent_app import trace_sql, trace_table

    rows = _run_sql(query)
    trace_sql(query, row_count=len(rows), warehouse_id=WAREHOUSE_ID)
    trace_table(f"{CATALOG}.{SCHEMA}.accounts_enriched")
"""

from __future__ import annotations

import time
from contextvars import ContextVar
from typing import Any, Dict, List, Optional

# Per-request trace accumulator
_trace_ctx: ContextVar[Optional[Dict[str, Any]]] = ContextVar("_trace_ctx", default=None)


def _get_or_create() -> Dict[str, Any]:
    ctx = _trace_ctx.get()
    if ctx is None:
        ctx = {
            "tables_accessed": [],
            "sql_queries": [],
            "sub_agents": [],
            "llm_calls": [],
        }
        _trace_ctx.set(ctx)
    return ctx


def reset_trace_context() -> None:
    """Reset the trace context (called by framework before each request)."""
    _trace_ctx.set(None)


def collect_trace_metadata() -> Dict[str, Any]:
    """Collect accumulated trace data and reset (called by framework after handler)."""
    ctx = _trace_ctx.get()
    _trace_ctx.set(None)
    if not ctx:
        return {}

    result: Dict[str, Any] = {}
    if ctx["tables_accessed"]:
        result["tables_accessed"] = list(dict.fromkeys(ctx["tables_accessed"]))
    if ctx["sql_queries"]:
        result["sql_queries"] = ctx["sql_queries"]
    if ctx["sub_agents"]:
        result["sub_agents"] = list(dict.fromkeys(ctx["sub_agents"]))
    if ctx["llm_calls"]:
        result["llm_calls"] = ctx["llm_calls"]
    return result


# --- Public API for agent code ---


def trace_table(full_name: str) -> None:
    """Record a UC table access (e.g. 'catalog.schema.table')."""
    ctx = _get_or_create()
    ctx["tables_accessed"].append(full_name)


def trace_sql(
    statement: str,
    *,
    row_count: int = 0,
    duration_ms: Optional[float] = None,
    warehouse_id: Optional[str] = None,
    columns: Optional[List[Dict[str, str]]] = None,
) -> None:
    """Record a SQL query execution."""
    ctx = _get_or_create()
    entry: Dict[str, Any] = {"statement": statement, "row_count": row_count}
    if duration_ms is not None:
        entry["duration_ms"] = duration_ms
    if warehouse_id:
        entry["warehouse_id"] = warehouse_id
    if columns:
        entry["columns"] = columns
    ctx["sql_queries"].append(entry)


def trace_subagent(agent_name: str) -> None:
    """Record a sub-agent call."""
    ctx = _get_or_create()
    ctx["sub_agents"].append(agent_name)


def trace_llm(
    model: str,
    *,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    duration_ms: Optional[float] = None,
) -> None:
    """Record an LLM call."""
    ctx = _get_or_create()
    entry: Dict[str, Any] = {"model": model}
    if prompt_tokens is not None:
        entry["prompt_tokens"] = prompt_tokens
    if completion_tokens is not None:
        entry["completion_tokens"] = completion_tokens
    if duration_ms is not None:
        entry["duration_ms"] = duration_ms
    ctx["llm_calls"].append(entry)
