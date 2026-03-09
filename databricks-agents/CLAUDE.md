# databricks-agent-deploy

## Project Overview

Agent platform for Databricks Apps. Package name: `databricks-agent-deploy` (PyPI), import as `databricks_agents` (Python).

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
from databricks_agents import app_agent, AgentRequest, AgentResponse

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
from databricks_agents.core.compat import to_langchain_messages
messages = to_langchain_messages(request)  # -> List[BaseMessage]
```

## Helpers API (plain FastAPI)

For agents that want full control over their FastAPI app:

```python
from fastapi import FastAPI
from databricks_agents import add_agent_card, add_mcp_endpoints

app = FastAPI()

@app.post("/invocations")
async def invocations(request): ...

add_agent_card(app, name="my_agent", description="...", capabilities=["search"])
add_mcp_endpoints(app, tools=[...])  # optional
```

## Project Structure

- `src/databricks_agents/core/` — `@app_agent` decorator, wire types, helpers, compat
- `src/databricks_agents/dashboard/` — **the platform app** (FastAPI + React SPA)
- `src/databricks_agents/deploy/` — multi-agent deploy orchestration (agents.yaml)
- `src/databricks_agents/discovery/` — workspace agent scanning
- `src/databricks_agents/registry/` — Unity Catalog registration
- `src/databricks_agents/mcp/` — MCP JSON-RPC server
- `src/databricks_agents/cli.py` — CLI entry point
- `examples/` — example agents using helpers + official framework
- `tests/` — SDK tests

## Key Conventions

- SDK dependencies stay minimal (FastAPI, uvicorn, pydantic, httpx, databricks-sdk)
- mlflow is optional (`pip install databricks-agent-deploy[mlflow]`)
- The dashboard is the primary product, not a side feature
- `agents.yaml` defines agent systems (topology, dependencies, wiring)
- Examples use `@app_agent` decorator (preferred) or plain FastAPI + `add_agent_card()`
- Platform is framework-agnostic: any app serving `/.well-known/agent.json` gets discovered

## CLI Commands

```
databricks-agents deploy     # Deploy agents from agents.yaml
databricks-agents status     # Show deployment status
databricks-agents destroy    # Tear down deployed agents
databricks-agents dashboard  # Launch platform locally (dev)
databricks-agents platform   # Deploy platform as a Databricks App
```
