"""
OT (Orden de Trabajo) API routes for the PEI Platform.
Provides endpoints for OT management, status updates, and agent invocation.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.models import OT
from backend.models.ot import OTStatus, ProjectType
from backend.schemas import OTResponse, OTStatusUpdate
from backend.utils.business_rules import validate_project_completion, can_assign_to_cuadrilla
from backend.config import get_settings
from backend.services.telcos_service import TelcosService

# Note: PEIGraphRunner will be imported after agents are created
# from backend.agents.graph_runner import PEIGraphRunner

router = APIRouter(prefix="/api/ots", tags=["ots"])


@router.get("", response_model=List[OTResponse])
async def list_ots(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by OT status"),
    project_type: Optional[str] = Query(None, description="Filter by project type"),
    cuadrilla_id: Optional[int] = Query(None, description="Filter by assigned cuadrilla"),
    geo_error: Optional[bool] = Query(None, description="Filter by geo error flag"),
) -> List[OTResponse]:
    """
    List all OTs with optional filtering.

    Query Parameters:
        - status: Filter by OT status (PREPLANIFICADA, PLANIFICADA, ASIGNADO_TAREA, DETENIDA, ANULADA, FINALIZADA)
        - project_type: Filter by project type (PUBLICO, PRIVADO, TERCERIZADO)
        - cuadrilla_id: Filter by assigned cuadrilla ID
        - geo_error: Filter by geo error flag (true/false)

    Returns:
        List of OTResponse objects matching the filters
    """
    query = db.query(OT)

    # Apply filters if provided
    if status:
        try:
            query = query.filter(OT.status == OTStatus[status.upper()])
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if project_type:
        try:
            query = query.filter(OT.project_type == ProjectType[project_type.upper()])
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid project type: {project_type}")

    if cuadrilla_id is not None:
        query = query.filter(OT.cuadrilla_id == cuadrilla_id)

    if geo_error is not None:
        query = query.filter(OT.geo_error == geo_error)

    ots = query.all()
    return ots


@router.get("/{ot_id}", response_model=OTResponse)
async def get_ot(ot_id: int, db: Session = Depends(get_db)) -> OTResponse:
    """
    Get a single OT by ID.

    Path Parameters:
        - ot_id: ID of the OT to retrieve

    Returns:
        OTResponse object if found

    Raises:
        404: OT not found
    """
    ot = db.query(OT).filter(OT.id == ot_id).first()
    if not ot:
        raise HTTPException(status_code=404, detail=f"OT with id {ot_id} not found")
    return ot


@router.post("/sync", response_model=dict)
async def sync_ots(db: Session = Depends(get_db)) -> dict:
    """
    Trigger OTS Agent to fetch OTs from TELCOS API and persist to database.

    This endpoint invokes the OTSAgent via PEIGraphRunner to:
    1. Fetch OTs from TELCOS API (or mock service)
    2. Validate geographic coordinates
    3. Persist new/updated OTs to database
    4. Track any geographic errors

    Returns:
        Dictionary with sync results including OT count and geo errors

    Note:
        This is a fire-and-forget operation. The actual agent execution
        is asynchronous and may continue after the endpoint returns.
    """
    # TODO: Implement PEIGraphRunner integration once agents are created
    # For now, return a placeholder response
    return {
        "status": "sync_initiated",
        "message": "OTS Agent invoked to sync OTs from TELCOS",
        "ot_count": 0,
        "geo_errors": 0,
    }


@router.patch("/{ot_id}/status", response_model=OTResponse)
async def update_ot_status(
    ot_id: int,
    status_update: OTStatusUpdate,
    db: Session = Depends(get_db),
) -> OTResponse:
    """
    Update OT status with business rule validation and agent invocation.

    This endpoint:
    1. Validates the status transition is allowed
    2. Invokes Gobernanza Agent to validate status change
    3. If transitioning to PLANIFICADA, invokes Planificación Agent for assignment
    4. Persists the updated OT to database

    Path Parameters:
        - ot_id: ID of the OT to update

    Request Body:
        - status: New status value
        - cuadrilla_id: (Optional) Cuadrilla to assign to
        - detencion_motivo: (Optional) Reason for detention if status=DETENIDA

    Returns:
        Updated OTResponse object

    Raises:
        404: OT not found
        400: Invalid status transition or business rule violation
    """
    # Get the OT from database
    ot = db.query(OT).filter(OT.id == ot_id).first()
    if not ot:
        raise HTTPException(status_code=404, detail=f"OT with id {ot_id} not found")

    # Validate status transition
    try:
        new_status = OTStatus[status_update.status.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status_update.status}")

    if not ot.can_transition_to(new_status):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {ot.status} to {new_status}",
        )

    # Handle detention with motivo
    if new_status == OTStatus.DETENIDA:
        if not status_update.detencion_motivo:
            raise HTTPException(
                status_code=400,
                detail="detencion_motivo is required when setting status to DETENIDA",
            )
        ot.detencion_motivo = status_update.detencion_motivo

    # Update OT status
    ot.status = new_status

    # Handle cuadrilla assignment if provided
    if status_update.cuadrilla_id is not None:
        ot.cuadrilla_id = status_update.cuadrilla_id

    # TODO: Invoke Gobernanza Agent for validation
    # TODO: If transitioning to PLANIFICADA, invoke Planificación Agent

    # Persist changes
    db.commit()
    db.refresh(ot)

    return ot


@router.post("/{ot_id}/detention", response_model=OTResponse)
async def set_ot_detention(
    ot_id: int,
    detention_data: dict,
    db: Session = Depends(get_db),
) -> OTResponse:
    """
    Set an OT status to DETENIDA (detained) with a reason.

    This endpoint:
    1. Finds the OT
    2. Updates status to DETENIDA
    3. Records the detention reason (motivo)
    4. Triggers necessary governance checks

    Path Parameters:
        - ot_id: ID of the OT to detain

    Request Body:
        - motivo: Reason for detention (required)

    Returns:
        Updated OTResponse object with DETENIDA status

    Raises:
        404: OT not found
        400: Invalid status transition or missing motivo
    """
    # Get the OT from database
    ot = db.query(OT).filter(OT.id == ot_id).first()
    if not ot:
        raise HTTPException(status_code=404, detail=f"OT with id {ot_id} not found")

    # Extract motivo from request body
    motivo = detention_data.get("motivo") if isinstance(detention_data, dict) else None
    if not motivo:
        raise HTTPException(
            status_code=400,
            detail="motivo (detention reason) is required",
        )

    # Validate status transition to DETENIDA
    if not ot.can_transition_to(OTStatus.DETENIDA):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot set {ot.status} OT to DETENIDA status",
        )

    # Update OT status and detention reason
    ot.status = OTStatus.DETENIDA
    ot.detencion_motivo = motivo

    # TODO: Invoke GobernanzaAgent for detention handling

    # Persist changes
    db.commit()
    db.refresh(ot)

    return ot

