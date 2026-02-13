"""OT (Work Order) management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from backend.database.db import get_db
from backend.database.models import OT, Cuadrilla, OTStatus, ProjectType
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Initialize router
router = APIRouter()


# Pydantic models for request/response
class OTBase(BaseModel):
    """Base OT model with common fields."""
    external_id: str
    status: str
    project_type: str
    lat: float
    long: float
    cliente_id: str
    login: str


class OTCreate(OTBase):
    """OT creation model."""
    pass


class OTResponse(OTBase):
    """OT response model."""
    id: int
    created_at: datetime
    updated_at: datetime
    cuadrilla_id: Optional[int] = None
    error_geo: bool = False
    cuadrilla_name: Optional[str] = None

    class Config:
        from_attributes = True


class OTListResponse(BaseModel):
    """Paginated OT list response."""
    total: int
    page: int
    limit: int
    items: List[OTResponse]


class OTStatusUpdate(BaseModel):
    """OT status update request model."""
    new_status: str
    reason: Optional[str] = None


class OTSyncResponse(BaseModel):
    """Response from sync operation."""
    success: bool
    message: str
    total_fetched: int = 0
    inserted: int = 0
    duplicates: int = 0
    geo_errors: int = 0


# Endpoints

@router.get("/api/ots", response_model=OTListResponse)
async def list_ots(
    status: Optional[str] = Query(None),
    project_type: Optional[str] = Query(None),
    cuadrilla_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List all OTs with optional filtering.
    
    Query Parameters:
    - status: Filter by OT status (PREPLANIFICADA, PLANIFICADA, etc.)
    - project_type: Filter by project type (PUBLICO, PRIVADO, TERCERIZADO)
    - cuadrilla_id: Filter by assigned crew
    - limit: Number of results per page (default 50, max 200)
    - offset: Number of results to skip (for pagination)
    """
    query = db.query(OT)
    
    # Apply filters
    if status:
        query = query.filter(OT.status == status)
    if project_type:
        query = query.filter(OT.project_type == project_type)
    if cuadrilla_id:
        query = query.filter(OT.cuadrilla_id == cuadrilla_id)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination
    ots = query.order_by(OT.created_at.desc()).offset(offset).limit(limit).all()
    
    # Build response with cuadrilla names
    items = []
    for ot in ots:
        ot_dict = {
            "id": ot.id,
            "external_id": ot.external_id,
            "status": ot.status,
            "project_type": ot.project_type,
            "lat": ot.lat,
            "long": ot.long,
            "cliente_id": ot.cliente_id,
            "login": ot.login,
            "created_at": ot.created_at,
            "updated_at": ot.updated_at,
            "cuadrilla_id": ot.cuadrilla_id,
            "error_geo": ot.error_geo,
            "cuadrilla_name": ot.cuadrilla.name if ot.cuadrilla else None,
        }
        items.append(OTResponse(**ot_dict))
    
    return OTListResponse(
        total=total,
        page=offset // limit + 1,
        limit=limit,
        items=items,
    )


@router.get("/api/ots/{ot_id}", response_model=OTResponse)
async def get_ot(ot_id: int, db: Session = Depends(get_db)):
    """Get single OT details with assigned cuadrilla information."""
    ot = db.query(OT).filter(OT.id == ot_id).first()
    
    if not ot:
        raise HTTPException(status_code=404, detail=f"OT with id {ot_id} not found")
    
    ot_dict = {
        "id": ot.id,
        "external_id": ot.external_id,
        "status": ot.status,
        "project_type": ot.project_type,
        "lat": ot.lat,
        "long": ot.long,
        "cliente_id": ot.cliente_id,
        "login": ot.login,
        "created_at": ot.created_at,
        "updated_at": ot.updated_at,
        "cuadrilla_id": ot.cuadrilla_id,
        "error_geo": ot.error_geo,
        "cuadrilla_name": ot.cuadrilla.name if ot.cuadrilla else None,
    }
    
    return OTResponse(**ot_dict)


@router.post("/api/ots/sync", response_model=OTSyncResponse)
async def sync_ots(db: Session = Depends(get_db)):
    """
    Trigger sync from TELCOS API to fetch new OTs.
    
    This endpoint calls the OTS Agent to:
    1. Fetch new OTs from TELCOS API (or mock service)
    2. Validate geographic coordinates
    3. Check for duplicates
    4. Create OT records in database
    5. Log any errors or warnings
    """
    # TODO: Integrate with OTS Agent via LangGraph workflow
    # For now, return a placeholder response
    return OTSyncResponse(
        success=True,
        message="OT sync completed",
        total_fetched=0,
        inserted=0,
        duplicates=0,
        geo_errors=0,
    )


@router.patch("/api/ots/{ot_id}/status", response_model=OTResponse)
async def update_ot_status(
    ot_id: int,
    status_update: OTStatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Update OT status (used for drag & drop transitions).
    
    Request Body:
    - new_status: New status value
    - reason: Optional reason for status change (required for DETENIDA)
    
    Process:
    1. Validate the status transition
    2. Update the OT status in database
    3. Log the change
    4. Return updated OT
    """
    ot = db.query(OT).filter(OT.id == ot_id).first()
    
    if not ot:
        raise HTTPException(status_code=404, detail=f"OT with id {ot_id} not found")
    
    # TODO: Call validation endpoint to validate_state_transition
    # For now, allow the update
    old_status = ot.status
    ot.status = status_update.new_status
    ot.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(ot)
    
    ot_dict = {
        "id": ot.id,
        "external_id": ot.external_id,
        "status": ot.status,
        "project_type": ot.project_type,
        "lat": ot.lat,
        "long": ot.long,
        "cliente_id": ot.cliente_id,
        "login": ot.login,
        "created_at": ot.created_at,
        "updated_at": ot.updated_at,
        "cuadrilla_id": ot.cuadrilla_id,
        "error_geo": ot.error_geo,
        "cuadrilla_name": ot.cuadrilla.name if ot.cuadrilla else None,
    }
    
    return OTResponse(**ot_dict)


@router.delete("/api/ots/{ot_id}", response_model=OTResponse)
async def delete_ot(ot_id: int, db: Session = Depends(get_db)):
    """
    Soft delete OT by setting status to ANULADA.
    
    This is a soft delete - the OT record is not removed from database,
    only marked as ANULADA for audit purposes.
    """
    ot = db.query(OT).filter(OT.id == ot_id).first()
    
    if not ot:
        raise HTTPException(status_code=404, detail=f"OT with id {ot_id} not found")
    
    # Soft delete: set status to ANULADA
    ot.status = OTStatus.ANULADA.value
    ot.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(ot)
    
    ot_dict = {
        "id": ot.id,
        "external_id": ot.external_id,
        "status": ot.status,
        "project_type": ot.project_type,
        "lat": ot.lat,
        "long": ot.long,
        "cliente_id": ot.cliente_id,
        "login": ot.login,
        "created_at": ot.created_at,
        "updated_at": ot.updated_at,
        "cuadrilla_id": ot.cuadrilla_id,
        "error_geo": ot.error_geo,
        "cuadrilla_name": ot.cuadrilla.name if ot.cuadrilla else None,
    }
    
    return OTResponse(**ot_dict)

