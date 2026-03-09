"""Sub-agent: Expert Finder — finds experts by topic, specialty, or name."""

# Auth cleanup: prefer OAuth over PAT in Databricks Apps
import os
if os.environ.get("DATABRICKS_CLIENT_ID"):
    os.environ.pop("DATABRICKS_TOKEN", None)

import time
import logging
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementParameterListItem
from databricks_agents import app_agent, AgentRequest, AgentResponse

logger = logging.getLogger(__name__)

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


def _extract_keywords(query: str) -> list[str]:
    stop = {"a","an","the","is","are","on","any","do","does","for","in","of",
            "to","what","who","how","can","this","that","find","check","show",
            "me","my","about","with","and","or","all","get","list","tell"}
    return [w for w in query.lower().split() if w not in stop and len(w) > 1]


def _build_like_clauses(column: str, keywords: list[str], prefix: str = ""):
    col_tag = prefix or column.replace(".", "_")
    clauses, params = [], []
    for i, kw in enumerate(keywords):
        name = f"{col_tag}_{i}"
        clauses.append(f"LOWER({column}) LIKE :{name}")
        params.append({"name": name, "value": f"%{kw}%"})
    return " OR ".join(clauses) if clauses else "FALSE", params


# ---------------------------------------------------------------------------
# Demo fallback
# ---------------------------------------------------------------------------

def _demo_response(query: str) -> dict:
    return {
        "response": f"""**Found 5 experts for "{query}":**

**1. Dr. Sarah Chen** - Healthcare Technology
   - Relevance: 94%
   - 23 interviews | Rating: 4.9

**2. Michael Torres** - Supply Chain Analytics
   - Relevance: 89%
   - 18 interviews | Rating: 4.8

*Demo fallback -- UC tables not available*""",
        "data_source": "demo_fallback",
        "tables_accessed": [_fqn("experts")],
        "keywords_extracted": _extract_keywords(query),
        "sql_queries": [],
        "timing": {"sql_total_ms": 0, "total_ms": 0},
    }


# ---------------------------------------------------------------------------
# Agent + Tool
# ---------------------------------------------------------------------------

@app_agent(
    name="sub_expert_finder",
    description="Find experts who have knowledge on specific topics",
    capabilities=["expert_search", "expert_matching"],
    uc_catalog=os.environ.get("UC_CATALOG", "main"),
    uc_schema=os.environ.get("UC_SCHEMA", "agents"),
    enable_mcp=True,
)
async def sub_expert_finder(request: AgentRequest) -> dict:
    """Delegate to search tool."""
    return await search(request.last_user_message)


@sub_expert_finder.tool(description="Find experts who have knowledge on specific topics")
async def search(query: str) -> dict:
    """
    Find experts by topic, specialty, or name.

    Args:
        query: Topic or expertise to search for

    Returns:
        Structured result with ranked experts, metadata, and SQL traces
    """
    total_start = time.monotonic()
    sql_queries = []

    try:
        keywords = _extract_keywords(query)
        if not keywords:
            keywords = [query.lower()]

        topics_clause, topics_params = _build_like_clauses("topics", keywords)
        spec_clause, spec_params = _build_like_clauses("specialty", keywords)
        name_clause, name_params = _build_like_clauses("name", keywords)
        all_params = topics_params + spec_params + name_params

        result, trace = _execute_sql(
            f"""
            SELECT expert_id, name, specialty, interview_count, rating, topics, bio, region
            FROM {_fqn('experts')}
            WHERE {topics_clause} OR {spec_clause} OR {name_clause}
            ORDER BY rating DESC
            LIMIT 5
            """,
            all_params,
        )
        sql_queries.append(trace)

        if not result.result or not result.result.data_array:
            text = f'No experts found matching "{query}".'
        else:
            rows = result.result.data_array
            text = f'**Found {len(rows)} experts for "{query}":**\n\n'
            for i, row in enumerate(rows, 1):
                eid, name, spec, count, rating, topics, bio, region = row
                text += f"**{i}. {name}** -- {spec}\n"
                text += f"   - Relevance topics: {topics}\n"
                text += f"   - {count} interviews | Rating: {float(rating):.1f} | Region: {region}\n"
                text += f"   - {bio[:150]}{'...' if len(str(bio)) > 150 else ''}\n\n"
            text += f"\n*Data source: {_fqn('experts')}*"

        total_ms = round((time.monotonic() - total_start) * 1000, 1)
        sql_total_ms = sum(q["duration_ms"] for q in sql_queries)

        return {
            "response": text,
            "data_source": "live",
            "tables_accessed": [_fqn("experts")],
            "keywords_extracted": keywords,
            "sql_queries": sql_queries,
            "timing": {"sql_total_ms": sql_total_ms, "total_ms": total_ms},
        }

    except Exception as e:
        logger.error("SQL query failed for expert_finder: %s", e, exc_info=True)
        return _demo_response(query)


app = sub_expert_finder.app
