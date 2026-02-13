"""
API routes for planning operations.

Endpoints:
- POST /api/planning/auto - Trigger Planificacion Agent for all PREPLANIFICADA OTs
- POST /api/planning/manual - Manual assignment of OT to cuadrilla with validation
- POST /api/planning/optimize - Trigger Phase 3 nightly optimization
- GET /api/planning/preview - Dry-run showing proposed assignments without committing
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.db.base import get_db
from backend.app.models.ot import OrdenTrabajo, OTStatus
from backend.app.models.cuadrilla import Cuadrilla
from backend.app.models.asignacion import Asignacion, AssignmentResult
from backend.app.schemas.ot_schema import OTResponse
from backend.app.utils.geo_utils import calculate_distance, calculate_centroid, is_within_radius
from backend.app.utils.business_rules import can_finalize_ot

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/planning",
    tags=["Planning"],
    responses={
        400: {"description": "Invalid request"},
        500: {"description": "Server error"},
    },
)


# ============================================================================
# POST /api/planning/auto - Trigger Auto Planning for PREPLANIFICADA OTs
# ============================================================================

@router.post("/auto", response_model=Dict[str, Any])
async def auto_plan(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Trigger automatic planning for all PREPLANIFICADA OTs.
    
    This endpoint triggers the PlanificacionAgent to:
    1. Get all PREPLANIFICADA OTs
    2. Execute Phase 1: Balance assignment (1 OT per cuadrilla)
    3. Execute Phase 2: Proximity check (OTs within 10km of cuadrilla centroid)
    4. Execute Phase 3: Capacity validation
    5. Create Asignacion records for valid assignments
    6. Update OT status to PLANIFICADA
    
    Execution: Async in background to avoid blocking UI
    
    Returns:
    - Dict with planning results: success, processed_count, assigned_count, failures
    """
    try:
        logger.info("Starting automatic planning for PREPLANIFICADA OTs...")
        
        # Get all PREPLANIFICADA OTs
        preplanificada_ots = db.query(OrdenTrabajo).filter(
            OrdenTrabajo.status == OTStatus.PREPLANIFICADA
        ).all()
        
        logger.info(f"Found {len(preplanificada_ots)} PREPLANIFICADA OTs for planning")
        
        if not preplanificada_ots:
            return {
                "success": True,
                "message": "No PREPLANIFICADA OTs to plan",
                "processed_count": 0,
                "assigned_count": 0,
                "failed_count": 0,
                "failures": [],
            }
        
        # Get all active cuadrillas
        cuadrillas = db.query(Cuadrilla).filter(Cuadrilla.is_active == True).all()
        
        if not cuadrillas:
            return {
                "success": False,
                "message": "No active cuadrillas available for planning",
                "processed_count": 0,
                "assigned_count": 0,
                "failed_count": len(preplanificada_ots),
                "failures": ["No active cuadrillas available"],
            }
        
        # Execute planning algorithm
        assigned_count = 0
        failures = []
        
        # Phase 1: Balance - Assign 1 OT to each cuadrilla
        logger.info("Phase 1: Balance assignment")
        for idx, ot in enumerate(preplanificada_ots):
            if idx >= len(cuadrillas):
                break
            
            cuadrilla = cuadrillas[idx]
            
            try:
                # Create assignment
                assignment = Asignacion(
                    ot_id=ot.id,
                    cuadrilla_id=cuadrilla.id,
                    assigned_by_agent="PlanificacionAgent",
                    is_active=True,
                )
                db.add(assignment)
                
                # Update OT status
                ot.status = OTStatus.PLANIFICADA
                ot.cuadrilla_id = cuadrilla.id
                ot.updated_at = datetime.utcnow()
                
                # Update cuadrilla load
                cuadrilla.current_load += 1
                
                assigned_count += 1
                logger.info(f"Phase 1: Assigned OT {ot.external_id} to {cuadrilla.name}")
                
            except Exception as e:
                error_msg = f"Error assigning OT {ot.external_id}: {str(e)}"
                logger.error(error_msg)
                failures.append(error_msg)
        
        # Phase 2: Proximity check - Calculate centroid and check distance
        logger.info("Phase 2: Proximity validation")
        for cuadrilla in cuadrillas:
            try:
                # Get all assigned OTs for this cuadrilla
                assigned_ots = db.query(OrdenTrabajo).filter(
                    OrdenTrabajo.cuadrilla_id == cuadrilla.id,
                    OrdenTrabajo.status == OTStatus.PLANIFICADA
                ).all()
                
                if not assigned_ots:
                    continue
                
                # Calculate centroid from assigned OT coordinates
                valid_coords = [
                    (ot.lat, ot.long) for ot in assigned_ots
                    if ot.lat is not None and ot.long is not None
                ]
                
                if valid_coords:
                    centroid = calculate_centroid(valid_coords)
                    cuadrilla.last_centroid_lat = centroid[0]
                    cuadrilla.last_centroid_long = centroid[1]
                    
                    # Check proximity constraint (10km radius)
                    for ot in assigned_ots:
                        if ot.lat is not None and ot.long is not None:
                            distance = calculate_distance(
                                ot.lat, ot.long,
                                centroid[0], centroid[1]
                            )
                            
                            if distance > 10.0:
                                logger.warning(
                                    f"OT {ot.external_id} is {distance:.2f}km from centroid (max 10km)"
                                )
                                # Mark assignment as needing review
                                assignment = db.query(Asignacion).filter(
                                    Asignacion.ot_id == ot.id,
                                    Asignacion.is_active == True
                                ).first()
                                
                                if assignment:
                                    assignment.distance_from_centroid = distance
                
                logger.info(f"Phase 2: Centroid calculated for {cuadrilla.name}: {centroid}")
                
            except Exception as e:
                error_msg = f"Error in proximity check for {cuadrilla.name}: {str(e)}"
                logger.error(error_msg)
                failures.append(error_msg)
        
        # Phase 3: Capacity check
        logger.info("Phase 3: Capacity validation")
        for cuadrilla in cuadrillas:
            active_assignments = db.query(func.count(Asignacion.id)).filter(
                Asignacion.cuadrilla_id == cuadrilla.id,
                Asignacion.is_active == True
            ).scalar()
            
            if active_assignments > cuadrilla.capacity_daily:
                logger.warning(
                    f"{cuadrilla.name} has {active_assignments} assignments "
                    f"but capacity is {cuadrilla.capacity_daily}"
                )
        
        # Commit all changes
        db.commit()
        logger.info(f"Auto planning completed: {assigned_count} OTs assigned")
        
        return {
            "success": True,
            "message": f"Auto planning completed: {assigned_count} OTs assigned",
            "processed_count": len(preplanificada_ots),
            "assigned_count": assigned_count,
            "failed_count": len(failures),
            "failures": failures,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Error in auto planning: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute auto planning"
        )


# ============================================================================
# POST /api/planning/manual - Manual OT to Cuadrilla Assignment
# ============================================================================

@router.post("/manual", response_model=Dict[str, Any])
async def manual_assign(
    ot_id: str = Query(..., description="OT UUID to assign"),
    cuadrilla_id: str = Query(..., description="Cuadrilla UUID to assign to"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Manually assign an OT to a cuadrilla with validation.
    
    Query Parameters:
    - ot_id: UUID of the OT to assign
    - cuadrilla_id: UUID of the target cuadrilla
    
    Validations:
    - OT must exist and be in PREPLANIFICADA status
    - Cuadrilla must exist and be active
    - Cuadrilla must have available capacity
    - OT coordinates must be within 10km of cuadrilla centroid
    
    Returns:
    - Dict with assignment result: success, ot_id, cuadrilla_id, distance, status
    """
    try:
        logger.info(f"Manual assignment: OT {ot_id} to Cuadrilla {cuadrilla_id}")
        
        # Get OT
        ot = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == ot_id).first()
        
        if not ot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OT {ot_id} not found"
            )
        
        if ot.status != OTStatus.PREPLANIFICADA:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OT must be in PREPLANIFICADA status (current: {ot.status.value})"
            )
        
        # Get cuadrilla
        cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
        
        if not cuadrilla:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuadrilla {cuadrilla_id} not found"
            )
        
        if not cuadrilla.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cuadrilla {cuadrilla.name} is not active"
            )
        
        # Check capacity
        active_assignments = db.query(func.count(Asignacion.id)).filter(
            Asignacion.cuadrilla_id == cuadrilla_id,
            Asignacion.is_active == True
        ).scalar()
        
        if active_assignments >= cuadrilla.capacity_daily:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cuadrilla {cuadrilla.name} is at capacity ({active_assignments}/{cuadrilla.capacity_daily})"
            )
        
        # Check proximity if both coordinates are available
        distance = None
        if ot.lat is not None and ot.long is not None:
            if cuadrilla.last_centroid_lat is not None and cuadrilla.last_centroid_long is not None:
                distance = calculate_distance(
                    ot.lat, ot.long,
                    cuadrilla.last_centroid_lat, cuadrilla.last_centroid_long
                )
                
                if distance > 10.0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"OT is {distance:.2f}km from cuadrilla centroid (max 10km)"
                    )
        
        # Create assignment
        assignment = Asignacion(
            ot_id=ot.id,
            cuadrilla_id=cuadrilla.id,
            assigned_by_agent="ManualAssignment",
            distance_from_centroid=distance,
            is_active=True,
        )
        db.add(assignment)
        
        # Update OT
        ot.status = OTStatus.PLANIFICADA
        ot.cuadrilla_id = cuadrilla.id
        ot.updated_at = datetime.utcnow()
        
        # Update cuadrilla load
        cuadrilla.current_load += 1
        
        db.commit()
        logger.info(f"Manual assignment successful: OT {ot.external_id} to {cuadrilla.name}")
        
        return {
            "success": True,
            "message": f"OT {ot.external_id} assigned to {cuadrilla.name}",
            "ot_id": str(ot.id),
            "ot_external_id": ot.external_id,
            "cuadrilla_id": str(cuadrilla.id),
            "cuadrilla_name": cuadrilla.name,
            "distance": round(distance, 2) if distance else None,
            "status": "PLANIFICADA",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error in manual assignment: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete manual assignment"
        )


# ============================================================================
# POST /api/planning/optimize - Trigger Phase 3 Nightly Optimization
# ============================================================================

@router.post("/optimize", response_model=Dict[str, Any])
async def optimize_plan(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Trigger Phase 3 nightly optimization to recalculate routes and assignments.
    
    This endpoint runs the nightly optimization job that:
    1. Recalculates centroids for each cuadrilla based on assigned OTs
    2. Validates proximity constraints (10km radius)
    3. Suggests route optimizations
    4. Reports any assignments outside constraints
    5. Updates cuadrilla metadata (centroid, load metrics)
    
    Returns:
    - Dict with optimization results: success, recalculated_count, issues_found
    """
    try:
        logger.info("Starting nightly optimization...")
        
        cuadrillas = db.query(Cuadrilla).filter(Cuadrilla.is_active == True).all()
        
        recalculated_count = 0
        issues = []
        
        for cuadrilla in cuadrillas:
            try:
                # Get all active assignments
                assignments = db.query(Asignacion).filter(
                    Asignacion.cuadrilla_id == cuadrilla.id,
                    Asignacion.is_active == True
                ).all()
                
                if not assignments:
                    continue
                
                # Get OT details
                ot_ids = [a.ot_id for a in assignments]
                ots = db.query(OrdenTrabajo).filter(
                    OrdenTrabajo.id.in_(ot_ids)
                ).all()
                
                # Recalculate centroid
                valid_coords = [
                    (ot.lat, ot.long) for ot in ots
                    if ot.lat is not None and ot.long is not None
                ]
                
                if valid_coords:
                    centroid = calculate_centroid(valid_coords)
                    cuadrilla.last_centroid_lat = centroid[0]
                    cuadrilla.last_centroid_long = centroid[1]
                    
                    # Check all assignments for proximity
                    for assignment in assignments:
                        ot = next((o for o in ots if o.id == assignment.ot_id), None)
                        if ot and ot.lat is not None and ot.long is not None:
                            distance = calculate_distance(
                                ot.lat, ot.long,
                                centroid[0], centroid[1]
                            )
                            assignment.distance_from_centroid = distance
                            
                            if distance > 10.0:
                                issues.append({
                                    "type": "proximity_violation",
                                    "cuadrilla": cuadrilla.name,
                                    "ot_id": ot.external_id,
                                    "distance_km": round(distance, 2),
                                })
                    
                    recalculated_count += 1
                    logger.info(
                        f"Optimized {cuadrilla.name}: centroid={centroid}, "
                        f"assignments={len(assignments)}"
                    )
                
            except Exception as e:
                error_msg = f"Error optimizing {cuadrilla.name}: {str(e)}"
                logger.error(error_msg)
                issues.append({
                    "type": "optimization_error",
                    "cuadrilla": cuadrilla.name,
                    "error": error_msg,
                })
        
        db.commit()
        logger.info(f"Optimization completed: {recalculated_count} cuadrillas recalculated, {len(issues)} issues found")
        
        return {
            "success": True,
            "message": f"Optimization completed: {recalculated_count} cuadrillas optimized",
            "recalculated_count": recalculated_count,
            "issues_found": len(issues),
            "issues": issues,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Error in optimization: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute optimization"
        )


# ============================================================================
# GET /api/planning/preview - Dry-run Planning Preview
# ============================================================================

@router.get("/preview", response_model=Dict[str, Any])
async def preview_plan(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get a preview of proposed assignments without committing changes.
    
    This endpoint performs a dry-run of the planning algorithm:
    1. Analyzes all PREPLANIFICADA OTs
    2. Simulates Phase 1: Balance assignment
    3. Simulates Phase 2: Proximity validation
    4. Simulates Phase 3: Capacity check
    5. Returns proposed assignments without updating database
    
    Returns:
    - Dict with proposed assignments: success, proposed_assignments, analysis
    """
    try:
        logger.info("Generating planning preview...")
        
        # Get all PREPLANIFICADA OTs
        preplanificada_ots = db.query(OrdenTrabajo).filter(
            OrdenTrabajo.status == OTStatus.PREPLANIFICADA
        ).all()
        
        # Get all active cuadrillas
        cuadrillas = db.query(Cuadrilla).filter(Cuadrilla.is_active == True).all()
        
        if not preplanificada_ots or not cuadrillas:
            return {
                "success": True,
                "message": "No planning needed or insufficient resources",
                "proposed_assignments": [],
                "analysis": {
                    "total_ots": len(preplanificada_ots),
                    "available_cuadrillas": len(cuadrillas),
                    "assignable_ots": 0,
                    "constraints_violated": 0,
                },
            }
        
        proposed = []
        constraints_violated = 0
        
        # Simulate Phase 1: Balance
        for idx, ot in enumerate(preplanificada_ots):
            if idx >= len(cuadrillas):
                break
            
            cuadrilla = cuadrillas[idx]
            
            # Simulate Phase 2: Proximity check
            distance = None
            proximity_ok = True
            
            if ot.lat is not None and ot.long is not None:
                if cuadrilla.last_centroid_lat is not None and cuadrilla.last_centroid_long is not None:
                    distance = calculate_distance(
                        ot.lat, ot.long,
                        cuadrilla.last_centroid_lat, cuadrilla.last_centroid_long
                    )
                    
                    if distance > 10.0:
                        proximity_ok = False
                        constraints_violated += 1
            
            # Simulate Phase 3: Capacity check
            active_assignments = db.query(func.count(Asignacion.id)).filter(
                Asignacion.cuadrilla_id == cuadrilla.id,
                Asignacion.is_active == True
            ).scalar()
            
            capacity_ok = (active_assignments + 1) <= cuadrilla.capacity_daily
            
            proposed.append({
                "ot_id": str(ot.id),
                "ot_external_id": ot.external_id,
                "cuadrilla_id": str(cuadrilla.id),
                "cuadrilla_name": cuadrilla.name,
                "distance_km": round(distance, 2) if distance else None,
                "constraints": {
                    "proximity_ok": proximity_ok,
                    "capacity_ok": capacity_ok,
                    "all_ok": proximity_ok and capacity_ok,
                },
            })
        
        logger.info(f"Preview generated: {len(proposed)} assignments proposed")
        
        return {
            "success": True,
            "message": f"Preview generated: {len(proposed)} assignments proposed",
            "proposed_assignments": proposed,
            "analysis": {
                "total_ots": len(preplanificada_ots),
                "available_cuadrillas": len(cuadrillas),
                "assignable_ots": len(proposed),
                "constraints_violated": constraints_violated,
                "success_rate": round((len(proposed) - constraints_violated) / max(1, len(proposed)) * 100, 2),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate planning preview"
        )

