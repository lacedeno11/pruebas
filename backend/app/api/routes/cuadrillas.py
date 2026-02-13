"""
API routes for Cuadrilla (work crew) management.

Endpoints:
- GET /api/cuadrillas - List all cuadrillas with current load and OT count
- GET /api/cuadrillas/{cuadrilla_id} - Get cuadrilla details with assigned OTs
- POST /api/cuadrillas - Create new cuadrilla
- PUT /api/cuadrillas/{cuadrilla_id} - Update cuadrilla properties
- GET /api/cuadrillas/{cuadrilla_id}/workload - Calculate workload and availability
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.db.base import get_db
from backend.app.models.cuadrilla import Cuadrilla, CuadrillaType
from backend.app.models.ot import OrdenTrabajo
from backend.app.models.asignacion import Asignacion
from backend.app.schemas.cuadrilla_schema import (
    CuadrillaResponse,
    CuadrillaCreate,
    CuadrillaUpdate,
    CuadrillaWithOTs,
)
from backend.app.schemas.ot_schema import OTResponse
from backend.app.utils.geo_utils import calculate_centroid

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/cuadrillas",
    tags=["Cuadrillas"],
    responses={
        404: {"description": "Cuadrilla not found"},
        400: {"description": "Invalid request"},
        500: {"description": "Server error"},
    },
)


# ============================================================================
# GET /api/cuadrillas - List all cuadrillas with current load and OT count
# ============================================================================

@router.get("", response_model=List[dict])
async def list_cuadrillas(
    is_active_filter: Optional[bool] = Query(None, alias="is_active", description="Filter by active status"),
    type_filter: Optional[str] = Query(None, alias="type", description="Filter by cuadrilla type"),
    db: Session = Depends(get_db),
) -> List[dict]:
    """
    Get a list of all cuadrillas with their current load and assigned OT count.
    
    Query Parameters:
    - is_active: Filter by active status (true/false)
    - type: Filter by cuadrilla type (PRINCIPAL, RESERVA)
    
    Returns:
    - List of cuadrillas with extended information:
      - id, name, type, capacity_daily, current_load
      - last_centroid_lat, last_centroid_long
      - is_active, created_at
      - ot_count: Number of assigned OTs
      - load_percentage: Current load as percentage of capacity
      - availability: Number of available slots
    """
    try:
        # Start with base query
        query = db.query(Cuadrilla)
        
        # Apply filters
        if is_active_filter is not None:
            query = query.filter(Cuadrilla.is_active == is_active_filter)
        
        if type_filter:
            try:
                type_enum = CuadrillaType[type_filter.upper()]
                query = query.filter(Cuadrilla.type == type_enum)
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid type: {type_filter}. Must be one of: {', '.join([t.value for t in CuadrillaType])}"
                )
        
        # Fetch all cuadrillas
        cuadrillas = query.order_by(Cuadrilla.created_at.desc()).all()
        
        # Enrich with OT count and load percentage
        result = []
        for cuadrilla in cuadrillas:
            # Count assigned OTs
            ot_count = db.query(func.count(Asignacion.id)).filter(
                Asignacion.cuadrilla_id == cuadrilla.id,
                Asignacion.is_active == True
            ).scalar()
            
            # Calculate load percentage and availability
            load_percentage = (cuadrilla.current_load / cuadrilla.capacity_daily * 100) if cuadrilla.capacity_daily > 0 else 0
            availability = max(0, cuadrilla.capacity_daily - cuadrilla.current_load)
            
            result.append({
                'id': str(cuadrilla.id),
                'name': cuadrilla.name,
                'type': cuadrilla.type.value if hasattr(cuadrilla.type, 'value') else cuadrilla.type,
                'capacity_daily': cuadrilla.capacity_daily,
                'current_load': cuadrilla.current_load,
                'last_centroid_lat': cuadrilla.last_centroid_lat,
                'last_centroid_long': cuadrilla.last_centroid_long,
                'is_active': cuadrilla.is_active,
                'created_at': cuadrilla.created_at.isoformat() if cuadrilla.created_at else None,
                'ot_count': ot_count or 0,
                'load_percentage': round(load_percentage, 2),
                'availability': availability,
            })
        
        logger.info(f"Listed {len(result)} cuadrillas with filters - is_active: {is_active_filter}, type: {type_filter}")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing cuadrillas: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list cuadrillas"
        )


# ============================================================================
# GET /api/cuadrillas/{cuadrilla_id} - Get cuadrilla details with assigned OTs
# ============================================================================

@router.get("/{cuadrilla_id}", response_model=CuadrillaWithOTs)
async def get_cuadrilla_detail(
    cuadrilla_id: str,
    db: Session = Depends(get_db),
) -> CuadrillaWithOTs:
    """
    Get detailed information about a specific cuadrilla including all assigned OTs.
    
    Path Parameters:
    - cuadrilla_id: UUID of the cuadrilla
    
    Returns:
    - CuadrillaWithOTs with full details and list of assigned OTs
    """
    try:
        cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
        
        if not cuadrilla:
            logger.warning(f"Cuadrilla not found: {cuadrilla_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuadrilla with id {cuadrilla_id} not found"
            )
        
        # Get assigned OTs (only active assignments)
        assignments = db.query(Asignacion).filter(
            Asignacion.cuadrilla_id == cuadrilla_id,
            Asignacion.is_active == True
        ).all()
        
        assigned_ot_ids = [str(a.ot_id) for a in assignments]
        
        # Get full OT details for assigned OTs
        ots = []
        if assigned_ot_ids:
            ot_list = db.query(OrdenTrabajo).filter(
                OrdenTrabajo.id.in_(assigned_ot_ids)
            ).all()
            
            for ot in ot_list:
                ot_data = {
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
                ots.append(OTResponse(**ot_data))
        
        logger.info(f"Retrieved cuadrilla details: {cuadrilla_id} with {len(ots)} assigned OTs")
        
        # Build response
        response_data = {
            'id': str(cuadrilla.id),
            'name': cuadrilla.name,
            'type': cuadrilla.type.value if hasattr(cuadrilla.type, 'value') else cuadrilla.type,
            'capacity_daily': cuadrilla.capacity_daily,
            'current_load': cuadrilla.current_load,
            'last_centroid_lat': cuadrilla.last_centroid_lat,
            'last_centroid_long': cuadrilla.last_centroid_long,
            'is_active': cuadrilla.is_active,
            'created_at': cuadrilla.created_at,
            'ots': ots,
        }
        
        return CuadrillaWithOTs(**response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving cuadrilla {cuadrilla_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cuadrilla details"
        )


# ============================================================================
# POST /api/cuadrillas - Create new cuadrilla
# ============================================================================

@router.post("", response_model=CuadrillaResponse, status_code=status.HTTP_201_CREATED)
async def create_cuadrilla(
    cuadrilla_data: CuadrillaCreate,
    db: Session = Depends(get_db),
) -> CuadrillaResponse:
    """
    Create a new cuadrilla.
    
    Request Body:
    - name: Unique name for the cuadrilla
    - type: Cuadrilla type (PRINCIPAL, RESERVA)
    - capacity_daily: Daily capacity (number of OTs per day)
    
    Returns:
    - CuadrillaResponse with created cuadrilla details
    """
    try:
        # Check if name already exists
        existing = db.query(Cuadrilla).filter(Cuadrilla.name == cuadrilla_data.name).first()
        
        if existing:
            logger.warning(f"Cuadrilla name already exists: {cuadrilla_data.name}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cuadrilla with name '{cuadrilla_data.name}' already exists"
            )
        
        # Create new cuadrilla
        new_cuadrilla = Cuadrilla(
            name=cuadrilla_data.name,
            type=cuadrilla_data.type if hasattr(cuadrilla_data.type, 'value') else CuadrillaType[cuadrilla_data.type.upper()],
            capacity_daily=cuadrilla_data.capacity_daily or 10,
            current_load=0,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        
        db.add(new_cuadrilla)
        db.commit()
        db.refresh(new_cuadrilla)
        
        logger.info(f"Created new cuadrilla: {new_cuadrilla.id} - {new_cuadrilla.name}")
        
        response_data = {
            'id': str(new_cuadrilla.id),
            'name': new_cuadrilla.name,
            'type': new_cuadrilla.type.value if hasattr(new_cuadrilla.type, 'value') else new_cuadrilla.type,
            'capacity_daily': new_cuadrilla.capacity_daily,
            'current_load': new_cuadrilla.current_load,
            'last_centroid_lat': new_cuadrilla.last_centroid_lat,
            'last_centroid_long': new_cuadrilla.last_centroid_long,
            'is_active': new_cuadrilla.is_active,
            'created_at': new_cuadrilla.created_at,
        }
        
        return CuadrillaResponse(**response_data)
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error creating cuadrilla: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create cuadrilla"
        )


# ============================================================================
# PUT /api/cuadrillas/{cuadrilla_id} - Update cuadrilla
# ============================================================================

@router.put("/{cuadrilla_id}", response_model=CuadrillaResponse)
async def update_cuadrilla(
    cuadrilla_id: str,
    cuadrilla_update: CuadrillaUpdate,
    db: Session = Depends(get_db),
) -> CuadrillaResponse:
    """
    Update cuadrilla properties.
    
    Path Parameters:
    - cuadrilla_id: UUID of the cuadrilla
    
    Request Body (all optional):
    - name: New cuadrilla name
    - type: New cuadrilla type (PRINCIPAL, RESERVA)
    - capacity_daily: New daily capacity
    - is_active: Active status
    - current_load: Current load (useful for manual adjustments)
    
    Returns:
    - Updated CuadrillaResponse
    """
    try:
        cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
        
        if not cuadrilla:
            logger.warning(f"Cuadrilla not found for update: {cuadrilla_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuadrilla with id {cuadrilla_id} not found"
            )
        
        # Update name if provided (check for duplicates)
        if cuadrilla_update.name and cuadrilla_update.name != cuadrilla.name:
            existing = db.query(Cuadrilla).filter(
                Cuadrilla.name == cuadrilla_update.name
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cuadrilla with name '{cuadrilla_update.name}' already exists"
                )
            
            cuadrilla.name = cuadrilla_update.name
            logger.info(f"Updated cuadrilla {cuadrilla_id} name to {cuadrilla_update.name}")
        
        # Update type if provided
        if cuadrilla_update.type:
            cuadrilla.type = cuadrilla_update.type
            logger.info(f"Updated cuadrilla {cuadrilla_id} type to {cuadrilla_update.type}")
        
        # Update capacity if provided
        if cuadrilla_update.capacity_daily is not None:
            cuadrilla.capacity_daily = cuadrilla_update.capacity_daily
            logger.info(f"Updated cuadrilla {cuadrilla_id} capacity to {cuadrilla_update.capacity_daily}")
        
        # Update is_active if provided
        if cuadrilla_update.is_active is not None:
            cuadrilla.is_active = cuadrilla_update.is_active
            logger.info(f"Updated cuadrilla {cuadrilla_id} active status to {cuadrilla_update.is_active}")
        
        # Update current_load if provided (manual adjustment)
        if cuadrilla_update.current_load is not None:
            cuadrilla.current_load = cuadrilla_update.current_load
            logger.info(f"Updated cuadrilla {cuadrilla_id} current load to {cuadrilla_update.current_load}")
        
        db.commit()
        db.refresh(cuadrilla)
        
        logger.info(f"Cuadrilla {cuadrilla_id} updated successfully")
        
        response_data = {
            'id': str(cuadrilla.id),
            'name': cuadrilla.name,
            'type': cuadrilla.type.value if hasattr(cuadrilla.type, 'value') else cuadrilla.type,
            'capacity_daily': cuadrilla.capacity_daily,
            'current_load': cuadrilla.current_load,
            'last_centroid_lat': cuadrilla.last_centroid_lat,
            'last_centroid_long': cuadrilla.last_centroid_long,
            'is_active': cuadrilla.is_active,
            'created_at': cuadrilla.created_at,
        }
        
        return CuadrillaResponse(**response_data)
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error updating cuadrilla {cuadrilla_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update cuadrilla"
        )


# ============================================================================
# GET /api/cuadrillas/{cuadrilla_id}/workload - Calculate workload and availability
# ============================================================================

@router.get("/{cuadrilla_id}/workload", response_model=dict)
async def get_cuadrilla_workload(
    cuadrilla_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    Calculate current workload and availability for a cuadrilla.
    
    This endpoint provides detailed workload analysis:
    - Current load: Number of assigned OTs
    - Capacity: Daily capacity
    - Available slots: Remaining capacity
    - Load percentage: Current load as percentage of capacity
    - Assigned OTs breakdown by status
    - Centroid information for geographic planning
    
    Path Parameters:
    - cuadrilla_id: UUID of the cuadrilla
    
    Returns:
    - Dict with workload metrics and OT breakdown
    """
    try:
        cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
        
        if not cuadrilla:
            logger.warning(f"Cuadrilla not found for workload check: {cuadrilla_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuadrilla with id {cuadrilla_id} not found"
            )
        
        # Get all active assignments
        assignments = db.query(Asignacion).filter(
            Asignacion.cuadrilla_id == cuadrilla_id,
            Asignacion.is_active == True
        ).all()
        
        # Get full OT details for status breakdown
        ot_ids = [a.ot_id for a in assignments]
        ots = []
        status_breakdown = {}
        
        if ot_ids:
            ots = db.query(OrdenTrabajo).filter(OrdenTrabajo.id.in_(ot_ids)).all()
            
            # Build status breakdown
            for ot in ots:
                status = ot.status.value if hasattr(ot.status, 'value') else ot.status
                if status not in status_breakdown:
                    status_breakdown[status] = 0
                status_breakdown[status] += 1
        
        # Calculate centroid from assigned OTs
        centroid = None
        if ots and len(ots) > 0:
            # Get valid coordinates from OTs
            valid_coords = [
                (ot.lat, ot.long) for ot in ots
                if ot.lat is not None and ot.long is not None
            ]
            
            if valid_coords:
                centroid = calculate_centroid(valid_coords)
                # Update cuadrilla centroid
                cuadrilla.last_centroid_lat = centroid[0]
                cuadrilla.last_centroid_long = centroid[1]
                db.commit()
        
        # Calculate workload metrics
        current_load = len(assignments)
        capacity = cuadrilla.capacity_daily
        available_slots = max(0, capacity - current_load)
        load_percentage = (current_load / capacity * 100) if capacity > 0 else 0
        
        logger.info(f"Retrieved workload for cuadrilla {cuadrilla_id}: {current_load}/{capacity}")
        
        return {
            "success": True,
            "cuadrilla_id": str(cuadrilla.id),
            "cuadrilla_name": cuadrilla.name,
            "workload": {
                "current_load": current_load,
                "capacity": capacity,
                "available_slots": available_slots,
                "load_percentage": round(load_percentage, 2),
                "is_at_capacity": current_load >= capacity,
            },
            "assigned_ots": {
                "total_count": current_load,
                "breakdown_by_status": status_breakdown,
                "ot_ids": [str(a.ot_id) for a in assignments],
            },
            "centroid": {
                "lat": centroid[0] if centroid else cuadrilla.last_centroid_lat,
                "long": centroid[1] if centroid else cuadrilla.last_centroid_long,
                "calculated": centroid is not None,
            },
            "capacity_info": {
                "daily_capacity": capacity,
                "current_utilization": current_load,
                "utilization_percentage": round(load_percentage, 2),
                "can_accept_more": available_slots > 0,
                "slots_available": available_slots,
            },
            "status": "active" if cuadrilla.is_active else "inactive",
            "updated_at": datetime.utcnow().isoformat(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating workload for cuadrilla {cuadrilla_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate workload"
        )

