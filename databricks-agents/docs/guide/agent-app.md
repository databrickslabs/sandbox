# Agent App

`AgentApp` is the core class of the SDK. It extends `FastAPI` and adds A2A protocol endpoints, MCP server integration, and Unity Catalog registration. You use it exactly like a FastAPI application -- with the addition of automatic agent infrastructure.

```python
from databricks_agents import AgentApp
```

## Constructor

```python
app = AgentApp(
    name="my_agent",
    description="What this agent does",
    capabilities=["search", "analysis"],
    uc_catalog="main",
    uc_schema="agents",
    auto_register=True,
    enable_mcp=True,
    # ...any additional FastAPI kwargs
)
```

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | *required* | Agent name. Used in the agent card, UC registration, and MCP server info. |
| `description` | `str` | *required* | Human-readable description of the agent's purpose. |
| `capabilities` | `List[str]` | *required* | List of capability tags (e.g., `["search", "analysis"]`). Surfaced in the agent card for discovery. |
| `uc_catalog` | `Optional[str]` | `"main"` | Unity Catalog catalog name for registration. Falls back to the `UC_CATALOG` environment variable. |
| `uc_schema` | `Optional[str]` | `"agents"` | Unity Catalog schema name for registration. Falls back to the `UC_SCHEMA` environment variable. |
| `auto_register` | `bool` | `True` | Automatically register the agent in Unity Catalog on startup. |
| `enable_mcp` | `bool` | `True` | Mount the MCP JSON-RPC server at `/api/mcp`. |
| `**kwargs` | | | Any additional keyword arguments are forwarded to the `FastAPI` constructor (e.g., `docs_url`, `root_path`, `middleware`). |

## Auto-generated endpoints

When you instantiate `AgentApp`, the following endpoints are created automatically:

### `GET /.well-known/agent.json`

The A2A protocol agent card. Returns JSON describing the agent's name, description, capabilities, tools, and available endpoints.

### `GET /.well-known/openid-configuration`

OIDC delegation endpoint. Points authentication to the Databricks workspace identity provider using the `DATABRICKS_HOST` environment variable. This allows other agents and clients to obtain tokens for calling your agent.

### `GET /health`

Standard health check. Returns the agent name, version, and `"status": "healthy"`.

### `POST /api/tools/<tool_name>`

One endpoint per registered tool. Created automatically when you use the `@app.tool` decorator. Accepts JSON request body matching the tool's parameter schema.

### `POST /api/mcp` (when `enable_mcp=True`)

MCP JSON-RPC 2.0 endpoint. Supports `tools/list`, `tools/call`, and `server/info` methods.

### `GET /api/mcp/tools` (when `enable_mcp=True`)

Convenience endpoint that lists all tools in MCP format (equivalent to calling `tools/list` via JSON-RPC).

## The `@app.tool` decorator

Register functions as agent tools:

```python
@app.tool(description="Search for companies by industry")
async def search_companies(industry: str, limit: int = 10) -> dict:
    return {"results": [...]}
```

The decorator:

1. Inspects the function signature to build a parameter schema
2. Adds a `ToolDefinition` to the agent metadata (visible in the agent card)
3. Creates a `POST /api/tools/<function_name>` FastAPI endpoint
4. Registers the tool with the MCP server (if enabled)

See [Tool Registration](tools.md) for full details on parameter types and schema overrides.

## MCP server

When `enable_mcp=True` (the default), AgentApp creates an MCP server that exposes all registered tools via the Model Context Protocol. The MCP server is mounted at `/api/mcp` and speaks JSON-RPC 2.0.

Supported MCP methods:

| Method | Description |
|---|---|
| `tools/list` | List all available tools with their input schemas |
| `tools/call` | Execute a tool by name with arguments |
| `server/info` | Get server name, version, and protocol version |

### Disabling MCP

```python
app = AgentApp(
    name="my_agent",
    description="...",
    capabilities=["..."],
    enable_mcp=False,
)
```

Tools are still available via `/api/tools/<name>` endpoints; only the MCP JSON-RPC interface is skipped.

## Unity Catalog registration

When `auto_register=True` and the `DATABRICKS_APP_URL` environment variable is set (which Databricks Apps sets automatically), the agent registers itself in Unity Catalog on startup.

Registration creates a UC registered model tagged with `databricks_agent=true` and stores metadata:

- `endpoint_url` -- the agent's base URL
- `agent_card_url` -- full URL to `/.well-known/agent.json`
- `capabilities` -- comma-separated capability list

### How it works

1. On startup, `AgentApp` checks for `DATABRICKS_APP_URL`.
2. If present, it creates a `UCAgentRegistry` instance and calls `register_agent()`.
3. The registry creates (or updates) a registered model at `{uc_catalog}.{uc_schema}.{name}`.
4. Tags are set on the model to store agent metadata.

### Disabling UC registration

Set `auto_register=False`, or simply run locally without `DATABRICKS_APP_URL` set. Registration is silently skipped in both cases.

```python
app = AgentApp(
    name="my_agent",
    description="...",
    capabilities=["..."],
    auto_register=False,
)
```

## OIDC delegation

The `/.well-known/openid-configuration` endpoint delegates authentication to the Databricks workspace OIDC provider. This is how other agents authenticate when calling your agent.

The endpoint reads the `DATABRICKS_HOST` environment variable (set automatically in Databricks Apps) and returns standard OIDC discovery metadata pointing to the workspace identity provider:

```json
{
    "issuer": "https://<workspace>.databricks.com/oidc",
    "authorization_endpoint": "https://<workspace>.databricks.com/oidc/oauth2/v2.0/authorize",
    "token_endpoint": "https://<workspace>.databricks.com/oidc/v1/token",
    "jwks_uri": "https://<workspace>.databricks.com/oidc/v1/keys"
}
```

## Lifespan integration

`AgentApp` uses FastAPI's lifespan context manager internally for UC registration. If you need your own startup/shutdown logic, pass a `lifespan` kwarg and it will be composed with the SDK's lifespan:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def my_lifespan(app):
    # startup: initialize database pool, load model, etc.
    db = await create_pool()
    yield {"db": db}
    # shutdown: clean up
    await db.close()

app = AgentApp(
    name="my_agent",
    description="...",
    capabilities=["..."],
    lifespan=my_lifespan,
)
```

The SDK runs UC registration first, then enters your lifespan context. The state dictionary you yield from your lifespan is available in FastAPI's `request.state` as usual.

## Since it's FastAPI

`AgentApp` is a `FastAPI` subclass, so you have full access to everything FastAPI offers:

```python
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom routes
@app.get("/api/custom")
async def custom_endpoint(request: Request):
    return {"message": "This is a regular FastAPI route"}

# Mount sub-applications, add dependencies, etc.
```

## Environment variables

| Variable | Purpose | Set automatically in Databricks Apps? |
|---|---|---|
| `DATABRICKS_APP_URL` | Agent's public URL. Triggers UC registration. | Yes |
| `DATABRICKS_HOST` | Workspace URL. Used for OIDC delegation. | Yes |
| `UC_CATALOG` | Default catalog for UC registration. | No (use `app.yaml` env) |
| `UC_SCHEMA` | Default schema for UC registration. | No (use `app.yaml` env) |
