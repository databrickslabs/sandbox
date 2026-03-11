"""
Campaign Supervisor — routes to campaign_insights or account_lookup via /invocations.

Proves multi-agent: LLM picks the right sub-agent, calls it over HTTP, returns the result.
"""

# Clean up auth environment for Databricks Apps (OAuth vs PAT conflict)
import os
if os.environ.get("DATABRICKS_CLIENT_ID"):
    os.environ.pop("DATABRICKS_TOKEN", None)

import json
import time

import httpx
from databricks.sdk import WorkspaceClient

from dbx_agent_app import AgentRequest, AgentResponse, app_agent, trace_subagent, trace_llm, trace_table, trace_sql

MODEL_ENDPOINT = os.environ.get("MODEL_ENDPOINT", "databricks-claude-sonnet-4-6")
CAMPAIGN_INSIGHTS_URL = os.environ.get(
    "CAMPAIGN_INSIGHTS_URL", "https://campaign-insights-7474654520950726.aws.databricksapps.com"
)
ACCOUNT_LOOKUP_URL = os.environ.get(
    "ACCOUNT_LOOKUP_URL", "https://account-lookup-7474654520950726.aws.databricksapps.com"
)

AGENTS = {
    "campaign_insights": {
        "url": CAMPAIGN_INSIGHTS_URL,
        "description": "Pipeline analytics, top accounts, spend data, general questions about the campaign pipeline",
    },
    "account_lookup": {
        "url": ACCOUNT_LOOKUP_URL,
        "description": "Look up a specific account by name, get its profile and pipeline UCOs",
    },
}

_ws: WorkspaceClient | None = None


def _get_ws() -> WorkspaceClient:
    global _ws
    if _ws is None:
        _ws = WorkspaceClient()
    return _ws


def _get_auth_headers() -> dict:
    """Get auth headers from the workspace client."""
    ws = _get_ws()
    try:
        header_factory = ws.config.authenticate()
        if callable(header_factory):
            return header_factory()
        if isinstance(header_factory, dict):
            return header_factory
    except Exception:
        pass
    return {}


async def _route(question: str) -> tuple[str, str]:
    """Ask the LLM which sub-agent to route to and extract the core query.

    Returns (agent_name, refined_query).
    """
    ws = _get_ws()
    host = ws.config.host.rstrip("/")
    headers = _get_auth_headers()

    agent_list = "\n".join(
        f"- {name}: {info['description']}" for name, info in AGENTS.items()
    )

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{host}/serving-endpoints/{MODEL_ENDPOINT}/invocations",
            json={
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a router. Given a user question, respond with exactly two lines:\n"
                            "Line 1: the agent name to route to\n"
                            "Line 2: a refined query to send to that agent. "
                            "For account_lookup: just the account name (e.g. 'Curinos'). "
                            "For campaign_insights: the original question as-is.\n\n"
                            "No other text.\n\n"
                            f"Available agents:\n{agent_list}"
                        ),
                    },
                    {"role": "user", "content": question},
                ],
                "max_tokens": 60,
                "temperature": 0,
            },
            headers=headers,
        )
        r.raise_for_status()
        lines = r.json()["choices"][0]["message"]["content"].strip().split("\n", 1)

    agent_choice = lines[0].strip().lower()
    refined_query = lines[1].strip() if len(lines) > 1 else question

    # Match to known agent
    for name in AGENTS:
        if name in agent_choice:
            return name, refined_query
    return "campaign_insights", question


def _call_subagent(agent_name: str, question: str) -> dict:
    """Call a sub-agent via /invocations (Databricks Responses Agent protocol)."""
    url = AGENTS[agent_name]["url"].rstrip("/") + "/invocations"
    headers = {**_get_auth_headers(), "Content-Type": "application/json"}

    start = time.monotonic()
    resp = httpx.post(
        url,
        json={"input": [{"role": "user", "content": question}]},
        headers=headers,
        timeout=60.0,
        follow_redirects=False,
    )

    # If we get a redirect, the auth didn't work for this app
    if resp.status_code in (301, 302, 303, 307, 308):
        latency_ms = round((time.monotonic() - start) * 1000)
        return {
            "agent": agent_name,
            "response": f"[Auth redirect — supervisor cannot reach {agent_name} directly. "
                        f"The sub-agent requires OAuth that the supervisor SP doesn't have yet.]",
            "latency_ms": latency_ms,
        }

    resp.raise_for_status()
    latency_ms = round((time.monotonic() - start) * 1000)

    data = resp.json()

    # Extract text from Responses Agent protocol
    text = ""
    for item in data.get("output", []):
        if isinstance(item, dict):
            for part in item.get("content", []):
                if isinstance(part, dict) and part.get("type") == "output_text":
                    text = part.get("text", "")
                    break
            if text:
                break

    # Fallback: if no output_text found, return raw JSON
    if not text:
        text = json.dumps(data, indent=2)

    # Relay sub-agent's _metadata into the supervisor's trace context
    sub_meta = data.get("_metadata", {})
    if isinstance(sub_meta, dict):
        for tbl in sub_meta.get("tables_accessed", []):
            trace_table(tbl)
        for sq in sub_meta.get("sql_queries", []):
            if isinstance(sq, dict):
                trace_sql(
                    sq.get("statement", ""),
                    row_count=sq.get("row_count", 0),
                    duration_ms=sq.get("duration_ms", 0),
                    warehouse_id=sq.get("warehouse_id", ""),
                    columns=sq.get("columns"),
                )

    return {"agent": agent_name, "response": text, "latency_ms": latency_ms}


@app_agent(
    name="campaign_supervisor",
    description="Supervisor that routes to campaign_insights or account_lookup agents",
    capabilities=["orchestration", "routing", "multi_agent"],
    enable_mcp=True,
)
async def campaign_supervisor(request: AgentRequest) -> AgentResponse:
    question = request.last_user_message

    trace_llm(MODEL_ENDPOINT)
    agent_name, refined_query = await _route(question)
    trace_subagent(agent_name)
    result = _call_subagent(agent_name, refined_query)

    header = f"*Routed to **{agent_name}*** ({result['latency_ms']}ms)\n\n"
    return AgentResponse.text(header + result["response"])


@campaign_supervisor.tool(description="List available sub-agents and their capabilities")
async def list_agents() -> dict:
    return {
        name: info["description"] for name, info in AGENTS.items()
    }


@campaign_supervisor.tool(description="Route a question to the best sub-agent and return the answer")
async def ask(question: str) -> dict:
    agent_name, refined_query = await _route(question)
    return _call_subagent(agent_name, refined_query)


app = campaign_supervisor.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
