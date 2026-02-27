# Quick Start

Get up and running with databricks-agents in 5 minutes.

## Installation

Install via pip:

```bash
pip install databricks-agents
```

For development:

```bash
pip install databricks-agents[dev]
```

## Create Your First Agent

Create a file called `app.py`:

```python
from databricks_agents import AgentApp

# Create the agent
app = AgentApp(
    name="hello_agent",
    description="A simple greeting agent",
    capabilities=["greetings"],
)

# Add a tool
@app.tool(description="Generate a personalized greeting")
async def greet(name: str, language: str = "english") -> dict:
    greetings = {
        "english": f"Hello, {name}!",
        "spanish": f"¡Hola, {name}!",
        "french": f"Bonjour, {name}!",
    }
    return {
        "greeting": greetings.get(language, greetings["english"]),
        "language": language,
    }

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
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
    "mcp": "/api/mcp",
    "invoke": "/api/invoke"
  },
  "tools": [
    {
      "name": "greet",
      "description": "Generate a personalized greeting",
      "parameters": {
        "name": {"type": "str", "required": true},
        "language": {"type": "str", "required": false}
      }
    }
  ]
}
```

Test a tool endpoint:

```bash
curl -X POST http://localhost:8000/api/tools/greet \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "language": "spanish"}'
```

Expected response:

```json
{
  "greeting": "¡Hola, Alice!",
  "language": "spanish"
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
✅ Registered in Unity Catalog (main.agents.hello_agent)  
✅ Available to other agents

## Discover Your Agent

Create `discover.py`:

```python
import asyncio
from databricks_agents.discovery import AgentDiscovery

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
