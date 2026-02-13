from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Cuadrilla, Asignacion, OT
from app.schemas import CuadrillaCreate, CuadrillaResponse
from app.services import PlanningService

router = APIRouter()
planning_service = PlanningService()


@router.post("/", response_model=CuadrillaResponse)
def create_cuadrilla(
    cuadrilla: CuadrillaCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new Cuadrilla with validation
    """
    # Check if name already exists
    existing = db.query(Cuadrilla).filter(
        Cuadrilla.name == cuadrilla.name
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Cuadrilla name already exists")
    
    # Validate type
    if cuadrilla.type not in ["Principal", "Reserva"]:
        raise HTTPException(
            status_code=400,
            detail="Cuadrilla type must be 'Principal' or 'Reserva'"
        )
    
    new_cuadrilla = Cuadrilla(**cuadrilla.model_dump())
    db.add(new_cuadrilla)
    db.commit()
    db.refresh(new_cuadrilla)
    
    return new_cuadrilla


@router.get("/", response_model=List[CuadrillaResponse])
def list_cuadrillas(
    type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List all Cuadrillas with optional filters
    """
    query = db.query(Cuadrilla)
    
    if type:
        query = query.filter(Cuadrilla.type == type)
    
    if is_active is not None:
        query = query.filter(Cuadrilla.is_active == is_active)
    
    return query.all()


@router.get("/{cuadrilla_id}", response_model=CuadrillaResponse)
def get_cuadrilla(
    cuadrilla_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a single Cuadrilla by ID with assigned OTs count
    """
    cuadrilla = db.query(Cuadrilla).filter(
        Cuadrilla.id == cuadrilla_id
    ).first()
    
    if not cuadrilla:
        raise HTTPException(status_code=404, detail="Cuadrilla not found")
    
    return cuadrilla


@router.put("/{cuadrilla_id}", response_model=CuadrillaResponse)
def update_cuadrilla(
    cuadrilla_id: int,
    cuadrilla_data: dict,
    db: Session = Depends(get_db)
):
    """
    Update a Cuadrilla
    """
    cuadrilla = db.query(Cuadrilla).filter(
        Cuadrilla.id == cuadrilla_id
    ).first()
    
    if not cuadrilla:
        raise HTTPException(status_code=404, detail="Cuadrilla not found")
    
    for key, value in cuadrilla_data.items():
        if hasattr(cuadrilla, key):
            setattr(cuadrilla, key, value)
    
    db.commit()
    db.refresh(cuadrilla)
    
    return cuadrilla


@router.get("/{cuadrilla_id}/assignments")
def get_cuadrilla_assignments(
    cuadrilla_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all OTs assigned to a Cuadrilla
    """
    cuadrilla = db.query(Cuadrilla).filter(
        Cuadrilla.id == cuadrilla_id
    ).first()
    
    if not cuadrilla:
        raise HTTPException(status_code=404, detail="Cuadrilla not found")
    
    assignments = db.query(Asignacion).filter(
        Asignacion.cuadrilla_id == cuadrilla_id
    ).all()
    
    return {
        "cuadrilla_id": cuadrilla_id,
        "cuadrilla_name": cuadrilla.name,
        "assignment_count": len(assignments),
        "assignments": assignments
    }


@router.put("/{cuadrilla_id}/centroid")
def recalculate_centroid(
    cuadrilla_id: int,
    db: Session = Depends(get_db)
):
    """
    Manually trigger centroid recalculation for a Cuadrilla
    """
    cuadrilla = db.query(Cuadrilla).filter(
        Cuadrilla.id == cuadrilla_id
    ).first()
    
    if not cuadrilla:
        raise HTTPException(status_code=404, detail="Cuadrilla not found")
    
    planning_service.update_cuadrilla_centroid(db, cuadrilla_id)
    
    return {
        "success": True,
        "centroid_lat": cuadrilla.last_centroid_lat,
        "centroid_long": cuadrilla.last_centroid_long
    }


cuadrillas_router = router

