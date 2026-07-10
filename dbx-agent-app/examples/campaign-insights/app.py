"""
Campaign Insights Agent — passthrough to UC tables + foundation model.

Proves the plumbing: @app_agent → SQL warehouse → LLM → MCP tools → dashboard.
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
                "max_tokens": 2048,
                "temperature": 0.3,
            },
            headers=headers,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


@app_agent(
    name="campaign_insights",
    description="Passthrough agent for AI campaign pipeline data",
    capabilities=["sql", "analysis"],
    enable_mcp=True,
)
async def campaign_insights(request: AgentRequest) -> AgentResponse:
    question = request.last_user_message

    trace_table(f"{CATALOG}.{SCHEMA}.accounts_enriched")
    accounts = _run_sql(
        f"SELECT * FROM {CATALOG}.{SCHEMA}.accounts_enriched ORDER BY ai_opportunity_score DESC LIMIT 15"
    )
    trace_table(f"{CATALOG}.{SCHEMA}.v_ai_pipeline")
    pipeline = _run_sql(
        f"SELECT * FROM {CATALOG}.{SCHEMA}.v_ai_pipeline ORDER BY weighted_dbus DESC LIMIT 15"
    )

    trace_llm(MODEL_ENDPOINT)
    answer = await _call_llm(
        "You are a data assistant. Answer using the provided data. Be concise.",
        f"Question: {question}\n\nAccounts:\n{json.dumps(accounts, indent=2)}\n\nPipeline:\n{json.dumps(pipeline, indent=2)}",
    )
    return AgentResponse.text(answer)


@campaign_insights.tool(description="Query accounts_enriched table")
async def get_accounts(limit: int = 10) -> dict:
    try:
        n = max(1, min(int(limit), 100))
    except (ValueError, TypeError):
        n = 10
    rows = _run_sql(f"SELECT * FROM {CATALOG}.{SCHEMA}.accounts_enriched ORDER BY ai_opportunity_score DESC LIMIT {n}")
    return {"rows": rows, "count": len(rows)}


@campaign_insights.tool(description="Query v_ai_pipeline table")
async def get_pipeline(limit: int = 20) -> dict:
    try:
        n = max(1, min(int(limit), 100))
    except (ValueError, TypeError):
        n = 20
    rows = _run_sql(f"SELECT * FROM {CATALOG}.{SCHEMA}.v_ai_pipeline ORDER BY weighted_dbus DESC LIMIT {n}")
    return {"rows": rows, "count": len(rows)}


@campaign_insights.tool(description="Run a read-only SQL query")
async def query(sql: str) -> dict:
    if not sql.strip().upper().startswith("SELECT"):
        return {"error": "Only SELECT queries are allowed"}
    rows = _run_sql(sql)
    return {"rows": rows, "count": len(rows)}


@campaign_insights.tool(description="Send a question to the foundation model")
async def ask_llm(question: str, context: str = "") -> dict:
    answer = await _call_llm(
        "You are a data assistant. Answer concisely.",
        f"Question: {question}\n\nContext:\n{context}" if context else question,
    )
    return {"answer": answer}


app = campaign_insights.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
