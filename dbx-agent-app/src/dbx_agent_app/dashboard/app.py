"""
FastAPI application for the developer dashboard.

Routes:
  SPA:   GET /           — React SPA (if built) or server-rendered HTML fallback
  API:   GET  /api/agents              — JSON list of agents
         GET  /api/agents/{name}/card  — full agent card
         POST /api/agents/{name}/test  — call agent via /invocations
         POST /api/agents/{name}/evaluate — run eval bridge against agent
         GET  /api/agents/{name}/analytics — invocation analytics summary
         GET  /api/agents/{name}/lineage    — agent-centric lineage graph
         GET  /api/agents/{name}/governance — app governance status + declared resources
         POST /api/agents/{name}/mcp   — MCP JSON-RPC proxy
         POST /api/agents/{name}/chat  — A2A message/send proxy (A2A -> /invocations -> MCP)
         POST /api/agents/{name}/chat/stream — SSE streaming A2A proxy
         GET  /api/lineage             — workspace-wide lineage graph
         POST /api/scan                — trigger re-scan
         GET  /health                  — health check
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .analytics import AnalyticsTracker
from .governance import GovernanceService
from .scanner import DashboardScanner
from .system_builder import SystemBuilderService, SystemCreate, SystemUpdate, DeployProgress
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
    system_builder: Optional[SystemBuilderService] = None,
    auto_scan_interval: int = 60,
) -> FastAPI:
    """Build and return the dashboard FastAPI app.

    Args:
        scanner: DashboardScanner for workspace discovery
        profile: Databricks CLI profile name
        governance: Optional GovernanceService for lineage/UC
        auto_scan_interval: Seconds between background scans (0 to disable)
    """
    async def _background_scan():
        """Periodically re-scan workspace for agents."""
        while True:
            await asyncio.sleep(auto_scan_interval)
            try:
                agents = await scanner.scan()
                logger.info("Background scan found %d agent(s)", len(agents))
            except Exception as e:
                logger.warning("Background scan failed: %s", e)

    @asynccontextmanager
    async def lifespan(app):
        # Initial scan on startup
        try:
            agents = await scanner.scan()
            logger.info("Startup scan found %d agent(s)", len(agents))
        except Exception as e:
            logger.warning("Startup scan failed: %s", e)

        # Start background scan task if interval > 0
        bg_task = None
        if auto_scan_interval > 0:
            bg_task = asyncio.create_task(_background_scan())
            logger.info("Background scan started (every %ds)", auto_scan_interval)

        yield

        if bg_task:
            bg_task.cancel()
            try:
                await bg_task
            except asyncio.CancelledError:
                pass

    app = FastAPI(
        title="Agent Platform",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )

    analytics = AnalyticsTracker()

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

    @app.post("/api/agents/{name}/test")
    async def api_test_agent(name: str, body: ChatRequest):
        """Test an agent via the /invocations protocol (Databricks standard)."""
        agent = scanner.get_agent_by_name(name)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)

        t0 = time.monotonic()
        try:
            result = await scanner.call_invocations(agent.endpoint_url, body.message)
            latency = int((time.monotonic() - t0) * 1000)
            analytics.record(name, success=True, latency_ms=latency, source="test")
            if governance and isinstance(result, dict):
                trace = result.get("_trace", {})
                if trace:
                    try:
                        governance.ingest_trace(name, trace)
                    except Exception:
                        pass
            return {"result": result}
        except Exception as e:
            latency = int((time.monotonic() - t0) * 1000)
            analytics.record(name, success=False, latency_ms=latency, source="test", error=str(e))
            return JSONResponse({"error": str(e)}, status_code=502)

    @app.post("/api/agents/{name}/chat")
    async def api_chat(name: str, body: ChatRequest):
        """Send an A2A message to an agent and return the response."""
        agent = scanner.get_agent_by_name(name)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)

        t0 = time.monotonic()
        try:
            result = await scanner.send_a2a_message(
                agent.endpoint_url, body.message, body.context_id
            )
            latency = int((time.monotonic() - t0) * 1000)
            analytics.record(name, success=True, latency_ms=latency, source="chat")
            # Auto-ingest trace for runtime lineage
            if governance and isinstance(result, dict):
                trace = result.get("_trace", {})
                if trace:
                    try:
                        governance.ingest_trace(name, trace)
                    except Exception:
                        pass  # best-effort
            return {"result": result}
        except Exception as e:
            latency = int((time.monotonic() - t0) * 1000)
            analytics.record(name, success=False, latency_ms=latency, source="chat", error=str(e))
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

    # --- Analytics & Evaluation API ----------------------------------------

    @app.get("/api/agents/{name}/analytics")
    async def api_agent_analytics(name: str):
        """Return invocation analytics summary for an agent."""
        return analytics.get_summary(name)

    @app.post("/api/agents/{name}/evaluate")
    async def api_evaluate_agent(name: str, request: Request):
        """Run eval bridge — send messages to agent and return structured result."""
        agent = scanner.get_agent_by_name(name)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        if not agent.endpoint_url:
            return JSONResponse({"error": "Agent has no endpoint URL"}, status_code=400)

        body = await request.json()
        messages = body.get("messages", [])
        if not messages:
            return JSONResponse({"error": "messages required"}, status_code=400)

        from dbx_agent_app.bridge.eval import app_predict_fn

        # Get auth token from scanner's workspace client if available
        token = None
        try:
            ws = scanner._discovery._w if hasattr(scanner, "_discovery") else None
            if ws:
                auth = ws.config.authenticate()
                if callable(auth):
                    headers = auth()
                    if headers:
                        token = dict(headers).get("Authorization", "").replace("Bearer ", "")
        except Exception:
            pass

        t0 = time.monotonic()
        try:
            predict = app_predict_fn(agent.endpoint_url, token=token)
            result = predict(messages=messages)
            latency = int((time.monotonic() - t0) * 1000)
            analytics.record(name, success=True, latency_ms=latency, source="evaluate")
            return result
        except Exception as e:
            latency = int((time.monotonic() - t0) * 1000)
            analytics.record(name, success=False, latency_ms=latency, source="evaluate", error=str(e))
            return JSONResponse({"error": str(e)}, status_code=502)

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

    # --- System Builder API -----------------------------------------------

    @app.get("/api/systems")
    async def api_list_systems():
        if not system_builder:
            return JSONResponse({"error": "System builder not available"}, status_code=503)
        return [s.model_dump() for s in system_builder.list_systems()]

    @app.post("/api/systems")
    async def api_create_system(request: Request):
        if not system_builder:
            return JSONResponse({"error": "System builder not available"}, status_code=503)
        body = await request.json()
        try:
            data = SystemCreate(**body)
            defn = system_builder.create_system(data)
            return defn.model_dump()
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    @app.get("/api/systems/{system_id}")
    async def api_get_system(system_id: str):
        if not system_builder:
            return JSONResponse({"error": "System builder not available"}, status_code=503)
        defn = system_builder.get_system(system_id)
        if not defn:
            return JSONResponse({"error": "System not found"}, status_code=404)
        return defn.model_dump()

    @app.put("/api/systems/{system_id}")
    async def api_update_system(system_id: str, request: Request):
        if not system_builder:
            return JSONResponse({"error": "System builder not available"}, status_code=503)
        body = await request.json()
        try:
            data = SystemUpdate(**body)
            defn = system_builder.update_system(system_id, data)
            if not defn:
                return JSONResponse({"error": "System not found"}, status_code=404)
            return defn.model_dump()
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    @app.delete("/api/systems/{system_id}")
    async def api_delete_system(system_id: str):
        if not system_builder:
            return JSONResponse({"error": "System builder not available"}, status_code=503)
        if system_builder.delete_system(system_id):
            return {"ok": True}
        return JSONResponse({"error": "System not found"}, status_code=404)

    @app.post("/api/systems/{system_id}/deploy")
    async def api_deploy_system(system_id: str, request: Request):
        if not system_builder:
            return JSONResponse({"error": "System builder not available"}, status_code=503)
        body = {}
        try:
            body = await request.json()
        except Exception:
            pass
        # Async mode: start background deploy and return immediately
        if isinstance(body, dict) and body.get("async"):
            progress = system_builder.start_deploy(system_id)
            return progress.model_dump()
        # Sync mode (legacy): wait for full result
        result = await system_builder.deploy_system(system_id)
        return result.model_dump()

    @app.get("/api/systems/{system_id}/deploy/status")
    async def api_deploy_status(system_id: str):
        if not system_builder:
            return JSONResponse({"error": "System builder not available"}, status_code=503)
        progress = system_builder.get_deploy_status(system_id)
        if not progress:
            return JSONResponse({"error": "No active deploy"}, status_code=404)
        return progress.model_dump()

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
