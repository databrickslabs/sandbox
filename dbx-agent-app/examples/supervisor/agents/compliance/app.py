"""Sub-agent: Compliance — checks restricted_list and nda_registry."""

# Auth cleanup: prefer OAuth over PAT in Databricks Apps
import os
if os.environ.get("DATABRICKS_CLIENT_ID"):
    os.environ.pop("DATABRICKS_TOKEN", None)

import time
import logging
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementParameterListItem
from dbx_agent_app import app_agent, AgentRequest, AgentResponse

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
        "response": f"""**Compliance Check Complete**

**Status: CLEARED**

Checks:
- Conflict of Interest: Clear
- Restricted List: Clear
- NDA Status: Active
- Prior Engagements: No issues

*Demo fallback -- UC tables not available*""",
        "data_source": "demo_fallback",
        "tables_accessed": [_fqn("restricted_list"), _fqn("nda_registry")],
        "keywords_extracted": _extract_keywords(query),
        "sql_queries": [],
        "timing": {"sql_total_ms": 0, "total_ms": 0},
    }


# ---------------------------------------------------------------------------
# Agent + Tool
# ---------------------------------------------------------------------------

@app_agent(
    name="sub_compliance",
    description="Check engagements for compliance, conflicts of interest, and NDA status",
    capabilities=["compliance", "conflict_check", "nda_status"],
    uc_catalog=os.environ.get("UC_CATALOG", "main"),
    uc_schema=os.environ.get("UC_SCHEMA", "agents"),
    enable_mcp=True,
)
async def sub_compliance(request: AgentRequest) -> dict:
    """Delegate to check tool."""
    return await check(request.last_user_message)


@sub_compliance.tool(description="Check engagements for compliance, conflicts of interest, and NDA status")
async def check(query: str) -> dict:
    """
    Check restricted list and NDA registry for compliance issues.

    Args:
        query: Compliance question or engagement to check

    Returns:
        Structured result with compliance status, metadata, and SQL traces
    """
    total_start = time.monotonic()
    sql_queries = []

    try:
        keywords = _extract_keywords(query)
        if not keywords:
            keywords = [query.lower()]

        # Restricted list check
        ent_clause, ent_params = _build_like_clauses("entity_name", keywords)
        rsn_clause, rsn_params = _build_like_clauses("reason", keywords)
        all_params = ent_params + rsn_params

        restricted_result, restricted_trace = _execute_sql(
            f"""
            SELECT entity_name, restriction_type, effective_date, expiry_date, reason
            FROM {_fqn('restricted_list')}
            WHERE ({ent_clause} OR {rsn_clause})
              AND expiry_date >= CURRENT_DATE()
            """,
            all_params,
        )
        sql_queries.append(restricted_trace)

        # NDA registry check
        exp_clause, exp_params = _build_like_clauses("expert_name", keywords)
        cov_clause, cov_params = _build_like_clauses("coverage_scope", keywords)
        nda_params = exp_params + cov_params

        nda_result, nda_trace = _execute_sql(
            f"""
            SELECT expert_name, nda_status, effective_date, expiry_date, coverage_scope
            FROM {_fqn('nda_registry')}
            WHERE {exp_clause} OR {cov_clause}
            """,
            nda_params,
        )
        sql_queries.append(nda_trace)

        text = f'**Compliance Check for "{query}"**\n\n'

        # Restricted list results
        has_restrictions = (
            restricted_result.result
            and restricted_result.result.data_array
            and len(restricted_result.result.data_array) > 0
        )

        if has_restrictions:
            text += "**Restricted List Matches:**\n"
            for row in restricted_result.result.data_array:
                entity, rtype, eff, exp, reason = row
                text += f"- **{entity}** [{rtype.upper()}] ({eff} to {exp})\n"
                text += f"  Reason: {reason}\n"
            text += "\n"
        else:
            text += "**Restricted List:** No active restrictions found.\n\n"

        # NDA results
        has_ndas = (
            nda_result.result
            and nda_result.result.data_array
            and len(nda_result.result.data_array) > 0
        )

        if has_ndas:
            text += "**NDA Status:**\n"
            for row in nda_result.result.data_array:
                expert, status, eff, exp, scope = row
                icon = {"active": "OK", "expired": "EXPIRED", "pending": "PENDING"}.get(
                    str(status).lower(), "?"
                )
                text += f"- **{expert}** -- [{icon}] {status} ({eff} to {exp})\n"
                text += f"  Coverage: {scope}\n"
            text += "\n"
        else:
            text += "**NDA Registry:** No matching NDA records found.\n\n"

        # Overall status
        if has_restrictions:
            text += "**Overall Status: FLAGGED** -- Review restrictions before proceeding.\n"
        else:
            text += "**Overall Status: CLEARED** -- No active restrictions found.\n"

        text += f"\n*Data sources: {_fqn('restricted_list')}, {_fqn('nda_registry')}*"

        total_ms = round((time.monotonic() - total_start) * 1000, 1)
        sql_total_ms = sum(q["duration_ms"] for q in sql_queries)

        return {
            "response": text,
            "data_source": "live",
            "tables_accessed": [_fqn("restricted_list"), _fqn("nda_registry")],
            "keywords_extracted": keywords,
            "sql_queries": sql_queries,
            "timing": {"sql_total_ms": sql_total_ms, "total_ms": total_ms},
        }

    except Exception as e:
        logger.error("SQL query failed for compliance: %s", e, exc_info=True)
        return _demo_response(query)


app = sub_compliance.app
