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
- Add `add_agent_card(app, ...)` for discoverability (optional, ~1 line)
- Deploy as Databricks Apps

## Primary API (helpers for agent developers)

```python
from fastapi import FastAPI
from databricks_agents import add_agent_card, add_mcp_endpoints

app = FastAPI()

@app.post("/invocations")
async def invocations(request): ...

# Make discoverable by the platform (~1 line)
add_agent_card(app, name="my_agent", description="...", capabilities=["search"])

# Optional: expose tools via MCP
add_mcp_endpoints(app, tools=[...])
```

## Legacy AgentApp (backward compatible)

`AgentApp` still works but is no longer the primary pattern. Prefer plain FastAPI + helpers.

```python
agent = AgentApp(name="my_agent", description="...", capabilities=["..."])
@agent.tool(description="Search")
async def search(query: str) -> dict: ...
app = agent.as_fastapi()
```

## Project Structure

- `src/databricks_agents/core/` — helpers (`add_agent_card`, `add_mcp_endpoints`) + legacy AgentApp
- `src/databricks_agents/dashboard/` — **the platform app** (FastAPI + React SPA)
- `src/databricks_agents/deploy/` — multi-agent deploy orchestration (agents.yaml)
- `src/databricks_agents/discovery/` — workspace agent scanning
- `src/databricks_agents/registry/` — Unity Catalog registration
- `src/databricks_agents/mcp/` — MCP JSON-RPC server (decoupled from AgentApp)
- `src/databricks_agents/cli.py` — CLI entry point
- `examples/` — example agents using helpers + official framework
- `tests/` — SDK tests

## Key Conventions

- SDK dependencies stay minimal (FastAPI, uvicorn, pydantic, httpx, databricks-sdk)
- mlflow is optional (`pip install databricks-agent-deploy[mlflow]`)
- The dashboard is the primary product, not a side feature
- `agents.yaml` defines agent systems (topology, dependencies, wiring)
- Examples use plain FastAPI + `add_agent_card()`, NOT AgentApp
- Platform is framework-agnostic: any app serving `/.well-known/agent.json` gets discovered

## CLI Commands

```
databricks-agents deploy     # Deploy agents from agents.yaml
databricks-agents status     # Show deployment status
databricks-agents destroy    # Tear down deployed agents
databricks-agents dashboard  # Launch platform locally (dev)
databricks-agents platform   # Deploy platform as a Databricks App
```
