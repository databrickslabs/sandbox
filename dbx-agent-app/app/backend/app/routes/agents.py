"""
CRUD endpoints for Agents + A2A Agent Card.
"""

import json
import logging
from fastapi import APIRouter, HTTPException, Request, status, Query
import math

logger = logging.getLogger(__name__)

from typing import Dict, Any, List

from app.db_adapter import WarehouseDB
from app.config import settings
from app.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentCardResponse,
    A2ACapabilities,
    A2ASkill,
)
from app.schemas.common import PaginatedResponse
from app.services.audit import record_audit

router = APIRouter(prefix="/agents", tags=["Agents"])


def _safe_agent_response(agent_dict: dict) -> AgentResponse:
    """Build AgentResponse, stripping auth_token from output."""
    filtered = {k: v for k, v in agent_dict.items() if k != "auth_token"}
    return AgentResponse(**filtered)


@router.get(
    "",
    response_model=PaginatedResponse[AgentResponse],
    status_code=status.HTTP_200_OK,
    summary="List Agents",
    description="List all registered agents with pagination",
)
def list_agents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[AgentResponse]:
    """List all agents with pagination."""
    agents, total = WarehouseDB.list_agents(page=page, page_size=page_size)
    total = int(total) if total else 0  # Convert string to int from warehouse
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse(
        items=[_safe_agent_response(agent) for agent in agents],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Agent",
    description="Register a new agent",
)
def create_agent(agent_data: AgentCreate, request: Request) -> AgentResponse:
    """Create a new agent."""
    try:
        agent = WarehouseDB.create_agent(
            name=agent_data.name,
            description=agent_data.description,
            capabilities=agent_data.capabilities,
            status=agent_data.status,
            collection_id=agent_data.collection_id,
            endpoint_url=agent_data.endpoint_url,
            auth_token=agent_data.auth_token,
            a2a_capabilities=agent_data.a2a_capabilities,
            skills=agent_data.skills,
            protocol_version=agent_data.protocol_version,
            system_prompt=agent_data.system_prompt,
        )
        record_audit(request, "create", "agent", str(agent["id"]), agent["name"])
        return _safe_agent_response(agent)
    except Exception as e:
        logger.error("Failed to create agent: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to create agent",
        )


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Agent",
    description="Get a specific agent by ID",
)
def get_agent(agent_id: int) -> AgentResponse:
    """Get a specific agent by ID."""
    agent = WarehouseDB.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found",
        )
    return _safe_agent_response(agent)


@router.put(
    "/{agent_id}",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Agent",
    description="Update an existing agent",
)
def update_agent(agent_id: int, agent_data: AgentUpdate, request: Request) -> AgentResponse:
    """Update an existing agent."""
    existing = WarehouseDB.get_agent(agent_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found",
        )

    update_dict = agent_data.model_dump(exclude_unset=True)
    agent = WarehouseDB.update_agent(agent_id, **update_dict)
    record_audit(request, "update", "agent", str(agent_id), agent["name"])
    return _safe_agent_response(agent)


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Agent",
    description="Delete an agent from the registry",
)
def delete_agent(agent_id: int, request: Request) -> None:
    """Delete an agent."""
    existing = WarehouseDB.get_agent(agent_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found",
        )
    WarehouseDB.delete_agent(agent_id)
    record_audit(request, "delete", "agent", str(agent_id), existing["name"])


@router.get(
    "/{agent_id}/card",
    response_model=AgentCardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Agent Card",
    description="Get A2A-compliant Agent Card for discovery",
)
def get_agent_card(agent_id: int, request: Request) -> AgentCardResponse:
    """Generate A2A-compliant Agent Card from agent model data."""
    agent = WarehouseDB.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found",
        )

    # Build A2A URL: prefer agent's own endpoint, fallback to registry A2A endpoint
    base_url = settings.a2a_base_url or str(request.base_url).rstrip("/")
    a2a_url = agent.get("endpoint_url") or f"{base_url}/api/a2a/{agent_id}"

    # Parse capabilities JSON
    caps = A2ACapabilities()
    if agent.get("a2a_capabilities"):
        try:
            caps_data = json.loads(agent["a2a_capabilities"])
            caps = A2ACapabilities(**caps_data)
        except (json.JSONDecodeError, TypeError):
            pass

    # Parse skills JSON
    skill_list = []
    if agent.get("skills"):
        try:
            skills_data = json.loads(agent["skills"])
            skill_list = [A2ASkill(**s) for s in skills_data]
        except (json.JSONDecodeError, TypeError):
            pass

    # Security schemes: present if agent has auth_token
    security_schemes = None
    security = None
    if agent.get("auth_token"):
        security_schemes = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
            }
        }
        security = [{"bearerAuth": []}]

    return AgentCardResponse(
        name=agent["name"],
        description=agent.get("description"),
        version=settings.api_version,
        protocolVersion=agent.get("protocol_version") or settings.a2a_protocol_version,
        url=a2a_url,
        capabilities=caps,
        skills=skill_list,
        securitySchemes=security_schemes,
        security=security,
    )


@router.get(
    "/{agent_id}/analytics",
    status_code=status.HTTP_200_OK,
    summary="Get Agent Analytics",
    description="Get performance analytics for an agent (summary stats + recent history)",
)
def get_agent_analytics(
    agent_id: int,
    limit: int = Query(20, ge=1, le=100, description="Max recent entries to return"),
) -> Dict[str, Any]:
    """Get summary stats and recent analytics history for an agent."""
    agent = WarehouseDB.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found",
        )

    summary = WarehouseDB.get_agent_summary_stats(agent_id)
    recent = WarehouseDB.list_agent_analytics(agent_id, limit=limit)

    return {
        "agent_id": agent_id,
        "agent_name": agent["name"],
        "summary": summary,
        "recent": recent,
    }
