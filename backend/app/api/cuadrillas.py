from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models import Cuadrilla, OT
from backend.app.schemas.cuadrilla_schema import CuadrillaResponse
from backend.app.schemas.ot_schema import OTResponse

router = APIRouter()


@router.get("/cuadrillas", response_model=List[CuadrillaResponse])
def list_cuadrillas(db: Session = Depends(get_db)):
    """
    List all cuadrillas (teams) with their current load information.
    
    Returns:
    - List of CuadrillaResponse objects with load percentage calculated
    """
    cuadrillas = db.query(Cuadrilla).all()
    return cuadrillas


@router.get("/cuadrillas/{cuadrilla_id}", response_model=CuadrillaResponse)
def get_cuadrilla(cuadrilla_id: int, db: Session = Depends(get_db)):
    """
    Get a specific cuadrilla by ID with load information.
    
    Path Parameters:
    - cuadrilla_id: The ID of the cuadrilla to retrieve
    
    Returns:
    - CuadrillaResponse object with current load percentage
    """
    cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
    if not cuadrilla:
        raise HTTPException(status_code=404, detail="Cuadrilla not found")
    return cuadrilla


@router.get("/cuadrillas/{cuadrilla_id}/ots", response_model=List[OTResponse])
def get_cuadrilla_ots(
    cuadrilla_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all OTs assigned to a specific cuadrilla with current load calculation.
    
    Path Parameters:
    - cuadrilla_id: The ID of the cuadrilla
    
    Query Parameters:
    - status: Optional filter by OT status
    
    Returns:
    - List of OTResponse objects assigned to the cuadrilla
    """
    # Verify cuadrilla exists
    cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
    if not cuadrilla:
        raise HTTPException(status_code=404, detail="Cuadrilla not found")
    
    # Query OTs assigned to this cuadrilla
    query = db.query(OT).filter(OT.cuadrilla_id == cuadrilla_id)
    
    # Optional status filter
    if status:
        query = query.filter(OT.status == status)
    
    ots = query.all()
    return ots

