# dbx-agent-app

A lightweight Python framework for building discoverable AI agents on Databricks Apps.

## What is dbx-agent-app?

`dbx-agent-app` makes it trivial to turn any Databricks App into a discoverable, standards-compliant agent that can:

- **Auto-generate A2A protocol endpoints** for agent discovery and communication
- **Register in Unity Catalog** for centralized agent management
- **Communicate with other agents** using standard protocols
- **Expose tools and capabilities** through a simple decorator pattern

## Key Features

:material-rocket-launch: **5 Lines to Create an Agent**
```python
from dbx_agent_app import app_agent, AgentRequest, AgentResponse

@app_agent(
    name="my_agent",
    description="Does useful things",
    capabilities=["search", "analysis"],
)
async def my_agent(request: AgentRequest) -> AgentResponse:
    return AgentResponse.text(f"You said: {request.last_user_message}")
```

:material-magnify: **Automatic Discovery**  
Agents are automatically discoverable via workspace scanning and Unity Catalog

:material-connection: **Standards-Based**  
Built on A2A protocol for interoperability with any A2A-compatible system

:material-database: **Unity Catalog Integration**  
Register agents as UC objects with built-in permission management

## Quick Example

```python
from dbx_agent_app import app_agent, AgentRequest, AgentResponse

# Create your agent
@app_agent(
    name="customer_research",
    description="Research customer information",
    capabilities=["search", "analysis"],
)
async def customer_research(request: AgentRequest) -> AgentResponse:
    return AgentResponse.text(f"Researching: {request.last_user_message}")

# Deploy to Databricks Apps - agent card auto-generated!
app = customer_research.app
```

## Why dbx-agent-app?

### Before

- Manual A2A protocol implementation
- No standard way to make apps discoverable
- Complex agent-to-agent communication
- Agents tied to Model Serving endpoints

### After

- One decorator: `@app_agent` makes any function an agent
- Auto-generated discovery endpoints
- Built-in workspace discovery
- Agents can be full applications

## Agent = Databricks App

Unlike traditional approaches, this framework treats **Databricks Apps as first-class agents**, enabling:

- Full application logic with custom UI
- Stateful operations and workflows
- Integration with Databricks data and AI
- Standard discovery and communication

## Get Started

Choose your path:

<div class="grid cards" markdown>

-   :material-clock-fast:{ .lg .middle } __Quick Start__

    ---

    Install and create your first agent in 5 minutes

    [:octicons-arrow-right-24: Quick Start](getting-started/quickstart.md)

-   :material-book-open-variant:{ .lg .middle } __User Guide__

    ---

    Deep dive into features and capabilities

    [:octicons-arrow-right-24: User Guide](guide/agent-app.md)

-   :material-code-braces:{ .lg .middle } __Examples__

    ---

    Learn from complete working examples

    [:octicons-arrow-right-24: Examples](examples/customer-research.md)

-   :material-api:{ .lg .middle } __API Reference__

    ---

    Complete API documentation

    [:octicons-arrow-right-24: API Docs](api/discovery.md)

</div>

## What Gets Auto-Generated

When you create an agent with `@app_agent`, the framework automatically provides:

### `/.well-known/agent.json` (Agent Card)
Your agent's capabilities, tools, and metadata in standard A2A format

### `/.well-known/openid-configuration`
Authentication delegation to Databricks workspace OIDC

### `/health`
Standard health check endpoint

### `/api/tools/<tool_name>`
FastAPI endpoints for each registered tool

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Databricks Workspace                     │
│                                                              │
│  ┌────────────────┐         ┌────────────────┐             │
│  │  Agent App 1   │         │  Agent App 2   │             │
│  │                │         │                │             │
│  │ @app_agent     │◄────────┤ Discovery      │             │
│  │ + agent card   │         │ Service        │             │
│  │ + /invocations │         │                │             │
│  └────────────────┘         └────────────────┘             │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────────────────────┐               │
│  │        Workspace Agent Registry         │               │
│  │  - customer_research                    │               │
│  │  - market_analysis                      │               │
│  │  - data_processor                       │               │
│  └─────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

## Community

- :material-github: [GitHub Repository](https://github.com/databricks-labs/dbx-agent-app)
- :material-bug: [Issue Tracker](https://github.com/databricks-labs/dbx-agent-app/issues)
- :material-chat: [Discussions](https://github.com/databricks-labs/dbx-agent-app/discussions)

## License

Apache 2.0 - See [LICENSE](https://github.com/databricks-labs/dbx-agent-app/blob/main/LICENSE) for details
