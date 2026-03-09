"""
Supervisor Agent — @app_agent pattern

Routes queries to specialized sub-agents (research, expert_finder,
analytics, compliance) via their /invocations endpoints.

Single-layer API: the decorated function IS the /invocations handler.
"""

import os

from databricks_agents import app_agent, AgentRequest, AgentResponse
from agent import SupervisorAgent


# Initialize agent (singleton)
_agent = None


def get_agent() -> SupervisorAgent:
    """Get or create supervisor agent instance."""
    global _agent
    if _agent is None:
        config = {
            "endpoint": os.environ.get("MODEL_ENDPOINT", "databricks-claude-sonnet-4-5"),
            "catalog": os.environ.get("UC_CATALOG", "serverless_dxukih_catalog"),
            "schema": os.environ.get("UC_SCHEMA", "agents"),
        }
        _agent = SupervisorAgent(config)
    return _agent


@app_agent(
    name="supervisor",
    description="Multi-agent supervisor that routes queries to specialized sub-agents",
    capabilities=["orchestration", "routing", "research", "expert_finder", "analytics", "compliance"],
    uc_catalog=os.environ.get("UC_CATALOG", "main"),
    uc_schema=os.environ.get("UC_SCHEMA", "agents"),
)
async def supervisor(request: AgentRequest) -> AgentResponse:
    """Route query to the appropriate sub-agent."""
    agent = get_agent()
    response = agent.predict(request)

    # Attach routing metadata for observability
    result = {"response": response.output[0].content[0].text if response.output else ""}
    if agent._last_routing:
        result["_routing"] = agent._last_routing

    return AgentResponse.from_dict(result)


@supervisor.tool(description="Get supervisor configuration and sub-agent status")
async def get_config() -> dict:
    """Get supervisor configuration and available sub-agents."""
    agent = get_agent()
    sub_agents = []
    for name, cfg in agent.SUBAGENT_CONFIG.items():
        url = os.environ.get(cfg["url_env"], "not configured")
        sub_agents.append({
            "name": name,
            "url": url,
            "description": {
                "research": "Expert transcript research",
                "expert_finder": "Find experts by topic",
                "analytics": "Business metrics and SQL queries",
                "compliance": "Conflict of interest checks",
            }.get(name, name),
        })
    return {
        "model_endpoint": agent.config.get("endpoint"),
        "sub_agents": sub_agents,
        "tools_count": len(agent.tools),
        "architecture": "invocations_routing",
    }


# The FastAPI app — uvicorn app:supervisor.app
app = supervisor.app


if __name__ == "__main__":
    import uvicorn

    os.environ.setdefault("UC_CATALOG", "main")
    os.environ.setdefault("UC_SCHEMA", "agents")
    os.environ.setdefault("MODEL_ENDPOINT", "databricks-claude-sonnet-4-5")

    print("Starting Supervisor Agent (@app_agent)")
    print("\nEndpoints:")
    print("   http://localhost:8000/invocations               - Responses Agent protocol")
    print("   http://localhost:8000/.well-known/agent.json    - Agent card (A2A)")
    print("   http://localhost:8000/health                    - Health check")
    print("   http://localhost:8000/api/mcp                   - MCP server")
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)
