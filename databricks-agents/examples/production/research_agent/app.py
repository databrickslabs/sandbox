"""
FastAPI wrapper for SGP Research Agent with MLflow Tracking

MIGRATED TO databricks-agents FRAMEWORK

This version uses the databricks-agents framework to auto-generate:
- /.well-known/agent.json (A2A protocol agent card)
- /.well-known/openid-configuration (OIDC delegation)
- /health (health check endpoint)
- /api/mcp (MCP server for tools)
- Unity Catalog registration on deployment

Authentication is handled via Kasal pattern in agent_uc_native_with_tracking.py
"""

import os
import mlflow
from typing import List, Optional
from pydantic import BaseModel

# Framework import - replaces ~100 lines of FastAPI boilerplate!
from databricks_agents import AgentApp

# Import the tracking-enabled agent (unchanged)
from agent import SGPResearchAgentWithTracking


# Create agent with framework - ONE DECLARATION!
app = AgentApp(
    name="sgp_research",
    description=" SGP Research Agent with MLflow performance tracking",
    capabilities=["research", "sgp_search", "expert_analysis", "tracking"],
    uc_catalog=os.environ.get("UC_CATALOG", "main"),
    uc_schema=os.environ.get("UC_SCHEMA", "agents"),
    auto_register=True,  # Auto-register in Unity Catalog on deploy
    enable_mcp=True,     # Enable MCP server at /api/mcp
    version="1.0.0",
)

# CORS is already enabled by default in FastAPI/AgentApp
# No need for manual CORS middleware setup!

# Initialize agent (singleton pattern preserved)
_agent = None


def get_agent() -> SGPResearchAgentWithTracking:
    """Get or create agent instance."""
    global _agent
    if _agent is None:
        # Configuration from environment (unchanged logic)
        config = {
            "catalog": app.uc_catalog,
            "schema": app.uc_schema,
            "endpoint": os.environ.get("MODEL_ENDPOINT", "databricks-claude-sonnet-4-5"),
            "temperature": float(os.environ.get("TEMPERATURE", "0.7")),
            "max_tokens": int(os.environ.get("MAX_TOKENS", "4096")),
        }

        # Optional warehouse ID
        if "WAREHOUSE_ID" in os.environ:
            config["warehouse_id"] = os.environ["WAREHOUSE_ID"]

        # Set MLflow experiment
        experiment_name = os.environ.get(
            "MLFLOW_EXPERIMENT_NAME",
            "/Users/databricks/agents-agent-tracking"
        )
        try:
            mlflow.set_experiment(experiment_name)
        except:
            pass  # May not have permissions in Apps environment

        _agent = SGPResearchAgentWithTracking(config)

    return _agent


# Request/Response models (unchanged)
class Message(BaseModel):
    role: str
    content: str


class QueryRequest(BaseModel):
    messages: List[Message]
    stream: Optional[bool] = False


class QueryResponse(BaseModel):
    response: str
    metrics: dict


# Tools - Framework registers these as both tools AND endpoints!
# Each @app.tool() creates:
#   - /api/tools/<tool_name> endpoint
#   - Tool entry in /.well-known/agent.json
#   - Tool in /api/mcp server

@app.tool(description="Query the SGP research agent with conversation history")
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
        agent = get_agent()

        # Convert messages to agent format
        from mlflow.types.responses import ResponsesAgentRequest, ResponsesAgentInputItem

        input_items = [
            ResponsesAgentInputItem(role=msg["role"], content=msg["content"])
            for msg in messages
        ]

        agent_request = ResponsesAgentRequest(input=input_items)

        # Execute query with tracking
        response = agent.predict(agent_request)

        # Extract response text
        response_text = response.output[0].text if response.output else ""

        # Get performance metrics
        metrics = agent.metrics.get_summary()

        return {
            "response": response_text,
            "metrics": metrics
        }

    except Exception as e:
        raise Exception(f"Query failed: {str(e)}")


@app.tool(description="Get agent performance metrics")
async def get_metrics() -> dict:
    """Get agent performance metrics."""
    try:
        agent = get_agent()
        if agent.metrics:
            return agent.metrics.get_summary()
        else:
            return {"message": "No metrics available yet"}
    except Exception as e:
        raise Exception(f"Failed to get metrics: {str(e)}")


@app.tool(description="Get agent configuration details")
async def get_config() -> dict:
    """Get agent configuration."""
    try:
        agent = get_agent()
        return {
            "catalog": agent.catalog,
            "schema": agent.schema,
            "model_endpoint": agent.config.get("endpoint"),
            "temperature": agent.config.get("temperature"),
            "max_tokens": agent.config.get("max_tokens"),
            "warehouse_id": agent._warehouse_id_cache if hasattr(agent, '_warehouse_id_cache') else None
        }
    except Exception as e:
        raise Exception(f"Failed to get config: {str(e)}")


# Additional custom endpoints (if needed beyond tools)
# The framework's health endpoint is at /health
# You can add more custom endpoints using standard FastAPI decorators:

@app.get("/")
async def root():
    """Root endpoint - compatibility with existing clients."""
    return {
        "status": "healthy",
        "service": "sgp-research-agent",
        "version": "1.0.0",
        "tracking_enabled": True,
        "framework": "databricks-agents",
        "endpoints": {
            "agent_card": "/.well-known/agent.json",
            "oidc_config": "/.well-known/openid-configuration",
            "health": "/health",
            "mcp_server": "/api/mcp",
            "tools": {
                "query": "/api/tools/query",
                "get_metrics": "/api/tools/get_metrics",
                "get_config": "/api/tools/get_config"
            }
        }
    }


# Legacy endpoint compatibility - maps old /query to new /api/tools/query
# This preserves backward compatibility with existing clients
@app.post("/query", response_model=QueryResponse)
async def query_legacy(request: QueryRequest):
    """
    Legacy query endpoint for backward compatibility.

    New clients should use: POST /api/tools/query
    """
    messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
    result = await query(messages)
    return QueryResponse(response=result["response"], metrics=result["metrics"])


# Legacy metrics endpoint - maps to tool
@app.get("/metrics")
async def metrics_legacy():
    """Legacy metrics endpoint. New clients should use: POST /api/tools/get_metrics"""
    return await get_metrics()


# Legacy config endpoint - maps to tool
@app.get("/config")
async def config_legacy():
    """Legacy config endpoint. New clients should use: POST /api/tools/get_config"""
    return await get_config()


# For local testing
if __name__ == "__main__":
    import uvicorn

    # Set defaults for local testing
    os.environ.setdefault("UC_CATALOG", "main")
    os.environ.setdefault("UC_SCHEMA", "agents")
    os.environ.setdefault("MODEL_ENDPOINT", "databricks-claude-sonnet-4-5")

    print("🚀 Starting  SGP Research Agent (databricks-agents framework)")
    print("\n📍 Endpoints:")
    print("   http://localhost:8000                           - Root")
    print("   http://localhost:8000/docs                      - Interactive API docs")
    print("   http://localhost:8000/.well-known/agent.json    - Agent card (A2A)")
    print("   http://localhost:8000/health                    - Health check")
    print("   http://localhost:8000/api/mcp                   - MCP server")
    print("   http://localhost:8000/api/tools/query           - Query tool")
    print("\n🔄 Legacy endpoints (backward compatible):")
    print("   http://localhost:8000/query                     - Old query endpoint")
    print("   http://localhost:8000/metrics                   - Old metrics endpoint")
    print("   http://localhost:8000/config                    - Old config endpoint")
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)
