# Your First Agent

This guide walks through building an agent with two tools, testing it locally, and verifying every endpoint the SDK generates.

## Create the agent

Create a file called `app.py`:

```python
from databricks_agents import AgentApp

app = AgentApp(
    name="company_lookup",
    description="Look up company information and financial data",
    capabilities=["search", "financials"],
    auto_register=False,   # skip UC registration for local dev
    enable_mcp=True,       # expose tools via MCP (default)
)


@app.tool(description="Search for companies by name or industry")
async def search_companies(query: str, limit: int = 5) -> dict:
    """Return matching companies. In production this would hit a real database."""
    fake_results = [
        {"name": "Acme Corp", "industry": "Manufacturing", "ticker": "ACME"},
        {"name": "Globex Inc", "industry": "Technology", "ticker": "GLBX"},
        {"name": "Initech", "industry": "Technology", "ticker": "INTC"},
    ]
    filtered = [c for c in fake_results if query.lower() in c["name"].lower()
                or query.lower() in c["industry"].lower()]
    return {"query": query, "results": filtered[:limit]}


@app.tool(description="Get financial summary for a company by ticker symbol")
async def get_financials(ticker: str, year: int = 2025) -> dict:
    """Return financial summary. In production this would query a data warehouse."""
    return {
        "ticker": ticker,
        "year": year,
        "revenue": "$4.2B",
        "net_income": "$380M",
        "employees": 12400,
    }
```

### Key constructor parameters

| Parameter | Default | Purpose |
|---|---|---|
| `auto_register` | `True` | Register agent in Unity Catalog on startup. Set to `False` for local development since `DATABRICKS_APP_URL` won't be set. |
| `enable_mcp` | `True` | Mount the MCP JSON-RPC server at `/api/mcp`. Set to `False` if you don't need MCP. |
| `uc_catalog` | `"main"` (or `UC_CATALOG` env var) | Unity Catalog catalog for registration. |
| `uc_schema` | `"agents"` (or `UC_SCHEMA` env var) | Unity Catalog schema for registration. |

## Run locally

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

You should see output similar to:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     databricks_agents.core.agent_app: MCP server enabled at /api/mcp
```

## Test the agent card

Every `AgentApp` exposes its A2A agent card at `/.well-known/agent.json`:

```bash
curl -s http://localhost:8000/.well-known/agent.json | python -m json.tool
```

Expected response:

```json
{
    "schema_version": "a2a/1.0",
    "name": "company_lookup",
    "description": "Look up company information and financial data",
    "capabilities": ["search", "financials"],
    "version": "1.0.0",
    "endpoints": {
        "mcp": "/api/mcp",
        "invoke": "/api/invoke"
    },
    "tools": [
        {
            "name": "search_companies",
            "description": "Search for companies by name or industry",
            "parameters": {
                "query": {"type": "string", "required": true},
                "limit": {"type": "integer", "required": false}
            }
        },
        {
            "name": "get_financials",
            "description": "Get financial summary for a company by ticker symbol",
            "parameters": {
                "ticker": {"type": "string", "required": true},
                "year": {"type": "integer", "required": false}
            }
        }
    ]
}
```

## Test the health endpoint

```bash
curl -s http://localhost:8000/health | python -m json.tool
```

```json
{
    "status": "healthy",
    "agent": "company_lookup",
    "version": "1.0.0"
}
```

## Test tool endpoints

Each tool registered with `@app.tool` is automatically available as a POST endpoint under `/api/tools/<name>`.

### search_companies

```bash
curl -s -X POST http://localhost:8000/api/tools/search_companies \
  -H "Content-Type: application/json" \
  -d '{"query": "tech", "limit": 2}' | python -m json.tool
```

```json
{
    "query": "tech",
    "results": [
        {"name": "Globex Inc", "industry": "Technology", "ticker": "GLBX"},
        {"name": "Initech", "industry": "Technology", "ticker": "INTC"}
    ]
}
```

### get_financials

```bash
curl -s -X POST http://localhost:8000/api/tools/get_financials \
  -H "Content-Type: application/json" \
  -d '{"ticker": "ACME"}' | python -m json.tool
```

```json
{
    "ticker": "ACME",
    "year": 2025,
    "revenue": "$4.2B",
    "net_income": "$380M",
    "employees": 12400
}
```

## Test the MCP endpoint

The MCP server is available at `/api/mcp` and accepts JSON-RPC 2.0 requests.

### List tools via MCP

```bash
curl -s -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | python -m json.tool
```

### Call a tool via MCP

```bash
curl -s -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "search_companies",
      "arguments": {"query": "Acme"}
    }
  }' | python -m json.tool
```

Expected response:

```json
{
    "jsonrpc": "2.0",
    "id": 2,
    "result": {
        "result": {
            "query": "Acme",
            "results": [
                {"name": "Acme Corp", "industry": "Manufacturing", "ticker": "ACME"}
            ]
        }
    }
}
```

### Get MCP server info

```bash
curl -s -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 3, "method": "server/info"}' | python -m json.tool
```

## OIDC configuration endpoint

The SDK also generates a `/.well-known/openid-configuration` endpoint that delegates authentication to the Databricks workspace OIDC provider. This is used by other agents and clients for token-based auth when deployed:

```bash
curl -s http://localhost:8000/.well-known/openid-configuration | python -m json.tool
```

In local development (without `DATABRICKS_HOST` set), the OIDC URLs will be empty strings. When deployed to Databricks Apps, they will point to the workspace identity provider automatically.

## Disabling features for local dev

For local development you typically want to disable UC registration and may optionally disable MCP:

```python
app = AgentApp(
    name="my_agent",
    description="...",
    capabilities=["..."],
    auto_register=False,   # don't try to register in Unity Catalog
    enable_mcp=False,      # skip MCP server setup (tools still available via /api/tools/)
)
```

Even with `auto_register=True` (the default), registration is silently skipped when `DATABRICKS_APP_URL` is not set, so local development works without configuration changes.

## Next steps

- [Agent App reference](../guide/agent-app.md) -- full details on `AgentApp` constructor and behavior
- [Tool Registration](../guide/tools.md) -- parameter types, schema overrides, and testing
- [Quick Start: Deploy to Databricks](quickstart.md#deploy-to-databricks-apps) -- deploy what you built
