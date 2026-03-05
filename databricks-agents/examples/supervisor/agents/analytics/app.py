"""Sub-agent: Analytics — queries call_metrics and engagement_summary."""

# Auth cleanup: prefer OAuth over PAT in Databricks Apps
import os
if os.environ.get("DATABRICKS_CLIENT_ID"):
    os.environ.pop("DATABRICKS_TOKEN", None)

import time
import logging
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementParameterListItem
from databricks_agents import AgentApp

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

agent = AgentApp(
    name="sub_analytics",
    description="Query business metrics, usage data, and operational analytics",
    capabilities=["analytics", "metrics", "reporting"],
    uc_catalog=os.environ.get("UC_CATALOG", "main"),
    uc_schema=os.environ.get("UC_SCHEMA", "agents"),
    auto_register=True,
    enable_mcp=True,
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

_workspace = WorkspaceClient()
_warehouse_id_cache = os.environ.get("WAREHOUSE_ID")

CATALOG = os.environ.get("UC_CATALOG", "serverless_dxukih_catalog")
SCHEMA = os.environ.get("UC_SCHEMA", "agents")


def _fqn(table: str) -> str:
    return f"{CATALOG}.{SCHEMA}.{table}"


def _get_warehouse_id() -> str:
    global _warehouse_id_cache
    if _warehouse_id_cache:
        return _warehouse_id_cache
    for wh in _workspace.warehouses.list():
        if wh.enable_serverless_compute:
            _warehouse_id_cache = wh.id
            return wh.id
    first = next(iter(_workspace.warehouses.list()), None)
    if first:
        _warehouse_id_cache = first.id
        return first.id
    raise ValueError("No SQL warehouse available")


def _execute_sql(statement, parameters=None):
    """Execute SQL and return (result, trace_entry)."""
    raw_params = parameters or []
    params = [
        StatementParameterListItem(name=p["name"], value=p["value"])
        if isinstance(p, dict) else p
        for p in raw_params
    ]
    wh_id = _get_warehouse_id()
    start = time.monotonic()
    result = _workspace.statement_execution.execute_statement(
        warehouse_id=wh_id, statement=statement,
        parameters=params, wait_timeout="50s",
    )
    duration_ms = round((time.monotonic() - start) * 1000, 1)

    row_count = len(result.result.data_array) if result.result and result.result.data_array else 0
    columns = []
    if result.manifest and result.manifest.schema and result.manifest.schema.columns:
        columns = [
            {"name": c.name,
             "type": str(c.type_name.value) if hasattr(c.type_name, "value") else str(c.type_name)}
            for c in result.manifest.schema.columns
        ]

    trace = {
        "statement": " ".join(statement.split()),
        "parameters": [
            {"name": p["name"], "value": p["value"]} if isinstance(p, dict)
            else {"name": p.name, "value": p.value}
            for p in raw_params
        ],
        "row_count": row_count,
        "columns": columns,
        "duration_ms": duration_ms,
        "warehouse_id": wh_id,
    }
    return result, trace


# ---------------------------------------------------------------------------
# Demo fallback
# ---------------------------------------------------------------------------

def _demo_response(query: str) -> dict:
    return {
        "response": f"""**Analytics Results:**

Query: {query}

- Total calls (last 90 days): 2,847
- Average duration: 52 minutes
- Month-over-month growth: +18%
- Top segment: Healthcare (34%)

*Demo fallback -- UC tables not available*""",
        "data_source": "demo_fallback",
        "tables_accessed": [_fqn("call_metrics"), _fqn("engagement_summary")],
        "keywords_extracted": [],
        "sql_queries": [],
        "timing": {"sql_total_ms": 0, "total_ms": 0},
    }


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------

@agent.tool(description="Query business metrics, usage data, and operational analytics")
async def query(query: str) -> dict:
    """
    Query call metrics and engagement summary data.

    Args:
        query: Analytics question to answer

    Returns:
        Structured result with metrics, tables, and SQL traces
    """
    total_start = time.monotonic()
    sql_queries = []

    try:
        # Aggregate call metrics for last 90 days
        metrics_result, metrics_trace = _execute_sql(
            f"""
            SELECT region,
                   SUM(call_count) AS total_calls,
                   ROUND(AVG(avg_duration_min), 1) AS avg_duration,
                   segment,
                   ROUND(SUM(revenue_usd), 2) AS total_revenue
            FROM {_fqn('call_metrics')}
            WHERE metric_date >= DATE_ADD(CURRENT_DATE(), -90)
            GROUP BY region, segment
            ORDER BY total_calls DESC
            LIMIT 12
            """
        )
        sql_queries.append(metrics_trace)

        # Get engagement summary
        summary_result, summary_trace = _execute_sql(
            f"SELECT metric_name, metric_value, period FROM {_fqn('engagement_summary')}"
        )
        sql_queries.append(summary_trace)

        text = f"**Analytics Results** (query: {query})\n\n"

        # Format engagement summary
        if summary_result.result and summary_result.result.data_array:
            text += "**Key Metrics (Last 90 Days):**\n"
            for row in summary_result.result.data_array:
                name, value, period = row
                display_name = str(name).replace("_", " ").title()
                val = float(value)
                if "pct" in str(name):
                    text += f"- {display_name}: {val:.1f}%\n"
                elif "usd" in str(name) or "revenue" in str(name):
                    text += f"- {display_name}: ${val:,.0f}\n"
                else:
                    text += f"- {display_name}: {val:,.1f}\n"
            text += "\n"

        # Format call metrics breakdown
        if metrics_result.result and metrics_result.result.data_array:
            text += "**Breakdown by Region & Segment:**\n\n"
            text += "| Region | Segment | Calls | Avg Duration | Revenue |\n"
            text += "|--------|---------|-------|--------------|---------|\n"
            for row in metrics_result.result.data_array:
                region, calls, dur, segment, rev = row
                text += f"| {region} | {segment} | {int(float(calls)):,} | {float(dur):.1f} min | ${float(rev):,.0f} |\n"
            text += "\n"

        text += f"*Data sources: {_fqn('call_metrics')}, {_fqn('engagement_summary')}*"

        total_ms = round((time.monotonic() - total_start) * 1000, 1)
        sql_total_ms = sum(q["duration_ms"] for q in sql_queries)

        return {
            "response": text,
            "data_source": "live",
            "tables_accessed": [_fqn("call_metrics"), _fqn("engagement_summary")],
            "keywords_extracted": [],
            "sql_queries": sql_queries,
            "timing": {"sql_total_ms": sql_total_ms, "total_ms": total_ms},
        }

    except Exception as e:
        logger.error("SQL query failed for analytics: %s", e, exc_info=True)
        return _demo_response(query)


# Build the FastAPI app with /invocations, A2A, MCP, and health endpoints
app = agent.as_fastapi()
