"""Crew (Cuadrilla) management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database.db import get_db
from backend.database.models import Cuadrilla, OT, CuadrillaType
from backend.utils.geo import calculate_centroid
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Initialize router
router = APIRouter()


# Pydantic models for request/response
class CuadrillaBase(BaseModel):
    """Base Cuadrilla model with common fields."""
    name: str
    type: str
    capacidad_diaria: int = 20


class CuadrillaCreate(CuadrillaBase):
    """Cuadrilla creation model."""
    pass


class CuadrillaUpdate(BaseModel):
    """Cuadrilla update model."""
    name: Optional[str] = None
    type: Optional[str] = None
    capacidad_diaria: Optional[int] = None


class CentroidCoordinates(BaseModel):
    """Centroid coordinates model."""
    lat: Optional[float] = None
    long: Optional[float] = None
    calculated_at: Optional[datetime] = None


class CuadrillaResponse(CuadrillaBase):
    """Cuadrilla response model."""
    id: int
    ots_asignadas_count: int
    last_centroid_lat: Optional[float] = None
    last_centroid_long: Optional[float] = None

    class Config:
        from_attributes = True


class CuadrillaDetailResponse(CuadrillaResponse):
    """Detailed Cuadrilla response with additional info."""
    current_centroid: Optional[CentroidCoordinates] = None
    assigned_ots: List[dict] = []


class CuadrillaListResponse(BaseModel):
    """Cuadrilla list response."""
    total: int
    items: List[CuadrillaResponse]


# Endpoints

@router.get("/api/cuadrillas", response_model=CuadrillaListResponse)
async def list_cuadrillas(db: Session = Depends(get_db)):
    """
    Get all crews with current load information.
    
    Returns:
    - List of all cuadrillas with their current load (ots_asignadas_count)
    """
    cuadrillas = db.query(Cuadrilla).all()
    
    items = [
        CuadrillaResponse(
            id=c.id,
            name=c.name,
            type=c.type.value if isinstance(c.type, CuadrillaType) else c.type,
            capacidad_diaria=c.capacidad_diaria,
            ots_asignadas_count=c.ots_asignadas_count,
            last_centroid_lat=c.last_centroid_lat,
            last_centroid_long=c.last_centroid_long,
        )
        for c in cuadrillas
    ]
    
    return CuadrillaListResponse(total=len(cuadrillas), items=items)


@router.get("/api/cuadrillas/{cuadrilla_id}", response_model=CuadrillaDetailResponse)
async def get_cuadrilla(cuadrilla_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific crew.
    
    Path Parameters:
    - cuadrilla_id: Crew ID
    
    Returns:
    - Crew details including centroid coordinates and assigned OTs
    """
    cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
    
    if not cuadrilla:
        raise HTTPException(status_code=404, detail=f"Cuadrilla with id {cuadrilla_id} not found")
    
    # Calculate current centroid from assigned OTs
    assigned_ots = db.query(OT).filter(OT.cuadrilla_id == cuadrilla_id).all()
    current_centroid = None
    
    if assigned_ots and len(assigned_ots) > 0:
        coordinates = [(ot.lat, ot.long) for ot in assigned_ots]
        try:
            centroid_lat, centroid_long = calculate_centroid(coordinates)
            current_centroid = CentroidCoordinates(
                lat=centroid_lat,
                long=centroid_long,
                calculated_at=datetime.utcnow(),
            )
        except Exception:
            # If centroid calculation fails, use last stored centroid
            if cuadrilla.last_centroid_lat and cuadrilla.last_centroid_long:
                current_centroid = CentroidCoordinates(
                    lat=cuadrilla.last_centroid_lat,
                    long=cuadrilla.last_centroid_long,
                )
    
    # Build assigned OTs list
    assigned_ots_list = [
        {
            "id": ot.id,
            "external_id": ot.external_id,
            "status": ot.status,
            "project_type": ot.project_type,
            "lat": ot.lat,
            "long": ot.long,
            "cliente_id": ot.cliente_id,
        }
        for ot in assigned_ots
    ]
    
    return CuadrillaDetailResponse(
        id=cuadrilla.id,
        name=cuadrilla.name,
        type=cuadrilla.type.value if isinstance(cuadrilla.type, CuadrillaType) else cuadrilla.type,
        capacidad_diaria=cuadrilla.capacidad_diaria,
        ots_asignadas_count=cuadrilla.ots_asignadas_count,
        last_centroid_lat=cuadrilla.last_centroid_lat,
        last_centroid_long=cuadrilla.last_centroid_long,
        current_centroid=current_centroid,
        assigned_ots=assigned_ots_list,
    )


@router.get("/api/cuadrillas/{cuadrilla_id}/ots")
async def get_cuadrilla_ots(cuadrilla_id: int, db: Session = Depends(get_db)):
    """
    Get all assigned OTs for a specific crew.
    
    Path Parameters:
    - cuadrilla_id: Crew ID
    
    Returns:
    - List of OTs assigned to the crew
    """
    cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
    
    if not cuadrilla:
        raise HTTPException(status_code=404, detail=f"Cuadrilla with id {cuadrilla_id} not found")
    
    ots = db.query(OT).filter(OT.cuadrilla_id == cuadrilla_id).all()
    
    return {
        "cuadrilla_id": cuadrilla_id,
        "cuadrilla_name": cuadrilla.name,
        "total_assigned": len(ots),
        "ots": [
            {
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
                "error_geo": ot.error_geo,
            }
            for ot in ots
        ]
    }


@router.post("/api/cuadrillas", response_model=CuadrillaResponse)
async def create_cuadrilla(
    cuadrilla_create: CuadrillaCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new crew.
    
    Request Body:
    - name: Crew name (must be unique)
    - type: Crew type (Principal or Reserva)
    - capacidad_diaria: Daily capacity (default 20)
    
    Returns:
    - Created cuadrilla with ID
    """
    # Check if crew with same name already exists
    existing = db.query(Cuadrilla).filter(Cuadrilla.name == cuadrilla_create.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Cuadrilla with name '{cuadrilla_create.name}' already exists")
    
    # Create new cuadrilla
    new_cuadrilla = Cuadrilla(
        name=cuadrilla_create.name,
        type=cuadrilla_create.type,
        capacidad_diaria=cuadrilla_create.capacidad_diaria,
        ots_asignadas_count=0,
    )
    
    db.add(new_cuadrilla)
    db.commit()
    db.refresh(new_cuadrilla)
    
    return CuadrillaResponse(
        id=new_cuadrilla.id,
        name=new_cuadrilla.name,
        type=new_cuadrilla.type.value if isinstance(new_cuadrilla.type, CuadrillaType) else new_cuadrilla.type,
        capacidad_diaria=new_cuadrilla.capacidad_diaria,
        ots_asignadas_count=new_cuadrilla.ots_asignadas_count,
        last_centroid_lat=new_cuadrilla.last_centroid_lat,
        last_centroid_long=new_cuadrilla.last_centroid_long,
    )


@router.patch("/api/cuadrillas/{cuadrilla_id}", response_model=CuadrillaResponse)
async def update_cuadrilla(
    cuadrilla_id: int,
    cuadrilla_update: CuadrillaUpdate,
    db: Session = Depends(get_db),
):
    """
    Update crew details.
    
    Path Parameters:
    - cuadrilla_id: Crew ID
    
    Request Body:
    - name: New crew name (optional)
    - type: New crew type (optional)
    - capacidad_diaria: New daily capacity (optional)
    
    Returns:
    - Updated cuadrilla
    """
    cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
    
    if not cuadrilla:
        raise HTTPException(status_code=404, detail=f"Cuadrilla with id {cuadrilla_id} not found")
    
    # Update fields if provided
    if cuadrilla_update.name is not None:
        # Check if new name is unique
        existing = db.query(Cuadrilla).filter(
            Cuadrilla.name == cuadrilla_update.name,
            Cuadrilla.id != cuadrilla_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Cuadrilla with name '{cuadrilla_update.name}' already exists")
        cuadrilla.name = cuadrilla_update.name
    
    if cuadrilla_update.type is not None:
        cuadrilla.type = cuadrilla_update.type
    
    if cuadrilla_update.capacidad_diaria is not None:
        cuadrilla.capacidad_diaria = cuadrilla_update.capacidad_diaria
    
    db.commit()
    db.refresh(cuadrilla)
    
    return CuadrillaResponse(
        id=cuadrilla.id,
        name=cuadrilla.name,
        type=cuadrilla.type.value if isinstance(cuadrilla.type, CuadrillaType) else cuadrilla.type,
        capacidad_diaria=cuadrilla.capacidad_diaria,
        ots_asignadas_count=cuadrilla.ots_asignadas_count,
        last_centroid_lat=cuadrilla.last_centroid_lat,
        last_centroid_long=cuadrilla.last_centroid_long,
    )


@router.get("/api/cuadrillas/{cuadrilla_id}/centroid", response_model=CentroidCoordinates)
async def get_centroid(cuadrilla_id: int, db: Session = Depends(get_db)):
    """
    Get current centroid coordinates for a crew.
    
    Calculates the geographic center point of all assigned OTs for the crew.
    
    Path Parameters:
    - cuadrilla_id: Crew ID
    
    Returns:
    - Centroid coordinates (lat, long) or last stored centroid
    """
    cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
    
    if not cuadrilla:
        raise HTTPException(status_code=404, detail=f"Cuadrilla with id {cuadrilla_id} not found")
    
    # Get all assigned OTs
    assigned_ots = db.query(OT).filter(OT.cuadrilla_id == cuadrilla_id).all()
    
    # Calculate centroid from assigned OTs
    if assigned_ots and len(assigned_ots) > 0:
        coordinates = [(ot.lat, ot.long) for ot in assigned_ots]
        try:
            centroid_lat, centroid_long = calculate_centroid(coordinates)
            return CentroidCoordinates(
                lat=centroid_lat,
                long=centroid_long,
                calculated_at=datetime.utcnow(),
            )
        except Exception:
            # If calculation fails, return last stored centroid
            if cuadrilla.last_centroid_lat and cuadrilla.last_centroid_long:
                return CentroidCoordinates(
                    lat=cuadrilla.last_centroid_lat,
                    long=cuadrilla.last_centroid_long,
                )
            raise HTTPException(status_code=400, detail="Cannot calculate centroid: no assigned OTs or invalid coordinates")
    
    # No assigned OTs, check for stored centroid
    if cuadrilla.last_centroid_lat and cuadrilla.last_centroid_long:
        return CentroidCoordinates(
            lat=cuadrilla.last_centroid_lat,
            long=cuadrilla.last_centroid_long,
        )
    
    raise HTTPException(status_code=404, detail="No centroid available: crew has no assigned OTs")

