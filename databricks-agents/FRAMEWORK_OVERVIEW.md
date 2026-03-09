# dbx-agent-app Framework Overview

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
dbx-agent-app/
├── src/dbx_agent_app/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── decorator.py            # @app_agent decorator
│   │   ├── types.py                # AgentRequest, AgentResponse
│   │   └── helpers.py              # add_agent_card() helper
│   ├── discovery/
│   │   ├── __init__.py
│   │   ├── a2a_client.py           # A2A protocol client
│   │   └── agent_discovery.py      # Workspace agent discovery
│   ├── mcp/                        # MCP server support
│   ├── registry/                   # UC integration
│   └── orchestration/              # Multi-agent patterns
│
├── examples/
│   ├── customer_research_agent.py  # Full agent example using @app_agent
│   ├── discover_agents.py          # Discovery client example
│   └── plain_fastapi_agent.py      # Plain FastAPI + add_agent_card()
│
├── tests/
│   └── test_decorator.py           # Core decorator tests
│
├── README.md                       # Comprehensive documentation
├── CONTRIBUTING.md                 # Contribution guidelines
├── LICENSE                         # Apache 2.0
└── pyproject.toml                  # Package configuration
```

## Core Components

### 1. @app_agent Decorator (core/decorator.py)

Python decorator that transforms an async function into an agent with auto-generated endpoints:
- `/.well-known/agent.json` - A2A protocol agent card
- `/invocations` - Standard Databricks protocol endpoint
- `/.well-known/openid-configuration` - OIDC delegation
- `/health` - Health check endpoint

**Usage:**
```python
from dbx_agent_app import app_agent, AgentRequest, AgentResponse

@app_agent(
    name="my_agent",
    description="Does useful things",
    capabilities=["search", "analysis"],
)
async def my_agent(request: AgentRequest) -> AgentResponse:
    return AgentResponse.text(f"You said: {request.last_user_message}")

app = my_agent.app  # FastAPI app
```

### 2. AgentDiscovery (discovery/agent_discovery.py)

Discovers agent-enabled apps in your workspace by:
1. Listing all running Databricks Apps via SDK
2. Probing each app for A2A agent cards (/.well-known/agent.json)
3. Returning DiscoveredAgent objects with metadata

**Usage:**
```python
from dbx_agent_app.discovery import AgentDiscovery

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
from dbx_agent_app.discovery import A2AClient

async with A2AClient() as client:
    card = await client.fetch_agent_card(agent_url)
    response = await client.send_message(agent_url, "Hello")
```

## What Gets Auto-Generated

When you create an agent with `@app_agent`, the framework automatically provides:

### Agent Card (/.well-known/agent.json)
```json
{
  "schema_version": "a2a/1.0",
  "name": "my_agent",
  "description": "Does useful things",
  "capabilities": ["search", "analysis"],
  "endpoints": {
    "invoke": "/invocations"
  }
}
```

### Invocations Endpoint (/invocations)
Standard Databricks protocol endpoint for agent communication

### OIDC Configuration (/.well-known/openid-configuration)
Delegates to Databricks workspace OIDC provider for authentication

## Examples

### Creating an Agent with @app_agent
```python
# examples/customer_research_agent.py
from dbx_agent_app import app_agent, AgentRequest, AgentResponse

@app_agent(
    name="customer_research",
    description="Research customer information",
    capabilities=["search", "analysis"],
)
async def customer_research(request: AgentRequest) -> AgentResponse:
    return AgentResponse.text(f"Processing: {request.last_user_message}")

app = customer_research.app
```

### Plain FastAPI with Helpers
```python
# examples/plain_fastapi_agent.py
from fastapi import FastAPI
from dbx_agent_app import add_agent_card

app = FastAPI()

@app.post("/invocations")
async def invocations(request):
    return {"response": "Hello"}

add_agent_card(
    app,
    name="my_agent",
    description="My agent",
    capabilities=["search"],
)
```

### Discovering Agents
```python
# examples/discover_agents.py
from dbx_agent_app.discovery import AgentDiscovery

discovery = AgentDiscovery(profile="my-profile")
result = await discovery.discover_agents()

for agent in result.agents:
    print(f"Found: {agent.name}")
```

## Testing

```bash
# Run tests
pytest

# Example test: test_decorator.py
def test_agent_card_endpoint():
    @app_agent(name="test", description="Test", capabilities=[])
    async def test_agent(request: AgentRequest) -> AgentResponse:
        return AgentResponse.text("OK")

    client = TestClient(test_agent.app)
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
- Manual protocol implementation required
- No workspace-level agent discovery
- Agents tied to Model Serving endpoints

**After:**
- Single decorator: `@app_agent` makes any function an agent
- Auto-generated protocol endpoints
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
