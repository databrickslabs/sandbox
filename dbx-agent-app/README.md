# dbx-agent-app

A lightweight Python framework for building discoverable AI agents on Databricks Apps that automatically expose A2A (Agent-to-Agent) protocol endpoints.

## What It Does

The `dbx-agent-app` framework makes it trivial to turn a Databricks App into a discoverable, standards-compliant agent:

- **Auto-generates A2A protocol endpoints** (`/.well-known/agent.json`, `/.well-known/openid-configuration`)
- **Wraps FastAPI** to seamlessly integrate agent capabilities with your web app
- **Provides discovery clients** to find and communicate with other agents in your workspace
- **Handles authentication** by delegating to Databricks workspace OIDC

## Key Concepts

### Agent = Databricks App

Unlike traditional approaches where agents are backed by Model Serving endpoints, this framework treats **Databricks Apps as first-class agents**. Each app:

- Exposes its capabilities via a standard agent card
- Can be discovered by other agents and systems
- Runs as a full application with custom logic, tools, and UI

### A2A Protocol

The [A2A (Agent-to-Agent) protocol](https://a2a.so/) provides a standard way for agents to:
- Advertise their capabilities via `/.well-known/agent.json`
- Delegate authentication via `/.well-known/openid-configuration`
- Communicate using JSON-RPC over HTTP

## Installation

```bash
pip install dbx-agent-app
```

Or with development dependencies:

```bash
pip install dbx-agent-app[dev]
```

## Quick Start

### 1. Create an Agent

```python
from dbx_agent_app import app_agent, AgentRequest, AgentResponse

# Create your agent with capabilities
@app_agent(
    name="customer_research",
    description="Research customer information and market trends",
    capabilities=["search", "analysis", "research"],
)
async def customer_research(request: AgentRequest) -> AgentResponse:
    # Your agent logic here
    return AgentResponse.text(f"Processing: {request.last_user_message}")

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(customer_research.app, host="0.0.0.0", port=8000)
```

### 2. Deploy to Databricks Apps

Create an `app.yaml`:

```yaml
command:
  - "python"
  - "-m"
  - "uvicorn"
  - "app:app"
  - "--host"
  - "0.0.0.0"
  - "--port"
  - "8000"

env:
  - name: DATABRICKS_HOST
    valueFrom: system
```

Deploy:

```bash
databricks apps create customer-research --description "Customer research agent"
databricks apps deploy customer-research --source-code-path ./
```

### 3. Discover Agents in Your Workspace

```python
import asyncio
from dbx_agent_app.discovery import AgentDiscovery

async def main():
    discovery = AgentDiscovery(profile="my-profile")
    result = await discovery.discover_agents()
    
    for agent in result.agents:
        print(f"Found: {agent.name} - {agent.description}")
        print(f"  URL: {agent.endpoint_url}")
        print(f"  Capabilities: {agent.capabilities}")

asyncio.run(main())
```

## What Gets Auto-Generated

When you create an agent with `@app_agent`, the framework automatically sets up:

### `/.well-known/agent.json` (Agent Card)

```json
{
  "schema_version": "a2a/1.0",
  "name": "customer_research",
  "description": "Research customer information and market trends",
  "capabilities": ["search", "analysis", "research"],
  "version": "1.0.0",
  "endpoints": {
    "mcp": "/api/mcp",
    "invoke": "/api/invoke"
  },
  "tools": [
    {
      "name": "search_companies",
      "description": "Search for companies by industry",
      "parameters": {
        "industry": {"type": "str", "required": true},
        "limit": {"type": "int", "required": false}
      }
    }
  ]
}
```

### `/.well-known/openid-configuration`

Delegates authentication to the Databricks workspace OIDC provider:

```json
{
  "issuer": "https://your-workspace.cloud.databricks.com/oidc",
  "authorization_endpoint": "https://your-workspace.cloud.databricks.com/oidc/oauth2/v2.0/authorize",
  "token_endpoint": "https://your-workspace.cloud.databricks.com/oidc/v1/token",
  "jwks_uri": "https://your-workspace.cloud.databricks.com/oidc/v1/keys"
}
```

### `/health`

Standard health check endpoint:

```json
{
  "status": "healthy",
  "agent": "customer_research",
  "version": "1.0.0"
}
```

## Discovery API

The `AgentDiscovery` class scans your workspace for agent-enabled apps:

```python
from dbx_agent_app.discovery import AgentDiscovery

# Initialize with optional profile
discovery = AgentDiscovery(profile="my-profile")

# Discover all agents
result = await discovery.discover_agents()

# Access discovered agents
for agent in result.agents:
    print(agent.name)           # Agent name from card
    print(agent.endpoint_url)   # Base URL of the app
    print(agent.app_name)       # Databricks App name
    print(agent.description)    # Agent description
    print(agent.capabilities)   # Comma-separated capabilities
    print(agent.protocol_version)  # A2A protocol version

# Check for errors
if result.errors:
    for error in result.errors:
        print(f"Error: {error}")
```

## A2A Client API

Communicate with other agents using the A2A protocol:

```python
from dbx_agent_app.discovery import A2AClient

async with A2AClient() as client:
    # Fetch an agent's card
    card = await client.fetch_agent_card("https://agent.databricksapps.com")
    
    # Send a message
    response = await client.send_message(
        "https://agent.databricksapps.com/api/a2a",
        "What are your capabilities?"
    )
    
    # Send a streaming message
    async for event in client.send_streaming_message(url, "Analyze this data"):
        print(event)
```

## Tool Registration

When building agents with `@app_agent`, you can define tools directly within your agent or use helper functions. Tools are automatically exposed through A2A protocol endpoints.

For agents using plain FastAPI with the `add_agent_card()` helper, tools can be registered using the same pattern and will be included in the agent card.

Example:

```python
from dbx_agent_app import app_agent, AgentRequest, AgentResponse

@app_agent(
    name="customer_research",
    description="Research customers",
    capabilities=["search"],
)
async def customer_research(request: AgentRequest) -> AgentResponse:
    # Process customer queries with your custom logic
    return AgentResponse.text(f"Result: {request.last_user_message}")

app = customer_research.app  # FastAPI app with agent endpoints
```

## Unity Catalog Integration

The framework integrates with Unity Catalog for agent registration and discovery:

- Agents are discoverable via workspace scanning
- UC integration tracks agent metadata and lineage
- Manage agent permissions through UC grants

Agents using `@app_agent` are automatically discovered when deployed to Databricks Apps. The discovery service scans for agent cards at `/.well-known/agent.json` across all running apps.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Databricks Workspace                     │
│                                                              │
│  ┌────────────────┐         ┌────────────────┐             │
│  │  Agent App 1   │         │  Agent App 2   │             │
│  │ (Customer      │         │ (Market        │             │
│  │  Research)     │         │  Analysis)     │             │
│  │                │         │                │             │
│  │ @app_agent     │         │ @app_agent     │             │
│  │ + agent card   │         │ + agent card   │             │
│  │ + /invocations │         │ + /invocations │             │
│  └────────────────┘         └────────────────┘             │
│         ▲                           ▲                        │
│         │                           │                        │
│         └───────────┬───────────────┘                        │
│                     │                                        │
│              ┌──────▼──────┐                                │
│              │  Discovery   │                                │
│              │  Service     │                                │
│              │              │                                │
│              │ Workspace    │                                │
│              │ Scanning     │                                │
│              └──────────────┘                                │
└─────────────────────────────────────────────────────────────┘
```

## Examples

See the `examples/` directory for complete working examples:

- `customer_research_agent.py` - Full agent with multiple tools
- `discover_agents.py` - Workspace agent discovery
- `communicate_with_agent.py` - A2A protocol communication

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/

# Lint
ruff check src/
```

## Roadmap

- [x] Unity Catalog integration for agent registration
- [x] MCP (Model Context Protocol) server support
- [ ] Built-in RAG and vector search utilities
- [ ] Observability and logging integrations

## Contributing

Contributions welcome! This is a Databricks Labs project. See `CONTRIBUTING.md` for guidelines.

## License

Apache 2.0

## Related Projects

- [A2A Protocol](https://a2a.so/) - Agent-to-Agent communication standard
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol
- [Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/) - Deploy apps on Databricks
- [Databricks SDK](https://github.com/databricks/databricks-sdk-py) - Python SDK for Databricks
