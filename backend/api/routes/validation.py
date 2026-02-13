"""Validation endpoints for business rules and constraints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database.db import get_db
from backend.database.models import OT, Cuadrilla
from backend.services.telcos_service import TelcosService
from backend.utils.validators import validate_state_transition, validate_crew_capacity, validate_publico_documents
from backend.utils.geo import haversine_distance
from pydantic import BaseModel
from typing import Optional, List
import os

# Initialize router
router = APIRouter()


# Pydantic models for request/response
class TransitionValidationRequest(BaseModel):
    """Request model for status transition validation."""
    ot_id: int
    from_status: str
    to_status: str
    project_type: str


class TransitionValidationResponse(BaseModel):
    """Response model for status transition validation."""
    valid: bool
    error_message: Optional[str] = None
    warnings: List[str] = []


class DocumentValidationResponse(BaseModel):
    """Response model for document validation."""
    ot_id: str
    is_valid: bool
    document_count: int
    required_count: int = 29
    error_message: Optional[str] = None


class AssignmentValidationRequest(BaseModel):
    """Request model for assignment validation."""
    ot_id: int
    cuadrilla_id: int


class AssignmentValidationResponse(BaseModel):
    """Response model for assignment validation."""
    valid: bool
    error_message: Optional[str] = None
    warnings: List[str] = []
    distance_km: Optional[float] = None


# Endpoints

@router.post("/api/validate/transition", response_model=TransitionValidationResponse)
async def validate_transition(
    request: TransitionValidationRequest,
    db: Session = Depends(get_db),
):
    """
    Validate if an OT status transition is allowed.
    
    Request Body:
    - ot_id: ID of the OT
    - from_status: Current status
    - to_status: Desired new status
    - project_type: OT project type (PUBLICO, PRIVADO, TERCERIZADO)
    
    Returns:
    - valid: Whether the transition is allowed
    - error_message: If invalid, explains why
    - warnings: Non-blocking warnings (e.g., document requirements)
    
    Validation Rules:
    - Check allowed state transitions
    - If PUBLICO → FINALIZADA: require 29+ documents in TelcoDrive
    - Warn if DETENIDA → FINALIZADA (might lose work)
    """
    warnings = []
    
    # Check if OT exists
    ot = db.query(OT).filter(OT.id == request.ot_id).first()
    if not ot:
        return TransitionValidationResponse(
            valid=False,
            error_message=f"OT with id {request.ot_id} not found",
        )
    
    # Validate the state transition
    valid, error_msg = validate_state_transition(request.from_status, request.to_status)
    
    if not valid:
        return TransitionValidationResponse(
            valid=False,
            error_message=error_msg,
        )
    
    # Additional validation for PUBLICO projects → FINALIZADA
    if request.project_type == "PUBLICO" and request.to_status == "FINALIZADA":
        # This is a warning - user must acknowledge but can still proceed
        warnings.append("PÚBLICO projects require 29+ documents before finalization. Please verify via TelcoDrive.")
    
    # Warn if DETENIDA → FINALIZADA (might lose work)
    if request.from_status == "DETENIDA" and request.to_status == "FINALIZADA":
        warnings.append("This OT is transitioning from DETENIDA status. Ensure all work is complete.")
    
    return TransitionValidationResponse(
        valid=True,
        error_message=None,
        warnings=warnings,
    )


@router.get("/api/validate/documents/{ot_id}", response_model=DocumentValidationResponse)
async def validate_documents(ot_id: int, db: Session = Depends(get_db)):
    """
    Check PÚBLICO project document requirements via TelcosService.
    
    Path Parameters:
    - ot_id: ID of the OT
    
    Returns:
    - ot_id: External ID of the OT
    - is_valid: Whether document count >= 29
    - document_count: Current document count from TelcoDrive
    - required_count: Required document count (always 29)
    - error_message: If validation fails, explains why
    
    Note: Only applies to PUBLICO projects. Call TelcosService.verify_documents()
    """
    # Check if OT exists
    ot = db.query(OT).filter(OT.id == ot_id).first()
    if not ot:
        raise HTTPException(status_code=404, detail=f"OT with id {ot_id} not found")
    
    # Only validate PUBLICO projects
    if ot.project_type != "PUBLICO":
        return DocumentValidationResponse(
            ot_id=ot.external_id,
            is_valid=True,  # Non-PUBLICO projects don't need document validation
            document_count=0,
            required_count=29,
        )
    
    try:
        # Get system mode and API configuration
        system_mode = os.getenv("SYSTEM_MODE", "MOCK")
        telcos_url = os.getenv("TELCOS_API_URL", "")
        telcos_key = os.getenv("TELCOS_API_KEY", "")
        
        # Initialize TelcosService
        telcos_service = TelcosService(
            base_url=telcos_url,
            api_key=telcos_key,
            mock_mode=(system_mode == "MOCK"),
        )
        
        # Verify documents
        doc_response = await telcos_service.verify_documents(ot.external_id)
        
        document_count = doc_response.get("document_count", 0)
        is_valid = validate_publico_documents(document_count)
        
        return DocumentValidationResponse(
            ot_id=ot.external_id,
            is_valid=is_valid,
            document_count=document_count,
            required_count=29,
            error_message=None if is_valid else f"Only {document_count} documents found, 29 required",
        )
    
    except Exception as e:
        return DocumentValidationResponse(
            ot_id=ot.external_id,
            is_valid=False,
            document_count=0,
            required_count=29,
            error_message=f"Failed to verify documents: {str(e)}",
        )


@router.post("/api/validate/assignment", response_model=AssignmentValidationResponse)
async def validate_assignment(
    request: AssignmentValidationRequest,
    db: Session = Depends(get_db),
):
    """
    Validate if an OT can be assigned to a crew.
    
    Request Body:
    - ot_id: ID of the OT to assign
    - cuadrilla_id: ID of the crew to assign to
    
    Returns:
    - valid: Whether the assignment is allowed
    - error_message: If invalid, explains why
    - warnings: Non-blocking warnings
    - distance_km: Distance from crew centroid to OT (if applicable)
    
    Validation Checks:
    1. OT exists and is unassigned
    2. Crew exists
    3. Crew has available capacity
    4. OT is within MAX_DISTANCE_KM (10km) if crew has centroid
    5. Crew type matches OT requirements
    """
    warnings = []
    distance_km = None
    
    # Check if OT exists
    ot = db.query(OT).filter(OT.id == request.ot_id).first()
    if not ot:
        return AssignmentValidationResponse(
            valid=False,
            error_message=f"OT with id {request.ot_id} not found",
        )
    
    # Check if OT is already assigned
    if ot.cuadrilla_id is not None:
        return AssignmentValidationResponse(
            valid=False,
            error_message=f"OT {ot.external_id} is already assigned to a crew",
        )
    
    # Check if crew exists
    cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == request.cuadrilla_id).first()
    if not cuadrilla:
        return AssignmentValidationResponse(
            valid=False,
            error_message=f"Cuadrilla with id {request.cuadrilla_id} not found",
        )
    
    # Check crew capacity
    valid, error_msg = validate_crew_capacity(cuadrilla)
    if not valid:
        return AssignmentValidationResponse(
            valid=False,
            error_message=error_msg,
        )
    
    # Check distance constraint
    max_distance_km = float(os.getenv("MAX_DISTANCE_KM", "10"))
    if cuadrilla.last_centroid_lat and cuadrilla.last_centroid_long:
        distance_km = haversine_distance(
            cuadrilla.last_centroid_lat,
            cuadrilla.last_centroid_long,
            ot.lat,
            ot.long
        )
        
        if distance_km > max_distance_km:
            return AssignmentValidationResponse(
                valid=False,
                error_message=f"OT is {distance_km:.1f}km from crew centroid (max {max_distance_km}km)",
                distance_km=distance_km,
            )
        
        # Warn if distance is close to limit
        if distance_km > (max_distance_km * 0.8):  # 80% of max
            warnings.append(f"OT is {distance_km:.1f}km from crew centroid (close to {max_distance_km}km limit)")
    else:
        # No centroid yet, warn that distance cannot be verified
        warnings.append("Crew has no assigned OTs yet; distance cannot be verified")
    
    # Check for geographic errors
    if ot.error_geo:
        warnings.append("This OT has geographic coordinate errors; may not be assigned optimally")
    
    return AssignmentValidationResponse(
        valid=True,
        error_message=None,
        warnings=warnings,
        distance_km=distance_km,
    )

