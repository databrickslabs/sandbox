"""
FastAPI wrapper for Research Agent with MLflow Tracking

Uses the databricks-agent-deploy framework with composition pattern:
- agent = AgentApp(...) registers tools and metadata
- app = agent.as_fastapi() builds the FastAPI app with all endpoints

Endpoints provided automatically:
- /invocations  (Databricks Responses Agent protocol)
- /.well-known/agent.json  (A2A protocol agent card)
- /.well-known/openid-configuration  (OIDC delegation)
- /health  (health check)
- /api/mcp  (MCP server for tools)
- /api/tools/<name>  (individual tool endpoints)
"""

import os
import mlflow
from typing import List, Optional
from pydantic import BaseModel

from databricks_agents import AgentApp
from agent import SGPResearchAgentWithTracking


# Create agent with framework
agent = AgentApp(
    name="research",
    description="Research Agent with MLflow performance tracking",
    capabilities=["research", "search", "expert_analysis", "tracking"],
    uc_catalog=os.environ.get("UC_CATALOG", "main"),
    uc_schema=os.environ.get("UC_SCHEMA", "agents"),
    auto_register=True,
    enable_mcp=True,
    version="1.0.0",
)

# Initialize agent (singleton pattern)
_agent = None


def get_agent() -> SGPResearchAgentWithTracking:
    """Get or create agent instance."""
    global _agent
    if _agent is None:
        config = {
            "catalog": agent.uc_catalog,
            "schema": agent.uc_schema,
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
        except:
            pass

        _agent = SGPResearchAgentWithTracking(config)

    return _agent


# Request/Response models
class Message(BaseModel):
    role: str
    content: str


class QueryRequest(BaseModel):
    messages: List[Message]
    stream: Optional[bool] = False


class QueryResponse(BaseModel):
    response: str
    metrics: dict


# Tools

@agent.tool(description="Query the research agent with conversation history")
async def query(messages: List[dict]) -> dict:
    """
    Query the agent with a user message.

    Returns the agent's response plus performance metrics.

    Args:
        messages: List of conversation messages with 'role' and 'content'

    Returns:
        Dictionary with 'response' and 'metrics' keys
    """
    try:
        research_agent = get_agent()

        from mlflow.types.responses import ResponsesAgentRequest, ResponsesAgentInputItem

        input_items = [
            ResponsesAgentInputItem(role=msg["role"], content=msg["content"])
            for msg in messages
        ]

        agent_request = ResponsesAgentRequest(input=input_items)
        response = research_agent.predict(agent_request)

        response_text = response.output[0].text if response.output else ""
        metrics = research_agent.metrics.get_summary()

        return {
            "response": response_text,
            "metrics": metrics
        }

    except Exception as e:
        raise Exception(f"Query failed: {str(e)}")


@agent.tool(description="Get agent performance metrics")
async def get_metrics() -> dict:
    """Get agent performance metrics."""
    try:
        research_agent = get_agent()
        if research_agent.metrics:
            return research_agent.metrics.get_summary()
        else:
            return {"message": "No metrics available yet"}
    except Exception as e:
        raise Exception(f"Failed to get metrics: {str(e)}")


@agent.tool(description="Get agent configuration details")
async def get_config() -> dict:
    """Get agent configuration."""
    try:
        research_agent = get_agent()
        return {
            "catalog": research_agent.catalog,
            "schema": research_agent.schema,
            "model_endpoint": research_agent.config.get("endpoint"),
            "temperature": research_agent.config.get("temperature"),
            "max_tokens": research_agent.config.get("max_tokens"),
            "warehouse_id": research_agent._warehouse_id_cache if hasattr(research_agent, '_warehouse_id_cache') else None
        }
    except Exception as e:
        raise Exception(f"Failed to get config: {str(e)}")


# Build the FastAPI app
app = agent.as_fastapi()


# Additional custom endpoints

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "status": "healthy",
        "service": "research-agent",
        "version": "1.0.0",
        "tracking_enabled": True,
        "framework": "databricks-agent-deploy",
        "endpoints": {
            "invocations": "/invocations",
            "agent_card": "/.well-known/agent.json",
            "health": "/health",
            "mcp_server": "/api/mcp",
            "tools": {
                "query": "/api/tools/query",
                "get_metrics": "/api/tools/get_metrics",
                "get_config": "/api/tools/get_config"
            }
        }
    }


# Legacy endpoints
@app.post("/query", response_model=QueryResponse)
async def query_legacy(request: QueryRequest):
    """Legacy query endpoint. New clients should use: POST /invocations"""
    messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
    result = await query(messages)
    return QueryResponse(response=result["response"], metrics=result["metrics"])


@app.get("/metrics")
async def metrics_legacy():
    """Legacy metrics endpoint. New clients should use: POST /api/tools/get_metrics"""
    return await get_metrics()


@app.get("/config")
async def config_legacy():
    """Legacy config endpoint. New clients should use: POST /api/tools/get_config"""
    return await get_config()


# For local testing
if __name__ == "__main__":
    import uvicorn

    os.environ.setdefault("UC_CATALOG", "main")
    os.environ.setdefault("UC_SCHEMA", "agents")
    os.environ.setdefault("MODEL_ENDPOINT", "databricks-claude-sonnet-4-5")

    print("Starting Research Agent (databricks-agent-deploy framework)")
    print("\nEndpoints:")
    print("   http://localhost:8000/invocations               - Responses Agent protocol")
    print("   http://localhost:8000/.well-known/agent.json    - Agent card (A2A)")
    print("   http://localhost:8000/health                    - Health check")
    print("   http://localhost:8000/api/mcp                   - MCP server")
    print("   http://localhost:8000/api/tools/query           - Query tool")
    print("\nLegacy endpoints:")
    print("   http://localhost:8000/query                     - Old query endpoint")
    print("   http://localhost:8000/metrics                   - Old metrics endpoint")
    print("   http://localhost:8000/config                    - Old config endpoint")
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)
