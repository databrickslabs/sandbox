"""
Chat endpoint for testing registered agents and tools.

This route provides a chat interface that can use registered MCP servers
and tools from the registry.
"""

import os
import json
import logging
import time
import uuid
from collections import OrderedDict

import httpx
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.db_adapter import WarehouseDB
from app.config import settings

try:
    import mlflow
    from mlflow.entities import SpanType
    _mlflow_available = True
except ImportError:
    _mlflow_available = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

# Configuration
LLM_ENDPOINT = settings.llm_endpoint
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))


class BoundedDict(OrderedDict):
    """OrderedDict with max size — evicts oldest entries when full."""

    def __init__(self, max_size: int = 1000, *args, **kwargs):
        self._max_size = max_size
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        while len(self) > self._max_size:
            self.popitem(last=False)


# In-memory stores with LRU eviction to prevent unbounded growth
conversations: BoundedDict = BoundedDict(max_size=500)
trace_events: BoundedDict = BoundedDict(max_size=2000)
trace_spans: BoundedDict = BoundedDict(max_size=2000)


class ChatRequest(BaseModel):
    """Chat request model."""
    query: Optional[str] = None
    text: Optional[str] = None  # Frontend alias for query
    server_urls: Optional[List[str]] = None  # Accepted but ignored
    agent_id: Optional[str] = None  # MCP server ID to use
    collection_id: Optional[int] = None  # Collection of tools to use
    conversation_id: Optional[str] = None

    @property
    def effective_query(self) -> str:
        """Use text as fallback if query is empty."""
        return self.query or self.text or ""


class ToolCall(BaseModel):
    """Tool call info."""
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None
    latency_ms: Optional[float] = None


class ChatResponse(BaseModel):
    """Chat response model."""
    query: str
    response: str
    text: Optional[str] = None  # Mirror of response for frontend
    trace_id: Optional[str] = None  # Trace ID for event streaming
    conversation_id: str
    routed_to: Optional[str] = None
    agent_display_name: Optional[str] = None
    routing_reason: Optional[str] = None
    latency_ms: Optional[float] = None
    tool_calls: List[ToolCall] = []
    technical_context: Optional[Dict] = None


def get_llm_client():
    """Get Databricks Foundation Model client."""
    from databricks.sdk import WorkspaceClient
    return WorkspaceClient()


def get_available_tools(collection_id: Optional[int] = None, mcp_server_id: Optional[int] = None) -> List[Dict]:
    """Get available tools from the registry."""
    tools = []
    seen_tool_ids = set()  # Avoid duplicates

    if collection_id:
        # Get tools from collection
        items = WarehouseDB.list_collection_items(collection_id)
        for item in items:
            if item.get('tool_id'):
                # Individual tool reference
                tool = WarehouseDB.get_tool(item['tool_id'])
                if tool and tool.get('id') not in seen_tool_ids:
                    tools.append(tool)
                    seen_tool_ids.add(tool.get('id'))

            elif item.get('mcp_server_id'):
                # MCP server reference - get all its tools
                server_tools, _ = WarehouseDB.list_tools(mcp_server_id=item['mcp_server_id'])
                for tool in server_tools:
                    if tool.get('id') not in seen_tool_ids:
                        tools.append(tool)
                        seen_tool_ids.add(tool.get('id'))

            elif item.get('app_id'):
                # App reference - get all MCP servers for this app, then all their tools
                all_servers, _ = WarehouseDB.list_mcp_servers()
                for server in all_servers:
                    if server.get('app_id') == item['app_id']:
                        server_tools, _ = WarehouseDB.list_tools(mcp_server_id=server.get('id'))
                        for tool in server_tools:
                            if tool.get('id') not in seen_tool_ids:
                                tools.append(tool)
                                seen_tool_ids.add(tool.get('id'))

    elif mcp_server_id:
        # Get tools from specific MCP server
        server_tools, _ = WarehouseDB.list_tools(mcp_server_id=mcp_server_id)
        tools.extend(server_tools)
    else:
        # Get all tools
        all_tools, _ = WarehouseDB.list_tools(page_size=100)
        tools.extend(all_tools)

    return tools


def format_tools_for_llm(tools: List[Dict]) -> List[Dict]:
    """Format tools for LLM function calling (OpenAI-compatible format)."""
    formatted = []
    for tool in tools:
        try:
            params = json.loads(tool.get('parameters', '{}')) if tool.get('parameters') else {}
        except json.JSONDecodeError:
            params = {}

        # Ensure parameters follow JSON Schema spec with type: "object" wrapper
        if params and params.get("type") != "object":
            params = {
                "type": "object",
                "properties": params,
                "required": [],
            }

        formatted.append({
            "type": "function",
            "function": {
                "name": tool.get('name', ''),
                "description": tool.get('description', ''),
                "parameters": params or {"type": "object", "properties": {}},
            }
        })
    return formatted


async def call_mcp_tool(server_url: str, tool_name: str, arguments: Dict) -> str:
    """Call a tool on an MCP server."""
    # MCP uses JSON-RPC 2.0
    request_body = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                server_url,
                json=request_body,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                return f"Error: {result['error'].get('message', 'Unknown error')}"

            return json.dumps(result.get("result", {}))
        except Exception as e:
            return f"Error calling tool: {str(e)}"


async def call_foundation_model(
    messages: List[Dict],
    tools: List[Dict] = None
) -> Dict:
    """Call Databricks Foundation Model API (async)."""
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()

    endpoint_url = f"{w.config.host}/serving-endpoints/{LLM_ENDPOINT}/invocations"

    request_body = {
        "messages": messages,
        "max_tokens": MAX_TOKENS,
    }

    if tools:
        request_body["tools"] = tools
        request_body["tool_choice"] = "auto"

    headers = {"Content-Type": "application/json"}
    headers.update(w.config.authenticate())

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(endpoint_url, json=request_body, headers=headers)

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"LLM API error: {response.text}"
        )

    return response.json()


def _make_span(trace_id: str, name: str, start_s: float, end_s: float,
               attributes: Dict[str, Any], span_status: str = "OK") -> Dict[str, Any]:
    """Build a span dict matching the frontend Span interface."""
    return {
        "id": str(uuid.uuid4()),
        "trace_id": trace_id,
        "name": name,
        "start_time": int(start_s * 1000),
        "end_time": int(end_s * 1000),
        "attributes": attributes,
        "status": span_status,
    }


DATABRICKS_SYSTEM_PROMPT = (
    "You are an intelligent assistant for a Databricks workspace. You have access to tools "
    "registered in the Multi-Agent Registry — MCP servers, catalog assets, notebooks, jobs, "
    "and other workspace resources.\n\n"
    "When answering questions:\n"
    "- Use available tools to look up live data when possible\n"
    "- Reference specific catalog assets (tables, views, functions) by their full name\n"
    "- Explain your reasoning and tool usage clearly"
)


async def _run_chat(request: ChatRequest, root_span=None) -> ChatResponse:
    """Core chat logic. If root_span is provided, child spans are logged to MLflow."""
    start_time = time.time()
    query = request.effective_query
    use_mlflow = root_span is not None and _mlflow_available

    trace_id = root_span.request_id if use_mlflow else str(uuid.uuid4())

    if use_mlflow:
        root_span.set_inputs({"query": query, "collection_id": request.collection_id})

    # Initialize in-memory trace stores (fast path for SSE streaming)
    trace_events[trace_id] = []
    trace_spans[trace_id] = []

    trace_events[trace_id].append({
        "type": "request.started",
        "timestamp": time.time(),
        "data": {"query": query},
    })

    # Get or create conversation — persist to DB with in-memory fallback
    conversation_id = request.conversation_id or str(uuid.uuid4())
    is_new_conversation = False
    db_messages = []

    try:
        existing = WarehouseDB.get_conversation(conversation_id)
        if existing:
            db_messages = existing.get("messages", [])
        else:
            is_new_conversation = True
            title = query[:60] + ("..." if len(query) > 60 else "")
            WarehouseDB.create_conversation(
                id=conversation_id,
                title=title,
                collection_id=request.collection_id,
            )
    except Exception as e:
        logger.warning("DB conversation access failed, using in-memory fallback: %s", e)

    # In-memory fallback for conversation history
    if conversation_id not in conversations:
        conversations[conversation_id] = []

    # Get available tools
    tools = get_available_tools(
        collection_id=request.collection_id,
        mcp_server_id=int(request.agent_id) if request.agent_id else None
    )

    # Build system prompt with context injection
    from app.services.chat_context import enrich_system_prompt
    system_prompt = enrich_system_prompt(DATABRICKS_SYSTEM_PROMPT, query)

    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history — prefer DB messages, fall back to in-memory
    history = db_messages if db_messages else conversations[conversation_id]
    for msg in history[-10:]:
        messages.append({"role": msg.get("role"), "content": msg.get("content")})

    # Add current query
    messages.append({"role": "user", "content": query})

    # Format tools for LLM
    llm_tools = format_tools_for_llm(tools) if tools else None

    tool_calls_made = []

    # Call Foundation Model (with MLflow child span)
    llm_start = time.time()
    if use_mlflow:
        with mlflow.start_span(name="llm_call", span_type=SpanType.CHAT_MODEL) as llm_span:
            llm_span.set_inputs({"messages_count": len(messages), "tools_count": len(llm_tools or [])})
            response = await call_foundation_model(messages, llm_tools)
            llm_span.set_outputs({"model": response.get("model", ""), "usage": response.get("usage", {})})
    else:
        response = await call_foundation_model(messages, llm_tools)
    llm_end = time.time()

    trace_spans[trace_id].append(
        _make_span(trace_id, "llm_call", llm_start, llm_end,
                   {"messages_count": len(messages), "tools_count": len(llm_tools or [])})
    )

    # Extract response
    choice = response.get("choices", [{}])[0]
    message = choice.get("message", {})

    # Handle tool calls
    if message.get("tool_calls"):
        for tool_call in message["tool_calls"]:
            func = tool_call.get("function", {})
            tool_name = func.get("name", "")
            try:
                arguments = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                arguments = {}

            # Find the tool's MCP server
            tool_info = next((t for t in tools if t.get('name') == tool_name), None)
            if tool_info:
                server = WarehouseDB.get_mcp_server(tool_info.get('mcp_server_id'))
                if server:
                    tool_start = time.time()
                    trace_events[trace_id].append({
                        "type": "tool.called",
                        "timestamp": time.time(),
                        "data": {"tool_name": tool_name, "arguments": arguments},
                    })

                    # Call MCP tool (with MLflow child span)
                    if use_mlflow:
                        with mlflow.start_span(name=f"tool:{tool_name}", span_type=SpanType.TOOL) as tool_span:
                            tool_span.set_inputs({"tool_name": tool_name, "arguments": arguments})
                            result = await call_mcp_tool(
                                server.get('server_url'), tool_name, arguments
                            )
                            tool_latency = (time.time() - tool_start) * 1000
                            tool_span.set_outputs({"latency_ms": tool_latency})
                    else:
                        result = await call_mcp_tool(
                            server.get('server_url'), tool_name, arguments
                        )
                        tool_latency = (time.time() - tool_start) * 1000

                    tool_end = time.time()
                    trace_events[trace_id].append({
                        "type": "tool.output",
                        "timestamp": time.time(),
                        "data": {"tool_name": tool_name, "latency_ms": tool_latency},
                    })
                    trace_spans[trace_id].append(
                        _make_span(trace_id, f"tool:{tool_name}", tool_start, tool_end,
                                   {"tool_name": tool_name, "latency_ms": tool_latency})
                    )

                    tool_calls_made.append(ToolCall(
                        tool_name=tool_name,
                        arguments=arguments,
                        result=result[:500] if result else None,
                        latency_ms=tool_latency
                    ))

                    # Add tool result to messages and call LLM again
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": result
                    })

        # Get final response after tool use (with MLflow child span)
        llm_final_start = time.time()
        if use_mlflow:
            with mlflow.start_span(name="llm_final", span_type=SpanType.CHAT_MODEL) as final_span:
                final_span.set_inputs({"messages_count": len(messages)})
                response = await call_foundation_model(messages, llm_tools)
                final_span.set_outputs({"model": response.get("model", ""), "usage": response.get("usage", {})})
        else:
            response = await call_foundation_model(messages, llm_tools)
        llm_final_end = time.time()

        trace_spans[trace_id].append(
            _make_span(trace_id, "llm_final", llm_final_start, llm_final_end,
                       {"messages_count": len(messages)})
        )

        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})

    response_text = message.get("content", "I'm sorry, I couldn't generate a response.")

    # Save to conversation history — DB + in-memory fallback
    conversations[conversation_id].append({"role": "user", "content": query})
    conversations[conversation_id].append({"role": "assistant", "content": response_text})

    try:
        WarehouseDB.create_conversation_message(conversation_id, "user", query)
        WarehouseDB.create_conversation_message(conversation_id, "assistant", response_text, trace_id=trace_id)
    except Exception as e:
        logger.warning("Failed to persist messages to DB: %s", e)

    latency_ms = (time.time() - start_time) * 1000

    # Final trace event
    trace_events[trace_id].append({
        "type": "response.done",
        "timestamp": time.time(),
        "data": {"latency_ms": latency_ms},
    })
    end_time = time.time()
    trace_spans[trace_id].append(
        _make_span(trace_id, "chat", start_time, end_time,
                   {"latency_ms": latency_ms, "tools_called": len(tool_calls_made)})
    )

    if use_mlflow:
        root_span.set_outputs({"response_length": len(response_text), "tools_called": len(tool_calls_made)})

    return ChatResponse(
        query=query,
        response=response_text,
        text=response_text,
        trace_id=trace_id,
        conversation_id=conversation_id,
        routed_to=request.agent_id,
        agent_display_name=f"Collection {request.collection_id}" if request.collection_id else "All Tools",
        latency_ms=latency_ms,
        tool_calls=tool_calls_made,
        technical_context={
            "routing_strategy": "direct" if request.agent_id else "auto",
            "tools_available": len(tools),
            "tools_called": len(tool_calls_made),
            "llm_endpoint": LLM_ENDPOINT,
        }
    )


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat with registered agents and tools.

    Sends the query to a Foundation Model that can use
    tools registered in the registry.
    """
    try:
        if _mlflow_available:
            with mlflow.start_span(name="chat", span_type=SpanType.AGENT) as root_span:
                return await _run_chat(request, root_span=root_span)
        else:
            return await _run_chat(request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Chat request failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat request failed: {str(e)}",
        )


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str) -> Dict:
    """Get conversation history."""
    if conversation_id not in conversations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )

    return {
        "conversation_id": conversation_id,
        "messages": conversations[conversation_id],
        "message_count": len(conversations[conversation_id])
    }


@router.post("/conversations/{conversation_id}/clear")
async def clear_conversation(conversation_id: str) -> Dict:
    """Clear conversation history."""
    if conversation_id in conversations:
        del conversations[conversation_id]

    return {"status": "cleared", "conversation_id": conversation_id}


@router.get("/tools/preview")
async def preview_available_tools(
    collection_id: Optional[int] = None,
    mcp_server_id: Optional[int] = None
) -> Dict:
    """
    Preview which tools would be available for a chat request.

    Useful for debugging tool resolution from collections.
    """
    tools = get_available_tools(collection_id=collection_id, mcp_server_id=mcp_server_id)
    llm_tools = format_tools_for_llm(tools) if tools else []

    return {
        "collection_id": collection_id,
        "mcp_server_id": mcp_server_id,
        "tool_count": len(tools),
        "tools": [
            {
                "id": t.get('id'),
                "name": t.get('name'),
                "description": t.get('description'),
                "mcp_server_id": t.get('mcp_server_id'),
            }
            for t in tools
        ],
        "llm_formatted_tools": llm_tools,
    }


@router.get("/collections")
async def list_chat_collections() -> Dict:
    """
    List available collections for chat with tool counts.

    Use this to see which collections are available and how many tools each has.
    """
    collections, total = WarehouseDB.list_collections()

    result = []
    for collection in collections:
        collection_id = collection.get('id')
        tools = get_available_tools(collection_id=collection_id)
        result.append({
            "id": collection_id,
            "name": collection.get('name'),
            "description": collection.get('description'),
            "tool_count": len(tools),
            "tools": [t.get('name') for t in tools],
        })

    return {
        "collections": result,
        "total": total,
    }
