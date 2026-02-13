"""
OT (Work Order) API Endpoints

This module provides REST API endpoints for managing work orders (OTs) in the DERCAS PEI system.

Endpoints:
    GET    /ots              - List all OTs with optional filters
    POST   /ots              - Create a new OT
    GET    /ots/{ot_id}      - Get single OT details
    PATCH  /ots/{ot_id}      - Update OT fields
    POST   /ots/{ot_id}/transition - Perform state transition
    DELETE /ots/{ot_id}      - Soft delete OT (transition to ANULADA)

Features:
    - Pagination support with skip/limit parameters
    - Filtering by status, project_type, cuadrilla_id
    - State machine validation for transitions
    - Proper HTTP status codes and error responses
    - Automatic audit logging via LogAgente
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models import OT, LogAgente
from app.schemas import OTCreate, OTUpdate, OTResponse, OTTransitionRequest, OTStatus
from app.services.governance_service import GovernanceService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/ots",
    tags=["ots"],
    responses={
        404: {"description": "OT not found"},
        500: {"description": "Internal server error"},
    },
)


# ============================================================================
# List OTs Endpoint
# ============================================================================


@router.get("/", response_model=dict, status_code=status.HTTP_200_OK)
async def list_ots(
    db: AsyncSession = Depends(get_db_session),
    skip: int = Query(0, ge=0, description="Number of OTs to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum OTs to return"),
    status_filter: Optional[str] = Query(None, description="Filter by OT status"),
    project_type: Optional[str] = Query(None, description="Filter by project type (PUBLICO, PRIVADO, TERCERIZADO)"),
    cuadrilla_id: Optional[int] = Query(None, description="Filter by assigned crew ID"),
) -> dict:
    """
    List all work orders with optional filtering and pagination.
    
    Query Parameters:
        skip: Number of results to skip for pagination (default: 0)
        limit: Maximum number of results to return (default: 50, max: 100)
        status_filter: Filter by OT status (PREPLANIFICADA, PLANIFICADA, etc.)
        project_type: Filter by project type (PUBLICO, PRIVADO, TERCERIZADO)
        cuadrilla_id: Filter by assigned crew ID
    
    Returns:
        Dict with:
        - items: List of OTResponse objects
        - total: Total count of matching OTs
        - skip: Pagination offset
        - limit: Page size
    
    Status Codes:
        200: Success
        400: Invalid filter parameters
    """
    try:
        # Build base query
        query = select(OT)

        # Apply filters
        if status_filter:
            try:
                OTStatus(status_filter)  # Validate enum
                query = query.where(OT.status == status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}",
                )

        if project_type:
            query = query.where(OT.project_type == project_type)

        if cuadrilla_id is not None:
            query = query.where(OT.cuadrilla_id == cuadrilla_id)

        # Get total count
        count_query = select(func.count(OT.id))
        if status_filter:
            count_query = count_query.where(OT.status == status_filter)
        if project_type:
            count_query = count_query.where(OT.project_type == project_type)
        if cuadrilla_id is not None:
            count_query = count_query.where(OT.cuadrilla_id == cuadrilla_id)

        total = await db.scalar(count_query)

        # Apply pagination and execute
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        ots = result.scalars().all()

        logger.info(
            f"Listed {len(ots)} OTs with filters: "
            f"status={status_filter}, project_type={project_type}, cuadrilla_id={cuadrilla_id}"
        )

        return {
            "items": [OTResponse.from_orm(ot) for ot in ots],
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing OTs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list OTs",
        )


# ============================================================================
# Create OT Endpoint
# ============================================================================


@router.post("/", response_model=OTResponse, status_code=status.HTTP_201_CREATED)
async def create_ot(
    ot_data: OTCreate,
    db: AsyncSession = Depends(get_db_session),
) -> OT:
    """
    Create a new work order.
    
    Request Body:
        OTCreate schema with:
        - external_id: Unique identifier from TELCOS system
        - cliente_id: Customer identifier
        - login: Field technician login
        - lat: Latitude (optional, triggers ERROR_GEO if missing)
        - long: Longitude (optional, triggers ERROR_GEO if missing)
        - project_type: PUBLICO, PRIVADO, or TERCERIZADO
    
    Returns:
        OTResponse with created OT details and id
    
    Status Codes:
        201: OT created successfully
        400: Invalid request data
        409: Duplicate external_id
        500: Internal server error
    """
    try:
        # Check for duplicate external_id
        existing = await db.execute(
            select(OT).where(OT.external_id == ot_data.external_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"OT with external_id {ot_data.external_id} already exists",
            )

        # Create new OT
        new_ot = OT(**ot_data.dict())

        # Set ERROR_GEO status if coordinates missing
        if not new_ot.has_coordinates:
            new_ot.status = "ERROR_GEO"

        db.add(new_ot)
        await db.flush()

        # Log creation
        log = LogAgente(
            ot_id=new_ot.id,
            agente_name="ROUTER",
            accion=f"OT created: {ot_data.external_id}",
            resultado="SUCCESS",
        )
        db.add(log)
        await db.commit()

        logger.info(f"Created OT {new_ot.external_id} with id {new_ot.id}")

        return new_ot

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating OT: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create OT",
        )


# ============================================================================
# Get OT Endpoint
# ============================================================================


@router.get("/{ot_id}", response_model=OTResponse, status_code=status.HTTP_200_OK)
async def get_ot(
    ot_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> OT:
    """
    Get details of a specific work order.
    
    Path Parameters:
        ot_id: OT database ID
    
    Returns:
        OTResponse with full OT details
    
    Status Codes:
        200: Success
        404: OT not found
        500: Internal server error
    """
    try:
        query = select(OT).where(OT.id == ot_id)
        result = await db.execute(query)
        ot = result.scalar_one_or_none()

        if not ot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OT with id {ot_id} not found",
            )

        logger.info(f"Retrieved OT {ot.external_id}")
        return ot

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving OT {ot_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OT",
        )


# ============================================================================
# Update OT Endpoint
# ============================================================================


@router.patch("/{ot_id}", response_model=OTResponse, status_code=status.HTTP_200_OK)
async def update_ot(
    ot_id: int,
    ot_data: OTUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> OT:
    """
    Partially update a work order.
    
    Path Parameters:
        ot_id: OT database ID
    
    Request Body:
        OTUpdate schema with optional fields to update
    
    Returns:
        Updated OTResponse
    
    Status Codes:
        200: Updated successfully
        404: OT not found
        500: Internal server error
    """
    try:
        # Get OT
        query = select(OT).where(OT.id == ot_id)
        result = await db.execute(query)
        ot = result.scalar_one_or_none()

        if not ot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OT with id {ot_id} not found",
            )

        # Update fields
        update_data = ot_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(ot, field, value)

        # Check coordinates
        if not ot.has_coordinates:
            ot.status = "ERROR_GEO"

        db.add(ot)

        # Log update
        log = LogAgente(
            ot_id=ot.id,
            agente_name="ROUTER",
            accion=f"OT updated: {list(update_data.keys())}",
            resultado="SUCCESS",
        )
        db.add(log)
        await db.commit()

        logger.info(f"Updated OT {ot.external_id}")
        return ot

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating OT {ot_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update OT",
        )


# ============================================================================
# State Transition Endpoint
# ============================================================================


@router.post(
    "/{ot_id}/transition",
    response_model=OTResponse,
    status_code=status.HTTP_200_OK,
)
async def transition_ot(
    ot_id: int,
    transition_data: OTTransitionRequest,
    db: AsyncSession = Depends(get_db_session),
) -> OT:
    """
    Perform a state transition on a work order.
    
    Path Parameters:
        ot_id: OT database ID
    
    Request Body:
        OTTransitionRequest with:
        - new_status: Target status
        - cuadrilla_id: Optional crew assignment
        - reason: Required for DETENIDA status (detention reason)
    
    Returns:
        OTResponse with updated status
    
    Status Codes:
        200: Transition successful
        400: Invalid transition
        404: OT not found
        422: Validation error (e.g., missing reason for DETENIDA)
        500: Internal server error
    """
    try:
        # Get OT
        query = select(OT).where(OT.id == ot_id)
        result = await db.execute(query)
        ot = result.scalar_one_or_none()

        if not ot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OT with id {ot_id} not found",
            )

        # Validate transition
        governance_service = GovernanceService()
        is_valid, error_msg = await governance_service.validate_transition(
            ot_id, transition_data.new_status, db
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Invalid state transition",
            )

        # Check DETENIDA transition requirements
        if transition_data.new_status == "DETENIDA":
            if not transition_data.reason:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Detention reason required for DETENIDA status",
                )
            ot.detention_reason = transition_data.reason
            ot.detention_date = None  # Will be set in model

        # Update status
        old_status = ot.status
        ot.status = transition_data.new_status

        # Update crew assignment if provided
        if transition_data.cuadrilla_id is not None:
            ot.cuadrilla_id = transition_data.cuadrilla_id

        db.add(ot)
        await db.flush()

        # Log transition
        log = LogAgente(
            ot_id=ot.id,
            agente_name="ROUTER",
            accion=(
                f"State transition: {old_status} → {transition_data.new_status}"
                f"{f' (Reason: {transition_data.reason})' if transition_data.reason else ''}"
            ),
            resultado="SUCCESS",
        )
        db.add(log)
        await db.commit()

        logger.info(
            f"OT {ot.external_id} transitioned: {old_status} → {transition_data.new_status}"
        )

        return ot

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error transitioning OT {ot_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to transition OT",
        )


# ============================================================================
# Delete OT Endpoint (Soft Delete)
# ============================================================================


@router.delete("/{ot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ot(
    ot_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Soft delete a work order by transitioning to ANULADA status.
    
    Instead of hard deleting, this transitions the OT to ANULADA status,
    preserving audit trail and historical data.
    
    Path Parameters:
        ot_id: OT database ID
    
    Status Codes:
        204: Deleted successfully
        404: OT not found
        400: Cannot transition to ANULADA from current status
        500: Internal server error
    """
    try:
        # Get OT
        query = select(OT).where(OT.id == ot_id)
        result = await db.execute(query)
        ot = result.scalar_one_or_none()

        if not ot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OT with id {ot_id} not found",
            )

        # Check if already deleted
        if ot.status == "ANULADA":
            logger.info(f"OT {ot.external_id} already deleted")
            return  # Idempotent

        # Validate transition to ANULADA
        if not ot.can_transition_to("ANULADA"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete OT from {ot.status} status",
            )

        # Transition to ANULADA
        old_status = ot.status
        ot.status = "ANULADA"
        db.add(ot)
        await db.flush()

        # Log deletion
        log = LogAgente(
            ot_id=ot.id,
            agente_name="ROUTER",
            accion=f"OT deleted (soft delete): {old_status} → ANULADA",
            resultado="SUCCESS",
        )
        db.add(log)
        await db.commit()

        logger.info(f"OT {ot.external_id} soft deleted")

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting OT {ot_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete OT",
        )


# ============================================================================
# Module Exports
# ============================================================================

__all__ = ["router"]

