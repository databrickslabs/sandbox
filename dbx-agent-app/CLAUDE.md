# dbx-agent-app

## Project Overview

Agent platform for Databricks Apps. Package name: `dbx-agent-app` (PyPI), import as `dbx_agent_app` (Python).

Build agents with any framework (official Databricks SDK, LangGraph, CrewAI, plain FastAPI). Deploy the platform to discover, test, trace, and govern all of them.

## Architecture: Agent Platform (v0.3)

This is NOT an agent-building SDK. It's the **control plane** for agents in your workspace.

### What the platform does:
- **Auto-discovery** — scans workspace apps for agent cards at `/.well-known/agent.json`
- **Testing** — call any agent via `/invocations` (Databricks standard protocol)
- **Governance** — register discovered agents in Unity Catalog, track lineage
- **Observability** — trace timing, protocol detection, agent handoff routing
- **Multi-agent deploy** — `agents.yaml` → topological sort → deploy → wire → permissions

### What agent developers do:
- Build agents with any framework
- Use `@app_agent` decorator (recommended) or `add_agent_card()` helper
- Deploy as Databricks Apps

## Primary API: `@app_agent` decorator

The recommended way to build agents. One decorator gives you `/invocations`, agent card, health, and MCP.

```python
from dbx_agent_app import app_agent, AgentRequest, AgentResponse

@app_agent(name="my_agent", description="Does stuff", capabilities=["search"])
async def my_agent(request: AgentRequest) -> AgentResponse:
    return AgentResponse.text(f"You said: {request.last_user_message}")

# my_agent.app → FastAPI with /invocations, /.well-known/agent.json, /health
# uvicorn app:my_agent.app
```

Return types auto-coerced: `AgentResponse`, `str`, or `dict`.

### Wire protocol types

SDK types that replace `mlflow.types.responses` — no mlflow dependency needed:

- `AgentRequest(input=[InputItem(role="user", content="...")])` — `.messages`, `.last_user_message`
- `AgentResponse.text("Hello!")` / `AgentResponse.from_dict({...})` — `.to_wire()`
- `StreamEvent.text_delta("chunk")` / `StreamEvent.done("full text")` — `.to_sse()`

### LangChain compatibility

For agents using LangChain, replace `self.prep_msgs_for_llm()` with:

```python
from dbx_agent_app.core.compat import to_langchain_messages
messages = to_langchain_messages(request)  # -> List[BaseMessage]
```

## Helpers API (plain FastAPI)

For agents that want full control over their FastAPI app:

```python
from fastapi import FastAPI
from dbx_agent_app import add_agent_card, add_mcp_endpoints

app = FastAPI()

@app.post("/invocations")
async def invocations(request): ...

add_agent_card(app, name="my_agent", description="...", capabilities=["search"])
add_mcp_endpoints(app, tools=[...])  # optional
```

## Project Structure

- `src/dbx_agent_app/core/` — `@app_agent` decorator, wire types, helpers, compat
- `src/dbx_agent_app/dashboard/` — **the platform app** (FastAPI + React SPA)
- `src/dbx_agent_app/deploy/` — multi-agent deploy orchestration (agents.yaml)
- `src/dbx_agent_app/discovery/` — workspace agent scanning
- `src/dbx_agent_app/registry/` — Unity Catalog registration
- `src/dbx_agent_app/mcp/` — MCP JSON-RPC server
- `src/dbx_agent_app/cli.py` — CLI entry point
- `examples/` — example agents using helpers + official framework
- `tests/` — SDK tests

## Key Conventions

- SDK dependencies stay minimal (FastAPI, uvicorn, pydantic, httpx, databricks-sdk)
- mlflow is optional (`pip install dbx-agent-app[mlflow]`)
- The dashboard is the primary product, not a side feature
- `agents.yaml` defines agent systems (topology, dependencies, wiring)
- Examples use `@app_agent` decorator (preferred) or plain FastAPI + `add_agent_card()`
- Platform is framework-agnostic: any app serving `/.well-known/agent.json` gets discovered

## CLI Commands

```
dbx-agent-app deploy     # Deploy agents from agents.yaml
dbx-agent-app status     # Show deployment status
dbx-agent-app destroy    # Tear down deployed agents
dbx-agent-app dashboard  # Launch platform locally (dev)
dbx-agent-app platform   # Deploy platform as a Databricks App
```
