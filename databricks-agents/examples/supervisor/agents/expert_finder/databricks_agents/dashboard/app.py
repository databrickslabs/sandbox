"""
FastAPI application for the developer dashboard.

Routes:
  HTML:  GET /           — agent list page
         GET /agent/{name} — agent detail page
  API:   GET  /api/agents          — JSON list of agents
         GET  /api/agents/{name}/card — full agent card
         POST /api/agents/{name}/mcp  — MCP JSON-RPC proxy
         POST /api/scan             — trigger re-scan
         GET  /health               — health check
"""

import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .scanner import DashboardScanner
from .templates import render_agent_list, render_agent_detail

logger = logging.getLogger(__name__)


def create_dashboard_app(
    scanner: DashboardScanner,
    profile: Optional[str] = None,
) -> FastAPI:
    """Build and return the dashboard FastAPI app."""
    app = FastAPI(title="databricks-agents dashboard", docs_url=None, redoc_url=None)

    # --- HTML pages -------------------------------------------------------

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

    @app.post("/api/scan")
    async def api_scan():
        agents = await scanner.scan()
        return {"count": len(agents), "agents": [a.name for a in agents]}

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "agents_cached": len(scanner.get_agents()),
            "profile": profile,
        }

    return app
