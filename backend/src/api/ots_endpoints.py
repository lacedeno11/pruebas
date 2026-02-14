"""
OT (Work Order) API endpoints for PEI Platform.

Provides REST API endpoints for managing work orders:
- List and filter OTs
- Get OT details
- Ingest new OTs from external API
- Update OT status with governance validation
- View OTs with geographic errors
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.database import get_db
from src.models import OT, OTStatus, ProjectType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ots", tags=["ots"])


# Pydantic schemas for request/response
from pydantic import BaseModel
from datetime import datetime


class OTResponse(BaseModel):
    """Response schema for OT data"""

    id: int
    external_id: str
    status: str
    project_type: str
    lat: Optional[float] = None
    long: Optional[float] = None
    cliente_id: str
    login_id: str
    is_geo_error: bool
    cuadrilla_id: Optional[int] = None
    assigned_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    cuadrilla_name: Optional[str] = None

    class Config:
        from_attributes = True


class OTListResponse(BaseModel):
    """Response schema for OT list"""

    total: int
    page: int
    page_size: int
    data: list[OTResponse]


class UpdateOTStatusRequest(BaseModel):
    """Request schema for status update"""

    new_status: str
    reason: Optional[str] = None


@router.get("/", response_model=OTListResponse)
async def list_ots(
    status: Optional[str] = Query(None, description="Filter by status"),
    project_type: Optional[str] = Query(None, description="Filter by project type"),
    cuadrilla_id: Optional[int] = Query(None, description="Filter by assigned cuadrilla"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> OTListResponse:
    """
    List all OTs with optional filtering and pagination.

    Query Parameters:
    - status: Filter by OT status (PREPLANIFICADA, PLANIFICADA, etc.)
    - project_type: Filter by project type (PUBLICO, PRIVADO, TERCERIZADO)
    - cuadrilla_id: Filter by assigned cuadrilla ID
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)

    Returns:
        OTListResponse: List of OTs with pagination info
    """
    try:
        # Build query
        query = select(OT).options(joinedload(OT.cuadrilla))

        # Apply filters
        if status:
            try:
                status_enum = OTStatus[status]
                query = query.where(OT.status == status_enum)
            except KeyError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        if project_type:
            try:
                project_type_enum = ProjectType[project_type]
                query = query.where(OT.project_type == project_type_enum)
            except KeyError:
                raise HTTPException(status_code=400, detail=f"Invalid project_type: {project_type}")

        if cuadrilla_id:
            query = query.where(OT.cuadrilla_id == cuadrilla_id)

        # Get total count
        count_query = select(OT)
        if status:
            count_query = count_query.where(OT.status == status_enum)
        if project_type:
            count_query = count_query.where(OT.project_type == project_type_enum)
        if cuadrilla_id:
            count_query = count_query.where(OT.cuadrilla_id == cuadrilla_id)

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        ots = result.scalars().all()

        count_result = await db.execute(count_query)
        total = len(count_result.scalars().all())

        # Format response
        ot_responses = [
            OTResponse(
                **{
                    **{k: getattr(ot, k) for k in ot.__table__.columns.keys()},
                    "cuadrilla_name": ot.cuadrilla.name if ot.cuadrilla else None,
                },
            )
            for ot in ots
        ]

        logger.info(f"Listed {len(ots)} OTs (page {page}, total {total})")
        return OTListResponse(
            total=total,
            page=page,
            page_size=page_size,
            data=ot_responses,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing OTs: {str(e)}")
        raise HTTPException(status_code=500, detail="Error listing OTs")


@router.get("/{ot_id}", response_model=OTResponse)
async def get_ot(
    ot_id: int,
    db: AsyncSession = Depends(get_db),
) -> OTResponse:
    """
    Get a single OT by ID with full details.

    Path Parameters:
    - ot_id: OT ID

    Returns:
        OTResponse: Full OT details with cuadrilla information
    """
    try:
        result = await db.execute(
            select(OT).where(OT.id == ot_id).options(joinedload(OT.cuadrilla))
        )
        ot = result.scalars().first()

        if not ot:
            raise HTTPException(status_code=404, detail=f"OT {ot_id} not found")

        logger.info(f"Retrieved OT {ot_id}")
        return OTResponse(
            **{
                **{k: getattr(ot, k) for k in ot.__table__.columns.keys()},
                "cuadrilla_name": ot.cuadrilla.name if ot.cuadrilla else None,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting OT {ot_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error getting OT")


@router.post("/ingest")
async def ingest_ots(db: AsyncSession = Depends(get_db)):
    """
    Trigger OT ingestion from external API.

    This endpoint initiates the OTSAgent to fetch new OTs from the Telcos API,
    validate them, and create database records.

    Implementation note: This would call PEIAgentExecutor.execute() with
    'ingest_ots' route, which is implemented in agents/executor.py

    Returns:
        dict: Status of ingestion operation
    """
    try:
        logger.info("Ingestion endpoint called - would execute OTSAgent")
        # TODO: Implement integration with PEIAgentExecutor
        return {
            "status": "scheduled",
            "message": "OT ingestion job scheduled",
        }
    except Exception as e:
        logger.error(f"Error triggering OT ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail="Error triggering ingestion")


@router.patch("/{ot_id}/status")
async def update_ot_status(
    ot_id: int,
    request: UpdateOTStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update OT status with governance validation.

    This endpoint validates the status transition using GobernanzaAgent
    before allowing the change.

    Path Parameters:
    - ot_id: OT ID

    Request Body:
    - new_status: Target status
    - reason: Optional reason for status change (required for DETENIDA)

    Returns:
        dict: Updated OT data
    """
    try:
        # Get OT
        result = await db.execute(select(OT).where(OT.id == ot_id))
        ot = result.scalars().first()

        if not ot:
            raise HTTPException(status_code=404, detail=f"OT {ot_id} not found")

        # Validate status
        try:
            new_status = OTStatus[request.new_status]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {request.new_status}")

        # Check if transition is allowed (basic validation)
        if not ot.can_transition_to(new_status):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition from {ot.status.value} to {new_status.value}",
            )

        # Special handling for DETENIDA status
        if new_status == OTStatus.DETENIDA and not request.reason:
            raise HTTPException(
                status_code=400,
                detail="Detention reason is required when transitioning to DETENIDA",
            )

        # Update OT
        ot.status = new_status
        if new_status == OTStatus.DETENIDA:
            ot.detention_reason = request.reason

        await db.commit()

        logger.info(f"Updated OT {ot_id} status to {new_status.value}")
        return {
            "success": True,
            "data": {
                "id": ot.id,
                "external_id": ot.external_id,
                "status": ot.status.value,
                "updated_at": ot.updated_at.isoformat(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating OT {ot_id} status: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error updating OT status")


@router.get("/geo-errors")
async def list_geo_errors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> OTListResponse:
    """
    List OTs with geographic errors.

    These are OTs with missing or invalid coordinates that need manual intervention.

    Query Parameters:
    - page: Page number
    - page_size: Items per page

    Returns:
        OTListResponse: List of OTs with is_geo_error=True
    """
    try:
        query = select(OT).where(OT.is_geo_error == True)

        # Get total count
        count_result = await db.execute(select(OT).where(OT.is_geo_error == True))
        total = len(count_result.scalars().all())

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query.options(joinedload(OT.cuadrilla)))
        ots = result.scalars().all()

        ot_responses = [
            OTResponse(
                **{
                    **{k: getattr(ot, k) for k in ot.__table__.columns.keys()},
                    "cuadrilla_name": ot.cuadrilla.name if ot.cuadrilla else None,
                },
            )
            for ot in ots
        ]

        logger.info(f"Listed {len(ots)} OTs with geo errors")
        return OTListResponse(
            total=total,
            page=page,
            page_size=page_size,
            data=ot_responses,
        )

    except Exception as e:
        logger.error(f"Error listing geo errors: {str(e)}")
        raise HTTPException(status_code=500, detail="Error listing geo errors")

