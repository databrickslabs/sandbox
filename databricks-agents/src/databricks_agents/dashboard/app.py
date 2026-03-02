"""
FastAPI application for the developer dashboard.

Routes:
  SPA:   GET /           — React SPA (if built) or server-rendered HTML fallback
  API:   GET  /api/agents              — JSON list of agents
         GET  /api/agents/{name}/card  — full agent card
         GET  /api/agents/{name}/lineage    — agent-centric lineage graph
         GET  /api/agents/{name}/governance — UC registration status
         POST /api/agents/{name}/mcp   — MCP JSON-RPC proxy
         POST /api/agents/{name}/chat  — A2A message/send proxy
         POST /api/agents/{name}/chat/stream — SSE streaming A2A proxy
         GET  /api/lineage             — workspace-wide lineage graph
         POST /api/scan                — trigger re-scan
         GET  /health                  — health check
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .governance import GovernanceService
from .scanner import DashboardScanner
from .templates import render_agent_list, render_agent_detail

logger = logging.getLogger(__name__)

# Path to built React SPA assets
STATIC_DIR = Path(__file__).parent / "static"


class ChatRequest(BaseModel):
    message: str
    context_id: Optional[str] = None


def create_dashboard_app(
    scanner: DashboardScanner,
    profile: Optional[str] = None,
    governance: Optional[GovernanceService] = None,
) -> FastAPI:
    """Build and return the dashboard FastAPI app."""
    app = FastAPI(title="databricks-agents dashboard", docs_url=None, redoc_url=None)

    has_spa = (STATIC_DIR / "index.html").is_file()

    # --- JSON API ---------------------------------------------------------

    @app.get("/api/agents")
    async def api_agents():
        agents = scanner.get_agents()
        return [
            {
                "name": a.name,
                "endpoint_url": a.endpoint_url,
                "app_name": a.app_name,
                "description": a.description,
                "capabilities": a.capabilities,
                "protocol_version": a.protocol_version,
            }
            for a in agents
        ]

    @app.get("/api/agents/{name}/card")
    async def api_agent_card(name: str):
        agent = scanner.get_agent_by_name(name)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)

        try:
            card = await scanner.get_agent_card(agent.endpoint_url)
            return card
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=502)

    @app.post("/api/agents/{name}/mcp")
    async def api_mcp_proxy(name: str, request: Request):
        agent = scanner.get_agent_by_name(name)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)

        try:
            payload = await request.json()
            result = await scanner.proxy_mcp(agent.endpoint_url, payload)
            return result
        except Exception as e:
            return JSONResponse(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -1, "message": str(e)}},
                status_code=502,
            )

    @app.post("/api/agents/{name}/chat")
    async def api_chat(name: str, body: ChatRequest):
        """Send an A2A message to an agent and return the response."""
        agent = scanner.get_agent_by_name(name)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)

        try:
            result = await scanner.send_a2a_message(
                agent.endpoint_url, body.message, body.context_id
            )
            return {"result": result}
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=502)

    @app.post("/api/agents/{name}/chat/stream")
    async def api_chat_stream(name: str, body: ChatRequest):
        """Stream an A2A message response as SSE events."""
        from starlette.responses import StreamingResponse

        agent = scanner.get_agent_by_name(name)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)

        import json

        async def event_generator():
            try:
                async for event in scanner.stream_a2a_message(
                    agent.endpoint_url, body.message
                ):
                    yield f"data: {json.dumps(event)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # --- Lineage & Governance API ------------------------------------------

    @app.get("/api/agents/{name}/lineage")
    async def api_agent_lineage(name: str):
        if not governance:
            return JSONResponse({"error": "Governance service not available"}, status_code=503)
        agent = scanner.get_agent_by_name(name)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        try:
            graph = await governance.get_agent_lineage(agent.name)
            return graph.to_dict()
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.get("/api/agents/{name}/governance")
    async def api_agent_governance(name: str):
        if not governance:
            return JSONResponse({"error": "Governance service not available"}, status_code=503)
        agent = scanner.get_agent_by_name(name)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        try:
            status = await governance.get_governance_status(agent.name)
            return status
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.get("/api/lineage")
    async def api_workspace_lineage(warehouse_id: Optional[str] = None):
        if not governance:
            return JSONResponse({"error": "Governance service not available"}, status_code=503)
        try:
            graph = await governance.get_workspace_lineage(warehouse_id=warehouse_id)
            return graph.to_dict()
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.post("/api/uc/register-all")
    async def api_register_all(request: Request):
        if not governance:
            return JSONResponse({"error": "Governance service not available"}, status_code=503)
        body = {}
        try:
            body = await request.json()
        except Exception:
            pass
        schema = body.get("schema", "agents") if isinstance(body, dict) else "agents"
        result = await governance.register_all_agents(schema=schema)
        return result

    @app.post("/api/lineage/observe")
    async def api_observe_trace(request: Request):
        if not governance:
            return JSONResponse({"error": "Governance not available"}, status_code=503)
        body = await request.json()
        agent_name = body.get("agent_name")
        trace = body.get("trace", {})
        if not agent_name:
            return JSONResponse({"error": "agent_name required"}, status_code=400)
        governance.ingest_trace(agent_name, trace)
        return {"ok": True}

    @app.post("/api/scan")
    async def api_scan():
        agents = await scanner.scan()
        if governance:
            governance.invalidate_cache()
        return {
            "count": len(agents),
            "agents": [a.name for a in agents],
            "lineage_refreshed": governance is not None,
        }

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "agents_cached": len(scanner.get_agents()),
            "profile": profile,
        }

    # --- SPA / HTML fallback -----------------------------------------------

    if has_spa:
        # Mount static assets (JS, CSS bundles)
        assets_dir = STATIC_DIR / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{full_path:path}")
        async def spa_catch_all(full_path: str):
            """Serve React SPA index.html for all non-API routes."""
            # Check if it's a direct static file request
            static_file = STATIC_DIR / full_path
            if static_file.is_file() and not full_path.startswith("api/"):
                return FileResponse(str(static_file))
            # Otherwise serve the SPA
            return FileResponse(str(STATIC_DIR / "index.html"))
    else:
        # Fallback: server-rendered HTML pages
        logger.info("No React build found at %s — using server-rendered HTML", STATIC_DIR)

        @app.get("/", response_class=HTMLResponse)
        async def index():
            agents = scanner.get_agents()
            return render_agent_list(agents)

        @app.get("/agent/{name}", response_class=HTMLResponse)
        async def agent_detail(name: str):
            agent = scanner.get_agent_by_name(name)
            if not agent:
                return HTMLResponse("<h1>Agent not found</h1>", status_code=404)

            card = None
            try:
                card = await scanner.get_agent_card(agent.endpoint_url)
            except Exception as e:
                logger.warning("Could not fetch card for %s: %s", name, e)

            return render_agent_detail(agent, card)

    return app
