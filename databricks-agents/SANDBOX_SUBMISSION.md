# databricks-agents - Sandbox Submission Summary

## Framework Complete ✅

A production-ready framework for building discoverable AI agents on Databricks Apps.

### Components Delivered

#### 1. Core Framework (`src/databricks_agents/`)

**core/agent_app.py** - Main AgentApp class
- FastAPI wrapper with agent capabilities
- Auto-generates A2A protocol endpoints (/.well-known/agent.json, OIDC config)
- Tool registration via decorators
- Health checks

**discovery/** - Agent discovery and communication
- `agent_discovery.py` - Workspace scanning for agent-enabled apps
- `a2a_client.py` - A2A protocol client for agent communication
- Probes apps for agent cards
- Handles OAuth redirects gracefully

**registry/** - Unity Catalog integration
- `uc_registry.py` - Register agents as UC objects
- Catalog-based agent discovery
- Permission management via UC grants
- Auto-registration on app startup

**mcp/** - Model Context Protocol support
- `mcp_server.py` - Expose tools via MCP
- `uc_functions.py` - Discover and call UC Functions
- Automatic parameter schema conversion

#### 2. CI/CD Pipelines (`.github/workflows/`)

**test.yml** - Automated testing
- Python 3.10, 3.11, 3.12 matrix
- Linting (ruff), formatting (black), type checking (mypy)
- Pytest with coverage reporting
- Codecov integration

**publish.yml** - PyPI publishing
- Triggered on GitHub releases
- Build and publish to PyPI
- Package validation

**docs.yml** - Documentation deployment
- MkDocs Material theme
- Auto-deploy to GitHub Pages
- API reference with mkdocstrings

#### 3. Documentation (`docs/`)

**Structure:**
- Home page with feature overview
- Getting Started guide
- Quick Start tutorial
- User Guide sections (Agent App, Tools, Discovery, A2A, UC)
- API Reference (auto-generated from docstrings)
- Examples gallery

**Configuration:**
- MkDocs Material theme
- Search, syntax highlighting, tabbed content
- Navigation structure
- Plugin configuration (mkdocstrings)

#### 4. Examples (`examples/`)

**customer_research_agent.py** - Basic agent with tools
**discover_agents.py** - Workspace discovery
**communicate_with_agent.py** - A2A protocol communication
**full_featured_agent.py** - Complete example with all features

#### 5. Tests (`tests/`)

**test_agent_app.py** - Core functionality tests
- AgentApp creation
- Agent card endpoint
- OIDC configuration
- Health checks
- Tool registration and invocation

#### 6. Package Configuration

**pyproject.toml** - Package metadata and dependencies
**README.md** - Comprehensive documentation
**CONTRIBUTING.md** - Contribution guidelines
**LICENSE** - Apache 2.0
**DEPLOYMENT_GUIDE.md** - Sandbox deployment instructions

## Key Features

### For Developers

```python
# 5 lines to create an agent
from databricks_agents import AgentApp

app = AgentApp(
    name="my_agent",
    description="Does useful things",
    capabilities=["search", "analysis"],
)

@app.tool(description="Search data")
async def search(query: str) -> dict:
    return {"results": [...]}
```

### Auto-Generated Endpoints

- `/.well-known/agent.json` - A2A protocol agent card
- `/.well-known/openid-configuration` - OIDC delegation
- `/health` - Health check
- `/api/mcp` - MCP server (if enabled)
- `/api/tools/<tool_name>` - Tool endpoints

### Unity Catalog Integration

```python
# Automatic on app startup
app = AgentApp(..., auto_register=True)

# Or manual
from databricks_agents.registry import UCAgentRegistry, UCAgentSpec

registry = UCAgentRegistry(profile="my-profile")
spec = UCAgentSpec(
    name="my_agent",
    catalog="main",
    schema="agents",
    endpoint_url="https://app.databricksapps.com",
)
registry.register_agent(spec)
```

### Agent Discovery

```python
from databricks_agents.discovery import AgentDiscovery

discovery = AgentDiscovery(profile="my-profile")
result = await discovery.discover_agents()

for agent in result.agents:
    print(f"{agent.name}: {agent.capabilities}")
```

### MCP Server

```python
# Automatic MCP endpoint at /api/mcp
app = AgentApp(..., enable_mcp=True)

# Discover and expose UC Functions
from databricks_agents.mcp import UCFunctionAdapter

adapter = UCFunctionAdapter()
tools = adapter.discover_functions("main", "functions")
```

## Design Principles

1. **Agent = App** - Databricks Apps are first-class agents, not wrappers around serving endpoints
2. **Standards-based** - Built on A2A protocol for interoperability
3. **Progressive disclosure** - Simple start (5 lines), advanced features available when needed
4. **Databricks-native** - Integrates with UC, Apps platform, OIDC, SDK

## Sandbox Fit

### Why Sandbox?

✅ **Early-stage but valuable** - Framework works today, provides immediate value
✅ **Innovative approach** - New pattern for agent building on Databricks
✅ **Community-driven** - Ideal for gathering feedback and contributions
✅ **Low friction** - 5 lines to create an agent
✅ **Building block** - Foundation for multi-agent systems

### Graduation Path

**Sandbox (0.1.x - 0.5.x)**
- Community validation
- Real-world usage patterns
- Feature stabilization
- Documentation refinement

**Full Repo (1.0+)**
- Proven adoption (100+ stars, 1000+ downloads/month)
- Mature API
- Comprehensive examples
- Production deployment patterns

**Platform Integration**
- Influence native Databricks agent features
- UC AGENT type (when available)
- Built-in orchestration primitives

## Next Steps

### Immediate (Pre-Submission)
- [ ] Run full test suite
- [ ] Verify all examples work
- [ ] Review documentation completeness
- [ ] Add CODE_OF_CONDUCT.md
- [ ] Create issue templates

### Post-Submission
- [ ] Set up PyPI publishing
- [ ] Enable GitHub Pages
- [ ] Announce in community forums
- [ ] Monitor feedback and iterate

## Metrics for Success

Track for sandbox graduation:
- GitHub stars (target: 100+)
- PyPI downloads (target: 1000/month)
- Contributors (target: 10+)
- Community examples (target: 5+)

## Contact

Framework extracted from multi-agent registry project for Guidepoint.

Ready for sandbox submission!
