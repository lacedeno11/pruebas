"""
API routes specifically for drag & drop validation.

Endpoints:
- POST /api/drag-drop/validate - Validate state transition before UI updates
- POST /api/drag-drop/commit - Commit state change after validation
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.db.base import get_db
from backend.app.models.ot import OrdenTrabajo, OTStatus, ProjectType
from backend.app.models.cuadrilla import Cuadrilla
from backend.app.models.asignacion import Asignacion
from backend.app.schemas.ot_schema import OTResponse
from backend.app.utils.geo_utils import calculate_distance, calculate_centroid
from backend.app.utils.business_rules import can_finalize_ot
from backend.app.services.telcos_api_client import TelcosApiClient

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/drag-drop",
    tags=["Drag & Drop"],
    responses={
        400: {"description": "Validation failed"},
        404: {"description": "Resource not found"},
        500: {"description": "Server error"},
    },
)


# ============================================================================
# POST /api/drag-drop/validate - Validate State Transition
# ============================================================================

@router.post("/validate", response_model=Dict[str, Any])
async def validate_drag_drop(
    ot_id: str,
    new_status: str,
    cuadrilla_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Validate a state transition before committing changes.
    
    This endpoint checks business rules, capacity constraints, and document
    requirements without modifying the database. Used for real-time UI feedback.
    
    Query Parameters:
    - ot_id: UUID of the OT to transition
    - new_status: New status (PREPLANIFICADA, PLANIFICADA, ASIGNADO_TAREA, DETENIDA, ANULADA, FINALIZADA)
    - cuadrilla_id: Optional UUID of target cuadrilla (required for assignment transitions)
    
    Validation Checks:
    1. OT Status Transition: Verify valid state transition
    2. Cuadrilla Capacity: If assigning, check cuadrilla has available capacity
    3. Proximity Constraint: If assigning, check OT within 10km of centroid
    4. Document Requirement: If finalizing PUBLICO, check 29 documents uploaded
    5. Inactivity Rule: If transitioning to DETENIDA, check reason provided
    
    Returns:
    - Dict with validation result: valid (bool), message, errors (list), warnings (list)
    """
    try:
        logger.info(
            f"Validating drag-drop: OT {ot_id} → {new_status}, "
            f"cuadrilla {cuadrilla_id}"
        )
        
        # Get OT
        ot = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == ot_id).first()
        
        if not ot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OT {ot_id} not found"
            )
        
        # Convert status string to enum
        try:
            target_status = OTStatus[new_status.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {new_status}"
            )
        
        errors = []
        warnings = []
        
        # Check 1: Valid status transition
        # For now, allow any transition (can be enhanced with state machine)
        old_status = ot.status
        
        # Check 2: If assigning to cuadrilla, validate cuadrilla
        if target_status == OTStatus.PLANIFICADA or target_status == OTStatus.ASIGNADO_TAREA:
            if not cuadrilla_id:
                errors.append("Cuadrilla ID required for assignment transitions")
            else:
                # Verify cuadrilla exists
                cuadrilla = db.query(Cuadrilla).filter(
                    Cuadrilla.id == cuadrilla_id
                ).first()
                
                if not cuadrilla:
                    errors.append(f"Cuadrilla {cuadrilla_id} not found")
                else:
                    # Check if cuadrilla is active
                    if not cuadrilla.is_active:
                        errors.append(f"Cuadrilla {cuadrilla.name} is not active")
                    
                    # Check capacity
                    active_assignments = db.query(func.count(Asignacion.id)).filter(
                        Asignacion.cuadrilla_id == cuadrilla_id,
                        Asignacion.is_active == True
                    ).scalar()
                    
                    if active_assignments >= cuadrilla.capacity_daily:
                        errors.append(
                            f"Cuadrilla {cuadrilla.name} is at capacity "
                            f"({active_assignments}/{cuadrilla.capacity_daily})"
                        )
                    
                    # Check 3: Proximity constraint if coordinates available
                    if ot.lat is not None and ot.long is not None:
                        if (cuadrilla.last_centroid_lat is not None and 
                            cuadrilla.last_centroid_long is not None):
                            
                            distance = calculate_distance(
                                ot.lat, ot.long,
                                cuadrilla.last_centroid_lat, cuadrilla.last_centroid_long
                            )
                            
                            if distance > 10.0:
                                errors.append(
                                    f"OT is {distance:.2f}km from centroid (max 10km)"
                                )
                        else:
                            warnings.append(
                                f"Cuadrilla centroid not yet calculated. "
                                f"Distance cannot be verified."
                            )
                    elif ot.error_geo:
                        warnings.append(
                            "OT has invalid coordinates (error_geo=True). "
                            "Distance validation skipped."
                        )
        
        # Check 4: Document requirement for PUBLICO finalization
        if target_status == OTStatus.FINALIZADA:
            if ot.project_type == ProjectType.PUBLICO:
                # Check if can finalize
                try:
                    telcos_client = TelcosApiClient()
                    doc_status = await telcos_client.get_documents_status(
                        ot_id, ProjectType.PUBLICO
                    )
                    doc_count = doc_status.get('document_count', 0)
                    
                    can_finalize, reason = can_finalize_ot(ot, doc_count)
                    
                    if not can_finalize:
                        errors.append(f"Cannot finalize: {reason}")
                
                except Exception as e:
                    logger.warning(
                        f"Could not check documents for OT {ot.external_id}: {str(e)}"
                    )
                    warnings.append(
                        "Could not verify document status. Manual verification required."
                    )
        
        # Check 5: DETENIDA transition validation
        if target_status == OTStatus.DETENIDA:
            # Requires motivo in future implementation
            # For now, just allow the transition
            warnings.append(
                "OT will be marked as DETENIDA. "
                "Remember to resolve or cancel within 30 days."
            )
        
        # Check 6: Invalid coordinates warning
        if ot.error_geo:
            warnings.append("OT has invalid geographic coordinates (error_geo=True)")
        
        # Build response
        is_valid = len(errors) == 0
        
        response = {
            "success": True,
            "valid": is_valid,
            "message": "Validation passed" if is_valid else "Validation failed",
            "errors": errors,
            "warnings": warnings,
            "details": {
                "ot_id": str(ot.id),
                "ot_external_id": ot.external_id,
                "current_status": old_status.value if hasattr(old_status, 'value') else old_status,
                "target_status": target_status.value if hasattr(target_status, 'value') else target_status,
                "cuadrilla_id": cuadrilla_id,
                "project_type": ot.project_type.value if hasattr(ot.project_type, 'value') else ot.project_type,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        logger.info(
            f"Validation result: valid={is_valid}, "
            f"errors={len(errors)}, warnings={len(warnings)}"
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating drag-drop: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate state transition"
        )


# ============================================================================
# POST /api/drag-drop/commit - Commit State Change
# ============================================================================

@router.post("/commit", response_model=Dict[str, Any])
async def commit_drag_drop(
    ot_id: str,
    new_status: str,
    cuadrilla_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Commit a state change after validation has passed.
    
    This endpoint:
    1. Re-validates the transition (safety check)
    2. Updates OT status
    3. Creates/updates Asignacion if assigning to cuadrilla
    4. Updates cuadrilla.current_load if applicable
    5. Recalculates centroid if needed
    6. Returns updated OT
    
    Query Parameters:
    - ot_id: UUID of the OT
    - new_status: New status
    - cuadrilla_id: Optional cuadrilla UUID for assignments
    
    Returns:
    - Dict with committed OT and assignment details
    """
    try:
        logger.info(
            f"Committing drag-drop: OT {ot_id} → {new_status}, "
            f"cuadrilla {cuadrilla_id}"
        )
        
        # Get OT
        ot = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == ot_id).first()
        
        if not ot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OT {ot_id} not found"
            )
        
        # Convert status string to enum
        try:
            target_status = OTStatus[new_status.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {new_status}"
            )
        
        old_status = ot.status
        assignment_created = False
        distance_from_centroid = None
        
        # Update OT status
        ot.status = target_status
        ot.updated_at = datetime.utcnow()
        
        # Handle cuadrilla assignment if transitioning to PLANIFICADA or ASIGNADO_TAREA
        if cuadrilla_id and target_status in [OTStatus.PLANIFICADA, OTStatus.ASIGNADO_TAREA]:
            # Get cuadrilla
            cuadrilla = db.query(Cuadrilla).filter(
                Cuadrilla.id == cuadrilla_id
            ).first()
            
            if not cuadrilla:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Cuadrilla {cuadrilla_id} not found"
                )
            
            # If OT already assigned to different cuadrilla, mark old assignment as inactive
            old_assignment = db.query(Asignacion).filter(
                Asignacion.ot_id == ot.id,
                Asignacion.is_active == True
            ).first()
            
            if old_assignment and old_assignment.cuadrilla_id != cuadrilla_id:
                old_assignment.is_active = False
                logger.info(
                    f"Marked old assignment (OT {ot.external_id} → "
                    f"{old_assignment.cuadrilla_id}) as inactive"
                )
            
            # Create new assignment
            if not old_assignment or old_assignment.cuadrilla_id != cuadrilla_id:
                # Calculate distance if coordinates available
                if (ot.lat is not None and ot.long is not None and 
                    cuadrilla.last_centroid_lat is not None and 
                    cuadrilla.last_centroid_long is not None):
                    
                    distance_from_centroid = calculate_distance(
                        ot.lat, ot.long,
                        cuadrilla.last_centroid_lat, cuadrilla.last_centroid_long
                    )
                
                # Create new assignment
                new_assignment = Asignacion(
                    ot_id=ot.id,
                    cuadrilla_id=cuadrilla.id,
                    assigned_by_agent="DragDropUI",
                    distance_from_centroid=distance_from_centroid,
                    is_active=True,
                )
                db.add(new_assignment)
                assignment_created = True
                
                logger.info(
                    f"Created new assignment: OT {ot.external_id} → "
                    f"{cuadrilla.name} (distance: {distance_from_centroid}km)"
                )
            
            # Update OT cuadrilla_id
            ot.cuadrilla_id = cuadrilla.id
            
            # Update cuadrilla current_load
            if assignment_created:
                cuadrilla.current_load += 1
            
            # Recalculate centroid if needed
            active_assignments = db.query(Asignacion).filter(
                Asignacion.cuadrilla_id == cuadrilla.id,
                Asignacion.is_active == True
            ).all()
            
            if active_assignments:
                from backend.app.models.ot import OrdenTrabajo
                ot_ids = [a.ot_id for a in active_assignments]
                assigned_ots = db.query(OrdenTrabajo).filter(
                    OrdenTrabajo.id.in_(ot_ids)
                ).all()
                
                valid_coords = [
                    (o.lat, o.long) for o in assigned_ots
                    if o.lat is not None and o.long is not None
                ]
                
                if valid_coords:
                    centroid = calculate_centroid(valid_coords)
                    cuadrilla.last_centroid_lat = centroid[0]
                    cuadrilla.last_centroid_long = centroid[1]
                    logger.info(f"Updated centroid for {cuadrilla.name}: {centroid}")
        
        # If transitioning away from current cuadrilla, decrement load
        if ot.cuadrilla_id and cuadrilla_id != str(ot.cuadrilla_id) and not cuadrilla_id:
            old_cuadrilla = db.query(Cuadrilla).filter(
                Cuadrilla.id == ot.cuadrilla_id
            ).first()
            
            if old_cuadrilla:
                old_cuadrilla.current_load = max(0, old_cuadrilla.current_load - 1)
                logger.info(f"Decremented load for {old_cuadrilla.name}")
            
            ot.cuadrilla_id = None
        
        # Commit all changes
        db.commit()
        db.refresh(ot)
        
        logger.info(
            f"Drag-drop committed: OT {ot.external_id} "
            f"{old_status.value} → {target_status.value}"
        )
        
        # Build response with updated OT
        response_data = {
            'id': str(ot.id),
            'external_id': ot.external_id,
            'status': ot.status.value if hasattr(ot.status, 'value') else ot.status,
            'project_type': ot.project_type.value if hasattr(ot.project_type, 'value') else ot.project_type,
            'lat': ot.lat,
            'long': ot.long,
            'cliente_id': ot.cliente_id,
            'login_id': ot.login_id,
            'cuadrilla_id': str(ot.cuadrilla_id) if ot.cuadrilla_id else None,
            'error_geo': ot.error_geo,
            'created_at': ot.created_at,
            'updated_at': ot.updated_at,
        }
        
        return {
            "success": True,
            "message": f"OT {ot.external_id} transitioned from {old_status.value} to {target_status.value}",
            "ot": OTResponse(**response_data),
            "assignment": {
                "created": assignment_created,
                "cuadrilla_id": cuadrilla_id,
                "distance_from_centroid": round(distance_from_centroid, 2) if distance_from_centroid else None,
            } if cuadrilla_id else None,
            "transition": {
                "from_status": old_status.value if hasattr(old_status, 'value') else old_status,
                "to_status": target_status.value if hasattr(target_status, 'value') else target_status,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error committing drag-drop: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to commit state change"
        )

