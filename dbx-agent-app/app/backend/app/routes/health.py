"""
Health check endpoints.
"""

import os
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.schemas.common import HealthResponse, ReadyResponse
from app.config import settings

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Check if the API is running",
)
def health_check() -> HealthResponse:
    """
    Simple health check endpoint that always returns 200 if the API is running.
    """
    return HealthResponse(
        status="healthy",
        version=settings.api_version,
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness Check",
    description="Check if the API is ready to accept requests (database connection)",
)
def readiness_check(db: Session = Depends(get_db)) -> ReadyResponse:
    """
    Readiness check that verifies database connectivity.
    Returns 200 if ready, 503 if not ready.
    """
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        return ReadyResponse(
            ready=True,
            database="connected",
        )
    except Exception as e:
        return ReadyResponse(
            ready=False,
            database=f"error: {str(e)}",
        )


@router.get(
    "/auth-test",
    status_code=status.HTTP_200_OK,
    summary="Test Authentication",
    description="Test if authentication is working (requires auth)",
)
def auth_test() -> dict:
    """
    Test endpoint to verify authentication is working.
    Returns 200 if authenticated, 401 if not.
    """
    return {
        "authenticated": True,
        "message": "Authentication successful"
    }


@router.get(
    "/debug-db",
    status_code=status.HTTP_200_OK,
    summary="Debug Database Info",
    description="Show database file location and record counts (debug only)",
)
def debug_database(db: Session = Depends(get_db)) -> dict:
    """
    Debug endpoint to show database information.
    Shows database URL, file existence, and record counts.
    """
    try:
        # Get database URL
        db_url = str(db.bind.url)

        # Extract file path from SQLite URL
        db_file = None
        if db_url.startswith("sqlite:///"):
            db_file = db_url.replace("sqlite:///", "")
            db_file_exists = os.path.exists(db_file)
            db_file_size = os.path.getsize(db_file) if db_file_exists else 0
        else:
            db_file_exists = None
            db_file_size = None

        # Get record counts
        apps_count = db.execute(text("SELECT COUNT(*) FROM apps")).scalar()
        mcp_servers_count = db.execute(text("SELECT COUNT(*) FROM mcp_servers")).scalar()
        tools_count = db.execute(text("SELECT COUNT(*) FROM tools")).scalar()
        agents_count = db.execute(text("SELECT COUNT(*) FROM agents")).scalar()

        return {
            "database_url": db_url,
            "database_file": db_file,
            "file_exists": db_file_exists,
            "file_size_bytes": db_file_size,
            "record_counts": {
                "apps": apps_count,
                "mcp_servers": mcp_servers_count,
                "tools": tools_count,
                "agents": agents_count,
            },
            "cwd": os.getcwd(),
            "env_database_url": os.environ.get("DATABASE_URL", "not set"),
        }
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__,
        }
