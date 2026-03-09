"""Sub-agent: Research — searches expert_transcripts for insights."""

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
        "response": f"""Based on analysis of expert transcripts:

**Key Insights on "{query}":**

1. **Dr. Sarah Chen** (Healthcare Technology, Interview #T-2025-1247):
   "We're seeing 40% year-over-year growth in AI implementation."

2. **Michael Torres** (Supply Chain, Interview #T-2025-1189):
   "Leaders prioritize real-time visibility and transparency."

**Themes:**
- Accelerating digital transformation (8/12 interviews)
- Talent shortage challenges (7/12 interviews)

*Demo fallback -- UC tables not available*""",
        "data_source": "demo_fallback",
        "tables_accessed": [_fqn("expert_transcripts")],
        "keywords_extracted": _extract_keywords(query),
        "sql_queries": [],
        "timing": {"sql_total_ms": 0, "total_ms": 0},
    }


# ---------------------------------------------------------------------------
# Agent + Tool
# ---------------------------------------------------------------------------

@app_agent(
    name="sub_research",
    description="Search expert interview transcripts for insights and opinions",
    capabilities=["research", "transcript_search"],
    uc_catalog=os.environ.get("UC_CATALOG", "main"),
    uc_schema=os.environ.get("UC_SCHEMA", "agents"),
    enable_mcp=True,
)
async def sub_research(request: AgentRequest) -> dict:
    """Delegate to search tool."""
    return await search(request.last_user_message)


@sub_research.tool(description="Search expert interview transcripts for insights and opinions")
async def search(query: str) -> dict:
    """
    Search expert transcripts by topic, sector, or keyword.

    Args:
        query: Natural-language research question

    Returns:
        Structured result with response text, metadata, and SQL traces
    """
    total_start = time.monotonic()
    sql_queries = []

    try:
        keywords = _extract_keywords(query)
        if not keywords:
            keywords = [query.lower()]

        topic_clause, topic_params = _build_like_clauses("topic", keywords)
        excerpt_clause, excerpt_params = _build_like_clauses("transcript_excerpt", keywords)
        sector_clause, sector_params = _build_like_clauses("sector", keywords)
        all_params = topic_params + excerpt_params + sector_params

        result, trace = _execute_sql(
            f"""
            SELECT transcript_id, expert_name, topic, transcript_excerpt,
                   interview_date, relevance_score, sector
            FROM {_fqn('expert_transcripts')}
            WHERE {topic_clause} OR {excerpt_clause} OR {sector_clause}
            ORDER BY relevance_score DESC
            LIMIT 5
            """,
            all_params,
        )
        sql_queries.append(trace)

        if not result.result or not result.result.data_array:
            text = f'No transcripts found matching "{query}".'
        else:
            rows = result.result.data_array
            text = f'**Research Results for "{query}"** ({len(rows)} transcripts found)\n\n'
            for i, row in enumerate(rows, 1):
                tid, expert, topic, excerpt, date, score, sector = row
                text += f"**{i}. {expert}** ({sector}, Interview #{tid})\n"
                text += f"   Topic: {topic} | Relevance: {float(score):.0%} | Date: {date}\n"
                text += f'   > "{excerpt[:250]}{"..." if len(str(excerpt)) > 250 else ""}"\n\n'
            text += f"\n*Data source: {_fqn('expert_transcripts')}*"

        total_ms = round((time.monotonic() - total_start) * 1000, 1)
        sql_total_ms = sum(q["duration_ms"] for q in sql_queries)

        return {
            "response": text,
            "data_source": "live",
            "tables_accessed": [_fqn("expert_transcripts")],
            "keywords_extracted": keywords,
            "sql_queries": sql_queries,
            "timing": {"sql_total_ms": sql_total_ms, "total_ms": total_ms},
        }

    except Exception as e:
        logger.error("SQL query failed for research: %s", e, exc_info=True)
        return _demo_response(query)


app = sub_research.app
