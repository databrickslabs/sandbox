"""
A2A Protocol endpoint — JSON-RPC 2.0 handler for agent-to-agent communication.

Handles:
  POST /api/a2a/{agent_id}          — JSON-RPC dispatch (message/send, tasks/get, tasks/cancel, tasks/list)
  POST /api/a2a/{agent_id}/stream   — SSE streaming for message/stream
  GET  /api/a2a/{agent_id}/tasks/{task_id}/subscribe — SSE subscription for existing task
  POST /api/a2a/{agent_id}/tasks/{task_id}/webhook   — Register push-notification webhook
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.db_adapter import WarehouseDB
from app.config import settings
from app.schemas.a2a import (
    TaskState,
    TERMINAL_STATES,
    A2ATaskResponse,
    A2ATaskStatus,
    A2AMessage,
    A2AArtifact,
    MessagePart,
    JsonRpcRequest,
)

try:
    import mlflow
    from mlflow.entities import SpanType
    _mlflow_available = True
except ImportError:
    _mlflow_available = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/a2a", tags=["A2A Protocol"])


# ────────────────────── Auth helper ──────────────────────

def _validate_bearer_token(request: Request, agent: Dict) -> None:
    """Validate bearer token if agent has auth_token set."""
    expected = agent.get("auth_token")
    if not expected:
        return
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    if auth_header[7:] != expected:
        raise HTTPException(status_code=401, detail="Invalid Bearer token")


# ────────────────────── Task helpers ──────────────────────

def _task_to_a2a_response(task_dict: Dict) -> Dict[str, Any]:
    """Convert DB task dict to A2A TaskResponse dict."""
    messages = []
    if task_dict.get("messages"):
        try:
            messages = json.loads(task_dict["messages"])
        except (json.JSONDecodeError, TypeError):
            pass

    artifacts = []
    if task_dict.get("artifacts"):
        try:
            artifacts = json.loads(task_dict["artifacts"])
        except (json.JSONDecodeError, TypeError):
            pass

    metadata = None
    if task_dict.get("metadata_json"):
        try:
            metadata = json.loads(task_dict["metadata_json"])
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "id": task_dict["id"],
        "contextId": task_dict.get("context_id"),
        "status": {"state": task_dict["status"]},
        "messages": messages,
        "artifacts": artifacts,
        "metadata": metadata,
    }


def _jsonrpc_success(rpc_id: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rpc_id, "result": result}


def _jsonrpc_error(rpc_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}


# ────────────────────── LLM processing (reuses chat.py patterns) ──────────────────────

async def _process_agent_task(agent: Dict, message_text: str) -> str:
    """
    Process a task through the agent's tool collection and LLM.

    Reuses the same Foundation Model + MCP tool-calling pattern from chat.py.
    """
    from app.routes.chat import (
        get_available_tools,
        format_tools_for_llm,
        call_foundation_model,
        call_mcp_tool,
    )

    collection_id = agent.get("collection_id")
    tools = get_available_tools(collection_id=collection_id)
    llm_tools = format_tools_for_llm(tools) if tools else None

    if agent.get('system_prompt'):
        system_prompt = agent['system_prompt']
    else:
        system_prompt = (
            f"You are {agent['name']}"
            + (f" — {agent['description']}" if agent.get('description') else "")
            + ". Respond helpfully using your available tools."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message_text},
    ]

    # First LLM call
    response = await call_foundation_model(messages, llm_tools)
    choice = response.get("choices", [{}])[0]
    message = choice.get("message", {})

    # Handle tool calls (single pass — matches chat.py dual-pass pattern)
    if message.get("tool_calls"):
        for tool_call in message["tool_calls"]:
            func = tool_call.get("function", {})
            tool_name = func.get("name", "")
            try:
                arguments = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                arguments = {}

            tool_info = next((t for t in tools if t.get('name') == tool_name), None)
            if tool_info:
                server = WarehouseDB.get_mcp_server(tool_info.get('mcp_server_id'))
                if server:
                    result = await call_mcp_tool(server.get('server_url'), tool_name, arguments)
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call],
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": result,
                    })

        # Final LLM call after tool use
        response = await call_foundation_model(messages, llm_tools)
        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})

    return message.get("content", "I could not generate a response.")


# ────────────────────── JSON-RPC method handlers ──────────────────────

async def _handle_send_message(
    agent: Dict, params: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle message/send — create task, process, return completed task."""
    msg_data = params.get("message", {})
    message_text = ""
    for part in msg_data.get("parts", []):
        if part.get("text"):
            message_text += part["text"]

    if not message_text:
        return _jsonrpc_error(None, -32602, "Message must contain at least one text part")

    task_id = str(uuid.uuid4())
    context_id = msg_data.get("contextId") or str(uuid.uuid4())

    # Create task → submitted
    WarehouseDB.create_a2a_task(
        task_id=task_id,
        agent_id=agent["id"],
        context_id=context_id,
        status=TaskState.SUBMITTED.value,
        messages=json.dumps([msg_data]),
    )

    # Update → working
    WarehouseDB.update_a2a_task(task_id, status=TaskState.WORKING.value)

    try:
        response_text = await _process_agent_task(agent, message_text)

        # Build response message + artifact
        response_msg = {
            "messageId": str(uuid.uuid4()),
            "role": "agent",
            "parts": [{"text": response_text}],
            "contextId": context_id,
        }
        artifact = {
            "artifactId": str(uuid.uuid4()),
            "name": "response",
            "parts": [{"text": response_text}],
        }

        all_messages = [msg_data, response_msg]
        WarehouseDB.update_a2a_task(
            task_id,
            status=TaskState.COMPLETED.value,
            messages=json.dumps(all_messages),
            artifacts=json.dumps([artifact]),
        )

    except Exception as e:
        logger.error("A2A task %s failed: %s", task_id, e, exc_info=True)
        WarehouseDB.update_a2a_task(task_id, status=TaskState.FAILED.value)
        task_dict = WarehouseDB.get_a2a_task(task_id)
        return _task_to_a2a_response(task_dict)

    task_dict = WarehouseDB.get_a2a_task(task_id)

    # Fire push notification if webhook registered
    if task_dict.get("webhook_url"):
        _fire_push_notification(task_dict)

    return _task_to_a2a_response(task_dict)


async def _handle_get_task(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tasks/get."""
    task_id = params.get("id")
    if not task_id:
        return _jsonrpc_error(None, -32602, "Missing required parameter: id")

    task_dict = WarehouseDB.get_a2a_task(task_id)
    if not task_dict:
        return _jsonrpc_error(None, -32001, f"Task {task_id} not found")

    return _task_to_a2a_response(task_dict)


async def _handle_cancel_task(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tasks/cancel — transition to canceled if not terminal."""
    task_id = params.get("id")
    if not task_id:
        return _jsonrpc_error(None, -32602, "Missing required parameter: id")

    task_dict = WarehouseDB.get_a2a_task(task_id)
    if not task_dict:
        return _jsonrpc_error(None, -32001, f"Task {task_id} not found")

    current_state = TaskState(task_dict["status"])
    if current_state in TERMINAL_STATES:
        return _jsonrpc_error(None, -32003, f"Cannot cancel task in terminal state: {current_state.value}")

    WarehouseDB.update_a2a_task(task_id, status=TaskState.CANCELED.value)
    task_dict = WarehouseDB.get_a2a_task(task_id)
    return _task_to_a2a_response(task_dict)


async def _handle_list_tasks(
    agent_id: int, params: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle tasks/list."""
    context_id = params.get("contextId")
    task_status = params.get("status")
    page = params.get("page", 1)
    page_size = params.get("pageSize", 50)

    tasks, total = WarehouseDB.list_a2a_tasks(
        agent_id=agent_id,
        context_id=context_id,
        status=task_status,
        page=page,
        page_size=page_size,
    )

    return {
        "tasks": [_task_to_a2a_response(t) for t in tasks],
        "total": total,
    }


# ────────────────────── Push notification helper ──────────────────────

def _fire_push_notification(task_dict: Dict) -> None:
    """Fire async push notification (best-effort, non-blocking)."""
    from app.services.a2a_notifications import send_push_notification
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(send_push_notification(
                webhook_url=task_dict["webhook_url"],
                task_id=task_dict["id"],
                status=task_dict["status"],
                webhook_token=task_dict.get("webhook_token"),
                artifacts=task_dict.get("artifacts"),
            ))
    except Exception as e:
        logger.warning("Failed to fire push notification: %s", e)


# ────────────────────── Main JSON-RPC endpoint ──────────────────────

@router.post(
    "/{agent_id}",
    status_code=status.HTTP_200_OK,
    summary="A2A JSON-RPC Endpoint",
    description="Handle A2A protocol JSON-RPC methods: message/send, tasks/get, tasks/cancel, tasks/list",
)
async def a2a_jsonrpc(agent_id: int, rpc: JsonRpcRequest, request: Request) -> Dict[str, Any]:
    """Single A2A JSON-RPC 2.0 dispatch endpoint."""
    agent = WarehouseDB.get_agent(agent_id)
    if not agent:
        return _jsonrpc_error(rpc.id, -32001, f"Agent {agent_id} not found")

    _validate_bearer_token(request, agent)

    params = rpc.params or {}

    method_handlers = {
        "message/send": lambda: _handle_send_message(agent, params),
        "tasks/get": lambda: _handle_get_task(params),
        "tasks/cancel": lambda: _handle_cancel_task(params),
        "tasks/list": lambda: _handle_list_tasks(agent_id, params),
    }

    handler = method_handlers.get(rpc.method)
    if not handler:
        return _jsonrpc_error(rpc.id, -32601, f"Method not found: {rpc.method}")

    result = await handler()

    # If result already looks like an error response, wrap it
    if isinstance(result, dict) and "error" in result:
        return {**result, "id": rpc.id}

    return _jsonrpc_success(rpc.id, result)


# ────────────────────── SSE Streaming (Phase 3) ──────────────────────

@router.post(
    "/{agent_id}/stream",
    status_code=status.HTTP_200_OK,
    summary="A2A Streaming Message",
    description="Send a message and receive SSE stream of task events",
)
async def a2a_stream(agent_id: int, rpc: JsonRpcRequest, request: Request):
    """SSE streaming endpoint for message/stream."""
    agent = WarehouseDB.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    _validate_bearer_token(request, agent)

    params = rpc.params or {}
    msg_data = params.get("message", {})
    message_text = ""
    for part in msg_data.get("parts", []):
        if part.get("text"):
            message_text += part["text"]

    if not message_text:
        raise HTTPException(status_code=400, detail="Message must contain text")

    task_id = str(uuid.uuid4())
    context_id = msg_data.get("contextId") or str(uuid.uuid4())

    async def event_generator():
        # Emit submitted
        WarehouseDB.create_a2a_task(
            task_id=task_id,
            agent_id=agent["id"],
            context_id=context_id,
            status=TaskState.SUBMITTED.value,
            messages=json.dumps([msg_data]),
        )
        yield f"event: task_status\ndata: {json.dumps({'taskId': task_id, 'status': 'submitted'})}\n\n"

        # Emit working
        WarehouseDB.update_a2a_task(task_id, status=TaskState.WORKING.value)
        yield f"event: task_status\ndata: {json.dumps({'taskId': task_id, 'status': 'working', 'stateReason': 'Processing request...'})}\n\n"

        try:
            response_text = await _process_agent_task(agent, message_text)

            # Emit artifact
            artifact_id = str(uuid.uuid4())
            artifact = {
                "artifactId": artifact_id,
                "name": "response",
                "parts": [{"text": response_text}],
            }
            yield f"event: task_artifact\ndata: {json.dumps({'taskId': task_id, 'artifact': artifact})}\n\n"

            # Update DB and emit completed
            response_msg = {
                "messageId": str(uuid.uuid4()),
                "role": "agent",
                "parts": [{"text": response_text}],
                "contextId": context_id,
            }
            WarehouseDB.update_a2a_task(
                task_id,
                status=TaskState.COMPLETED.value,
                messages=json.dumps([msg_data, response_msg]),
                artifacts=json.dumps([artifact]),
            )
            yield f"event: task_status\ndata: {json.dumps({'taskId': task_id, 'status': 'completed'})}\n\n"

        except Exception as e:
            logger.error("Streaming task %s failed: %s", task_id, e, exc_info=True)
            WarehouseDB.update_a2a_task(task_id, status=TaskState.FAILED.value)
            yield f"event: task_status\ndata: {json.dumps({'taskId': task_id, 'status': 'failed', 'stateReason': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get(
    "/{agent_id}/tasks/{task_id}/subscribe",
    status_code=status.HTTP_200_OK,
    summary="Subscribe to Task Updates",
    description="SSE stream for existing task — polls DB and emits events until terminal state",
)
async def a2a_subscribe(agent_id: int, task_id: str, request: Request):
    """Subscribe to task status updates via SSE."""
    agent = WarehouseDB.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    task = WarehouseDB.get_a2a_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    async def event_generator():
        last_status = None
        while True:
            task_dict = WarehouseDB.get_a2a_task(task_id)
            if not task_dict:
                break

            current_status = task_dict["status"]
            if current_status != last_status:
                yield f"event: task_status\ndata: {json.dumps({'taskId': task_id, 'status': current_status})}\n\n"
                last_status = current_status

                # Emit artifacts if terminal
                if TaskState(current_status) in TERMINAL_STATES:
                    if task_dict.get("artifacts"):
                        try:
                            artifacts = json.loads(task_dict["artifacts"])
                            for artifact in artifacts:
                                yield f"event: task_artifact\ndata: {json.dumps({'taskId': task_id, 'artifact': artifact})}\n\n"
                        except (json.JSONDecodeError, TypeError):
                            pass
                    break

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ────────────────────── Webhook Registration (Phase 3) ──────────────────────

class WebhookRegistration(BaseModel):
    url: str
    token: Optional[str] = None


@router.post(
    "/{agent_id}/tasks/{task_id}/webhook",
    status_code=status.HTTP_200_OK,
    summary="Register Webhook",
    description="Register a push-notification webhook for task state transitions",
)
async def register_webhook(
    agent_id: int, task_id: str, webhook: WebhookRegistration, request: Request
) -> Dict[str, Any]:
    """Register webhook URL + token on an A2A task."""
    agent = WarehouseDB.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    _validate_bearer_token(request, agent)

    task = WarehouseDB.get_a2a_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    WarehouseDB.update_a2a_task(
        task_id,
        webhook_url=webhook.url,
        webhook_token=webhook.token,
    )

    return {"status": "registered", "task_id": task_id, "webhook_url": webhook.url}
