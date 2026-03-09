"""Minimal deployable agent -- one tool, MCP enabled, zero external deps."""
from databricks_agents import app_agent, AgentRequest, AgentResponse


@app_agent(
    name="hello",
    description="A minimal greeting agent",
    capabilities=["greetings"],
    auto_register=False,
    enable_mcp=True,
)
async def hello(request: AgentRequest) -> str:
    return f"Hello, {request.last_user_message}!"


@hello.tool(description="Say hello to someone by name")
async def greet(name: str) -> dict:
    return {"message": f"Hello, {name}!"}


app = hello.app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
