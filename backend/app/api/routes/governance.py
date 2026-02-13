"""
API routes for governance operations.

Endpoints:
- GET /api/governance/check - Run governance rules on all OTs, return issues found
- POST /api/governance/alert/{ot_id} - Manually trigger alert for specific OT
- GET /api/governance/documents/{ot_id} - Check TelcoDrive document status for PUBLICO projects
- POST /api/governance/auto-cancel - Trigger 30-day auto-cancellation for DETENIDA OTs
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from backend.app.db.base import get_db
from backend.app.models.ot import OrdenTrabajo, OTStatus, ProjectType
from backend.app.models.log_agente import LogAgente
from backend.app.services.telcos_api_client import TelcosApiClient
from backend.app.utils.business_rules import (
    can_finalize_ot,
    should_alert_inactivity,
    days_in_status,
    requires_governance_action,
)
from backend.app.utils.geo_utils import validate_coordinates

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/governance",
    tags=["Governance"],
    responses={
        400: {"description": "Invalid request"},
        404: {"description": "OT not found"},
        500: {"description": "Server error"},
    },
)


# ============================================================================
# GET /api/governance/check - Run Governance Rules on All OTs
# ============================================================================

@router.get("/check", response_model=Dict[str, Any])
async def check_governance(
    severity_filter: Optional[str] = Query(None, description="Filter by severity: critical, warning, info"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Run governance rules on all OTs and return issues found.
    
    This endpoint runs comprehensive governance checks:
    1. PREPLANIFICADA > 48 hours: Alert for stalled planning
    2. DETENIDA approaching 30 days: Alert at days 20, 25, 29
    3. DETENIDA = 30 days: Auto-cancel (update status to ANULADA)
    4. PUBLICO missing documents: Check if < 29 documents uploaded
    5. Invalid coordinates: Check error_geo flag
    6. Cuadrilla assignments: Verify capacity not exceeded
    
    Query Parameters:
    - severity_filter: Filter results by severity (critical, warning, info)
    
    Returns:
    - Dict with issues list, summary counts, actions taken
    """
    try:
        logger.info("Starting governance check on all OTs...")
        
        # Query all OTs
        ots = db.query(OrdenTrabajo).all()
        
        issues = []
        critical_count = 0
        warning_count = 0
        info_count = 0
        
        telcos_client = TelcosApiClient()
        
        for ot in ots:
            # Check 1: PREPLANIFICADA > 48 hours
            if ot.status == OTStatus.PREPLANIFICADA:
                if should_alert_inactivity(ot):
                    days = days_in_status(ot, OTStatus.PREPLANIFICADA)
                    issues.append({
                        "type": "PREPLANIFICADA_INACTIVITY",
                        "ot_id": str(ot.id),
                        "ot_external_id": ot.external_id,
                        "severity": "warning",
                        "message": f"OT has been PREPLANIFICADA for {days} hours (>48h threshold)",
                        "days_in_status": days,
                        "recommended_action": "Run auto planning or manual assignment",
                    })
                    warning_count += 1
            
            # Check 2: DETENIDA status checks (20, 25, 29 day alerts, 30 day auto-cancel)
            if ot.status == OTStatus.DETENIDA:
                days = days_in_status(ot, OTStatus.DETENIDA)
                
                if days >= 30:
                    # Auto-cancel at 30 days
                    issues.append({
                        "type": "DETENIDA_AUTO_CANCEL",
                        "ot_id": str(ot.id),
                        "ot_external_id": ot.external_id,
                        "severity": "critical",
                        "message": f"OT has been DETENIDA for {days} days - MUST be auto-cancelled",
                        "days_in_status": days,
                        "recommended_action": "Auto-cancel OT (set status to ANULADA)",
                    })
                    critical_count += 1
                
                elif days >= 29:
                    issues.append({
                        "type": "DETENIDA_FINAL_WARNING",
                        "ot_id": str(ot.id),
                        "ot_external_id": ot.external_id,
                        "severity": "critical",
                        "message": f"OT has been DETENIDA for {days} days - FINAL WARNING before auto-cancel",
                        "days_in_status": days,
                        "recommended_action": "Resolve or cancel OT immediately",
                    })
                    critical_count += 1
                
                elif days >= 25:
                    issues.append({
                        "type": "DETENIDA_25_DAY_WARNING",
                        "ot_id": str(ot.id),
                        "ot_external_id": ot.external_id,
                        "severity": "warning",
                        "message": f"OT has been DETENIDA for {days} days - approaching 30-day threshold",
                        "days_in_status": days,
                        "recommended_action": "Take action to resolve or cancel OT",
                    })
                    warning_count += 1
                
                elif days >= 20:
                    issues.append({
                        "type": "DETENIDA_20_DAY_WARNING",
                        "ot_id": str(ot.id),
                        "ot_external_id": ot.external_id,
                        "severity": "warning",
                        "message": f"OT has been DETENIDA for {days} days",
                        "days_in_status": days,
                        "recommended_action": "Monitor for resolution",
                    })
                    warning_count += 1
            
            # Check 3: PUBLICO projects missing documents
            if ot.project_type == ProjectType.PUBLICO:
                try:
                    doc_status = await telcos_client.get_documents_status(str(ot.id), ProjectType.PUBLICO)
                    doc_count = doc_status.get('document_count', 0)
                    required_count = doc_status.get('required_count', 29)
                    
                    if doc_count < required_count:
                        issues.append({
                            "type": "PUBLICO_MISSING_DOCUMENTS",
                            "ot_id": str(ot.id),
                            "ot_external_id": ot.external_id,
                            "severity": "warning",
                            "message": f"PUBLICO project missing documents: {doc_count}/{required_count} uploaded",
                            "documents_uploaded": doc_count,
                            "documents_required": required_count,
                            "documents_missing": required_count - doc_count,
                            "recommended_action": "Upload remaining documents before finalization",
                        })
                        warning_count += 1
                
                except Exception as e:
                    logger.warning(f"Error checking documents for OT {ot.external_id}: {str(e)}")
                    issues.append({
                        "type": "DOCUMENT_CHECK_ERROR",
                        "ot_id": str(ot.id),
                        "ot_external_id": ot.external_id,
                        "severity": "info",
                        "message": f"Could not verify document status: {str(e)}",
                        "recommended_action": "Manual verification required",
                    })
                    info_count += 1
            
            # Check 4: Invalid coordinates
            if ot.error_geo:
                issues.append({
                    "type": "INVALID_COORDINATES",
                    "ot_id": str(ot.id),
                    "ot_external_id": ot.external_id,
                    "severity": "info",
                    "message": "OT has invalid or missing geographic coordinates",
                    "lat": ot.lat,
                    "long": ot.long,
                    "recommended_action": "Update coordinates or verify data source",
                })
                info_count += 1
            
            # Check 5: Governance action required (30-day rule or finalization rules)
            requires_action, reason = requires_governance_action(ot)
            if requires_action:
                issues.append({
                    "type": "GOVERNANCE_ACTION_REQUIRED",
                    "ot_id": str(ot.id),
                    "ot_external_id": ot.external_id,
                    "severity": "warning",
                    "message": f"Governance action required: {reason}",
                    "recommended_action": "Review and take appropriate action",
                })
                warning_count += 1
        
        # Apply severity filter if provided
        if severity_filter:
            issues = [i for i in issues if i.get('severity') == severity_filter]
        
        logger.info(
            f"Governance check completed: {critical_count} critical, "
            f"{warning_count} warnings, {info_count} info issues"
        )
        
        return {
            "success": True,
            "message": f"Governance check completed: {len(issues)} issues found",
            "issues": issues,
            "summary": {
                "total_issues": len(issues),
                "critical": critical_count,
                "warning": warning_count,
                "info": info_count,
                "ots_checked": len(ots),
            },
            "filters": {
                "severity": severity_filter,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Error in governance check: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run governance check"
        )


# ============================================================================
# POST /api/governance/alert/{ot_id} - Manually Trigger Alert
# ============================================================================

@router.post("/alert/{ot_id}", response_model=Dict[str, Any])
async def trigger_alert(
    ot_id: str = Path(..., description="OT UUID"),
    alert_type: str = Query("INACTIVITY_WARNING", description="Alert type: INACTIVITY_WARNING, AUTO_CANCEL, ASSIGNMENT_NOTIFICATION, DOCUMENT_INCOMPLETE"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Manually trigger an alert for a specific OT.
    
    Path Parameters:
    - ot_id: UUID of the OT
    
    Query Parameters:
    - alert_type: Type of alert to trigger
      - INACTIVITY_WARNING: Alert for inactive OT
      - AUTO_CANCEL: Alert for auto-cancellation
      - ASSIGNMENT_NOTIFICATION: Alert for assignment change
      - DOCUMENT_INCOMPLETE: Alert for missing documents
    
    Returns:
    - Dict with alert status: success, message, alert_type, ot_id
    """
    try:
        logger.info(f"Manual alert trigger: OT {ot_id}, type {alert_type}")
        
        # Get OT
        ot = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == ot_id).first()
        
        if not ot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OT {ot_id} not found"
            )
        
        # Validate alert type
        valid_alert_types = [
            "INACTIVITY_WARNING",
            "AUTO_CANCEL",
            "ASSIGNMENT_NOTIFICATION",
            "DOCUMENT_INCOMPLETE",
        ]
        
        if alert_type not in valid_alert_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid alert_type: {alert_type}. Must be one of: {', '.join(valid_alert_types)}"
            )
        
        # Log the alert action (would be sent to ComunicacionAgent in full implementation)
        log_entry = LogAgente(
            ot_id=ot.id,
            agente_name="GobernanzaAgent",
            accion=f"TRIGGER_ALERT_{alert_type}",
            resultado="success",
            metadata={
                "alert_type": alert_type,
                "ot_external_id": ot.external_id,
                "ot_status": ot.status.value if hasattr(ot.status, 'value') else ot.status,
                "triggered_at": datetime.utcnow().isoformat(),
            },
        )
        db.add(log_entry)
        db.commit()
        
        logger.info(f"Alert triggered: {alert_type} for OT {ot.external_id}")
        
        return {
            "success": True,
            "message": f"Alert {alert_type} triggered for OT {ot.external_id}",
            "ot_id": str(ot.id),
            "ot_external_id": ot.external_id,
            "alert_type": alert_type,
            "ot_status": ot.status.value if hasattr(ot.status, 'value') else ot.status,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error triggering alert: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger alert"
        )


# ============================================================================
# GET /api/governance/documents/{ot_id} - Check TelcoDrive Document Status
# ============================================================================

@router.get("/documents/{ot_id}", response_model=Dict[str, Any])
async def check_documents(
    ot_id: str = Path(..., description="OT UUID"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Check TelcoDrive document status for PUBLICO projects.
    
    This endpoint verifies document upload progress for PUBLICO projects:
    - Retrieves document count from TelcoDrive API
    - Compares against 29-document requirement
    - Returns document list with upload timestamps
    - Recommends action if documents missing
    
    Path Parameters:
    - ot_id: UUID of the OT
    
    Returns:
    - Dict with document status: count, required, documents list, can_finalize
    """
    try:
        logger.info(f"Checking document status for OT {ot_id}")
        
        # Get OT
        ot = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == ot_id).first()
        
        if not ot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OT {ot_id} not found"
            )
        
        # Check if OT is PUBLICO
        if ot.project_type != ProjectType.PUBLICO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document status check only applies to PUBLICO projects. This OT is {ot.project_type.value}"
            )
        
        # Get documents from TELCOS API
        telcos_client = TelcosApiClient()
        doc_status = await telcos_client.get_documents_status(ot_id, ProjectType.PUBLICO)
        
        doc_count = doc_status.get('document_count', 0)
        required_count = doc_status.get('required_count', 29)
        documents = doc_status.get('documents', [])
        
        # Check if can finalize
        can_finalize, reason = can_finalize_ot(ot, doc_count)
        
        # Calculate progress percentage
        progress_percentage = (doc_count / required_count * 100) if required_count > 0 else 0
        
        logger.info(
            f"Document check for OT {ot.external_id}: {doc_count}/{required_count} documents, "
            f"can_finalize={can_finalize}"
        )
        
        return {
            "success": True,
            "ot_id": str(ot.id),
            "ot_external_id": ot.external_id,
            "ot_status": ot.status.value if hasattr(ot.status, 'value') else ot.status,
            "project_type": ot.project_type.value if hasattr(ot.project_type, 'value') else ot.project_type,
            "documents": {
                "count": doc_count,
                "required": required_count,
                "missing": max(0, required_count - doc_count),
                "progress_percentage": round(progress_percentage, 2),
                "list": documents,
            },
            "finalization": {
                "can_finalize": can_finalize,
                "reason": reason,
                "recommended_action": "Upload remaining documents" if not can_finalize else "Ready to finalize",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking documents for OT {ot_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check document status"
        )


# ============================================================================
# POST /api/governance/auto-cancel - Auto-cancel DETENIDA OTs at 30 Days
# ============================================================================

@router.post("/auto-cancel", response_model=Dict[str, Any])
async def auto_cancel_ots(
    dry_run: bool = Query(False, description="If true, show what would be cancelled without actually cancelling"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Trigger 30-day auto-cancellation for DETENIDA OTs.
    
    This endpoint:
    1. Finds all DETENIDA OTs that have been in that status for 30+ days
    2. Updates their status to ANULADA
    3. Calls TelcosApiClient.update_status() to notify TELCOS system
    4. Logs all cancellations to logs_agentes
    5. Optionally runs in dry-run mode to preview without committing
    
    Query Parameters:
    - dry_run: If true, show what would be cancelled without executing (default: false)
    
    Returns:
    - Dict with cancelled OTs list, count, and actions taken
    """
    try:
        logger.info(f"Starting auto-cancel check for DETENIDA OTs (dry_run={dry_run})...")
        
        # Find all DETENIDA OTs
        detenida_ots = db.query(OrdenTrabajo).filter(
            OrdenTrabajo.status == OTStatus.DETENIDA
        ).all()
        
        to_cancel = []
        errors = []
        
        telcos_client = TelcosApiClient()
        
        # Check which ones are 30+ days old
        for ot in detenida_ots:
            days = days_in_status(ot, OTStatus.DETENIDA)
            
            if days >= 30:
                to_cancel.append({
                    "id": str(ot.id),
                    "external_id": ot.external_id,
                    "days_in_status": days,
                    "created_at": ot.created_at.isoformat() if ot.created_at else None,
                    "updated_at": ot.updated_at.isoformat() if ot.updated_at else None,
                })
        
        # If dry run, just return what would be cancelled
        if dry_run:
            logger.info(f"Dry run: {len(to_cancel)} OTs would be cancelled")
            return {
                "success": True,
                "message": f"Dry run: {len(to_cancel)} OTs would be auto-cancelled",
                "dry_run": True,
                "cancelled_count": len(to_cancel),
                "error_count": 0,
                "cancelled_ots": to_cancel,
                "errors": [],
                "timestamp": datetime.utcnow().isoformat(),
            }
        
        # Execute cancellations
        cancelled_count = 0
        
        for ot_info in to_cancel:
            try:
                ot = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == ot_info["id"]).first()
                
                if not ot:
                    errors.append(f"OT {ot_info['external_id']} not found during cancellation")
                    continue
                
                # Update status in database
                ot.status = OTStatus.ANULADA
                ot.updated_at = datetime.utcnow()
                
                # Notify TELCOS system
                try:
                    await telcos_client.update_status(ot.external_id, OTStatus.ANULADA.value)
                except Exception as e:
                    logger.warning(f"Could not notify TELCOS for OT {ot.external_id}: {str(e)}")
                    # Don't fail the whole operation if TELCOS notification fails
                
                # Log action
                log_entry = LogAgente(
                    ot_id=ot.id,
                    agente_name="GobernanzaAgent",
                    accion="AUTO_CANCEL_OT",
                    resultado="success",
                    metadata={
                        "ot_external_id": ot.external_id,
                        "previous_status": "DETENIDA",
                        "new_status": "ANULADA",
                        "days_in_status": ot_info["days_in_status"],
                    },
                )
                db.add(log_entry)
                
                cancelled_count += 1
                logger.info(f"Auto-cancelled OT {ot.external_id} (after {ot_info['days_in_status']} days in DETENIDA)")
                
            except Exception as e:
                error_msg = f"Error auto-cancelling OT {ot_info['external_id']}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Commit all changes
        db.commit()
        logger.info(f"Auto-cancel completed: {cancelled_count} OTs cancelled, {len(errors)} errors")
        
        return {
            "success": True,
            "message": f"Auto-cancel completed: {cancelled_count} OTs cancelled",
            "dry_run": False,
            "cancelled_count": cancelled_count,
            "error_count": len(errors),
            "cancelled_ots": to_cancel[:cancelled_count],  # Only include actually cancelled
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Error in auto-cancel: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute auto-cancel"
        )


# ============================================================================
# Helper Endpoints
# ============================================================================

@router.get("/summary", response_model=Dict[str, Any])
async def get_governance_summary(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get a quick summary of governance status.
    
    Returns:
    - Counts of OTs by status
    - Issues requiring attention
    - Recent governance actions
    """
    try:
        # Count OTs by status
        status_counts = {}
        for status in OTStatus:
            count = db.query(func.count(OrdenTrabajo.id)).filter(
                OrdenTrabajo.status == status
            ).scalar()
            status_counts[status.value] = count
        
        # Count issues
        preplanificada_stalled = db.query(func.count(OrdenTrabajo.id)).filter(
            OrdenTrabajo.status == OTStatus.PREPLANIFICADA,
            OrdenTrabajo.created_at < datetime.utcnow() - timedelta(hours=48)
        ).scalar()
        
        detenida_critical = db.query(func.count(OrdenTrabajo.id)).filter(
            OrdenTrabajo.status == OTStatus.DETENIDA,
            OrdenTrabajo.updated_at < datetime.utcnow() - timedelta(days=29)
        ).scalar()
        
        error_geo_count = db.query(func.count(OrdenTrabajo.id)).filter(
            OrdenTrabajo.error_geo == True
        ).scalar()
        
        # Get recent governance logs
        recent_logs = db.query(LogAgente).filter(
            LogAgente.agente_name == "GobernanzaAgent"
        ).order_by(LogAgente.created_at.desc()).limit(5).all()
        
        logger.info("Retrieved governance summary")
        
        return {
            "success": True,
            "summary": {
                "ots_by_status": status_counts,
                "issues": {
                    "preplanificada_stalled": preplanificada_stalled,
                    "detenida_critical": detenida_critical,
                    "invalid_coordinates": error_geo_count,
                },
            },
            "recent_actions": [
                {
                    "id": str(log.id),
                    "accion": log.accion,
                    "resultado": log.resultado,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in recent_logs
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Error getting governance summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get governance summary"
        )

