"""
Supervisor runtime - Actually RUN supervisors, not just generate code.

This provides a chat endpoint that executes the generated supervisor logic
so users can test supervisors immediately without deploying.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
import httpx
import json
from dataclasses import dataclass

logger = logging.getLogger(__name__)

from app.db_adapter import WarehouseDB
from app.config import settings

router = APIRouter(prefix="/supervisor-runtime", tags=["Supervisor Runtime"])


@dataclass
class ToolInfo:
    """Tool discovered from MCP server."""
    name: str
    description: str
    spec: Dict[str, Any]
    server_url: str


class SupervisorChatRequest(BaseModel):
    """Chat request for supervisor runtime."""
    collection_id: int = Field(..., description="Collection ID to use for supervisor")
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    mock_mode: bool = Field(False, description="Use mock responses (no real LLM/MCP calls). Set to true for demo mode.")
    orchestration_mode: bool = Field(
        True,
        description="Multi-agent orchestration (plan, route, execute, evaluate). Set to false for legacy single-cycle mode.",
    )


class SupervisorChatResponse(BaseModel):
    """Chat response from supervisor runtime."""
    response: str
    conversation_id: str
    tools_discovered: int
    tools_called: int
    mock: bool


async def fetch_tool_infos_mock(server_url: str) -> List[ToolInfo]:
    """Mock tool discovery for demo purposes."""
    # Return mock tools based on collection
    return [
        ToolInfo(
            name="search_transcripts",
            description="Search expert transcripts using RAG",
            spec={
                "type": "function",
                "function": {
                    "name": "search_transcripts",
                    "description": "Search expert transcripts using RAG",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            },
            server_url=server_url
        ),
        ToolInfo(
            name="get_expert_profile",
            description="Retrieve expert profile by ID",
            spec={
                "type": "function",
                "function": {
                    "name": "get_expert_profile",
                    "description": "Retrieve expert profile by ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expert_id": {"type": "string", "description": "Expert ID"}
                        },
                        "required": ["expert_id"]
                    }
                }
            },
            server_url=server_url
        )
    ]


def generate_mock_response(message: str, tools: List[ToolInfo]) -> Dict[str, Any]:
    """Generate a mock supervisor response."""
    message_lower = message.lower()

    # Simple keyword matching for demo
    if "search" in message_lower or "find" in message_lower:
        return {
            "response": f"""I found several experts based on your query: "{message}"

**Top Matches:**

1. **Dr. Sarah Chen** - Machine Learning Expert
   - 15 years experience in ML research
   - Specializes in neural networks and deep learning
   - Expert ID: EXP-2847

2. **Prof. Michael Rodriguez** - AI Ethics Researcher
   - Pioneer in responsible AI development
   - Published 47 papers on AI ethics
   - Expert ID: EXP-1923

3. **Dr. Aisha Patel** - Natural Language Processing
   - Expert in transformer models and LLMs
   - Built systems for 10+ companies
   - Expert ID: EXP-3156

Would you like me to retrieve full profiles for any of these experts?

*Note: This is a demo response. In production, this would call the real search_transcripts tool.*""",
            "tools_called": 1,
            "tool_name": "search_transcripts"
        }

    elif "profile" in message_lower or "exp-" in message_lower:
        return {
            "response": """**Dr. Sarah Chen (EXP-2847)**

**Background:**
- Ph.D. in Computer Science, Stanford University
- 15 years in Machine Learning Research
- Currently: Chief AI Scientist at TechCorp

**Expertise:**
- Deep Learning & Neural Networks
- Computer Vision
- Reinforcement Learning
- MLOps and Production ML

**Recent Work:**
- Led development of breakthrough transformer architecture
- Published in top-tier conferences (NeurIPS, ICML, CVPR)
- Advisory board for 3 AI startups

**Publications:** 87 papers, 12,000+ citations
**Availability:** Open to consulting engagements

*Note: This is a demo response. In production, this would call the real get_expert_profile tool.*""",
            "tools_called": 1,
            "tool_name": "get_expert_profile"
        }

    elif any(word in message_lower for word in ["hello", "hi", "hey", "help"]):
        return {
            "response": f"""Hello! I'm the **Expert Research Toolkit** supervisor.

I can help you with:

🔍 **Search Expert Transcripts** - Find relevant expert conversations using vector search
   Example: "Find experts in quantum computing"

👤 **Retrieve Expert Profiles** - Get detailed information about specific experts
   Example: "Get profile for EXP-2847"

**Available Tools:** {len(tools)} tools discovered
- {', '.join([t.name for t in tools])}

What would you like to explore?

*Note: This is running in demo mode. In production, this would connect to real MCP servers and use Databricks Foundation Models.*""",
            "tools_called": 0,
            "tool_name": None
        }

    else:
        return {
            "response": f"""I understand you're asking: "{message}"

Based on your query, I can:
- Search for relevant experts using the **search_transcripts** tool
- Retrieve detailed profiles using the **get_expert_profile** tool

Try asking:
- "Find experts in [your topic]"
- "Get profile for [expert ID]"

**Current Capabilities:**
- {len(tools)} tools available
- Pattern 3 dynamic discovery active
- Ready to orchestrate agent interactions

*Note: This is running in demo mode with simulated responses.*""",
            "tools_called": 0,
            "tool_name": None
        }


@router.post(
    "/chat",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Chat with Supervisor Runtime",
    description="Execute supervisor logic and chat - no deployment needed!",
    responses={
        200: {
            "description": "Supervisor response (standard or orchestrated)",
            "content": {"application/json": {}},
        }
    },
)
async def chat_with_supervisor(request: SupervisorChatRequest) -> SupervisorChatResponse:
    """
    Chat with a supervisor runtime.

    This runs the supervisor logic locally so you can test it immediately
    without deploying to Databricks Apps.

    **Mock Mode (default):**
    - Uses simulated responses
    - No real LLM or MCP calls
    - Instant responses for testing

    **Production Mode (mock_mode=false):**
    - Requires DATABRICKS_TOKEN and MCP server access
    - Real tool discovery and execution
    - Actual LLM orchestration
    """
    # Validate collection exists
    collection = WarehouseDB.get_collection(request.collection_id)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection {request.collection_id} not found"
        )

    # Get collection items to find MCP servers
    items = WarehouseDB.list_collection_items(request.collection_id)

    # Extract MCP server URLs
    mcp_server_urls = set()
    for item in items:
        if item.get("mcp_server_id"):
            server = WarehouseDB.get_mcp_server(item["mcp_server_id"])
            if server:
                mcp_server_urls.add(server["server_url"])
        if item.get("app_id"):
            app = WarehouseDB.get_app(item["app_id"])
            if app and app.get("url"):
                mcp_server_urls.add(app["url"])

    if request.mock_mode:
        # MOCK MODE: Simulated responses for demo
        tool_infos = []
        for server_url in mcp_server_urls:
            tools = await fetch_tool_infos_mock(server_url)
            tool_infos.extend(tools)

        # Generate mock response
        mock_result = generate_mock_response(request.message, tool_infos)

        return SupervisorChatResponse(
            response=mock_result["response"],
            conversation_id=request.conversation_id or "demo-session",
            tools_discovered=len(tool_infos),
            tools_called=mock_result["tools_called"],
            mock=True
        )

    elif request.orchestration_mode:
        # ORCHESTRATION MODE: Multi-agent planning, routing, execution, evaluation
        return await run_orchestrated_supervisor(
            collection=collection,
            mcp_server_urls=list(mcp_server_urls),
            message=request.message,
            conversation_id=request.conversation_id,
        )

    else:
        # PRODUCTION MODE: Real LLM and MCP calls (single-cycle)
        return await run_real_supervisor(
            collection=collection,
            mcp_server_urls=list(mcp_server_urls),
            message=request.message,
            conversation_id=request.conversation_id
        )


async def fetch_tool_infos_real(server_url: str) -> List[ToolInfo]:
    """Fetch tools from real MCP server via JSON-RPC."""
    tools: List[ToolInfo] = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            request_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }

            response = await client.post(
                server_url,
                json=request_payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            result = response.json()

            if "error" in result:
                logger.warning("MCP server error from %s: %s", server_url, result['error'])
                return tools

            tools_data = result.get("result", {}).get("tools", [])

            for tool_data in tools_data:
                tool_name = tool_data.get("name", "")
                if not tool_name:
                    continue

                tool_spec = {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": tool_data.get("description", ""),
                        "parameters": tool_data.get("inputSchema", {})
                    }
                }

                tools.append(ToolInfo(
                    name=tool_name,
                    description=tool_data.get("description", ""),
                    spec=tool_spec,
                    server_url=server_url
                ))

    except Exception as e:
        logger.error("Failed to fetch tools from %s: %s", server_url, e)

    return tools


async def call_tool_real(tool_name: str, tool_args: Dict[str, Any], server_url: str) -> Any:
    """Execute tool on real MCP server."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        request_payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": tool_args
            }
        }

        response = await client.post(
            server_url,
            json=request_payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        result = response.json()

        if "error" in result:
            error = result["error"]
            raise Exception(f"Tool call error: {error.get('message', 'Unknown error')}")

        return result.get("result", {})


def _get_databricks_llm_config():
    """Get Databricks LLM endpoint URL and auth headers via WorkspaceClient."""
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    endpoint_url = f"{w.config.host}/serving-endpoints/{settings.llm_endpoint}/invocations"
    headers = {"Content-Type": "application/json"}
    headers.update(w.config.authenticate())
    return endpoint_url, headers


async def _delegate_to_agent(agent_id: int, task_description: str, base_url: str) -> str:
    """
    Delegate a sub-task to a peer agent via A2A message/send.

    Returns the response text from the peer agent.
    """
    from app.services.a2a_client import A2AClient, A2AClientError

    agent = WarehouseDB.get_agent(agent_id)
    if not agent:
        return f"Error: Agent {agent_id} not found"

    # Determine A2A URL: prefer agent's endpoint_url, fallback to registry's A2A endpoint
    a2a_url = agent.get("endpoint_url") or f"{base_url}/api/a2a/{agent_id}"

    try:
        async with A2AClient(timeout=120.0) as client:
            result = await client.send_message(
                agent_url=a2a_url,
                message=task_description,
                auth_token=agent.get("auth_token"),
            )

        # Extract response text from task artifacts or messages
        artifacts = result.get("artifacts", [])
        if artifacts:
            for artifact in artifacts:
                for part in artifact.get("parts", []):
                    if part.get("text"):
                        return part["text"]

        messages = result.get("messages", [])
        for msg in reversed(messages):
            if msg.get("role") == "agent":
                for part in msg.get("parts", []):
                    if part.get("text"):
                        return part["text"]

        return json.dumps(result)

    except A2AClientError as e:
        return f"Delegation error: {e}"
    except Exception as e:
        return f"Delegation failed: {e}"


async def run_orchestrated_supervisor(
    collection: Dict[str, Any],
    mcp_server_urls: List[str],
    message: str,
    conversation_id: Optional[str],
) -> SupervisorChatResponse:
    """Run multi-agent orchestration: plan -> match -> execute -> evaluate."""
    from dataclasses import asdict
    from app.services.orchestrator import Orchestrator, MAX_RETRIES
    from app.services.search import SearchService
    from app.schemas.orchestrator import OrchestrationChatResponse, SubTaskResultItem

    # Step 1: Discover MCP tools (for tool count reporting)
    tool_infos: List[ToolInfo] = []
    for server_url in mcp_server_urls:
        if server_url and server_url.strip():
            server_tools = await fetch_tool_infos_real(server_url.strip())
            tool_infos.extend(server_tools)

    # Step 2: Get active A2A agents
    peer_agents = WarehouseDB.list_active_a2a_agents()

    # Step 3: Match agents to query via embedding similarity
    search_service = SearchService()
    matched = await search_service.match_agents(message, limit=5)

    # Merge: start with matched agents, then add any active agents not already included
    agent_ids_seen = {m["agent"]["id"] for m in matched}
    available_agents = [m["agent"] for m in matched]
    for pa in peer_agents:
        if pa["id"] not in agent_ids_seen:
            available_agents.append(pa)
            agent_ids_seen.add(pa["id"])

    if not available_agents:
        return SupervisorChatResponse(
            response="No active agents available for orchestration. Register and activate agents first.",
            conversation_id=conversation_id or "error-session",
            tools_discovered=len(tool_infos),
            tools_called=0,
            mock=False,
        )

    # Step 4: Plan
    orchestrator = Orchestrator()
    plan = await orchestrator.classify_and_plan(message, available_agents)

    if plan.complexity == "simple" and plan.sub_tasks:
        # For simple queries, fall through to the standard single-cycle supervisor
        return await run_real_supervisor(
            collection=collection,
            mcp_server_urls=mcp_server_urls,
            message=message,
            conversation_id=conversation_id,
        )

    # Step 5: Execute plan
    base_url = settings.a2a_base_url or "http://localhost:8000"
    results = await orchestrator.execute_plan(plan, base_url)

    # Step 6: Evaluate results
    evaluation = await orchestrator.evaluate_results(message, plan, results)

    # Step 6b: One retry if evaluation says results are poor
    retry_count = 0
    while evaluation.needs_retry and retry_count < MAX_RETRIES:
        retry_count += 1
        logger.info("Orchestration retry %d: %s", retry_count, evaluation.retry_suggestions)
        results = await orchestrator.execute_plan(plan, base_url)
        evaluation = await orchestrator.evaluate_results(message, plan, results)

    # Step 7: Record analytics for each sub-task
    for r in results:
        try:
            quality_int = round(evaluation.quality_score) if evaluation.quality_score else None
            WarehouseDB.create_agent_analytic(
                agent_id=r.agent_id,
                task_description=r.description,
                success=1 if r.success else 0,
                latency_ms=r.latency_ms,
                quality_score=quality_int,
                error_message=r.error,
            )
        except Exception as e:
            logger.warning("Failed to record analytics for agent %d: %s", r.agent_id, e)

    # Step 8: Build response
    plan_dict = {
        "complexity": plan.complexity,
        "reasoning": plan.reasoning,
        "sub_tasks": [asdict(st) for st in plan.sub_tasks],
    }
    result_items = [
        SubTaskResultItem(
            task_index=r.task_index,
            agent_id=r.agent_id,
            agent_name=r.agent_name,
            description=r.description,
            response=r.response,
            latency_ms=r.latency_ms,
            success=r.success,
            error=r.error,
        )
        for r in results
    ]

    return OrchestrationChatResponse(
        response=evaluation.final_response,
        conversation_id=conversation_id or "orchestrated-session",
        plan=plan_dict,
        sub_task_results=result_items,
        agents_used=len({r.agent_id for r in results}),
        tools_discovered=len(tool_infos),
        tools_called=0,
        quality_score=evaluation.quality_score,
        mock=False,
    )


async def run_real_supervisor(
    collection: Dict[str, Any],
    mcp_server_urls: List[str],
    message: str,
    conversation_id: Optional[str]
) -> SupervisorChatResponse:
    """Run real supervisor with actual LLM and MCP calls + A2A peer agent delegation."""

    try:
        import mlflow
        from mlflow.entities import SpanType
        _mlflow_ok = True
    except ImportError:
        _mlflow_ok = False

    # Validate Databricks auth
    try:
        endpoint_url, auth_headers = _get_databricks_llm_config()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Databricks auth failed: {e}. Ensure CLI profile or env vars are configured."
        )

    # Step 1: Discover tools from real MCP servers
    tool_infos: List[ToolInfo] = []
    for server_url in mcp_server_urls:
        if server_url and server_url.strip():
            server_tools = await fetch_tool_infos_real(server_url.strip())
            tool_infos.extend(server_tools)

    # Step 1b: Discover peer agents for delegation
    peer_agents = WarehouseDB.list_active_a2a_agents()

    if not tool_infos and not peer_agents:
        return SupervisorChatResponse(
            response="I couldn't discover any tools or peer agents. Please check that the MCP servers are running.",
            conversation_id=conversation_id or "error-session",
            tools_discovered=0,
            tools_called=0,
            mock=False
        )

    # Step 2: Create messages for LLM with peer agent info
    peer_agent_desc = ""
    if peer_agents:
        lines = ["\n\nAvailable Peer Agents (delegate sub-tasks to these using the delegate_to_agent tool):"]
        for pa in peer_agents:
            caps = pa.get("capabilities", "") or ""
            lines.append(f"- **{pa['name']}** (ID: {pa['id']}): {pa.get('description', 'No description')} [Capabilities: {caps}]")
        peer_agent_desc = "\n".join(lines)

    system_prompt = f"""You are {collection['name']}, an AI supervisor that coordinates multiple specialized agents.

Available tools: {len(tool_infos)} tools discovered from MCP servers.{peer_agent_desc}

Your responsibilities:
1. Understand user requests
2. Select appropriate tools to fulfill requests
3. Call tools with correct parameters
4. Delegate sub-tasks to peer agents when their specialization matches the request
5. Synthesize results into helpful responses

Always explain your reasoning and provide clear, actionable information."""

    messages_list = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]

    # Step 3: Build tools list — MCP tools + delegation tool
    tools_param = [ti.spec for ti in tool_infos]

    if peer_agents:
        delegation_tool = {
            "type": "function",
            "function": {
                "name": "delegate_to_agent",
                "description": "Delegate a sub-task to a peer agent. Use this when a peer agent's specialization matches the request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "integer", "description": "ID of the peer agent to delegate to"},
                        "task_description": {"type": "string", "description": "Description of the task to delegate"},
                    },
                    "required": ["agent_id", "task_description"],
                }
            }
        }
        tools_param.append(delegation_tool)

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            request_body = {
                "messages": messages_list,
                "tools": tools_param,
                "tool_choice": "auto",
                "max_tokens": 4096,
                "temperature": 0.1
            }

            response = await client.post(
                endpoint_url,
                headers=auth_headers,
                json=request_body
            )
            response.raise_for_status()
            result = response.json()

    except httpx.HTTPError as e:
        return SupervisorChatResponse(
            response=f"Error calling LLM: {str(e)}. Please check your Databricks credentials and endpoint availability.",
            conversation_id=conversation_id or "error-session",
            tools_discovered=len(tool_infos),
            tools_called=0,
            mock=False
        )

    # Step 4: Handle tool calls (MCP tools or delegation)
    message_content = result.get("choices", [{}])[0].get("message", {})
    tool_calls = message_content.get("tool_calls", [])
    tools_called_count = len(tool_calls)

    if tool_calls:
        tool_results = []

        # Derive base_url for delegation calls
        base_url = settings.a2a_base_url or "http://localhost:8000"

        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            tool_name = function.get("name")
            tool_args = json.loads(function.get("arguments", "{}"))

            if tool_name == "delegate_to_agent":
                # A2A delegation
                target_agent_id = tool_args.get("agent_id")
                task_desc = tool_args.get("task_description", "")

                if _mlflow_ok:
                    target_agent = WarehouseDB.get_agent(target_agent_id) if target_agent_id else None
                    agent_name = target_agent["name"] if target_agent else str(target_agent_id)
                    with mlflow.start_span(name=f"a2a_delegate:{agent_name}", span_type=SpanType.TOOL) as span:
                        span.set_inputs({"agent_id": target_agent_id, "task_description": task_desc})
                        delegation_result = await _delegate_to_agent(target_agent_id, task_desc, base_url)
                        span.set_outputs({"response_length": len(delegation_result)})
                else:
                    delegation_result = await _delegate_to_agent(target_agent_id, task_desc, base_url)

                tool_results.append({
                    "tool_call_id": tool_call.get("id"),
                    "role": "tool",
                    "name": tool_name,
                    "content": delegation_result
                })
            else:
                # Regular MCP tool call
                tool_info = next((t for t in tool_infos if t.name == tool_name), None)

                if not tool_info:
                    tool_results.append({
                        "tool_call_id": tool_call.get("id"),
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps({"error": f"Tool {tool_name} not found"})
                    })
                    continue

                try:
                    tool_result = await call_tool_real(tool_name, tool_args, tool_info.server_url)
                    tool_results.append({
                        "tool_call_id": tool_call.get("id"),
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps(tool_result)
                    })
                except Exception as e:
                    tool_results.append({
                        "tool_call_id": tool_call.get("id"),
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps({"error": str(e)})
                    })

        # Step 5: Get final response from LLM with tool results
        messages_list.append(message_content)
        messages_list.extend(tool_results)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    endpoint_url,
                    headers=auth_headers,
                    json={
                        "messages": messages_list,
                        "max_tokens": 4096,
                        "temperature": 0.1
                    }
                )
                response.raise_for_status()
                result = response.json()
        except Exception as e:
            return SupervisorChatResponse(
                response=f"Error getting final response: {str(e)}",
                conversation_id=conversation_id or "error-session",
                tools_discovered=len(tool_infos),
                tools_called=tools_called_count,
                mock=False
            )

    # Extract final response
    final_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

    if not final_content:
        final_content = "I apologize, but I couldn't generate a response. Please try again."

    return SupervisorChatResponse(
        response=final_content,
        conversation_id=conversation_id or "new",
        tools_discovered=len(tool_infos) + len(peer_agents),
        tools_called=tools_called_count,
        mock=False
    )


@router.get(
    "/status/{collection_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Supervisor Runtime Status",
    description="Check if supervisor runtime is available for a collection"
)
async def get_supervisor_status(collection_id: int) -> Dict[str, Any]:
    """Get supervisor runtime status for a collection."""
    collection = WarehouseDB.get_collection(collection_id)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection {collection_id} not found"
        )

    # Get items to count tools
    items = WarehouseDB.list_collection_items(collection_id)

    # Count MCP servers
    mcp_servers = set()
    for item in items:
        if item.get("mcp_server_id"):
            mcp_servers.add(item["mcp_server_id"])
        if item.get("app_id"):
            app = WarehouseDB.get_app(item["app_id"])
            if app and app.get("url"):
                mcp_servers.add(app["url"])

    return {
        "collection_id": collection_id,
        "collection_name": collection["name"],
        "runtime_available": True,
        "mock_mode": True,
        "production_mode": False,
        "tools_available": len(items),
        "mcp_servers": len(mcp_servers),
        "endpoints": {
            "chat": f"/api/supervisor-runtime/chat",
            "status": f"/api/supervisor-runtime/status/{collection_id}"
        }
    }
