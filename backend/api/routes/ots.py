"""
OT (Orden de Trabajo) API routes.
Handles CRUD operations and agent-triggered actions for work orders.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db, get_settings
from backend.api.schemas import (
    AssignCuadrillaRequest,
    OTListResponse,
    OTResponse,
    UpdateStatusRequest,
)
from backend.config import Settings
from backend.models import Asignacion, OrdenTrabajo
from backend.utils import validate_status_transition

router = APIRouter(prefix="/ots", tags=["OTs"])


@router.get("", response_model=OTListResponse)
async def get_ots(
    status: Optional[str] = Query(None, description="Filter by OT status"),
    project_type: Optional[str] = Query(None, description="Filter by project type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> OTListResponse:
    """
    Get list of OTs with optional filters.

    Args:
        status: Optional status filter
        project_type: Optional project type filter
        skip: Number of records to skip
        limit: Number of records to return
        db: Database session

    Returns:
        Paginated list of OTs
    """
    # TODO: Implement database query with filters
    return OTListResponse(items=[], total=0, page=1, page_size=limit)


@router.get("/{ot_id}", response_model=OTResponse)
async def get_ot(
    ot_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> OTResponse:
    """
    Get single OT with related data.

    Args:
        ot_id: OT ID
        db: Database session

    Returns:
        OT details with related cliente, login, assignment, and tasks
    """
    # TODO: Implement database query with relationships
    raise HTTPException(status_code=404, detail="OT not found")


@router.post("/ingest")
async def ingest_ots(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Ingest new OTs from TELCOS API using OTSAgent.

    Args:
        db: Database session
        settings: Application settings

    Returns:
        Summary dict with ingestion results
    """
    # TODO: Implement OTSAgent.ingest_ots() call
    return {
        "total_ingested": 0,
        "successful": 0,
        "errors": 0,
        "geo_errors": 0,
    }


@router.patch("/{ot_id}/status", response_model=OTResponse)
async def update_ot_status(
    ot_id: UUID,
    request: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
) -> OTResponse:
    """
    Update OT status with validation.

    Args:
        ot_id: OT ID
        request: Update request with new_status and optional reason
        db: Database session

    Returns:
        Updated OT
    """
    # TODO: Implement status transition validation and update
    raise HTTPException(status_code=404, detail="OT not found")


@router.post("/{ot_id}/assign", response_model=OTResponse)
async def assign_ot_to_crew(
    ot_id: UUID,
    request: AssignCuadrillaRequest,
    db: AsyncSession = Depends(get_db),
) -> OTResponse:
    """
    Assign OT to crew using PlanificacionAgent.

    Args:
        ot_id: OT ID
        request: Assignment request with cuadrilla_id
        db: Database session

    Returns:
        Updated OT with new assignment
    """
    # TODO: Implement PlanificacionAgent assignment logic
    raise HTTPException(status_code=404, detail="OT not found")

