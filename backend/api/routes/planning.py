"""Planning and assignment endpoints."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_
from backend.database.db import get_db
from backend.database.models import OT, Cuadrilla, Assignment, OTStatus
from backend.utils.validators import validate_crew_capacity
from backend.utils.geo import haversine_distance, calculate_centroid
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import os

# Initialize router
router = APIRouter()


# Pydantic models for request/response
class ManualAssignment(BaseModel):
    """Manual OT assignment request model."""
    ot_id: int
    cuadrilla_id: int


class AssignmentResponse(BaseModel):
    """Assignment response model."""
    id: int
    ot_id: int
    cuadrilla_id: int
    assigned_at: datetime
    assigned_by_agent: str

    class Config:
        from_attributes = True


class PlanningStatusResponse(BaseModel):
    """Planning status and statistics response."""
    total_ots: int
    ots_by_status: Dict[str, int]
    crew_utilization: List[Dict[str, Any]]
    total_assignments: int
    pending_ots: int


class AutoPlanningResponse(BaseModel):
    """Auto planning execution response."""
    success: bool
    message: str
    assignments_created: int = 0
    ots_assigned: int = 0
    ots_pending: int = 0


class OptimizationResponse(BaseModel):
    """Route optimization execution response."""
    success: bool
    message: str
    crews_optimized: int = 0
    centroids_updated: int = 0


# Endpoints

@router.post("/api/planning/auto", response_model=AutoPlanningResponse)
async def auto_planning(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Trigger automatic planning algorithm.
    
    This endpoint initiates the 3-phase planning algorithm:
    
    Phase 1 - Initial Balance:
    - Assigns 1 OT to each crew with zero assignments
    - Prioritizes PÚBLICO projects
    
    Phase 2 - Centroid Proximity:
    - Calculates each crew's centroid from assigned OTs
    - Assigns remaining OTs to crews within MAX_DISTANCE_KM (10km)
    - Assigns to crew with most available capacity
    
    Note: This endpoint calls the Planificación Agent via LangGraph workflow.
    For now, returns a placeholder response.
    """
    try:
        # TODO: Integrate with Planificación Agent via LangGraph workflow
        # For now, return placeholder response
        return AutoPlanningResponse(
            success=True,
            message="Auto planning triggered successfully",
            assignments_created=0,
            ots_assigned=0,
            ots_pending=0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Planning failed: {str(e)}")


@router.post("/api/planning/assign", response_model=AssignmentResponse)
async def manual_assignment(
    assignment: ManualAssignment,
    db: Session = Depends(get_db),
):
    """
    Manually assign an OT to a crew.
    
    Request Body:
    - ot_id: ID of the OT to assign
    - cuadrilla_id: ID of the crew to assign to
    
    Process:
    1. Validate OT exists and is unassigned
    2. Validate crew exists and has capacity
    3. Validate distance if centroid exists
    4. Create Assignment record
    5. Update OT status to PLANIFICADA
    6. Update crew's ots_asignadas_count
    
    Returns:
    - Created Assignment with timestamp
    """
    # Validate OT exists
    ot = db.query(OT).filter(OT.id == assignment.ot_id).first()
    if not ot:
        raise HTTPException(status_code=404, detail=f"OT with id {assignment.ot_id} not found")
    
    # Validate OT is not already assigned
    if ot.cuadrilla_id is not None:
        raise HTTPException(status_code=400, detail=f"OT {ot.external_id} is already assigned to a crew")
    
    # Validate crew exists
    cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == assignment.cuadrilla_id).first()
    if not cuadrilla:
        raise HTTPException(status_code=404, detail=f"Cuadrilla with id {assignment.cuadrilla_id} not found")
    
    # Validate crew has capacity
    if cuadrilla.ots_asignadas_count >= cuadrilla.capacidad_diaria:
        raise HTTPException(
            status_code=400,
            detail=f"Crew '{cuadrilla.name}' is at full capacity ({cuadrilla.capacidad_diaria} OTs)"
        )
    
    # Validate distance if crew has centroid
    max_distance_km = float(os.getenv("MAX_DISTANCE_KM", "10"))
    if cuadrilla.last_centroid_lat and cuadrilla.last_centroid_long:
        distance = haversine_distance(
            cuadrilla.last_centroid_lat,
            cuadrilla.last_centroid_long,
            ot.lat,
            ot.long
        )
        if distance > max_distance_km:
            raise HTTPException(
                status_code=400,
                detail=f"OT is {distance:.1f}km from crew centroid (max {max_distance_km}km)"
            )
    
    # Create Assignment
    new_assignment = Assignment(
        ot_id=assignment.ot_id,
        cuadrilla_id=assignment.cuadrilla_id,
        assigned_by_agent="Manual Assignment",
    )
    
    # Update OT
    ot.cuadrilla_id = assignment.cuadrilla_id
    ot.status = OTStatus.PLANIFICADA.value
    ot.updated_at = datetime.utcnow()
    
    # Update crew
    cuadrilla.ots_asignadas_count += 1
    
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    
    return AssignmentResponse(
        id=new_assignment.id,
        ot_id=new_assignment.ot_id,
        cuadrilla_id=new_assignment.cuadrilla_id,
        assigned_at=new_assignment.assigned_at,
        assigned_by_agent=new_assignment.assigned_by_agent,
    )


@router.post("/api/planning/optimize", response_model=OptimizationResponse)
async def optimize_routes(db: Session = Depends(get_db)):
    """
    Trigger nightly route optimization.
    
    This endpoint runs Phase 3 of the planning algorithm:
    - Recalculates centroid for each crew from assigned OTs
    - Stores new centroids in Cuadrilla.last_centroid_lat/long
    - Generates optimization report
    
    Typically called at 00:00 UTC daily via scheduler.
    
    Note: This endpoint calls the Planificación Agent Phase 3 via LangGraph workflow.
    For now, returns a placeholder response.
    """
    try:
        # Get all cuadrillas with assignments
        cuadrillas = db.query(Cuadrilla).all()
        centroids_updated = 0
        
        for cuadrilla in cuadrillas:
            # Get all assigned OTs
            assigned_ots = db.query(OT).filter(OT.cuadrilla_id == cuadrilla.id).all()
            
            if assigned_ots and len(assigned_ots) > 0:
                try:
                    # Calculate new centroid
                    coordinates = [(ot.lat, ot.long) for ot in assigned_ots]
                    centroid_lat, centroid_long = calculate_centroid(coordinates)
                    
                    # Update crew centroid
                    cuadrilla.last_centroid_lat = centroid_lat
                    cuadrilla.last_centroid_long = centroid_long
                    centroids_updated += 1
                except Exception:
                    # Skip if centroid calculation fails
                    pass
        
        db.commit()
        
        return OptimizationResponse(
            success=True,
            message="Route optimization completed",
            crews_optimized=len(cuadrillas),
            centroids_updated=centroids_updated,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.get("/api/planning/status", response_model=PlanningStatusResponse)
async def planning_status(db: Session = Depends(get_db)):
    """
    Get current planning statistics and metrics.
    
    Returns:
    - Total OT count
    - OTs grouped by status (PREPLANIFICADA, PLANIFICADA, etc.)
    - Crew utilization percentages
    - Total assignments
    - Pending (unassigned) OT count
    
    Used to display dashboard metrics and monitoring.
    """
    # Get all OTs
    all_ots = db.query(OT).all()
    total_ots = len(all_ots)
    
    # Count OTs by status
    ots_by_status = {}
    for status in OTStatus:
        count = db.query(OT).filter(OT.status == status.value).count()
        ots_by_status[status.value] = count
    
    # Get all assignments
    total_assignments = db.query(Assignment).count()
    
    # Count pending (unassigned) OTs
    pending_ots = db.query(OT).filter(OT.cuadrilla_id == None).count()
    
    # Calculate crew utilization
    cuadrillas = db.query(Cuadrilla).all()
    crew_utilization = []
    
    for cuadrilla in cuadrillas:
        utilization_percent = (cuadrilla.ots_asignadas_count / cuadrilla.capacidad_diaria) * 100 if cuadrilla.capacidad_diaria > 0 else 0
        
        # Get assigned OTs for this crew
        assigned_ots = db.query(OT).filter(OT.cuadrilla_id == cuadrilla.id).all()
        
        # Calculate average distance from centroid if it exists
        avg_distance = None
        if cuadrilla.last_centroid_lat and cuadrilla.last_centroid_long and assigned_ots:
            distances = [
                haversine_distance(
                    cuadrilla.last_centroid_lat,
                    cuadrilla.last_centroid_long,
                    ot.lat,
                    ot.long
                )
                for ot in assigned_ots
            ]
            avg_distance = sum(distances) / len(distances) if distances else None
        
        crew_utilization.append({
            "crew_id": cuadrilla.id,
            "crew_name": cuadrilla.name,
            "total_capacity": cuadrilla.capacidad_diaria,
            "ots_assigned": cuadrilla.ots_asignadas_count,
            "utilization_percent": round(utilization_percent, 1),
            "avg_distance_km": round(avg_distance, 2) if avg_distance else None,
            "centroid_lat": cuadrilla.last_centroid_lat,
            "centroid_long": cuadrilla.last_centroid_long,
        })
    
    return PlanningStatusResponse(
        total_ots=total_ots,
        ots_by_status=ots_by_status,
        crew_utilization=crew_utilization,
        total_assignments=total_assignments,
        pending_ots=pending_ots,
    )

