"""
FastAPI wrapper for Supervisor Agent

MIGRATED TO databricks-agents FRAMEWORK

This version uses the databricks-agents framework to auto-generate:
- /.well-known/agent.json (A2A protocol agent card)
- /.well-known/openid-configuration (OIDC delegation)
- /health (health check endpoint)
- /api/mcp (MCP server for tools)
- Unity Catalog registration on deployment

The supervisor routes queries to specialized sub-agents:
- sgp_research: Expert transcript research
- expert_finder: Find experts by topic
- analytics: Business metrics and SQL queries
- compliance_check: Conflict of interest checks
"""

import os
from typing import List, Optional
from pydantic import BaseModel

# Framework import - replaces ~100 lines of FastAPI boilerplate!
from databricks_agents import AgentApp

# Import the supervisor agent
from agent import SupervisorAgent


# Create agent with framework - ONE DECLARATION!
app = AgentApp(
    name="supervisor",
    description="Multi-agent supervisor that routes queries to specialized sub-agents",
    capabilities=[
        "orchestration",
        "routing",
        "sgp_research",
        "expert_finder",
        "analytics",
        "compliance"
    ],
    uc_catalog=os.environ.get("UC_CATALOG", "main"),
    uc_schema=os.environ.get("UC_SCHEMA", "agents"),
    auto_register=True,  # Auto-register in Unity Catalog on deploy
    enable_mcp=True,     # Enable MCP server at /api/mcp
    version="1.0.0",
)

# CORS is already enabled by default in FastAPI/AgentApp
# No need for manual CORS middleware setup!

# Initialize agent (singleton pattern)
_agent = None


def get_agent() -> SupervisorAgent:
    """Get or create supervisor agent instance."""
    global _agent
    if _agent is None:
        # Configuration from environment
        config = {
            "endpoint": os.environ.get("MODEL_ENDPOINT", "databricks-claude-sonnet-4-5"),
        }
        _agent = SupervisorAgent(config)
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


# Tools - Framework registers these as both tools AND endpoints!
# Each @app.tool() creates:
#   - /api/tools/<tool_name> endpoint
#   - Tool entry in /.well-known/agent.json
#   - Tool in /api/mcp server

@app.tool(description="Route query to appropriate sub-agent (sgp_research, expert_finder, analytics, compliance)")
async def route_query(messages: List[dict]) -> dict:
    """
    Route query to the appropriate sub-agent based on intent.

    The supervisor uses function calling to intelligently route to:
    - sgp_research: Expert transcript research
    - expert_finder: Find experts by topic
    - analytics: Business metrics and SQL queries
    - compliance_check: Conflict of interest checks

    Args:
        messages: List of conversation messages with 'role' and 'content'

    Returns:
        Dictionary with 'response' key containing sub-agent's response
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

        # Execute routing
        response = agent.predict(agent_request)

        # Extract response text
        response_text = response.output[0].text if response.output else ""

        return {
            "response": response_text
        }

    except Exception as e:
        raise Exception(f"Query routing failed: {str(e)}")


@app.tool(description="Get supervisor configuration and sub-agent status")
async def get_config() -> dict:
    """Get supervisor configuration and available sub-agents."""
    try:
        agent = get_agent()
        return {
            "model_endpoint": agent.config.get("endpoint"),
            "sub_agents": [
                {
                    "name": "sgp_research",
                    "endpoint": "agents_sgp_research",
                    "description": "Expert transcript research"
                },
                {
                    "name": "expert_finder",
                    "endpoint": "agents_expert_finder",
                    "description": "Find experts by topic"
                },
                {
                    "name": "analytics",
                    "endpoint": "agents_analytics",
                    "description": "Business metrics and SQL queries"
                },
                {
                    "name": "compliance_check",
                    "endpoint": "agents_compliance",
                    "description": "Conflict of interest checks"
                }
            ],
            "tools_count": len(agent.tools)
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
        "service": "agents-supervisor-agent",
        "version": "1.0.0",
        "framework": "databricks-agents",
        "agent_type": "multi-agent-orchestrator",
        "sub_agents": ["sgp_research", "expert_finder", "analytics", "compliance_check"],
        "endpoints": {
            "agent_card": "/.well-known/agent.json",
            "oidc_config": "/.well-known/openid-configuration",
            "health": "/health",
            "mcp_server": "/api/mcp",
            "tools": {
                "route_query": "/api/tools/route_query",
                "get_config": "/api/tools/get_config"
            }
        }
    }


# Legacy endpoint compatibility - maps old /query to new /api/tools/route_query
# This preserves backward compatibility with existing clients
@app.post("/query", response_model=QueryResponse)
async def query_legacy(request: QueryRequest):
    """
    Legacy query endpoint for backward compatibility.

    New clients should use: POST /api/tools/route_query
    """
    messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
    result = await route_query(messages)
    return QueryResponse(response=result["response"])


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

    print("🚀 Starting  Supervisor Agent (databricks-agents framework)")
    print("\n📍 Endpoints:")
    print("   http://localhost:8000                           - Root")
    print("   http://localhost:8000/docs                      - Interactive API docs")
    print("   http://localhost:8000/.well-known/agent.json    - Agent card (A2A)")
    print("   http://localhost:8000/health                    - Health check")
    print("   http://localhost:8000/api/mcp                   - MCP server")
    print("   http://localhost:8000/api/tools/route_query     - Route query tool")
    print("\n🔄 Legacy endpoints (backward compatible):")
    print("   http://localhost:8000/query                     - Old query endpoint")
    print("   http://localhost:8000/config                    - Old config endpoint")
    print("\n🤖 Sub-agents:")
    print("   - sgp_research      → Expert transcript research")
    print("   - expert_finder     → Find experts by topic")
    print("   - analytics         → Business metrics and SQL")
    print("   - compliance_check  → Conflict of interest checks")
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)
