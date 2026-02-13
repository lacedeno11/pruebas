from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models import OT, OTStatus, ProjectType, LogAgente
from backend.app.schemas.ot_schema import OTCreate, OTUpdate, OTResponse, OTStatus as SchemaOTStatus, ProjectType as SchemaProjectType

router = APIRouter()


def log_action(db: Session, agente_name: str, accion: str, resultado: str, ot_id: Optional[int] = None, raw_llm_response: Optional[str] = None):
    """Helper function to log agent actions to the logs_agentes table."""
    log = LogAgente(
        ot_id=ot_id,
        agente_name=agente_name,
        accion=accion,
        resultado=resultado,
        raw_llm_response=raw_llm_response,
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()


@router.get("/ots", response_model=List[OTResponse])
def list_ots(
    db: Session = Depends(get_db),
    status: Optional[SchemaOTStatus] = Query(None),
    project_type: Optional[SchemaProjectType] = Query(None),
    cuadrilla_id: Optional[int] = Query(None),
):
    """
    List all OTs with optional filtering.
    
    Query Parameters:
    - status: Filter by OT status (PREPLANIFICADA, PLANIFICADA, etc.)
    - project_type: Filter by project type (PUBLICO, PRIVADO, TERCERIZADO)
    - cuadrilla_id: Filter by assigned cuadrilla ID
    """
    query = db.query(OT)
    
    if status:
        query = query.filter(OT.status == status)
    if project_type:
        query = query.filter(OT.project_type == project_type)
    if cuadrilla_id is not None:
        query = query.filter(OT.cuadrilla_id == cuadrilla_id)
    
    ots = query.all()
    return ots


@router.get("/ots/{ot_id}", response_model=OTResponse)
def get_ot(ot_id: int, db: Session = Depends(get_db)):
    """Get a specific OT by ID."""
    ot = db.query(OT).filter(OT.id == ot_id).first()
    if not ot:
        raise HTTPException(status_code=404, detail="OT not found")
    return ot


@router.post("/ots", response_model=OTResponse, status_code=201)
def create_ot(ot_data: OTCreate, db: Session = Depends(get_db)):
    """
    Create a new OT or import from TELCOS.
    """
    # Check if external_id already exists
    existing = db.query(OT).filter(OT.external_id == ot_data.external_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="OT with this external_id already exists")
    
    # Create new OT
    ot = OT(
        external_id=ot_data.external_id,
        status=ot_data.status,
        project_type=ot_data.project_type,
        cliente_id=ot_data.cliente_id,
        login_id=ot_data.login_id,
        lat=ot_data.lat,
        long=ot_data.long,
        error_geo=ot_data.error_geo,
        cuadrilla_id=ot_data.cuadrilla_id,
    )
    
    db.add(ot)
    db.commit()
    db.refresh(ot)
    
    # Log the action
    log_action(db, "OTSAgent", "create_ot", f"OT created with external_id={ot.external_id}", ot_id=ot.id)
    
    return ot


@router.put("/ots/{ot_id}", response_model=OTResponse)
def update_ot(ot_id: int, ot_data: OTUpdate, db: Session = Depends(get_db)):
    """
    Update an OT's fields.
    """
    ot = db.query(OT).filter(OT.id == ot_id).first()
    if not ot:
        raise HTTPException(status_code=404, detail="OT not found")
    
    # Update fields if provided
    update_data = ot_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ot, field, value)
    
    ot.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ot)
    
    # Log the action
    log_action(db, "OTSAgent", "update_ot", f"OT updated: {list(update_data.keys())}", ot_id=ot.id)
    
    return ot


@router.put("/ots/{ot_id}/status", response_model=OTResponse)
def update_ot_status(
    ot_id: int,
    new_status: SchemaOTStatus,
    db: Session = Depends(get_db)
):
    """
    Update OT status with business logic validation.
    
    Status transition rules:
    - PUBLICO projects require 29 documents before FINALIZADA
    - All status transitions are logged to logs_agentes table
    """
    ot = db.query(OT).filter(OT.id == ot_id).first()
    if not ot:
        raise HTTPException(status_code=404, detail="OT not found")
    
    old_status = ot.status
    
    # Validate state transitions
    if new_status == OTStatus.FINALIZADA:
        # For PUBLICO projects, check document count
        if ot.project_type == ProjectType.PUBLICO:
            # TODO: Call TelcoDriveService to validate documents
            # For now, log that validation should occur
            log_action(
                db,
                "GobernanzaAgent",
                "validate_publico_documents",
                f"Document validation required for PUBLICO project OT {ot.external_id}",
                ot_id=ot.id
            )
    
    # Update status
    ot.status = new_status
    ot.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ot)
    
    # Log the status change
    log_action(
        db,
        "OTSAgent",
        "update_status",
        f"Status changed from {old_status} to {new_status}",
        ot_id=ot.id
    )
    
    return ot

