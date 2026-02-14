"""
Agent API routes.
Main endpoint for chat sidebar and agent action logging.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db
from backend.api.schemas import ChatRequest, ChatResponse
from backend.models import LogAgente

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Main chat endpoint for agent interaction.
    Triggers run_agent_workflow() from LangGraph orchestrator.

    Args:
        request: User message
        db: Database session

    Returns:
        Agent response
    """
    # TODO: Implement run_agent_workflow(request.message)
    return ChatResponse(
        message="Agent workflow not implemented",
        agent_used=None,
        success=False,
        error="Agent system not yet initialized",
    )


@router.get("/logs")
async def get_agent_logs(
    agente_name: Optional[str] = Query(None),
    ot_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get agent action logs with optional filters.

    Args:
        agente_name: Filter by agent name
        ot_id: Filter by OT ID
        skip: Number of records to skip
        limit: Number of records to return
        db: Database session

    Returns:
        List of agent action logs
    """
    # TODO: Implement log retrieval with filters
    return {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": limit,
    }

