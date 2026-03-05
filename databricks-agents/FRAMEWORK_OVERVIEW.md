# databricks-agents Framework Overview

## What We've Built

A lightweight Python framework for building discoverable AI agents on Databricks Apps. This is designed as a Databricks Labs contribution that makes it trivial to:

1. **Turn any Databricks App into an agent** with auto-generated A2A protocol endpoints
2. **Discover agent-enabled apps** across your Databricks workspace
3. **Communicate with agents** using the A2A protocol standard

## Key Design Principle

**Agent = Databricks App** (not Model Serving endpoint)

This framework treats Databricks Apps as first-class agents, allowing them to:
- Run custom logic, tools, and UI
- Expose capabilities via standard agent cards
- Be discovered by other agents and systems
- Delegate authentication to Databricks workspace OIDC

## Framework Structure

```
databricks-agents/
├── src/databricks_agents/
│   ├── core/
│   │   ├── __init__.py
│   │   └── agent_app.py           # AgentApp class (FastAPI wrapper)
│   ├── discovery/
│   │   ├── __init__.py
│   │   ├── a2a_client.py          # A2A protocol client
│   │   └── agent_discovery.py     # Workspace agent discovery
│   ├── mcp/                        # (Future: MCP server support)
│   ├── orchestration/              # (Future: Multi-agent patterns)
│   └── registry/                   # (Future: UC integration)
│
├── examples/
│   ├── customer_research_agent.py  # Full agent example
│   ├── discover_agents.py          # Discovery client example
│   └── communicate_with_agent.py   # A2A communication example
│
├── tests/
│   └── test_agent_app.py           # Core functionality tests
│
├── README.md                       # Comprehensive documentation
├── CONTRIBUTING.md                 # Contribution guidelines
├── LICENSE                         # Apache 2.0
└── pyproject.toml                  # Package configuration
```

## Core Components

### 1. AgentApp (core/agent_app.py)

FastAPI wrapper that auto-generates:
- `/.well-known/agent.json` - A2A protocol agent card
- `/.well-known/openid-configuration` - OIDC delegation
- `/health` - Health check endpoint
- `/api/tools/<tool_name>` - Tool endpoints

**Usage:**
```python
from databricks_agents import AgentApp

app = AgentApp(
    name="my_agent",
    description="Does useful things",
    capabilities=["search", "analysis"],
)

@app.tool(description="Search for data")
async def search(query: str) -> dict:
    return {"results": [...]}
```

### 2. AgentDiscovery (discovery/agent_discovery.py)

Discovers agent-enabled apps in your workspace by:
1. Listing all running Databricks Apps via SDK
2. Probing each app for A2A agent cards (/.well-known/agent.json)
3. Returning DiscoveredAgent objects with metadata

**Usage:**
```python
from databricks_agents.discovery import AgentDiscovery

discovery = AgentDiscovery(profile="my-profile")
result = await discovery.discover_agents()

for agent in result.agents:
    print(f"{agent.name}: {agent.endpoint_url}")
```

### 3. A2AClient (discovery/a2a_client.py)

Communicates with agents using A2A protocol:
- Fetch agent cards (with OAuth redirect detection)
- Send messages via JSON-RPC
- Stream responses via SSE
- Handle authentication

**Usage:**
```python
from databricks_agents.discovery import A2AClient

async with A2AClient() as client:
    card = await client.fetch_agent_card(agent_url)
    response = await client.send_message(agent_url, "Hello")
```

## What Gets Auto-Generated

When you create an `AgentApp`, the framework automatically provides:

### Agent Card (/.well-known/agent.json)
```json
{
  "schema_version": "a2a/1.0",
  "name": "my_agent",
  "description": "Does useful things",
  "capabilities": ["search", "analysis"],
  "endpoints": {
    "mcp": "/api/mcp",
    "invoke": "/api/invoke"
  },
  "tools": [...]
}
```

### OIDC Configuration (/.well-known/openid-configuration)
Delegates to Databricks workspace OIDC provider for authentication

### Tool Endpoints (/api/tools/<tool_name>)
Each tool registered with `@app.tool()` gets a FastAPI endpoint

## Examples

### Creating an Agent
```python
# examples/customer_research_agent.py
from databricks_agents import AgentApp

app = AgentApp(
    name="customer_research",
    description="Research customer information",
    capabilities=["search", "analysis"],
)

@app.tool(description="Search companies")
async def search_companies(industry: str) -> dict:
    return {"results": [...]}
```

### Discovering Agents
```python
# examples/discover_agents.py
from databricks_agents.discovery import AgentDiscovery

discovery = AgentDiscovery(profile="my-profile")
result = await discovery.discover_agents()

for agent in result.agents:
    print(f"Found: {agent.name}")
```

### Communicating with Agents
```python
# examples/communicate_with_agent.py
from databricks_agents.discovery import A2AClient

async with A2AClient() as client:
    card = await client.fetch_agent_card(agent_url)
    response = await client.send_message(agent_url, "Hello")
```

## Testing

```bash
# Run tests
pytest

# Example test: test_agent_app.py
def test_agent_card_endpoint():
    app = AgentApp(name="test", description="Test", capabilities=[])
    client = TestClient(app)
    response = client.get("/.well-known/agent.json")
    assert response.status_code == 200
    assert response.json()["name"] == "test"
```

## Future Roadmap

- **Unity Catalog integration**: Register agents as AGENT catalog objects
- **MCP server support**: Model Context Protocol endpoints
- **Orchestration patterns**: Multi-agent coordination utilities
- **RAG utilities**: Built-in vector search and retrieval
- **Observability**: Logging, metrics, tracing integrations

## Why This Matters

This framework solves the gap in Databricks' agent ecosystem:

**Before:**
- No standard way to make apps discoverable as agents
- Manual A2A protocol implementation required
- No workspace-level agent discovery
- Agents tied to Model Serving endpoints

**After:**
- Single decorator: `AgentApp()` makes any app an agent
- Auto-generated A2A protocol endpoints
- Built-in discovery across workspace
- Agents can be full applications with custom logic

## Databricks Labs Fit

This is a natural Labs contribution because it:
- Builds on top of Databricks primitives (Apps, SDK, OIDC)
- Follows open standards (A2A protocol)
- Enables new patterns (multi-agent systems on Databricks)
- Low-friction adoption (5 lines of code to get started)
- Complements existing offerings (Model Serving, UC Functions)

## Next Steps for Contribution

1. **Add tests** for discovery and A2A client modules
2. **Create integration examples** with real Databricks Apps
3. **Add Unity Catalog integration** for agent registration
4. **Write MCP server support** for UC Functions
5. **Build orchestration patterns** for multi-agent workflows
6. **Set up CI/CD** for testing and publishing
7. **Create documentation site** (GitHub Pages or Read the Docs)

## Contact

This framework was extracted from the multi-agent registry project and designed for Databricks Labs contribution.
