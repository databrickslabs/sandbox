"""
Agent Chat endpoints for querying Databricks serving endpoints.

Provides a chat interface that proxies queries to pre-built Databricks
serving endpoints and enriches responses with routing, slot filling,
and pipeline metadata.
"""

import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas.agent_chat import (
    AgentChatRequest,
    AgentChatResponse,
    AgentChatEndpoint,
    AgentChatEndpointsResponse,
)
from app.services.agent_chat import create_agent_chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-chat", tags=["Agent Chat"])


@router.post("/query", response_model=AgentChatResponse)
async def query_endpoint(request: AgentChatRequest) -> AgentChatResponse:
    """
    Query a Databricks serving endpoint.

    Sends the message to the specified endpoint and returns the response
    enriched with routing, slot filling, and pipeline metadata.
    """
    try:
        service = create_agent_chat_service()
        return await service.query_endpoint(request.endpoint_name, request.message)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Agent chat query failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent chat query failed: {str(e)}",
        )


@router.get("/endpoints", response_model=AgentChatEndpointsResponse)
async def get_endpoints() -> AgentChatEndpointsResponse:
    """
    List available agent chat endpoints.

    Returns the hardcoded demo endpoint list. Can be enhanced later
    to pull from the database or workspace.
    """
    endpoints = [
        AgentChatEndpoint(
            name="guidepoint_research",
            displayName="Research Agent",
            description="Search and analyze expert interview transcripts",
            type="research",
        ),
        AgentChatEndpoint(
            name="guidepoint_supervisor",
            displayName="Supervisor Agent",
            description="Routes queries to specialized sub-agents",
            type="supervisor",
        ),
        AgentChatEndpoint(
            name="agents_users-roberto_sanchez-agent",
            displayName="Roberto's Routing Agent",
            description="Fast routing assistant for services data",
            type="research",
        ),
    ]

    return AgentChatEndpointsResponse(
        endpoints=endpoints,
        count=len(endpoints),
    )
