# Your First Agent

This guide walks through building an agent with two tools, testing it locally, and verifying every endpoint the SDK generates.

## Create the agent

Create a file called `app.py`:

```python
from dbx_agent_app import app_agent, AgentRequest, AgentResponse

@app_agent(
    name="company_lookup",
    description="Look up company information and financial data",
    capabilities=["search", "financials"],
)
async def company_lookup(request: AgentRequest) -> AgentResponse:
    """
    Handle company lookup requests.
    In production this would call a real database or API.
    """
    user_message = request.last_user_message

    # Simple response for demonstration
    response = f"Looking up information for: {user_message}"

    return AgentResponse.text(response)
```

### Key decorator parameters

| Parameter | Purpose |
|---|---|
| `name` | Agent name (used in agent card and discovery) |
| `description` | Human-readable agent description |
| `capabilities` | List of capability tags (e.g., `["search", "analysis"]`) |

## Run locally

```bash
uvicorn app:company_lookup.app --host 0.0.0.0 --port 8000 --reload
```

You should see output similar to:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Test the agent card

Every agent created with `@app_agent` exposes its agent card at `/.well-known/agent.json`:

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
        "invoke": "/invocations"
    }
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

## Test the invocations endpoint

The `/invocations` endpoint is the standard Databricks protocol endpoint for agent communication:

```bash
curl -s -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "input": [
      {"role": "user", "content": "Look up company ACME"}
    ]
  }' | python -m json.tool
```

Expected response:

```json
{
    "output": "Looking up information for: Look up company ACME"
}
```

## OIDC configuration endpoint

The SDK also generates a `/.well-known/openid-configuration` endpoint that delegates authentication to the Databricks workspace OIDC provider. This is used by other agents and clients for token-based auth when deployed:

```bash
curl -s http://localhost:8000/.well-known/openid-configuration | python -m json.tool
```

In local development (without `DATABRICKS_HOST` set), the OIDC URLs will be empty strings. When deployed to Databricks Apps, they will point to the workspace identity provider automatically.

## Next steps

- [@app_agent decorator](../guide/agent-app.md) -- full details on decorator usage
- [Agent Discovery](../guide/discovery.md) -- find agents in your workspace
- [Quick Start: Deploy to Databricks](quickstart.md#deploy-to-databricks-apps) -- deploy what you built
