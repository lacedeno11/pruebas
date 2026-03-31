"""
API routes for OrdenTrabajo (OT) management.

Endpoints:
- GET /api/ots - List all OTs with filters and pagination
- GET /api/ots/{ot_id} - Get OT details
- POST /api/ots/sync - Sync OTs from TELCOS API
- PUT /api/ots/{ot_id}/status - Update OT status
- DELETE /api/ots/{ot_id} - Soft delete OT
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.db.base import get_db
from backend.app.models.ot import OrdenTrabajo, OTStatus, ProjectType
from backend.app.models.cuadrilla import Cuadrilla
from backend.app.schemas.ot_schema import (
    OTResponse,
    OTListResponse,
    OTUpdate,
    OTCreate,
)
from backend.app.services.telcos_api_client import TelcosApiClient

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/ots",
    tags=["OTs"],
    responses={
        404: {"description": "OT not found"},
        400: {"description": "Invalid request"},
        500: {"description": "Server error"},
    },
)


# ============================================================================
# GET /api/ots - List all OTs with filters and pagination
# ============================================================================

@router.get("", response_model=OTListResponse)
async def list_ots(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by OT status"),
    project_type_filter: Optional[str] = Query(None, alias="project_type", description="Filter by project type"),
    cuadrilla_id_filter: Optional[str] = Query(None, alias="cuadrilla_id", description="Filter by assigned cuadrilla"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Number of records to return"),
    db: Session = Depends(get_db),
) -> OTListResponse:
    """
    Get a paginated list of all OTs with optional filters.
    
    Query Parameters:
    - status: Filter by OT status (PREPLANIFICADA, PLANIFICADA, ASIGNADO_TAREA, DETENIDA, ANULADA, FINALIZADA)
    - project_type: Filter by project type (PUBLICO, PRIVADO, TERCERIZADO)
    - cuadrilla_id: Filter by assigned cuadrilla UUID
    - skip: Number of records to skip for pagination (default: 0)
    - limit: Number of records to return (default: 50, max: 500)
    
    Returns:
    - OTListResponse with items list and total count
    """
    try:
        # Start with base query
        query = db.query(OrdenTrabajo)
        
        # Apply filters
        if status_filter:
            try:
                status_enum = OTStatus[status_filter.upper()]
                query = query.filter(OrdenTrabajo.status == status_enum)
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}. Must be one of: {', '.join([s.value for s in OTStatus])}"
                )
        
        if project_type_filter:
            try:
                project_type_enum = ProjectType[project_type_filter.upper()]
                query = query.filter(OrdenTrabajo.project_type == project_type_enum)
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid project_type: {project_type_filter}. Must be one of: {', '.join([p.value for p in ProjectType])}"
                )
        
        if cuadrilla_id_filter:
            query = query.filter(OrdenTrabajo.cuadrilla_id == cuadrilla_id_filter)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination and ordering
        items = query.order_by(desc(OrdenTrabajo.created_at)).offset(skip).limit(limit).all()
        
        logger.info(f"Listed {len(items)} OTs with filters - status: {status_filter}, project_type: {project_type_filter}")
        
        return OTListResponse(
            items=[OTResponse.from_attributes(item) if hasattr(OTResponse, 'from_attributes') else OTResponse(**{**item.__dict__, 'id': str(item.id), 'cuadrilla_id': str(item.cuadrilla_id) if item.cuadrilla_id else None}) for item in items],
            total=total,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing OTs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list OTs"
        )


# ============================================================================
# GET /api/ots/{ot_id} - Get OT details
# ============================================================================

@router.get("/{ot_id}", response_model=OTResponse)
async def get_ot_detail(
    ot_id: str,
    db: Session = Depends(get_db),
) -> OTResponse:
    """
    Get detailed information about a specific OT.
    
    Path Parameters:
    - ot_id: UUID of the OT
    
    Returns:
    - OTResponse with full OT details including cuadrilla info
    """
    try:
        ot = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == ot_id).first()
        
        if not ot:
            logger.warning(f"OT not found: {ot_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OT with id {ot_id} not found"
            )
        
        logger.info(f"Retrieved OT details: {ot_id}")
        
        # Convert to response format
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
        
        return OTResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving OT {ot_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OT details"
        )


# ============================================================================
# POST /api/ots/sync - Sync OTs from TELCOS API
# ============================================================================

@router.post("/sync", response_model=dict)
async def sync_ots(
    db: Session = Depends(get_db),
) -> dict:
    """
    Trigger OTS Agent to sync new OTs from TELCOS API.
    
    This endpoint:
    1. Calls TelcosApiClient to fetch OTs from TELCOS API
    2. Validates coordinates using geo_utils
    3. Marks error_geo=True for invalid coordinates
    4. Persists new OTs to database
    5. Returns created OT IDs and any errors
    
    Returns:
    - Dict with created_count, error_count, created_ots list, errors list
    """
    try:
        logger.info("Starting OT sync from TELCOS API...")
        
        # Initialize TELCOS API client
        telcos_client = TelcosApiClient()
        
        # Fetch OTs from TELCOS API
        telcos_ots = await telcos_client.get_ots()
        logger.info(f"Fetched {len(telcos_ots)} OTs from TELCOS API")
        
        created_ots = []
        errors = []
        
        # Import geo_utils for coordinate validation
        from backend.app.utils.geo_utils import validate_coordinates
        
        # Process each OT
        for telcos_ot in telcos_ots:
            try:
                # Check if OT already exists
                existing = db.query(OrdenTrabajo).filter(
                    OrdenTrabajo.external_id == telcos_ot.external_id
                ).first()
                
                if existing:
                    logger.debug(f"OT already exists: {telcos_ot.external_id}")
                    continue
                
                # Validate coordinates
                error_geo = False
                if telcos_ot.lat is not None and telcos_ot.long is not None:
                    if not validate_coordinates(telcos_ot.lat, telcos_ot.long):
                        error_geo = True
                        logger.warning(f"Invalid coordinates for OT {telcos_ot.external_id}: ({telcos_ot.lat}, {telcos_ot.long})")
                
                # Create new OT
                new_ot = OrdenTrabajo(
                    external_id=telcos_ot.external_id,
                    status=telcos_ot.status if hasattr(telcos_ot.status, 'value') else OTStatus.PREPLANIFICADA,
                    project_type=telcos_ot.project_type if hasattr(telcos_ot.project_type, 'value') else ProjectType.PRIVADO,
                    lat=telcos_ot.lat,
                    long=telcos_ot.long,
                    cliente_id=telcos_ot.cliente_id,
                    login_id=telcos_ot.login_id,
                    error_geo=error_geo,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                
                db.add(new_ot)
                created_ots.append({
                    'id': str(new_ot.id),
                    'external_id': new_ot.external_id,
                    'error_geo': error_geo,
                })
                
            except Exception as e:
                error_msg = f"Error processing OT {getattr(telcos_ot, 'external_id', 'unknown')}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
        
        # Commit all changes
        db.commit()
        logger.info(f"Sync completed: {len(created_ots)} OTs created, {len(errors)} errors")
        
        return {
            "success": True,
            "created_count": len(created_ots),
            "error_count": len(errors),
            "created_ots": created_ots,
            "errors": errors,
        }
    
    except Exception as e:
        logger.error(f"Error syncing OTs: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync OTs from TELCOS API"
        )


# ============================================================================
# PUT /api/ots/{ot_id}/status - Update OT status
# ============================================================================

@router.put("/{ot_id}/status", response_model=OTResponse)
async def update_ot_status(
    ot_id: str,
    status_update: OTUpdate,
    db: Session = Depends(get_db),
) -> OTResponse:
    """
    Update the status of a specific OT.
    
    Path Parameters:
    - ot_id: UUID of the OT
    
    Request Body:
    - status: New OT status (PREPLANIFICADA, PLANIFICADA, ASIGNADO_TAREA, DETENIDA, ANULADA, FINALIZADA)
    - cuadrilla_id: Optional cuadrilla UUID to assign to
    
    Returns:
    - Updated OTResponse
    """
    try:
        ot = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == ot_id).first()
        
        if not ot:
            logger.warning(f"OT not found for status update: {ot_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OT with id {ot_id} not found"
            )
        
        # Update status if provided
        if status_update.status:
            old_status = ot.status
            ot.status = status_update.status
            logger.info(f"Updated OT {ot_id} status from {old_status} to {status_update.status}")
        
        # Update cuadrilla_id if provided
        if status_update.cuadrilla_id is not None:
            # Verify cuadrilla exists
            cuadrilla = db.query(Cuadrilla).filter(
                Cuadrilla.id == status_update.cuadrilla_id
            ).first()
            
            if not cuadrilla:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cuadrilla with id {status_update.cuadrilla_id} not found"
                )
            
            ot.cuadrilla_id = status_update.cuadrilla_id
            logger.info(f"Assigned OT {ot_id} to cuadrilla {status_update.cuadrilla_id}")
        
        # Update timestamp
        ot.updated_at = datetime.utcnow()
        
        db.commit()
        logger.info(f"OT {ot_id} updated successfully")
        
        # Convert to response format
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
        
        return OTResponse(**response_data)
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error updating OT {ot_id} status: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update OT status"
        )


# ============================================================================
# DELETE /api/ots/{ot_id} - Soft delete OT
# ============================================================================

@router.delete("/{ot_id}", response_model=dict)
async def delete_ot(
    ot_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    Soft delete an OT by marking its status as ANULADA.
    
    This is a soft delete that preserves the record in the database
    for audit trail purposes.
    
    Path Parameters:
    - ot_id: UUID of the OT
    
    Returns:
    - Dict with success status and message
    """
    try:
        ot = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == ot_id).first()
        
        if not ot:
            logger.warning(f"OT not found for deletion: {ot_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OT with id {ot_id} not found"
            )
        
        # Mark as ANULADA instead of hard delete
        ot.status = OTStatus.ANULADA
        ot.updated_at = datetime.utcnow()
        
        db.commit()
        logger.info(f"OT {ot_id} soft-deleted (marked as ANULADA)")
        
        return {
            "success": True,
            "message": f"OT {ot_id} successfully deleted",
            "ot_id": ot_id,
            "status": "ANULADA",
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error deleting OT {ot_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete OT"
        )

