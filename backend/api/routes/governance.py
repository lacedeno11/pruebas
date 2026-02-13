"""
Governance endpoints for state transition validation and inactivity monitoring.
Implements business rules checking for OT status changes.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database.base import get_db
from backend.database import schemas, models

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/governance", tags=["governance"])


# ============================================================================
# GET Endpoints
# ============================================================================


@router.get("/alerts", response_model=List[schemas.GovernanceAlert])
async def get_governance_alerts(
    urgency: Optional[str] = Query(None, description="Filter by urgency level"),
    db: Session = Depends(get_db),
):
    """
    Get list of OTs requiring governance attention.
    
    Includes OTs approaching or exceeding inactivity thresholds.
    
    Query Parameters:
    - urgency: Filter by urgency level (LOW, MEDIUM, HIGH, CRITICAL)
    
    Returns:
        List of governance alerts sorted by urgency
    """
    try:
        alerts = []
        
        # Check for PREPLANIFICADA OTs without assignment (>48 hours)
        preplanificada_ots = db.query(models.OrdenTrabajo).filter(
            models.OrdenTrabajo.status == models.OTStatus.PREPLANIFICADA,
            models.OrdenTrabajo.cuadrilla_id == None,
        ).all()
        
        for ot in preplanificada_ots:
            hours_elapsed = (datetime.now() - ot.created_at).total_seconds() / 3600
            
            if hours_elapsed > 48:
                alert = schemas.GovernanceAlert(
                    ot_id=ot.id,
                    external_id=ot.external_id,
                    status=ot.status,
                    days_in_status=int(hours_elapsed / 24),
                    reason=f"Unassigned for {int(hours_elapsed)} hours",
                    urgency="CRITICAL" if hours_elapsed > 72 else "HIGH",
                    action_recommended="Assign to available cuadrilla",
                )
                alerts.append(alert)
        
        # Check for DETENIDA OTs (inactivity alerts)
        detenida_ots = db.query(models.OrdenTrabajo).filter(
            models.OrdenTrabajo.status == models.OTStatus.DETENIDA,
        ).all()
        
        inactivity_alert_days = [20, 25, 29]
        auto_cancel_days = 30
        
        for ot in detenida_ots:
            days_elapsed = (datetime.now() - ot.updated_at).days
            
            if days_elapsed >= auto_cancel_days:
                # Auto-cancel threshold reached
                alert = schemas.GovernanceAlert(
                    ot_id=ot.id,
                    external_id=ot.external_id,
                    status=ot.status,
                    days_in_status=days_elapsed,
                    reason=f"Exceeded {auto_cancel_days} days in DETENIDA state",
                    urgency="CRITICAL",
                    action_recommended="Auto-cancel (ANULADA)",
                )
                alerts.append(alert)
            elif days_elapsed in inactivity_alert_days:
                # Inactivity warning threshold
                alert = schemas.GovernanceAlert(
                    ot_id=ot.id,
                    external_id=ot.external_id,
                    status=ot.status,
                    days_in_status=days_elapsed,
                    reason=f"{days_elapsed} days in DETENIDA state",
                    urgency="HIGH" if days_elapsed >= 25 else "MEDIUM",
                    action_recommended="Review detention reason",
                )
                alerts.append(alert)
        
        # Filter by urgency if requested
        if urgency:
            alerts = [a for a in alerts if a.urgency == urgency]
        
        # Sort by urgency and days in status
        urgency_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        alerts.sort(key=lambda a: (urgency_order.get(a.urgency, 4), -a.days_in_status))
        
        return alerts
    except Exception as e:
        logger.error(f"Error fetching governance alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching governance alerts",
        )


@router.get("/detention-reasons", response_model=List[str])
async def get_detention_reasons(
    db: Session = Depends(get_db),
):
    """
    Get list of valid detention reasons from system ontology.
    
    Returns:
        List of valid detention reasons
    """
    # TODO: Load from ontology configuration or database
    valid_reasons = [
        "Espera de aprobación de cliente",
        "Falta de materiales",
        "Problema técnico en instalación",
        "Falta de acceso a locación",
        "Espera de terceros",
        "Documentación incompleta",
        "Otro",
    ]
    return valid_reasons


# ============================================================================
# POST Endpoints
# ============================================================================


@router.post("/check-inactivity", response_model=dict)
async def check_inactivity_manual(
    db: Session = Depends(get_db),
):
    """
    Manually trigger inactivity check.
    
    Normally runs daily at 09:00 via scheduler.
    For testing purposes, can be triggered manually.
    
    Returns:
        Check results
    """
    try:
        alerts = await get_governance_alerts(db=db)
        
        return {
            "success": True,
            "message": "Inactivity check completed",
            "alerts_count": len(alerts),
            "critical_count": len([a for a in alerts if a.urgency == "CRITICAL"]),
            "alerts": alerts[:10],  # Return top 10 alerts
        }
    except Exception as e:
        logger.error(f"Error checking inactivity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error checking inactivity",
        )


@router.post("/validate-transition", response_model=dict)
async def validate_state_transition(
    request: schemas.StateTransitionRequest,
    db: Session = Depends(get_db),
):
    """
    Validate an OT state transition according to business rules.
    
    Request Body:
    - ot_id: OT ID
    - new_status: Proposed new status
    - reason: Reason for transition (required for DETENIDA/ANULADA)
    
    Returns:
        Validation result with error message if invalid
    """
    try:
        # Get OT
        ot = db.query(models.OrdenTrabajo).filter(
            models.OrdenTrabajo.id == request.ot_id
        ).first()
        
        if not ot:
            return {
                "valid": False,
                "error": f"OT with id {request.ot_id} not found",
            }
        
        current_status = ot.status
        new_status = request.new_status
        
        # Define valid state transitions
        valid_transitions = {
            models.OTStatus.PREPLANIFICADA: [
                models.OTStatus.PLANIFICADA,
                models.OTStatus.ANULADA,
            ],
            models.OTStatus.PLANIFICADA: [
                models.OTStatus.ASIGNADO_TAREA,
                models.OTStatus.DETENIDA,
                models.OTStatus.ANULADA,
            ],
            models.OTStatus.ASIGNADO_TAREA: [
                models.OTStatus.DETENIDA,
                models.OTStatus.FINALIZADA,
                models.OTStatus.ANULADA,
            ],
            models.OTStatus.DETENIDA: [
                models.OTStatus.PLANIFICADA,
                models.OTStatus.ANULADA,
            ],
            models.OTStatus.FINALIZADA: [],  # No transitions allowed
            models.OTStatus.ANULADA: [],  # No transitions allowed
        }
        
        # Check if transition is valid
        if new_status not in valid_transitions.get(current_status, []):
            return {
                "valid": False,
                "error": f"Invalid transition from {current_status} to {new_status}",
                "valid_next_states": [s.value for s in valid_transitions.get(current_status, [])],
            }
        
        # Check DETENIDA/ANULADA require reason
        if new_status in [models.OTStatus.DETENIDA, models.OTStatus.ANULADA]:
            if not request.reason:
                return {
                    "valid": False,
                    "error": f"Reason is required for {new_status} status",
                }
        
        # Check PUBLICO projects must have documents before FINALIZADA
        if new_status == models.OTStatus.FINALIZADA and ot.project_type == models.ProjectType.PUBLICO:
            # TODO: Check document count via MockApiService
            # For now, just note this should be validated
            return {
                "valid": False,
                "error": "PUBLICO projects must have >=29 documents to be FINALIZADA",
                "action": "validate_publico_documents",
            }
        
        return {
            "valid": True,
            "message": f"Transition from {current_status} to {new_status} is valid",
            "current_status": current_status.value,
            "new_status": new_status.value,
        }
    except Exception as e:
        logger.error(f"Error validating state transition: {e}")
        return {
            "valid": False,
            "error": "Error validating state transition",
        }


@router.post("/validate-publico", response_model=dict)
async def validate_publico_project(
    request: schemas.StateTransitionRequest,
    db: Session = Depends(get_db),
):
    """
    Validate PUBLICO project document count before FINALIZADA.
    
    Request Body:
    - ot_id: OT ID
    
    Returns:
        Validation result with document count
    """
    try:
        ot = db.query(models.OrdenTrabajo).filter(
            models.OrdenTrabajo.id == request.ot_id
        ).first()
        
        if not ot:
            return {
                "valid": False,
                "error": f"OT with id {request.ot_id} not found",
            }
        
        if ot.project_type != models.ProjectType.PUBLICO:
            return {
                "valid": True,
                "message": "Not a PUBLICO project",
                "document_check_required": False,
            }
        
        # TODO: Call MockApiService.get_telcodrive_documents(ot.external_id)
        # For now, return placeholder
        
        return {
            "valid": False,
            "message": "Document count validation pending MockApiService integration",
            "document_count": 0,
            "required_documents": 29,
            "action": "integrate_mockapi",
        }
    except Exception as e:
        logger.error(f"Error validating PUBLICO project: {e}")
        return {
            "valid": False,
            "error": "Error validating PUBLICO project",
        }


@router.post("/validate-detention-reason", response_model=dict)
async def validate_detention_reason(
    request: schemas.DetentionReasonValidationRequest,
    db: Session = Depends(get_db),
):
    """
    Validate a detention reason against system ontology.
    
    Request Body:
    - reason: Detention reason text
    
    Returns:
        Validation result
    """
    try:
        valid_reasons = [
            "Espera de aprobación de cliente",
            "Falta de materiales",
            "Problema técnico en instalación",
            "Falta de acceso a locación",
            "Espera de terceros",
            "Documentación incompleta",
            "Otro",
        ]
        
        reason_lower = request.reason.lower()
        
        # Check for exact or partial match
        is_valid = any(
            vr.lower() in reason_lower or reason_lower in vr.lower()
            for vr in valid_reasons
        )
        
        return {
            "valid": is_valid,
            "message": "Valid detention reason" if is_valid else "Reason does not match any valid reasons",
            "provided_reason": request.reason,
            "valid_reasons": valid_reasons,
        }
    except Exception as e:
        logger.error(f"Error validating detention reason: {e}")
        return {
            "valid": False,
            "error": "Error validating detention reason",
        }

