"""
@app_agent decorator — the API for building discoverable agents on Databricks Apps.

One decorator wires a plain async function into a fully-featured FastAPI app.

Usage:
    from dbx_agent_app import app_agent, AgentRequest, AgentResponse

    @app_agent(
        name="research",
        description="Search expert transcripts",
        capabilities=["research", "search"],
    )
    async def research(request: AgentRequest) -> AgentResponse:
        result = my_graph.invoke(request.messages)
        return AgentResponse.text(result)

    # research.app -> FastAPI with /invocations, /.well-known/agent.json, /health, /api/mcp
    # uvicorn app:research.app
"""

from __future__ import annotations

import inspect
import json
import logging
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Union

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .types import AgentRequest, AgentResponse, InputItem, StreamEvent, UserContext

logger = logging.getLogger(__name__)


def _python_type_to_json_schema(annotation) -> str:
    """Convert a Python type annotation to a JSON Schema type string."""
    if annotation is inspect.Parameter.empty:
        return "string"
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    return type_map.get(annotation, "string")


class AppAgent:
    """
    Wraps a handler function with a FastAPI app and agent platform endpoints.

    Created by the ``@app_agent`` decorator. Provides:

    - ``.app`` — lazily-built FastAPI with /invocations, agent card, health, MCP
    - ``.tool(description=...)`` — decorator to register tools
    - ``__call__()`` — calls handler directly (for testing)
    """

    def __init__(
        self,
        handler: Callable,
        *,
        name: str,
        description: str,
        capabilities: List[str],
        version: str = "1.0.0",
        enable_mcp: bool = True,
    ):
        self._handler = handler
        self._is_async = inspect.iscoroutinefunction(handler)
        self._is_generator = inspect.isasyncgenfunction(handler)

        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.version = version
        self.enable_mcp = enable_mcp

        self._tools: List[Dict[str, Any]] = []
        self._app: Optional[FastAPI] = None

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def tool(self, description: str, parameters: Optional[Dict[str, Any]] = None):
        """
        Decorator to register a function as an agent tool.

        Registered tools appear in the agent card, MCP, and /api/tools/<name>.

        Usage:
            @my_agent.tool(description="Search the database")
            async def search(query: str) -> dict:
                return {...}
        """

        def decorator(func: Callable):
            sig = inspect.signature(func)
            if parameters is None:
                param_schema = {}
                for pname, param in sig.parameters.items():
                    param_schema[pname] = {
                        "type": _python_type_to_json_schema(param.annotation),
                        "required": param.default is inspect.Parameter.empty,
                    }
            else:
                param_schema = parameters

            self._tools.append({
                "name": func.__name__,
                "description": description,
                "parameters": param_schema,
                "function": func,
            })
            return func

        return decorator

    # ------------------------------------------------------------------
    # Direct call (for testing)
    # ------------------------------------------------------------------

    async def __call__(self, request: AgentRequest) -> AgentResponse:
        """Call the handler directly. Useful for testing without HTTP."""
        result = self._handler(request)
        if inspect.isawaitable(result):
            result = await result
        return self._coerce_response(result)

    # ------------------------------------------------------------------
    # FastAPI app (lazy)
    # ------------------------------------------------------------------

    @property
    def app(self) -> FastAPI:
        """Lazily build and return the FastAPI application."""
        if self._app is None:
            self._app = self._build_app()
        return self._app

    def _build_app(self) -> FastAPI:
        fastapi_app = FastAPI()

        self._setup_invocations(fastapi_app)
        self._setup_agent_card(fastapi_app)
        self._setup_health(fastapi_app)
        self._setup_tool_endpoints(fastapi_app)

        if self.enable_mcp and self._tools:
            self._setup_mcp(fastapi_app)

        return fastapi_app

    # ------------------------------------------------------------------
    # Endpoint setup
    # ------------------------------------------------------------------

    def _setup_invocations(self, fastapi_app: FastAPI):
        agent = self

        @fastapi_app.post("/invocations")
        async def invocations(request: Request):
            body = await request.json()
            input_items = body.get("input", [])

            agent_request = AgentRequest(
                input=[InputItem(**item) for item in input_items]
            )

            # Extract on-behalf-of user identity from Databricks Apps headers
            fwd_token = request.headers.get("x-forwarded-access-token")
            fwd_email = request.headers.get("x-forwarded-email")
            fwd_user = request.headers.get("x-forwarded-user")
            if fwd_token or fwd_email or fwd_user:
                agent_request._user_context = UserContext(
                    access_token=fwd_token,
                    email=fwd_email,
                    user=fwd_user,
                )

            if not agent_request.last_user_message:
                return JSONResponse(
                    status_code=400,
                    content={"error": "No user message found in input"},
                )

            # Handle async generator (streaming)
            if agent._is_generator:
                return StreamingResponse(
                    agent._stream_handler(agent_request),
                    media_type="text/event-stream",
                )

            # Non-streaming: call handler and coerce response
            result = agent._handler(agent_request)
            if inspect.isawaitable(result):
                result = await result

            response = agent._coerce_response(result)
            return response.to_wire()

    def _setup_agent_card(self, fastapi_app: FastAPI):
        agent = self

        @fastapi_app.get("/.well-known/agent.json")
        async def agent_card():
            card = {
                "schema_version": "a2a/1.0",
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.capabilities,
                "version": agent.version,
                "endpoints": {
                    "invocations": "/invocations",
                },
                "tools": [
                    {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["parameters"],
                    }
                    for t in agent._tools
                ],
            }
            if agent.enable_mcp and agent._tools:
                card["endpoints"]["mcp"] = "/api/mcp"
            return card

    def _setup_health(self, fastapi_app: FastAPI):
        agent = self

        @fastapi_app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "agent": agent.name,
                "version": agent.version,
            }

    def _setup_tool_endpoints(self, fastapi_app: FastAPI):
        for tool_def in self._tools:
            fastapi_app.post(f"/api/tools/{tool_def['name']}")(tool_def["function"])

    def _setup_mcp(self, fastapi_app: FastAPI):
        try:
            from .helpers import add_mcp_endpoints

            add_mcp_endpoints(fastapi_app, tools=self._tools)
        except ImportError:
            logger.warning("Could not import add_mcp_endpoints — MCP disabled")

    # ------------------------------------------------------------------
    # Response coercion
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_response(result: Any) -> AgentResponse:
        """Coerce handler return value to AgentResponse."""
        if isinstance(result, AgentResponse):
            return result
        if isinstance(result, dict):
            return AgentResponse.from_dict(result)
        if isinstance(result, str):
            return AgentResponse.text(result)
        return AgentResponse.text(str(result))

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    async def _stream_handler(self, request: AgentRequest) -> AsyncGenerator[str, None]:
        """Consume an async generator handler and yield SSE events."""
        async for event in self._handler(request):
            if isinstance(event, StreamEvent):
                yield event.to_sse()
            elif isinstance(event, str):
                yield StreamEvent.text_delta(event).to_sse()
            else:
                yield StreamEvent.text_delta(str(event)).to_sse()



def app_agent(
    name: str,
    description: str,
    capabilities: List[str],
    *,
    version: str = "1.0.0",
    enable_mcp: bool = True,
) -> Callable[[Callable], AppAgent]:
    """
    Decorator to turn an async function into a discoverable Databricks Apps agent.

    The decorated function receives an ``AgentRequest`` and returns one of:
    - ``AgentResponse`` (direct)
    - ``str`` (auto-wrapped via ``AgentResponse.text()``)
    - ``dict`` (auto-wrapped via ``AgentResponse.from_dict()``)
    - ``AsyncGenerator[StreamEvent | str, None]`` (streaming SSE)

    Returns an ``AppAgent`` instance. Access the FastAPI app via ``.app``.

    Agent governance is handled via uc_securable resources declared in app.yaml
    or agents.yaml — no runtime UC registration needed.

    Example:
        @app_agent(name="hello", description="Greeter", capabilities=["chat"])
        async def hello(request: AgentRequest) -> AgentResponse:
            return AgentResponse.text(f"Hello! You said: {request.last_user_message}")

        # uvicorn app:hello.app
    """

    def decorator(func: Callable) -> AppAgent:
        return AppAgent(
            func,
            name=name,
            description=description,
            capabilities=capabilities,
            version=version,
            enable_mcp=enable_mcp,
        )

    return decorator
