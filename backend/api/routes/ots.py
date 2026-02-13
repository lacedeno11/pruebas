"""
OT (Orden de Trabajo) management endpoints.
Provides CRUD operations and status management for work orders.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database.base import get_db
from backend.database import schemas, models
from backend.services.ot_service import OTService
from backend.services.geo_service import GeoService

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/ots", tags=["ots"])

# Initialize services
ot_service = OTService()
geo_service = GeoService()


# ============================================================================
# GET Endpoints
# ============================================================================


@router.get("/", response_model=List[schemas.OTResponse])
async def list_ots(
    status: Optional[str] = Query(None, description="Filter by OT status"),
    project_type: Optional[str] = Query(None, description="Filter by project type"),
    geo_error: Optional[bool] = Query(None, description="Filter by geo_error flag"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db),
):
    """
    Get list of OTs with optional filtering.
    
    Query Parameters:
    - status: Filter by OT status (PREPLANIFICADA, PLANIFICADA, ASIGNADO_TAREA, DETENIDA, ANULADA, FINALIZADA)
    - project_type: Filter by project type (PUBLICO, PRIVADO, TERCERIZADO)
    - geo_error: Filter OTs with missing/invalid coordinates
    - skip: Pagination offset
    - limit: Maximum number of results
    
    Returns:
        List of OT objects
    """
    try:
        filters = {
            "status": status,
            "project_type": project_type,
            "geo_error": geo_error,
        }
        ots = ot_service.get_ots(db, filters, skip=skip, limit=limit)
        return ots
    except Exception as e:
        logger.error(f"Error fetching OTs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching OTs",
        )


@router.get("/unassigned", response_model=List[schemas.OTResponse])
async def get_unassigned_ots(
    db: Session = Depends(get_db),
):
    """
    Get unassigned OTs (PREPLANIFICADA status without cuadrilla).
    
    Returns:
        List of unassigned OT objects
    """
    try:
        ots = ot_service.get_unassigned_ots(db)
        return ots
    except Exception as e:
        logger.error(f"Error fetching unassigned OTs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching unassigned OTs",
        )


@router.get("/statistics", response_model=schemas.OTStatistics)
async def get_ot_statistics(
    db: Session = Depends(get_db),
):
    """
    Get aggregated OT statistics by status and project type.
    
    Returns:
        OT statistics including counts by status and project type
    """
    try:
        stats = ot_service.get_statistics(db)
        return stats
    except Exception as e:
        logger.error(f"Error calculating OT statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating statistics",
        )


@router.get("/{ot_id}", response_model=schemas.OTResponse)
async def get_ot(
    ot_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a specific OT by ID.
    
    Path Parameters:
    - ot_id: OT ID
    
    Returns:
        OT object
        
    Raises:
        404: If OT not found
    """
    try:
        ot = ot_service.get_ot_by_id(db, ot_id)
        if not ot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OT with id {ot_id} not found",
            )
        return ot
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching OT {ot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching OT",
        )


@router.get("/{ot_id}/logs", response_model=List[schemas.LogAgenteResponse])
async def get_ot_logs(
    ot_id: int,
    db: Session = Depends(get_db),
):
    """
    Get agent action logs for a specific OT.
    
    Path Parameters:
    - ot_id: OT ID
    
    Returns:
        List of LogAgente objects
    """
    try:
        logs = db.query(models.LogAgente).filter(
            models.LogAgente.ot_id == ot_id
        ).order_by(models.LogAgente.created_at.desc()).all()
        return logs
    except Exception as e:
        logger.error(f"Error fetching logs for OT {ot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching OT logs",
        )


# ============================================================================
# POST Endpoints
# ============================================================================


@router.post("/", response_model=schemas.OTResponse, status_code=status.HTTP_201_CREATED)
async def create_ot(
    ot_data: schemas.OTCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new OT.
    
    Request Body:
    - external_id: External system identifier
    - orden_servicio_id: Service order ID
    - login_id: Service point ID
    - cliente_id: Customer ID
    - status: Initial status (default: PREPLANIFICADA)
    - project_type: Project type (default: PRIVADO)
    - lat, long: Geographic coordinates (optional)
    - pm_email: Project manager email for notifications (optional)
    
    Returns:
        Created OT object
        
    Raises:
        400: If validation fails
        409: If external_id already exists
    """
    try:
        # Check if external_id already exists
        existing_ot = db.query(models.OrdenTrabajo).filter(
            models.OrdenTrabajo.external_id == ot_data.external_id
        ).first()
        if existing_ot:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"OT with external_id {ot_data.external_id} already exists",
            )
        
        # Create OT (service will handle geo validation and notifications)
        ot = ot_service.create_ot(db, ot_data)
        return ot
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating OT: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error creating OT",
        )


# ============================================================================
# PUT Endpoints
# ============================================================================


@router.put("/{ot_id}/status", response_model=schemas.OTResponse)
async def update_ot_status(
    ot_id: int,
    status_update: schemas.OTUpdate,
    db: Session = Depends(get_db),
):
    """
    Update OT status and create audit log.
    
    Path Parameters:
    - ot_id: OT ID
    
    Request Body:
    - new_status: New OT status
    - reason: Reason for status change (required for DETENIDA/ANULADA)
    
    Returns:
        Updated OT object
        
    Raises:
        404: If OT not found
        400: If status transition is invalid
    """
    try:
        ot = ot_service.get_ot_by_id(db, ot_id)
        if not ot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OT with id {ot_id} not found",
            )
        
        # Update status (service will handle business logic validation)
        updated_ot = ot_service.update_ot_status(
            db,
            ot_id,
            status_update.new_status,
            status_update.reason,
        )
        
        return updated_ot
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating OT {ot_id} status: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error updating OT status",
        )


# ============================================================================
# DELETE Endpoints
# ============================================================================


@router.delete("/{ot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ot(
    ot_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete an OT (soft delete - mark as ANULADA).
    
    Path Parameters:
    - ot_id: OT ID
    
    Raises:
        404: If OT not found
    """
    try:
        ot = ot_service.get_ot_by_id(db, ot_id)
        if not ot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OT with id {ot_id} not found",
            )
        
        # Mark as ANULADA instead of hard delete
        ot_service.update_ot_status(
            db,
            ot_id,
            models.OTStatus.ANULADA,
            "Deleted by API",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting OT {ot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting OT",
        )

