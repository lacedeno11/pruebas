"""
Planning and assignment endpoints for OT-to-Cuadrilla assignments.
Implements manual and automatic planning via PlanificacionAgent.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.orm import Session

from backend.database.base import get_db
from backend.database import schemas, models
from backend.services.cuadrilla_service import CuadrillaService
from backend.services.ot_service import OTService
from backend.services.geo_service import GeoService

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/planning", tags=["planning"])

# Initialize services
cuadrilla_service = CuadrillaService()
ot_service = OTService()
geo_service = GeoService()


# ============================================================================
# GET Endpoints
# ============================================================================


@router.get("/assignments", response_model=List[schemas.AsignacionResponse])
async def get_assignments(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    cuadrilla_id: Optional[int] = Query(None, description="Filter by cuadrilla ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db),
):
    """
    Get assignments with optional filtering by date and cuadrilla.
    
    Query Parameters:
    - date_from: Start date for filtering (format: YYYY-MM-DD)
    - date_to: End date for filtering (format: YYYY-MM-DD)
    - cuadrilla_id: Filter by specific cuadrilla ID
    - skip: Pagination offset
    - limit: Maximum number of results
    
    Returns:
        List of Asignacion objects with OT and Cuadrilla details
    """
    try:
        query = db.query(models.Asignacion)
        
        # Apply filters
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(models.Asignacion.assigned_at >= from_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_from format. Use YYYY-MM-DD",
                )
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
                query = query.filter(models.Asignacion.assigned_at < to_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_to format. Use YYYY-MM-DD",
                )
        
        if cuadrilla_id:
            query = query.filter(models.Asignacion.cuadrilla_id == cuadrilla_id)
        
        # Execute query with pagination
        assignments = query.order_by(models.Asignacion.assigned_at.desc()).offset(skip).limit(limit).all()
        return assignments
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching assignments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching assignments",
        )


# ============================================================================
# POST Endpoints
# ============================================================================


@router.post("/auto", response_model=dict)
async def auto_planning(
    request: schemas.PlanningAutoRequest = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Trigger automatic planning algorithm (3-phase planning).
    
    Optional Request Body:
    - project_type: Filter by project type (PUBLICO, PRIVADO, TERCERIZADO)
    - priority: Priority level for planning
    
    Returns:
        Planning results with assigned OTs count and details
        
    Note:
        This would normally trigger PlanificacionAgent via Orchestrator.
        For now, returns a placeholder response.
    """
    try:
        # Get unassigned OTs
        unassigned_ots = ot_service.get_unassigned_ots(db)
        
        if not unassigned_ots:
            return {
                "success": True,
                "message": "No unassigned OTs to plan",
                "assigned_count": 0,
                "assignments": [],
            }
        
        logger.info(f"Starting automatic planning for {len(unassigned_ots)} OTs")
        
        # TODO: Integrate with PlanificacionAgent via Orchestrator
        # For now, return placeholder response
        
        return {
            "success": True,
            "message": "Planning initiated",
            "assigned_count": 0,
            "assignments": [],
            "note": "PlanificacionAgent integration pending",
        }
    except Exception as e:
        logger.error(f"Error in automatic planning: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error in automatic planning",
        )


@router.post("/manual", response_model=schemas.AssignmentResponse)
async def manual_assignment(
    request: schemas.ManualAssignmentRequest,
    db: Session = Depends(get_db),
):
    """
    Manually assign an OT to a cuadrilla (Drag & Drop from UI).
    
    Request Body:
    - ot_id: OT ID to assign
    - cuadrilla_id: Target cuadrilla ID
    - reason: Reason for assignment (optional)
    
    Returns:
        Assignment confirmation with distance to centroid
        
    Raises:
        404: If OT or cuadrilla not found
        409: If assignment validation fails
    """
    try:
        # Validate OT and cuadrilla exist
        ot = ot_service.get_ot_by_id(db, request.ot_id)
        if not ot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OT with id {request.ot_id} not found",
            )
        
        cuadrilla = cuadrilla_service.get_cuadrilla_by_id(db, request.cuadrilla_id)
        if not cuadrilla:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuadrilla with id {request.cuadrilla_id} not found",
            )
        
        # Validate assignment constraints
        if cuadrilla.current_load >= cuadrilla.capacity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cuadrilla {cuadrilla.name} is at capacity",
            )
        
        # Calculate distance to centroid
        distance_km = None
        if cuadrilla.last_centroid_lat and cuadrilla.last_centroid_long and ot.lat and ot.long:
            distance_km = geo_service.calculate_distance_km(
                ot.lat,
                ot.long,
                cuadrilla.last_centroid_lat,
                cuadrilla.last_centroid_long,
            )
            
            # Check proximity constraint (10km default)
            if not geo_service.is_within_radius(
                ot.lat,
                ot.long,
                cuadrilla.last_centroid_lat,
                cuadrilla.last_centroid_long,
                radius_km=10.0,
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"OT is {distance_km:.1f}km away from cuadrilla centroid (limit: 10km)",
                )
        
        # Create assignment
        assignment = models.Asignacion(
            ot_id=request.ot_id,
            cuadrilla_id=request.cuadrilla_id,
            assigned_by_agent="manual_ui",
            distance_to_centroid_km=distance_km,
        )
        
        # Update OT
        ot.cuadrilla_id = request.cuadrilla_id
        ot.status = models.OTStatus.ASIGNADO_TAREA
        ot.updated_at = datetime.now()
        
        # Update cuadrilla load
        cuadrilla.current_load += 1
        
        # Create log entry
        log = models.LogAgente(
            ot_id=request.ot_id,
            agente_name="manual_assignment",
            accion=f"Assigned to cuadrilla {cuadrilla.name}",
            resultado="success",
        )
        if request.reason:
            log.raw_llm_response = request.reason
        
        db.add(assignment)
        db.add(log)
        db.commit()
        db.refresh(assignment)
        
        logger.info(f"Manual assignment: OT {request.ot_id} -> Cuadrilla {request.cuadrilla_id}")
        
        return schemas.AssignmentResponse(
            success=True,
            ot_id=request.ot_id,
            cuadrilla_id=request.cuadrilla_id,
            distance_to_centroid_km=distance_km,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manual assignment: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error in manual assignment",
        )


@router.post("/assign", response_model=schemas.AssignmentResponse)
async def simple_assign(
    request: schemas.ManualAssignmentRequest,
    db: Session = Depends(get_db),
):
    """
    Simple OT assignment endpoint (wrapper around manual_assignment).
    
    Request Body:
    - ot_id: OT ID to assign
    - cuadrilla_id: Target cuadrilla ID
    
    Returns:
        Assignment confirmation
    """
    return await manual_assignment(request, db)


@router.post("/validate-assignment", response_model=dict)
async def validate_assignment(
    request: schemas.AssignmentValidationRequest,
    db: Session = Depends(get_db),
):
    """
    Validate an assignment without committing (for UI preview).
    
    Request Body:
    - ot_id: OT ID
    - cuadrilla_id: Target cuadrilla ID
    
    Returns:
        Validation result with error message if invalid
    """
    try:
        # Validate OT and cuadrilla exist
        ot = ot_service.get_ot_by_id(db, request.ot_id)
        if not ot:
            return {
                "valid": False,
                "error": f"OT with id {request.ot_id} not found",
            }
        
        cuadrilla = cuadrilla_service.get_cuadrilla_by_id(db, request.cuadrilla_id)
        if not cuadrilla:
            return {
                "valid": False,
                "error": f"Cuadrilla with id {request.cuadrilla_id} not found",
            }
        
        # Check capacity
        if cuadrilla.current_load >= cuadrilla.capacity:
            return {
                "valid": False,
                "error": f"Cuadrilla is at capacity ({cuadrilla.current_load}/{cuadrilla.capacity})",
            }
        
        # Check proximity
        distance_km = None
        if cuadrilla.last_centroid_lat and cuadrilla.last_centroid_long and ot.lat and ot.long:
            distance_km = geo_service.calculate_distance_km(
                ot.lat,
                ot.long,
                cuadrilla.last_centroid_lat,
                cuadrilla.last_centroid_long,
            )
            
            if not geo_service.is_within_radius(
                ot.lat,
                ot.long,
                cuadrilla.last_centroid_lat,
                cuadrilla.last_centroid_long,
                radius_km=10.0,
            ):
                return {
                    "valid": False,
                    "error": f"OT is {distance_km:.1f}km away from centroid (limit: 10km)",
                    "distance_km": distance_km,
                }
        
        return {
            "valid": True,
            "cuadrilla_name": cuadrilla.name,
            "distance_km": distance_km,
            "available_capacity": cuadrilla.capacity - cuadrilla.current_load,
        }
    except Exception as e:
        logger.error(f"Error validating assignment: {e}")
        return {
            "valid": False,
            "error": "Error validating assignment",
        }


@router.post("/recalculate-centroids", response_model=dict)
async def recalculate_centroids(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Manually trigger centroid recalculation for all cuadrillas.
    
    This implements Phase 3 of the planning algorithm (nocturnal normalization).
    Normally runs at 00:00 daily via scheduler.
    
    Returns:
        Confirmation of centroid recalculation task
    """
    try:
        # Get all cuadrillas
        cuadrillas = db.query(models.Cuadrilla).all()
        
        if not cuadrillas:
            return {
                "success": True,
                "message": "No cuadrillas to recalculate",
                "updated_count": 0,
            }
        
        # Add background task
        background_tasks.add_task(
            _recalculate_all_centroids,
            cuadrilla_ids=[c.id for c in cuadrillas],
            db=db,
        )
        
        logger.info(f"Initiated centroid recalculation for {len(cuadrillas)} cuadrillas")
        
        return {
            "success": True,
            "message": "Centroid recalculation initiated",
            "cuadrillas_count": len(cuadrillas),
        }
    except Exception as e:
        logger.error(f"Error initiating centroid recalculation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error initiating centroid recalculation",
        )


# ============================================================================
# DELETE Endpoints
# ============================================================================


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete an assignment (unassign OT from cuadrilla).
    
    Path Parameters:
    - assignment_id: Assignment ID
    
    Raises:
        404: If assignment not found
    """
    try:
        assignment = db.query(models.Asignacion).filter(
            models.Asignacion.id == assignment_id
        ).first()
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignment with id {assignment_id} not found",
            )
        
        # Get OT and cuadrilla
        ot = ot_service.get_ot_by_id(db, assignment.ot_id)
        cuadrilla = cuadrilla_service.get_cuadrilla_by_id(db, assignment.cuadrilla_id)
        
        # Update OT
        if ot:
            ot.cuadrilla_id = None
            ot.status = models.OTStatus.PREPLANIFICADA
            ot.updated_at = datetime.now()
            
            # Create log entry
            log = models.LogAgente(
                ot_id=assignment.ot_id,
                agente_name="assignment_deletion",
                accion="Unassigned from cuadrilla",
                resultado="success",
            )
            db.add(log)
        
        # Update cuadrilla load
        if cuadrilla:
            cuadrilla.current_load = max(0, cuadrilla.current_load - 1)
        
        # Delete assignment
        db.delete(assignment)
        db.commit()
        
        logger.info(f"Deleted assignment {assignment_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting assignment {assignment_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting assignment",
        )


# ============================================================================
# Background Tasks
# ============================================================================


async def _recalculate_all_centroids(cuadrilla_ids: list, db: Session) -> None:
    """Background task to recalculate centroids for multiple cuadrillas."""
    try:
        for cuadrilla_id in cuadrilla_ids:
            cuadrilla_service.update_cuadrilla_centroid(db, cuadrilla_id)
            logger.info(f"Recalculated centroid for cuadrilla {cuadrilla_id}")
    except Exception as e:
        logger.error(f"Error recalculating centroids: {e}")

