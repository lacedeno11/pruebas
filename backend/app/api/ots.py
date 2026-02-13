from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import OT
from app.schemas import OTCreate, OTResponse, OTUpdate
from app.services import MockApiService
from app.config import get_settings
from app.utils.geo import validate_ecuador_bounds

router = APIRouter()
mock_service = MockApiService()
settings = get_settings()


@router.post("/sync")
async def sync_ots(db: Session = Depends(get_db)):
    """
    Sync OTs from mock or external API
    """
    try:
        if settings.SYSTEM_MODE == "MOCK":
            ots_data = await mock_service.get_ots()
        else:
            # In production, call actual API
            ots_data = []
        
        synced_count = 0
        geo_error_count = 0
        
        for ot_data in ots_data:
            # Check if OT already exists
            existing_ot = db.query(OT).filter(
                OT.external_id == ot_data["external_id"]
            ).first()
            
            # Validate geo coordinates
            geo_error = False
            if not ot_data.get("lat") or not ot_data.get("long"):
                geo_error = True
                geo_error_count += 1
            elif not validate_ecuador_bounds(ot_data["lat"], ot_data["long"]):
                geo_error = True
                geo_error_count += 1
            
            if existing_ot:
                # Update existing OT
                for key, value in ot_data.items():
                    if key != "external_id":
                        setattr(existing_ot, key, value)
                existing_ot.geo_error = geo_error
            else:
                # Create new OT
                new_ot = OT(
                    **ot_data,
                    geo_error=geo_error
                )
                db.add(new_ot)
            
            synced_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "synced_count": synced_count,
            "geo_error_count": geo_error_count,
            "message": f"Synced {synced_count} OTs ({geo_error_count} with geo errors)"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[OTResponse])
def list_ots(
    status: Optional[str] = Query(None),
    project_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List all OTs with optional filters
    """
    query = db.query(OT)
    
    if status:
        query = query.filter(OT.status == status)
    
    if project_type:
        query = query.filter(OT.project_type == project_type)
    
    return query.all()


@router.get("/{ot_id}", response_model=OTResponse)
def get_ot(ot_id: int, db: Session = Depends(get_db)):
    """
    Get a single OT by ID
    """
    ot = db.query(OT).filter(OT.id == ot_id).first()
    if not ot:
        raise HTTPException(status_code=404, detail="OT not found")
    return ot


@router.put("/{ot_id}", response_model=OTResponse)
def update_ot(
    ot_id: int,
    ot_update: OTUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an OT
    """
    ot = db.query(OT).filter(OT.id == ot_id).first()
    if not ot:
        raise HTTPException(status_code=404, detail="OT not found")
    
    update_data = ot_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(ot, key, value)
    
    db.commit()
    db.refresh(ot)
    return ot


@router.put("/{ot_id}/status")
def update_ot_status(
    ot_id: int,
    new_status: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Update OT status with validation
    """
    ot = db.query(OT).filter(OT.id == ot_id).first()
    if not ot:
        raise HTTPException(status_code=404, detail="OT not found")
    
    # Validate status transition
    valid_transitions = {
        "PREPLANIFICADA": ["PLANIFICADA", "ANULADA"],
        "PLANIFICADA": ["ASIGNADO_TAREA", "PREPLANIFICADA", "DETENIDA", "ANULADA"],
        "ASIGNADO_TAREA": ["DETENIDA", "FINALIZADA", "ANULADA"],
        "DETENIDA": ["PLANIFICADA", "ANULADA"],
        "ANULADA": [],
        "FINALIZADA": [],
    }
    
    if new_status not in valid_transitions.get(ot.status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {ot.status} to {new_status}"
        )
    
    # Special validation for PUBLICO projects moving to FINALIZADA
    if ot.project_type == "PUBLICO" and new_status == "FINALIZADA":
        # Would check TelcoDrive documents here
        pass
    
    ot.status = new_status
    db.commit()
    db.refresh(ot)
    
    return {"success": True, "ot": OTResponse.from_orm(ot)}


@router.delete("/{ot_id}")
def delete_ot(ot_id: int, db: Session = Depends(get_db)):
    """
    Soft delete an OT (set status to ANULADA)
    """
    ot = db.query(OT).filter(OT.id == ot_id).first()
    if not ot:
        raise HTTPException(status_code=404, detail="OT not found")
    
    ot.status = "ANULADA"
    db.commit()
    
    return {"success": True, "message": "OT marked as ANULADA"}


ots_router = router

