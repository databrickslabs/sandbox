# Tool Registration

Tools are the primary way to expose functionality from your agent. Register them with the `@app.tool` decorator and they become available through three interfaces simultaneously:

1. **REST endpoint** at `POST /api/tools/<name>`
2. **MCP JSON-RPC** at `POST /api/mcp` (via `tools/call`)
3. **Agent card** at `GET /.well-known/agent.json` (in the `tools` array)

## Basic usage

```python
from databricks_agents import AgentApp

app = AgentApp(
    name="my_agent",
    description="...",
    capabilities=["search"],
)

@app.tool(description="Search for items by keyword")
async def search(query: str, limit: int = 10) -> dict:
    return {"results": [], "total": 0}
```

The decorator inspects the function signature and builds a parameter schema automatically.

## Supported parameter types

The SDK maps Python type annotations to JSON Schema types for the agent card and MCP tool definitions:

| Python type | JSON Schema type | Notes |
|---|---|---|
| `str` | `"string"` | |
| `int` | `"integer"` | |
| `float` | `"number"` | |
| `bool` | `"boolean"` | |
| `list` / `List[str]` | `"array"` | Generic `list` and typed `List[X]` both map to `"array"` |
| `dict` / `Dict[str, Any]` | `"object"` | Generic `dict` and typed `Dict[K, V]` both map to `"object"` |
| `Optional[int]` | `"integer"` | The inner type is unwrapped; the parameter is marked `required: false` |
| `bytes` | `"string"` | |

Parameters with default values are marked `required: false`. Parameters without defaults are `required: true`.

### Example with various types

```python
from typing import List, Optional, Dict, Any

@app.tool(description="Complex search with filters")
async def advanced_search(
    query: str,                          # required, string
    tags: List[str] = [],                # optional, array
    max_results: int = 25,               # optional, integer
    include_metadata: bool = False,      # optional, boolean
    min_score: float = 0.5,              # optional, number
    filters: Optional[Dict[str, Any]] = None,  # optional, object
) -> dict:
    return {"results": []}
```

This produces the following parameter schema in the agent card:

```json
{
    "query": {"type": "string", "required": true},
    "tags": {"type": "array", "required": false},
    "max_results": {"type": "integer", "required": false},
    "include_metadata": {"type": "boolean", "required": false},
    "min_score": {"type": "number", "required": false},
    "filters": {"type": "object", "required": false}
}
```

## Explicit schema override

If auto-extraction doesn't capture what you need (e.g., you want descriptions, enums, or nested schemas), pass a `parameters` dictionary directly:

```python
@app.tool(
    description="Search companies with detailed schema",
    parameters={
        "query": {
            "type": "string",
            "required": True,
            "description": "Search term to match against company names",
        },
        "industry": {
            "type": "string",
            "required": False,
            "description": "Filter by industry sector",
            "enum": ["technology", "finance", "healthcare", "manufacturing"],
        },
        "limit": {
            "type": "integer",
            "required": False,
            "description": "Maximum number of results (1-100)",
        },
    },
)
async def search_companies(query: str, industry: str = "", limit: int = 10) -> dict:
    return {"results": []}
```

When `parameters` is provided, it is used as-is for the agent card and MCP schema. The auto-extraction logic is skipped entirely.

## Async and sync functions

Tools should be `async` functions. The SDK registers them as FastAPI POST endpoints, so async is recommended to avoid blocking the event loop:

```python
# Recommended: async
@app.tool(description="Fetch data")
async def fetch_data(id: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.example.com/{id}")
        return response.json()
```

Synchronous functions also work -- FastAPI will run them in a thread pool automatically:

```python
# Also works (runs in thread pool)
@app.tool(description="Compute something")
def compute(x: int, y: int) -> dict:
    return {"result": x + y}
```

## Testing tools via REST

Each tool gets a `POST /api/tools/<function_name>` endpoint. Pass arguments as a JSON body:

```bash
curl -s -X POST http://localhost:8000/api/tools/search \
  -H "Content-Type: application/json" \
  -d '{"query": "databricks", "limit": 5}'
```

The response is whatever the function returns -- typically a `dict` that FastAPI serializes to JSON.

## Testing tools via MCP

The MCP endpoint at `POST /api/mcp` supports the full tool lifecycle:

### List all tools

```bash
curl -s -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'
```

Response:

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "tools": [
            {
                "name": "search",
                "description": "Search for items by keyword",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": ""},
                        "limit": {"type": "integer", "description": ""}
                    },
                    "required": ["query"]
                }
            }
        ]
    }
}
```

### Call a tool

```bash
curl -s -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "search",
      "arguments": {"query": "databricks", "limit": 5}
    }
  }'
```

Response:

```json
{
    "jsonrpc": "2.0",
    "id": 2,
    "result": {
        "result": {
            "results": [],
            "total": 0
        }
    }
}
```

### Convenience listing

There's also a GET endpoint for quick inspection:

```bash
curl -s http://localhost:8000/api/mcp/tools
```

## How tool registration works internally

When `@app.tool` is applied:

1. **Signature inspection** -- `inspect.signature(func)` extracts parameter names, types, and defaults.
2. **Type mapping** -- Each Python type annotation is converted to a JSON Schema type string via `_python_type_to_json_schema()`.
3. **ToolDefinition creation** -- A `ToolDefinition` (Pydantic model) is created with the function name, description, parameter schema, and a reference to the original function.
4. **Metadata registration** -- The `ToolDefinition` is appended to `app.agent_metadata.tools`, making it visible in the agent card.
5. **FastAPI endpoint** -- `app.post(f"/api/tools/{name}")` is called to create the REST endpoint.
6. **MCP registration** -- When the MCP server handles `tools/list` or `tools/call`, it reads from `app.agent_metadata.tools` -- so any tool registered via `@app.tool` is automatically available via MCP.

## Multiple tools

Register as many tools as you need:

```python
@app.tool(description="Search the knowledge base")
async def search(query: str) -> dict:
    ...

@app.tool(description="Get details for a specific record")
async def get_details(record_id: str) -> dict:
    ...

@app.tool(description="Summarize a collection of records")
async def summarize(record_ids: List[str], format: str = "brief") -> dict:
    ...
```

All three tools appear in the agent card, have REST endpoints, and are callable via MCP.
