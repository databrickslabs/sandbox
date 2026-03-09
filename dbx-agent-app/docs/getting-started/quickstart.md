# Quick Start

Get up and running with dbx-agent-app in 5 minutes.

## Installation

Install via pip:

```bash
pip install dbx-agent-app
```

For development:

```bash
pip install dbx-agent-app[dev]
```

## Create Your First Agent

Create a file called `app.py`:

```python
from dbx_agent_app import app_agent, AgentRequest, AgentResponse

# Create the agent
@app_agent(
    name="hello_agent",
    description="A simple greeting agent",
    capabilities=["greetings"],
)
async def hello_agent(request: AgentRequest) -> AgentResponse:
    user_message = request.last_user_message
    return AgentResponse.text(f"Hello! You said: {user_message}")

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(hello_agent.app, host="0.0.0.0", port=8000)
```

## Test Locally

Run your agent:

```bash
python app.py
```

Test the agent card endpoint:

```bash
curl http://localhost:8000/.well-known/agent.json
```

Expected response:

```json
{
  "schema_version": "a2a/1.0",
  "name": "hello_agent",
  "description": "A simple greeting agent",
  "capabilities": ["greetings"],
  "version": "1.0.0",
  "endpoints": {
    "invoke": "/invocations"
  }
}
```

Test the invocations endpoint:

```bash
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "Hi Alice"}]}'
```

Expected response:

```json
{
  "output": "Hello! You said: Hi Alice"
}
```

## Deploy to Databricks Apps

Create `app.yaml`:

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
  - name: UC_CATALOG
    value: "main"
  - name: UC_SCHEMA
    value: "agents"
```

Deploy:

```bash
# Create the app
databricks apps create hello-agent \
  --description "Simple greeting agent"

# Deploy the code
databricks apps deploy hello-agent \
  --source-code-path ./
```

Your agent is now:

✅ Running on Databricks Apps
✅ Discoverable via agent card
✅ Available to other agents

## Discover Your Agent

Create `discover.py`:

```python
import asyncio
from dbx_agent_app.discovery import AgentDiscovery

async def main():
    discovery = AgentDiscovery(profile="DEFAULT")
    result = await discovery.discover_agents()
    
    for agent in result.agents:
        print(f"Found: {agent.name} - {agent.description}")

asyncio.run(main())
```

Run it:

```bash
python discover.py
```

Output:

```
Found: hello_agent - A simple greeting agent
```

## Next Steps

- [Create a more complex agent](first-agent.md)
- [Learn about tool registration](../guide/tools.md)
- [Explore agent discovery](../guide/discovery.md)
- [Set up Unity Catalog integration](../guide/unity-catalog.md)
