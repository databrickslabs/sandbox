# databricks-agents

**Status:** 🧪 Experimental (Sandbox Project)

Framework for building discoverable AI agents on Databricks Apps with auto-generated A2A protocol endpoints.

## Quick Start

### Installation

```bash
pip install databricks-agents
```

### Create an Agent (5 Lines!)

```python
from databricks_agents import AgentApp

app = AgentApp(
    name="my_agent",
    description="Does useful things",
    capabilities=["search", "analysis"],
)

@app.tool(description="Search data")
async def search(query: str) -> dict:
    return {"results": [...]}

# Deploy to Databricks Apps → Auto-registered in Unity Catalog!
```

## What It Does

- **Auto-generates A2A protocol endpoints** (`/.well-known/agent.json`, OIDC config)
- **Discovers agents** across your workspace via scanning and Unity Catalog
- **Registers in Unity Catalog** for centralized agent management
- **Exposes tools via MCP** (Model Context Protocol)
- **Enables agent-to-agent communication** using standard protocols

## Key Features

### Agent = Databricks App

Unlike traditional approaches, this framework treats **Databricks Apps as first-class agents**, enabling:
- Full application logic with custom UI
- Stateful operations and workflows
- Integration with Databricks data and AI

### 5 Lines to Production

```python
from databricks_agents import AgentApp

app = AgentApp(name="research", description="Research agent", capabilities=["search"])

@app.tool(description="Search companies")
async def search_companies(industry: str) -> dict:
    return {"results": [...]}
```

That's it! You get:
- ✅ Agent card at `/.well-known/agent.json`
- ✅ OIDC config at `/.well-known/openid-configuration`  
- ✅ Health check at `/health`
- ✅ MCP server at `/api/mcp`
- ✅ Unity Catalog registration (auto on deploy)

## Documentation

Full documentation: [databricks-agents docs](https://databrickslabs.github.io/sandbox/databricks-agents/)

## Examples

See the [`examples/`](./examples/) directory:
- `customer_research_agent.py` - Basic agent with custom tools
- `discover_agents.py` - Workspace agent discovery
- `communicate_with_agent.py` - A2A protocol communication
- `full_featured_agent.py` - Complete example with all features

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Databricks Workspace                     │
│                                                              │
│  ┌────────────────┐         ┌────────────────┐             │
│  │  Agent App 1   │         │  Agent App 2   │             │
│  │                │         │                │             │
│  │ AgentApp       │◄────────┤ AgentDiscovery │             │
│  │ + A2A protocol │         │ + A2AClient    │             │
│  │ + Tools        │         │                │             │
│  └────────────────┘         └────────────────┘             │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────────────────────┐               │
│  │        Unity Catalog (main.agents)      │               │
│  └─────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

## Components

- **AgentApp** - FastAPI wrapper that makes any app an agent
- **AgentDiscovery** - Discover agents across workspace
- **A2AClient** - Communicate with agents using A2A protocol  
- **UCAgentRegistry** - Register agents in Unity Catalog
- **MCPServer** - Expose tools via Model Context Protocol
- **UCFunctionAdapter** - Discover and call UC Functions

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup and contribution guidelines.

## License

Apache 2.0 - See [LICENSE](./LICENSE)

## Project Status

This is an experimental sandbox project. While functional and tested, it's designed for:
- Early adopters who want to build agent systems
- Community feedback and iteration
- Validation of the Agent = App pattern

Not yet recommended for production deployments without thorough testing.

## Support

- 📚 [Documentation](https://databrickslabs.github.io/sandbox/databricks-agents/)
- 🐛 [Issues](https://github.com/databrickslabs/sandbox/issues)
- 💬 [Discussions](https://github.com/databrickslabs/sandbox/discussions)
