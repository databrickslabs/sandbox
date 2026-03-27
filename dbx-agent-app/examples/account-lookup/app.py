"""
Account Lookup Agent — search and retrieve account profiles from UC.
"""

import os

import json

import httpx
from databricks.sdk import WorkspaceClient

from dbx_agent_app import AgentRequest, AgentResponse, app_agent, trace_sql, trace_table, trace_llm

CATALOG = os.environ.get("UC_CATALOG", "ai_campaign_pipeline_catalog")
SCHEMA = os.environ.get("UC_SCHEMA", "ai_campaign")
WAREHOUSE_ID = os.environ.get("WAREHOUSE_ID", "9628673416acf780")
MODEL_ENDPOINT = os.environ.get("MODEL_ENDPOINT", "databricks-claude-sonnet-4-6")

_ws: WorkspaceClient | None = None


def _get_ws() -> WorkspaceClient:
    global _ws
    if _ws is None:
        _ws = WorkspaceClient()
    return _ws


def _run_sql(query: str, max_rows: int = 50) -> list[dict]:
    import time as _time
    ws = _get_ws()
    t0 = _time.monotonic()
    resp = ws.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID,
        statement=query,
        wait_timeout="30s",
    )
    duration_ms = round((_time.monotonic() - t0) * 1000, 1)
    if not resp.result or not resp.result.data_array:
        trace_sql(query.strip(), row_count=0, duration_ms=duration_ms, warehouse_id=WAREHOUSE_ID)
        return []
    schema_cols = resp.manifest.schema.columns
    columns = [c.name for c in schema_cols]
    col_info = [{"name": c.name, "type": str(c.type_name.value) if c.type_name else "STRING"} for c in schema_cols]
    rows = [dict(zip(columns, row)) for row in resp.result.data_array[:max_rows]]
    trace_sql(query.strip(), row_count=len(rows), duration_ms=duration_ms, warehouse_id=WAREHOUSE_ID, columns=col_info)
    return rows


def _get_auth_headers() -> dict:
    ws = _get_ws()
    headers = {"Content-Type": "application/json"}
    try:
        factory = ws.config.authenticate()
        if callable(factory):
            headers.update(factory())
        elif isinstance(factory, dict):
            headers.update(factory)
    except Exception:
        if ws.config.token:
            headers["Authorization"] = f"Bearer {ws.config.token}"
    return headers


async def _call_llm(system: str, user: str) -> str:
    ws = _get_ws()
    host = ws.config.host.rstrip("/")
    headers = _get_auth_headers()
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{host}/serving-endpoints/{MODEL_ENDPOINT}/invocations",
            json={
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": 1024,
                "temperature": 0.2,
            },
            headers=headers,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


@app_agent(
    name="account_lookup",
    description="Look up account profiles, pipeline, and AI readiness from UC tables",
    capabilities=["accounts", "lookup", "search"],
    enable_mcp=True,
)
async def account_lookup(request: AgentRequest) -> AgentResponse:
    query = request.last_user_message
    safe_query = query.replace("'", "''")

    trace_table(f"{CATALOG}.{SCHEMA}.accounts_enriched")
    accounts = _run_sql(
        f"""
        SELECT * FROM {CATALOG}.{SCHEMA}.accounts_enriched
        WHERE LOWER(name) LIKE LOWER('%{safe_query}%')
        LIMIT 5
        """
    )

    if not accounts:
        return AgentResponse.text(f"No accounts found matching '{query}'.")

    trace_table(f"{CATALOG}.{SCHEMA}.v_ai_pipeline")
    pipeline = _run_sql(
        f"""
        SELECT * FROM {CATALOG}.{SCHEMA}.v_ai_pipeline
        WHERE LOWER(account_name) LIKE LOWER('%{safe_query}%')
        ORDER BY weighted_dbus DESC
        """
    )

    trace_llm(MODEL_ENDPOINT)
    answer = await _call_llm(
        "You are an account research assistant. Summarize the account profile and pipeline concisely.",
        f"Query: {query}\n\nAccount Profile:\n{json.dumps(accounts, indent=2)}\n\nPipeline:\n{json.dumps(pipeline, indent=2)}",
    )
    return AgentResponse.text(answer)


@account_lookup.tool(description="Search for accounts by name")
async def search_accounts(name: str) -> dict:
    safe = name.replace("'", "''")
    rows = _run_sql(
        f"SELECT name, segment, ae, sa, ai_opportunity_score, executive_summary "
        f"FROM {CATALOG}.{SCHEMA}.accounts_enriched "
        f"WHERE LOWER(name) LIKE LOWER('%{safe}%') LIMIT 10"
    )
    return {"accounts": rows, "count": len(rows)}


@account_lookup.tool(description="Get full profile for a specific account")
async def get_profile(account_name: str) -> dict:
    safe = account_name.replace("'", "''")
    rows = _run_sql(
        f"SELECT * FROM {CATALOG}.{SCHEMA}.accounts_enriched "
        f"WHERE LOWER(name) LIKE LOWER('%{safe}%') LIMIT 1"
    )
    if not rows:
        return {"error": f"Account '{account_name}' not found"}
    return {"profile": rows[0]}


@account_lookup.tool(description="Get pipeline UCOs for an account")
async def get_account_pipeline(account_name: str) -> dict:
    safe = account_name.replace("'", "''")
    rows = _run_sql(
        f"SELECT * FROM {CATALOG}.{SCHEMA}.v_ai_pipeline "
        f"WHERE LOWER(account_name) LIKE LOWER('%{safe}%') "
        f"ORDER BY weighted_dbus DESC"
    )
    return {"pipeline": rows, "count": len(rows)}


app = account_lookup.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
