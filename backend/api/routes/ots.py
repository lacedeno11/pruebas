"""OT (Orden de Trabajo) API routes"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.models import OT
from backend.models.ot import OTCreate, OTUpdate, OTInDB
from backend.models.proyecto import StandardResponse
from backend.api.dependencies import get_db, get_telcos_service, get_notification_service
from backend.utils.business_rules import validate_status_transition
from backend.utils.constants import OT_STATUS, PROJECT_TYPES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ots", tags=["ots"])


@router.get("", response_model=dict)
async def list_ots(
    status: Optional[str] = Query(None, description="Filter by status"),
    project_type: Optional[str] = Query(None, description="Filter by project type"),
    cuadrilla_id: Optional[int] = Query(None, description="Filter by cuadrilla"),
    limit: int = Query(100, ge=1, le=500, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """
    Get list of OTs with optional filters.

    Query Parameters:
    - status: Filter by OT status (PREPLANIFICADA, PLANIFICADA, etc.)
    - project_type: Filter by project type (PUBLICO, PRIVADO, TERCERIZADO)
    - cuadrilla_id: Filter by assigned cuadrilla
    - limit: Number of results (default 100, max 500)
    - offset: Pagination offset (default 0)

    Returns:
    - total: Total number of matching OTs
    - ots: List of OT objects
    """
    try:
        query = db.query(OT)

        # Apply filters
        if status:
            if status not in OT_STATUS.values():
                raise HTTPException(status_code=400, detail="Invalid status")
            query = query.filter(OT.status == status)

        if project_type:
            if project_type not in PROJECT_TYPES.values():
                raise HTTPException(status_code=400, detail="Invalid project_type")
            query = query.filter(OT.project_type == project_type)

        if cuadrilla_id:
            query = query.filter(OT.cuadrilla_id == cuadrilla_id)

        # Get total count before pagination
        total = query.count()

        # Apply pagination
        ots = query.order_by(OT.created_at.desc()).offset(offset).limit(limit).all()

        logger.info(
            f"Retrieved {len(ots)} OTs from database (total: {total})"
        )

        return {
            "total": total,
            "ots": [OTInDB.from_orm(ot) for ot in ots],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving OTs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{ot_id}", response_model=OTInDB)
async def get_ot(
    ot_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a single OT by ID.

    Parameters:
    - ot_id: The OT database ID

    Returns:
    - OT object with full details

    Raises:
    - 404: OT not found
    """
    try:
        ot = db.query(OT).filter(OT.id == ot_id).first()

        if not ot:
            logger.warning(f"OT {ot_id} not found")
            raise HTTPException(status_code=404, detail="OT not found")

        logger.info(f"Retrieved OT {ot_id}")
        return OTInDB.from_orm(ot)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving OT {ot_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("", response_model=OTInDB, status_code=201)
async def create_ot(
    ot_data: OTCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new OT.

    Request Body:
    - external_id: External OT ID from TELCOS
    - cliente_id: Client ID
    - login_id: Login ID
    - status: OT status
    - project_type: Project type
    - lat: Latitude (optional)
    - long: Longitude (optional)
    - detalle_detencion: Detail of stopped status (optional)

    Returns:
    - Created OT object

    Raises:
    - 400: Invalid data
    - 409: OT with same external_id already exists
    """
    try:
        # Check if OT with same external_id already exists
        existing_ot = db.query(OT).filter(OT.external_id == ot_data.external_id).first()
        if existing_ot:
            logger.warning(f"OT with external_id {ot_data.external_id} already exists")
            raise HTTPException(
                status_code=409,
                detail="OT with this external_id already exists",
            )

        # Create new OT
        new_ot = OT(
            external_id=ot_data.external_id,
            cliente_id=ot_data.cliente_id,
            login_id=ot_data.login_id,
            status=ot_data.status,
            project_type=ot_data.project_type,
            lat=ot_data.lat,
            long=ot_data.long,
            detalle_detencion=ot_data.detalle_detencion,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_status_change=datetime.now(),
        )

        db.add(new_ot)
        db.commit()
        db.refresh(new_ot)

        logger.info(f"Created new OT {new_ot.id} with external_id {ot_data.external_id}")
        return OTInDB.from_orm(new_ot)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating OT: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{ot_id}/status", response_model=StandardResponse)
async def update_ot_status(
    ot_id: int,
    status_update: dict,
    db: Session = Depends(get_db),
):
    """
    Update OT status with validation.

    Parameters:
    - ot_id: The OT database ID

    Request Body:
    - new_status: New status for the OT
    - motivo: Reason for status change (optional)
    - moved_by: User/agent that made the change

    Returns:
    - StandardResponse with success status

    Raises:
    - 404: OT not found
    - 400: Invalid status transition
    - 422: PUBLICO project missing required documents for FINALIZADA
    """
    try:
        # Get OT from database
        ot = db.query(OT).filter(OT.id == ot_id).first()
        if not ot:
            logger.warning(f"OT {ot_id} not found")
            raise HTTPException(status_code=404, detail="OT not found")

        new_status = status_update.get("new_status")
        motivo = status_update.get("motivo", "")
        moved_by = status_update.get("moved_by", "api")

        if not new_status:
            raise HTTPException(status_code=400, detail="new_status is required")

        # Validate status transition
        is_valid, error_msg = validate_status_transition(
            current=ot.status,
            new=new_status,
            role="admin"
        )

        if not is_valid:
            logger.warning(f"Invalid status transition for OT {ot_id}: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        # If transitioning to DETENIDA, store the motivo
        if new_status == OT_STATUS["DETENIDA"] and motivo:
            ot.detalle_detencion = motivo

        # Update status
        ot.status = new_status
        ot.updated_at = datetime.now()
        ot.last_status_change = datetime.now()

        db.commit()
        db.refresh(ot)

        logger.info(
            f"Updated OT {ot_id} status to {new_status} by {moved_by}"
        )

        return StandardResponse(
            success=True,
            data=OTInDB.from_orm(ot),
            error=None,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating OT {ot_id} status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{ot_id}", response_model=StandardResponse)
async def delete_ot(
    ot_id: int,
    db: Session = Depends(get_db),
):
    """
    Soft-delete an OT by marking it as ANULADA.

    Parameters:
    - ot_id: The OT database ID

    Returns:
    - StandardResponse with success status

    Raises:
    - 404: OT not found
    """
    try:
        ot = db.query(OT).filter(OT.id == ot_id).first()
        if not ot:
            logger.warning(f"OT {ot_id} not found for deletion")
            raise HTTPException(status_code=404, detail="OT not found")

        # Soft delete by setting status to ANULADA
        ot.status = OT_STATUS["ANULADA"]
        ot.updated_at = datetime.now()
        ot.last_status_change = datetime.now()

        db.commit()

        logger.info(f"Deleted (soft) OT {ot_id}")

        return StandardResponse(
            success=True,
            data={"id": ot.id, "status": ot.status},
            error=None,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting OT {ot_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

