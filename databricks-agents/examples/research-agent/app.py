"""
Research Agent — @app_agent pattern

The decorated function IS the /invocations handler.

Endpoints (auto-generated):
- POST /invocations        — Databricks Responses Agent protocol
- GET  /.well-known/agent.json — A2A agent card
- GET  /health             — Health check
- POST /api/mcp            — MCP JSON-RPC server
- POST /api/tools/<name>   — Individual tool endpoints
"""

import os
import mlflow

from dbx_agent_app import app_agent, AgentRequest, AgentResponse
from agent import SGPResearchAgent


# Initialize agent (singleton)
_agent = None


def get_agent() -> SGPResearchAgent:
    """Get or create agent instance."""
    global _agent
    if _agent is None:
        config = {
            "catalog": os.environ.get("UC_CATALOG", "main"),
            "schema": os.environ.get("UC_SCHEMA", "agents"),
            "endpoint": os.environ.get("MODEL_ENDPOINT", "databricks-claude-sonnet-4-5"),
            "temperature": float(os.environ.get("TEMPERATURE", "0.7")),
            "max_tokens": int(os.environ.get("MAX_TOKENS", "4096")),
        }

        if "WAREHOUSE_ID" in os.environ:
            config["warehouse_id"] = os.environ["WAREHOUSE_ID"]

        experiment_name = os.environ.get(
            "MLFLOW_EXPERIMENT_NAME",
            "/Users/databricks/agents-agent-tracking"
        )
        try:
            mlflow.set_experiment(experiment_name)
        except Exception:
            pass

        _agent = SGPResearchAgent(config)

    return _agent


@app_agent(
    name="research",
    description="Research Agent with MLflow performance tracking",
    capabilities=["research", "search", "expert_analysis", "tracking"],
    uc_catalog=os.environ.get("UC_CATALOG", "main"),
    uc_schema=os.environ.get("UC_SCHEMA", "agents"),
)
async def research(request: AgentRequest) -> AgentResponse:
    """Route to the research agent's predict method."""
    agent = get_agent()
    return agent.predict(request)


@research.tool(description="Get agent performance metrics")
async def get_metrics() -> dict:
    """Get agent performance metrics."""
    agent = get_agent()
    if agent.metrics:
        return agent.metrics.get_summary()
    return {"message": "No metrics available yet"}


@research.tool(description="Get agent configuration details")
async def get_config() -> dict:
    """Get agent configuration."""
    agent = get_agent()
    return {
        "catalog": agent.catalog,
        "schema": agent.schema,
        "model_endpoint": agent.config.get("endpoint"),
        "temperature": agent.config.get("temperature"),
        "max_tokens": agent.config.get("max_tokens"),
    }


# The FastAPI app — uvicorn app:research.app
app = research.app


if __name__ == "__main__":
    import uvicorn

    os.environ.setdefault("UC_CATALOG", "main")
    os.environ.setdefault("UC_SCHEMA", "agents")
    os.environ.setdefault("MODEL_ENDPOINT", "databricks-claude-sonnet-4-5")

    print("Starting Research Agent (@app_agent)")
    print("\nEndpoints:")
    print("   http://localhost:8000/invocations               - Responses Agent protocol")
    print("   http://localhost:8000/.well-known/agent.json    - Agent card (A2A)")
    print("   http://localhost:8000/health                    - Health check")
    print("   http://localhost:8000/api/mcp                   - MCP server")
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)
