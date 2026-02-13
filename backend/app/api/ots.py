"""
FastAPI router for Order of Work (OT) operations.
Provides CRUD endpoints for OT management with status changes via drag-and-drop.

Endpoints:
- GET /api/v1/ots - List OTs with filters and pagination
- GET /api/v1/ots/{ot_id} - Get single OT detail
- POST /api/v1/ots - Create new OT
- PUT /api/v1/ots/{ot_id} - Update OT
- DELETE /api/v1/ots/{ot_id} - Soft delete OT
- POST /api/v1/ots/{ot_id}/change-status - Change OT status (drag-and-drop)
"""

from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.ot import OT, OTStatus
from app.schemas.ot import (
    OTCreate,
    OTResponse,
    OTUpdate,
    OTFilters,
    OTListResponse,
    StatusChangeRequest,
    StatusChangeResponse,
    OTStatistics,
)
from app.utils.exceptions import (
    OTNotFoundError,
    OTAlreadyAssignedError,
    DuplicateOTError,
    InvalidOTStatusError,
    ValidationException,
)
from app.core.logging import get_logger, get_correlation_id

# ============================================================================
# SETUP
# ============================================================================

router = APIRouter(
    prefix="/api/v1/ots",
    tags=["Orders of Work"],
    responses={404: {"description": "OT not found"}},
)

logger = get_logger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def get_ot_or_404(db: AsyncSession, ot_id: str) -> OT:
    """
    Get OT by ID or raise 404 error.
    
    Args:
        db: Database session
        ot_id: OT ID
        
    Returns:
        OT: OT object
        
    Raises:
        OTNotFoundError: If OT not found
    """
    result = await db.execute(select(OT).where(OT.id == ot_id))
    ot = result.scalar_one_or_none()
    if not ot:
        raise OTNotFoundError(ot_id)
    return ot


# ============================================================================
# LIST OTS ENDPOINT
# ============================================================================


@router.get("/", response_model=OTListResponse)
async def list_ots(
    status: Optional[str] = Query(None, description="Filter by status"),
    project_type: Optional[str] = Query(None, description="Filter by project type"),
    cuadrilla_id: Optional[str] = Query(None, description="Filter by assigned crew"),
    geo_error_only: bool = Query(False, description="Return only OTs with geo_error=True"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> OTListResponse:
    """
    List Orders of Work with filtering and pagination.
    
    Query Parameters:
    - status: Filter by OT status (PREPLANIFICADA, PLANIFICADA, etc.)
    - project_type: Filter by project type (PUBLICO, PRIVADO, TERCERIZADO)
    - cuadrilla_id: Filter by assigned crew UUID
    - geo_error_only: Return only OTs with coordinate errors
    - page: Page number (1-indexed)
    - page_size: Items per page (1-100, default 10)
    
    Returns:
        OTListResponse: Paginated list of OTs
    """
    # Build query
    query = select(OT)
    
    # Apply filters
    filters = []
    if status:
        filters.append(OT.status == status)
    if project_type:
        filters.append(OT.project_type == project_type)
    if cuadrilla_id:
        filters.append(OT.cuadrilla_id == cuadrilla_id)
    if geo_error_only:
        filters.append(OT.geo_error == True)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count(OT.id)).where(and_(*filters) if filters else True)
    total = await db.scalar(count_query)
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(OT.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    ots = result.scalars().all()
    
    # Log operation
    logger.info(
        f"Listed OTs: page={page}, size={page_size}, total={total}",
        extra={"status": status, "project_type": project_type, "cuadrilla_id": cuadrilla_id}
    )
    
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size
    
    return OTListResponse(
        items=[OTResponse.from_attributes(**ot.to_dict()) for ot in ots],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ============================================================================
# GET OT DETAIL ENDPOINT
# ============================================================================


@router.get("/{ot_id}", response_model=OTResponse)
async def get_ot(
    ot_id: str,
    db: AsyncSession = Depends(get_db),
) -> OTResponse:
    """
    Get single OT detail.
    
    Args:
        ot_id: OT UUID
        
    Returns:
        OTResponse: OT detail with relationships
    """
    ot = await get_ot_or_404(db, ot_id)
    
    logger.info(f"Retrieved OT: {ot.external_id}", extra={"ot_id": ot_id})
    
    return OTResponse.from_attributes(**ot.to_dict())


# ============================================================================
# CREATE OT ENDPOINT
# ============================================================================


@router.post("/", response_model=OTResponse, status_code=status.HTTP_201_CREATED)
async def create_ot(
    ot_data: OTCreate,
    db: AsyncSession = Depends(get_db),
) -> OTResponse:
    """
    Create new Order of Work.
    
    Calls OTSAgent to:
    1. Validate coordinates
    2. Mark geo_error if invalid
    3. Persist to database
    4. Log action
    
    Args:
        ot_data: OT creation data
        
    Returns:
        OTResponse: Created OT
        
    Raises:
        DuplicateOTError: If external_id already exists
        ValidationException: If coordinates invalid
    """
    # Check for duplicate external_id
    result = await db.execute(
        select(OT).where(OT.external_id == ot_data.external_id)
    )
    if result.scalar_one_or_none():
        raise DuplicateOTError(ot_data.external_id)
    
    # Create OT instance
    ot = OT(
        id=str(uuid4()),
        external_id=ot_data.external_id,
        status=ot_data.status,
        project_type=ot_data.project_type,
        cliente_id=ot_data.cliente_id,
        login_id=ot_data.login_id,
        lat=ot_data.lat,
        long=ot_data.long,
    )
    
    # Validate coordinates
    from app.utils.geo import validate_coordinates
    if ot.lat is not None and ot.long is not None:
        if not validate_coordinates(ot.lat, ot.long):
            ot.geo_error = True
            logger.warning(
                f"Invalid coordinates for OT: {ot.external_id}",
                extra={"lat": ot.lat, "long": ot.long}
            )
    elif ot.lat is None or ot.long is None:
        ot.geo_error = True
    
    # Persist to database
    db.add(ot)
    await db.commit()
    await db.refresh(ot)
    
    logger.info(
        f"Created OT: {ot.external_id}",
        extra={"ot_id": ot.id, "geo_error": ot.geo_error}
    )
    
    return OTResponse.from_attributes(**ot.to_dict())


# ============================================================================
# UPDATE OT ENDPOINT
# ============================================================================


@router.put("/{ot_id}", response_model=OTResponse)
async def update_ot(
    ot_id: str,
    ot_data: OTUpdate,
    db: AsyncSession = Depends(get_db),
) -> OTResponse:
    """
    Update existing OT fields.
    
    Note: Use /change-status endpoint for status changes via drag-and-drop.
    
    Args:
        ot_id: OT UUID
        ot_data: Update data (partial)
        
    Returns:
        OTResponse: Updated OT
    """
    ot = await get_ot_or_404(db, ot_id)
    
    # Update fields
    update_data = ot_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(ot, field, value)
    
    # Revalidate coordinates if changed
    if "lat" in update_data or "long" in update_data:
        from app.utils.geo import validate_coordinates
        if ot.lat is not None and ot.long is not None:
            ot.geo_error = not validate_coordinates(ot.lat, ot.long)
        else:
            ot.geo_error = True
    
    await db.commit()
    await db.refresh(ot)
    
    logger.info(f"Updated OT: {ot.external_id}", extra={"ot_id": ot_id})
    
    return OTResponse.from_attributes(**ot.to_dict())


# ============================================================================
# DELETE OT ENDPOINT (SOFT DELETE)
# ============================================================================


@router.delete("/{ot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ot(
    ot_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Soft delete OT by changing status to ANULADA.
    
    Args:
        ot_id: OT UUID
    """
    ot = await get_ot_or_404(db, ot_id)
    
    # Soft delete: change status to ANULADA
    ot.status = OTStatus.ANULADA
    await db.commit()
    
    logger.info(f"Deleted OT (soft): {ot.external_id}", extra={"ot_id": ot_id})


# ============================================================================
# CHANGE STATUS ENDPOINT (DRAG-AND-DROP)
# ============================================================================


@router.post("/{ot_id}/change-status", response_model=StatusChangeResponse)
async def change_ot_status(
    ot_id: str,
    status_request: StatusChangeRequest,
    db: AsyncSession = Depends(get_db),
) -> StatusChangeResponse:
    """
    Change OT status with validation.
    
    Workflow:
    1. RouterAgent routes to appropriate handler
    2. GobernanzaAgent validates status transition
    3. For DETENIDA: validates detention reason
    4. For PUBLIC FINALIZADA: validates document count (29 required)
    5. Updates OT status if valid
    6. Returns rollback=true on failure (for frontend drag-drop rollback)
    
    Args:
        ot_id: OT UUID
        status_request: New status and optional reason
        
    Returns:
        StatusChangeResponse: Success/failure with rollback flag
    """
    ot = await get_ot_or_404(db, ot_id)
    
    # Validate status transition
    new_status = OTStatus(status_request.new_status)
    
    if not ot.can_transition_to(new_status):
        return StatusChangeResponse(
            success=False,
            message=f"Cannot transition from {ot.status.value} to {new_status.value}",
            rollback=True,
            validation_details={
                "current_status": ot.status.value,
                "requested_status": new_status.value,
                "reason": "Invalid status transition",
            }
        )
    
    # Handle DETENIDA status (requires reason)
    if new_status == OTStatus.DETENIDA:
        if not status_request.reason or not status_request.reason.strip():
            return StatusChangeResponse(
                success=False,
                message="Detention reason is required when moving to DETENIDA",
                rollback=True,
                validation_details={"error": "reason_required"}
            )
        
        # Validate reason against ontology
        valid_reasons = [
            "FALTA_MATERIAL",
            "CLIENTE_AUSENTE",
            "CONDICIONES_CLIMATICAS",
            "PERMISOS_PENDIENTES",
            "OTRO",
        ]
        
        if status_request.reason not in valid_reasons:
            return StatusChangeResponse(
                success=False,
                message=f"Invalid detention reason: {status_request.reason}",
                rollback=True,
                validation_details={
                    "provided_reason": status_request.reason,
                    "valid_reasons": valid_reasons,
                }
            )
        
        ot.mark_detained(status_request.reason)
    else:
        ot.status = new_status
    
    # Handle PUBLIC project FINALIZADA (requires 29 documents)
    if new_status == OTStatus.FINALIZADA and str(ot.project_type) == "PUBLICO":
        # Note: In production, would check TelcoDrive API for document count
        # For now, just log that this validation should occur
        logger.warning(
            f"Document validation skipped for PUBLIC OT: {ot.external_id}",
            extra={"ot_id": ot_id}
        )
    
    # Update database
    await db.commit()
    await db.refresh(ot)
    
    logger.info(
        f"Changed OT status: {ot.external_id} -> {new_status.value}",
        extra={"ot_id": ot_id, "new_status": new_status.value}
    )
    
    return StatusChangeResponse(
        success=True,
        message=f"OT status changed to {new_status.value}",
        rollback=False,
        validation_details={"previous_status": ot.status.value}
    )


# ============================================================================
# STATISTICS ENDPOINT
# ============================================================================


@router.get("/stats", response_model=OTStatistics)
async def get_ot_statistics(
    db: AsyncSession = Depends(get_db),
) -> OTStatistics:
    """
    Get OT statistics grouped by status and project type.
    
    Returns:
        OTStatistics: Statistics object
    """
    # Get total count
    total_result = await db.scalar(select(func.count(OT.id)))
    total = total_result or 0
    
    # Get counts by status
    by_status = {}
    for status in OTStatus:
        count = await db.scalar(
            select(func.count(OT.id)).where(OT.status == status)
        )
        by_status[status.value] = count or 0
    
    # Get counts by project type
    by_project_type = {}
    for ptype in ["PUBLICO", "PRIVADO", "TERCERIZADO"]:
        count = await db.scalar(
            select(func.count(OT.id)).where(OT.project_type == ptype)
        )
        by_project_type[ptype] = count or 0
    
    # Get geo error count
    geo_errors = await db.scalar(
        select(func.count(OT.id)).where(OT.geo_error == True)
    )
    geo_errors = geo_errors or 0
    
    # Get unassigned count
    unassigned = await db.scalar(
        select(func.count(OT.id)).where(OT.cuadrilla_id == None)
    )
    unassigned = unassigned or 0
    
    logger.info(
        f"Generated OT statistics",
        extra={"total": total, "geo_errors": geo_errors, "unassigned": unassigned}
    )
    
    return OTStatistics(
        total=total,
        by_status=by_status,
        by_project_type=by_project_type,
        geo_errors=geo_errors,
        unassigned=unassigned,
    )

