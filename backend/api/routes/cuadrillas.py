"""
Cuadrilla (Crew) management endpoints.
Provides CRUD operations and workload information for crews.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database.base import get_db
from backend.database import schemas, models
from backend.services.cuadrilla_service import CuadrillaService

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/cuadrillas", tags=["cuadrillas"])

# Initialize service
cuadrilla_service = CuadrillaService()


# ============================================================================
# GET Endpoints
# ============================================================================


@router.get("/", response_model=List[schemas.CuadrillaResponse])
async def list_cuadrillas(
    type: Optional[str] = Query(None, description="Filter by cuadrilla type (Principal/Reserva)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db),
):
    """
    Get list of cuadrillas with optional type filtering.
    
    Query Parameters:
    - type: Filter by cuadrilla type (Principal or Reserva)
    - skip: Pagination offset
    - limit: Maximum number of results
    
    Returns:
        List of Cuadrilla objects
    """
    try:
        cuadrillas = cuadrilla_service.get_cuadrillas(
            db,
            cuadrilla_type=type,
            skip=skip,
            limit=limit,
        )
        return cuadrillas
    except Exception as e:
        logger.error(f"Error fetching cuadrillas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching cuadrillas",
        )


@router.get("/available", response_model=dict)
async def get_available_cuadrillas(
    db: Session = Depends(get_db),
):
    """
    Get available cuadrillas grouped by type.
    Available means current_load < capacity.
    
    Returns:
        Dict with Principal and Reserva cuadrillas
    """
    try:
        available = cuadrilla_service.get_available_cuadrillas(db)
        
        # Group by type
        principal = [c for c in available if c.type == models.CuadrillaType.PRINCIPAL]
        reserva = [c for c in available if c.type == models.CuadrillaType.RESERVA]
        
        return {
            "principal": principal,
            "reserva": reserva,
            "total_available": len(available),
        }
    except Exception as e:
        logger.error(f"Error fetching available cuadrillas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching available cuadrillas",
        )


@router.get("/{cuadrilla_id}", response_model=schemas.CuadrillaResponse)
async def get_cuadrilla(
    cuadrilla_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a specific cuadrilla by ID.
    
    Path Parameters:
    - cuadrilla_id: Cuadrilla ID
    
    Returns:
        Cuadrilla object
        
    Raises:
        404: If cuadrilla not found
    """
    try:
        cuadrilla = cuadrilla_service.get_cuadrilla_by_id(db, cuadrilla_id)
        if not cuadrilla:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuadrilla with id {cuadrilla_id} not found",
            )
        return cuadrilla
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching cuadrilla {cuadrilla_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching cuadrilla",
        )


@router.get("/{cuadrilla_id}/workload", response_model=schemas.CuadrillaWorkload)
async def get_cuadrilla_workload(
    cuadrilla_id: int,
    db: Session = Depends(get_db),
):
    """
    Get detailed workload information for a cuadrilla.
    
    Returns:
        Workload information including current_load, capacity, utilization, and assigned OTs
    """
    try:
        cuadrilla = cuadrilla_service.get_cuadrilla_by_id(db, cuadrilla_id)
        if not cuadrilla:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuadrilla with id {cuadrilla_id} not found",
            )
        
        workload = cuadrilla_service.get_cuadrilla_workload(db, cuadrilla_id)
        return workload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching cuadrilla {cuadrilla_id} workload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching cuadrilla workload",
        )


@router.get("/{cuadrilla_id}/ots", response_model=List[schemas.OTResponse])
async def get_cuadrilla_ots(
    cuadrilla_id: int,
    db: Session = Depends(get_db),
):
    """
    Get all OTs assigned to a specific cuadrilla.
    
    Path Parameters:
    - cuadrilla_id: Cuadrilla ID
    
    Returns:
        List of assigned OT objects
    """
    try:
        cuadrilla = cuadrilla_service.get_cuadrilla_by_id(db, cuadrilla_id)
        if not cuadrilla:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuadrilla with id {cuadrilla_id} not found",
            )
        
        ots = db.query(models.OrdenTrabajo).filter(
            models.OrdenTrabajo.cuadrilla_id == cuadrilla_id
        ).all()
        return ots
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching OTs for cuadrilla {cuadrilla_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching OTs",
        )


# ============================================================================
# POST Endpoints
# ============================================================================


@router.post("/", response_model=schemas.CuadrillaResponse, status_code=status.HTTP_201_CREATED)
async def create_cuadrilla(
    cuadrilla_data: schemas.CuadrillaCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new cuadrilla.
    
    Request Body:
    - name: Cuadrilla name
    - type: Cuadrilla type (Principal or Reserva)
    - capacity: Maximum number of OTs (default: 10)
    
    Returns:
        Created Cuadrilla object
        
    Raises:
        409: If name already exists
    """
    try:
        # Check if name already exists
        existing = db.query(models.Cuadrilla).filter(
            models.Cuadrilla.name == cuadrilla_data.name
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cuadrilla with name {cuadrilla_data.name} already exists",
            )
        
        # Create new cuadrilla
        cuadrilla = models.Cuadrilla(
            name=cuadrilla_data.name,
            type=cuadrilla_data.type,
            capacity=cuadrilla_data.capacity,
            current_load=0,
        )
        db.add(cuadrilla)
        db.commit()
        db.refresh(cuadrilla)
        
        logger.info(f"Created cuadrilla: {cuadrilla.name}")
        return cuadrilla
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating cuadrilla: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error creating cuadrilla",
        )


# ============================================================================
# PUT Endpoints
# ============================================================================


@router.put("/{cuadrilla_id}/centroid", response_model=schemas.CuadrillaResponse)
async def recalculate_centroid(
    cuadrilla_id: int,
    db: Session = Depends(get_db),
):
    """
    Manually trigger centroid recalculation for a cuadrilla.
    
    Calculates the geographic center (centroid) of all assigned OTs.
    
    Path Parameters:
    - cuadrilla_id: Cuadrilla ID
    
    Returns:
        Updated Cuadrilla object with new centroid coordinates
        
    Raises:
        404: If cuadrilla not found
    """
    try:
        cuadrilla = cuadrilla_service.get_cuadrilla_by_id(db, cuadrilla_id)
        if not cuadrilla:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuadrilla with id {cuadrilla_id} not found",
            )
        
        # Update centroid
        updated_cuadrilla = cuadrilla_service.update_cuadrilla_centroid(db, cuadrilla_id)
        
        logger.info(f"Recalculated centroid for cuadrilla {cuadrilla_id}")
        return updated_cuadrilla
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recalculating centroid for cuadrilla {cuadrilla_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error recalculating centroid",
        )


@router.put("/{cuadrilla_id}", response_model=schemas.CuadrillaResponse)
async def update_cuadrilla(
    cuadrilla_id: int,
    cuadrilla_data: schemas.CuadrillaCreate,
    db: Session = Depends(get_db),
):
    """
    Update cuadrilla information.
    
    Path Parameters:
    - cuadrilla_id: Cuadrilla ID
    
    Request Body:
    - name: New cuadrilla name
    - type: New cuadrilla type
    - capacity: New capacity
    
    Returns:
        Updated Cuadrilla object
        
    Raises:
        404: If cuadrilla not found
    """
    try:
        cuadrilla = cuadrilla_service.get_cuadrilla_by_id(db, cuadrilla_id)
        if not cuadrilla:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuadrilla with id {cuadrilla_id} not found",
            )
        
        # Check if new name already exists (excluding current cuadrilla)
        if cuadrilla_data.name != cuadrilla.name:
            existing = db.query(models.Cuadrilla).filter(
                models.Cuadrilla.name == cuadrilla_data.name
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cuadrilla with name {cuadrilla_data.name} already exists",
                )
        
        # Update fields
        cuadrilla.name = cuadrilla_data.name
        cuadrilla.type = cuadrilla_data.type
        cuadrilla.capacity = cuadrilla_data.capacity
        
        db.commit()
        db.refresh(cuadrilla)
        
        logger.info(f"Updated cuadrilla {cuadrilla_id}")
        return cuadrilla
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cuadrilla {cuadrilla_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating cuadrilla",
        )


# ============================================================================
# DELETE Endpoints
# ============================================================================


@router.delete("/{cuadrilla_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cuadrilla(
    cuadrilla_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a cuadrilla (soft delete - only if no assigned OTs).
    
    Path Parameters:
    - cuadrilla_id: Cuadrilla ID
    
    Raises:
        404: If cuadrilla not found
        409: If cuadrilla has assigned OTs
    """
    try:
        cuadrilla = cuadrilla_service.get_cuadrilla_by_id(db, cuadrilla_id)
        if not cuadrilla:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuadrilla with id {cuadrilla_id} not found",
            )
        
        # Check if cuadrilla has assigned OTs
        assigned_ots = db.query(models.OrdenTrabajo).filter(
            models.OrdenTrabajo.cuadrilla_id == cuadrilla_id
        ).count()
        
        if assigned_ots > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete cuadrilla with {assigned_ots} assigned OTs",
            )
        
        # Delete cuadrilla
        db.delete(cuadrilla)
        db.commit()
        
        logger.info(f"Deleted cuadrilla {cuadrilla_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting cuadrilla {cuadrilla_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting cuadrilla",
        )

