"""
FastAPI wrapper for Supervisor Agent

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

The supervisor routes queries to specialized sub-agents:
- research: Expert transcript research
- expert_finder: Find experts by topic
- analytics: Business metrics and SQL queries
- compliance_check: Conflict of interest checks
"""

import os
from typing import List, Optional
from pydantic import BaseModel

from databricks_agents import AgentApp
from agent import SupervisorAgent


# Create agent with framework
agent = AgentApp(
    name="supervisor",
    description="Multi-agent supervisor that routes queries to specialized sub-agents",
    capabilities=[
        "orchestration",
        "routing",
        "research",
        "expert_finder",
        "analytics",
        "compliance"
    ],
    uc_catalog=os.environ.get("UC_CATALOG", "main"),
    uc_schema=os.environ.get("UC_SCHEMA", "agents"),
    auto_register=True,
    enable_mcp=True,
    version="1.0.0",
)

# Initialize agent (singleton pattern)
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


# Request/Response models
class Message(BaseModel):
    role: str
    content: str


class QueryRequest(BaseModel):
    messages: List[Message]
    stream: Optional[bool] = False


class QueryResponse(BaseModel):
    response: str


# Tools — @agent.tool() registers these for MCP, A2A, and /api/tools/<name>

@agent.tool(description="Route query to appropriate sub-agent (research, expert_finder, analytics, compliance)")
async def route_query(messages: List[dict]) -> dict:
    """
    Route query to the appropriate sub-agent based on intent.

    Args:
        messages: List of conversation messages with 'role' and 'content'

    Returns:
        Dictionary with 'response' key containing sub-agent's response
    """
    try:
        supervisor = get_agent()

        from mlflow.types.responses import ResponsesAgentRequest

        if isinstance(messages, str):
            input_items = [{"role": "user", "content": messages}]
        else:
            input_items = [{"role": msg["role"], "content": msg["content"]} for msg in messages]
        agent_request = ResponsesAgentRequest(input=input_items)

        response = supervisor.predict(agent_request)

        response_text = ""
        if response.output:
            item = response.output[0]
            if hasattr(item, "text") and item.text:
                response_text = item.text
            elif hasattr(item, "content") and item.content:
                for part in item.content:
                    part_dict = part.model_dump() if hasattr(part, "model_dump") else part
                    if isinstance(part_dict, dict) and part_dict.get("type") == "output_text":
                        response_text = part_dict.get("text", "")
                        break

        result = {"response": response_text}

        if supervisor._last_routing:
            result["_routing"] = supervisor._last_routing

        return result

    except Exception as e:
        raise Exception(f"Query routing failed: {str(e)}")


@agent.tool(description="Get supervisor configuration and sub-agent status")
async def get_config() -> dict:
    """Get supervisor configuration and available sub-agents."""
    try:
        supervisor = get_agent()
        sub_agents = []
        for name, cfg in supervisor.SUBAGENT_CONFIG.items():
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
            "model_endpoint": supervisor.config.get("endpoint"),
            "sub_agents": sub_agents,
            "tools_count": len(supervisor.tools),
            "architecture": "invocations_routing",
        }
    except Exception as e:
        raise Exception(f"Failed to get config: {str(e)}")


# Build the FastAPI app
app = agent.as_fastapi()


# Additional custom endpoints on the FastAPI app

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "status": "healthy",
        "service": "agents-supervisor-agent",
        "version": "1.0.0",
        "framework": "databricks-agent-deploy",
        "agent_type": "multi-agent-orchestrator",
        "sub_agents": ["research", "expert_finder", "analytics", "compliance_check"],
        "endpoints": {
            "invocations": "/invocations",
            "agent_card": "/.well-known/agent.json",
            "health": "/health",
            "mcp_server": "/api/mcp",
            "tools": {
                "route_query": "/api/tools/route_query",
                "get_config": "/api/tools/get_config"
            }
        }
    }


# Legacy endpoint compatibility
@app.post("/query", response_model=QueryResponse)
async def query_legacy(request: QueryRequest):
    """Legacy query endpoint. New clients should use: POST /invocations"""
    messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
    result = await route_query(messages)
    return QueryResponse(response=result["response"])


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

    print("Starting Supervisor Agent (databricks-agent-deploy framework)")
    print("\nEndpoints:")
    print("   http://localhost:8000/invocations               - Responses Agent protocol")
    print("   http://localhost:8000/.well-known/agent.json    - Agent card (A2A)")
    print("   http://localhost:8000/health                    - Health check")
    print("   http://localhost:8000/api/mcp                   - MCP server")
    print("   http://localhost:8000/api/tools/route_query     - Route query tool")
    print("\nLegacy endpoints:")
    print("   http://localhost:8000/query                     - Old query endpoint")
    print("   http://localhost:8000/config                    - Old config endpoint")
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)
