"""
Static file serving for React frontend.
Serves the built React app from the dist directory.
"""
from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

router = APIRouter()

# Path to the React build directory
STATIC_DIR = Path(__file__).parent.parent / "webapp_dist"

def setup_static_files(app):
    """
    Mount static files and setup catch-all route for React Router.
    Call this from main.py after setting up all API routes.
    """
    # Check if webapp_dist exists
    if STATIC_DIR.exists():
        # Mount static assets (JS, CSS, images)
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

        # Catch-all route for React Router - must be last
        @app.get("/{full_path:path}")
        async def serve_react(full_path: str):
            """
            Serve index.html for all non-API routes.
            This allows React Router to handle client-side routing.
            """
            # If it's an API route, let it pass through to API handlers
            if full_path.startswith("api/") or full_path == "health" or full_path == "docs" or full_path == "openapi.json":
                return None  # Let FastAPI handle these

            # For root or any other path, serve index.html
            index_path = STATIC_DIR / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            else:
                return HTMLResponse(
                    content="<h1>Frontend not built</h1><p>Run: cd webapp && npm run build && cp -r dist ../registry-api/webapp_dist</p>",
                    status_code=404
                )
    else:
        # Webapp not built yet, show instructions
        @app.get("/")
        async def root():
            return HTMLResponse(
                content="""
                <h1>Multi-Agent Registry API</h1>
                <p>API is running! Frontend not deployed yet.</p>
                <ul>
                    <li><a href="/docs">API Documentation</a></li>
                    <li><a href="/health">Health Check</a></li>
                </ul>
                <h2>To deploy frontend:</h2>
                <pre>
cd webapp
npm run build
cp -r dist ../registry-api/webapp_dist
                </pre>
                """,
                status_code=200
            )
