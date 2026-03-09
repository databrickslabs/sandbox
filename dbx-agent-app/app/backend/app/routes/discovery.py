"""
Discovery endpoint for refreshing MCP server catalog and agents.
"""

import asyncio
import logging
from fastapi import APIRouter, Body, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models.discovery_state import DiscoveryState
from app.schemas.discovery import (
    DiscoveryRefreshRequest,
    DiscoveryRefreshResponse,
    DiscoveryStatusResponse,
    WorkspaceProfileResponse,
    WorkspaceProfilesResponse,
)
from app.services.discovery import DiscoveryService
from app.services.workspace_profiles import (
    discover_workspace_profiles,
    DEFAULT_CONFIG_PATH,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["Discovery"])


def _get_or_create_state(db: Session) -> DiscoveryState:
    """Get the singleton discovery state row, creating it if needed."""
    state = db.query(DiscoveryState).filter(DiscoveryState.id == 1).first()
    if not state:
        state = DiscoveryState(id=1, is_running=False)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


@router.get(
    "/workspaces",
    response_model=WorkspaceProfilesResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover Workspace Profiles",
    description="Parse ~/.databrickscfg and validate auth for each workspace profile",
)
async def get_workspace_profiles() -> WorkspaceProfilesResponse:
    """
    Discover Databricks workspace profiles from CLI config.

    Parses ~/.databrickscfg, validates authentication for each workspace
    profile concurrently, and returns status for each.
    """
    try:
        profiles = await discover_workspace_profiles()
        profile_responses = [
            WorkspaceProfileResponse(
                name=p.name,
                host=p.host,
                auth_type=p.auth_type,
                is_account_profile=p.is_account_profile,
                auth_valid=p.auth_valid,
                auth_error=p.auth_error,
                username=p.username,
            )
            for p in profiles
        ]
        return WorkspaceProfilesResponse(
            profiles=profile_responses,
            config_path=DEFAULT_CONFIG_PATH,
            total=len(profile_responses),
            valid=sum(1 for p in profile_responses if p.auth_valid),
        )
    except Exception as e:
        logger.error("Failed to discover workspace profiles: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover workspace profiles: {e}",
        )


@router.post(
    "/refresh",
    response_model=DiscoveryRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh MCP Catalog",
    description="Discover MCP servers and tools from custom URLs, workspace, or catalog",
)
async def refresh_discovery(
    request: DiscoveryRefreshRequest = Body(default=None),
    db: Session = Depends(get_db),
) -> DiscoveryRefreshResponse:
    """
    Refresh the MCP catalog by discovering servers and tools.

    This endpoint:
    1. Discovers MCP servers from provided URLs (and optionally workspace/catalog)
    2. Queries each server for available tools
    3. Upserts discovered data into the registry database
    4. Returns summary of discovered/updated entities
    """
    # Default to workspace discovery when no body provided
    if request is None:
        request = DiscoveryRefreshRequest(discover_workspace=True)
    elif not request.server_urls and not request.discover_workspace and not request.discover_catalog:
        # Explicit request with no sources specified — reject
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one discovery source must be specified",
        )

    state = _get_or_create_state(db)

    # Check if discovery is already running
    if state.is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Discovery is already running. Use GET /discovery/status to check progress.",
        )

    # Mark as running
    state.is_running = True
    db.commit()

    try:
        # Create discovery service
        service = DiscoveryService()

        # Convert Pydantic HttpUrl to string
        server_urls = [str(url) for url in request.server_urls]

        # Run MCP discovery and agent discovery in parallel
        parallel_tasks = [
            service.discover_all(
                custom_urls=server_urls if server_urls else None,
                profile=request.databricks_profile,
            )
        ]

        run_agent_discovery = request.discover_agents or request.discover_workspace
        if run_agent_discovery:
            parallel_tasks.append(
                service.discover_agents_all(profile=request.databricks_profile)
            )

        gather_results = await asyncio.gather(*parallel_tasks)

        discovery_result = gather_results[0]
        agent_result = gather_results[1] if run_agent_discovery else None

        # Capture app count before upsert clears it
        apps_discovered = len(getattr(service, "_pending_apps", []))

        # Upsert MCP results into database
        upsert_result = service.upsert_discovery_results(discovery_result)

        # Upsert agent results into database
        agent_upsert = None
        if agent_result:
            agent_upsert = service.upsert_agent_discovery_results(agent_result)

        # Merge errors from both discovery sources
        all_errors = list(discovery_result.errors)
        if agent_result:
            all_errors.extend(agent_result.errors)

        # Determine status
        has_results = (
            discovery_result.servers_discovered > 0
            or (agent_result and len(agent_result.agents) > 0)
        )
        if all_errors:
            if has_results:
                result_status = "partial"
                message = f"Discovery completed with {len(all_errors)} errors"
            else:
                result_status = "failed"
                message = "Discovery failed: all sources unreachable"
        else:
            result_status = "success"
            message = "Discovery completed successfully"

        # Update state
        state.is_running = False
        state.last_run_timestamp = datetime.now(timezone.utc).isoformat()
        state.last_run_status = result_status
        state.last_run_message = message
        db.commit()

        return DiscoveryRefreshResponse(
            status=result_status,
            message=message,
            apps_discovered=apps_discovered,
            servers_discovered=discovery_result.servers_discovered,
            tools_discovered=discovery_result.tools_discovered,
            new_servers=upsert_result.new_servers,
            updated_servers=upsert_result.updated_servers,
            new_tools=upsert_result.new_tools,
            updated_tools=upsert_result.updated_tools,
            agents_discovered=len(agent_result.agents) if agent_result else 0,
            new_agents=agent_upsert.new_agents if agent_upsert else 0,
            updated_agents=agent_upsert.updated_agents if agent_upsert else 0,
            errors=all_errors,
        )

    except Exception as e:
        # Ensure state is cleaned up on failure
        state.is_running = False
        state.last_run_timestamp = datetime.now(timezone.utc).isoformat()
        state.last_run_status = "failed"
        state.last_run_message = f"Discovery failed: {type(e).__name__}"
        db.commit()
        logger.error("Discovery failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Discovery failed",
        )


@router.get(
    "/status",
    response_model=DiscoveryStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Discovery Status",
    description="Check if discovery is running and view last run results",
)
def get_discovery_status(
    db: Session = Depends(get_db),
) -> DiscoveryStatusResponse:
    """
    Get the current status of the discovery process.

    Returns:
        DiscoveryStatusResponse with current status and last run info
    """
    state = _get_or_create_state(db)
    return DiscoveryStatusResponse(
        is_running=state.is_running,
        last_run_timestamp=state.last_run_timestamp,
        last_run_status=state.last_run_status,
        last_run_message=state.last_run_message,
    )
