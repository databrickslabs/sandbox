"""Minimal agent example -- one tool, no external dependencies."""
from databricks_agents import AgentApp

app = AgentApp(
    name="hello",
    description="A minimal greeting agent",
    capabilities=["greetings"],
    auto_register=False,
    enable_mcp=False,
)


@app.tool(description="Say hello")
async def greet(name: str) -> dict:
    return {"message": f"Hello, {name}!"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
