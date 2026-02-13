"""
Cuadrilla API endpoints for PEI Platform.

Provides REST API endpoints for managing work teams (cuadrillas):
- List and filter cuadrillas
- Get cuadrilla details with assigned OTs
- Get cuadrilla centroid coordinates
- Create new cuadrillas
- Update cuadrilla configuration
- Get capacity utilization statistics
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.database import get_db
from src.models import Cuadrilla, CuadrillaType, OT, OTStatus
from src.utils.geo_utils import calculate_centroid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cuadrillas", tags=["cuadrillas"])


# Pydantic schemas for request/response
from pydantic import BaseModel
from typing import List


class CuadrillaResponse(BaseModel):
    """Response schema for Cuadrilla data"""

    id: int
    name: str
    type: str
    last_centroid_lat: Optional[float] = None
    last_centroid_long: Optional[float] = None
    max_daily_capacity: int
    current_load: int

    class Config:
        from_attributes = True


class CuadrillaDetailResponse(CuadrillaResponse):
    """Detailed cuadrilla response with assigned OTs"""

    assigned_ots_count: int
    available_capacity: int
    utilization_percentage: float


class CreateCuadrillaRequest(BaseModel):
    """Request schema for creating a cuadrilla"""

    name: str
    type: str  # PRINCIPAL or RESERVA
    max_daily_capacity: int = 10


class UpdateCuadrillaRequest(BaseModel):
    """Request schema for updating a cuadrilla"""

    name: Optional[str] = None
    max_daily_capacity: Optional[int] = None


class CentroidResponse(BaseModel):
    """Response schema for centroid coordinates"""

    latitude: float
    longitude: float
    updated_at: Optional[str] = None


class CapacityStats(BaseModel):
    """Capacity statistics response"""

    total_capacity: int
    used_capacity: int
    available_capacity: int
    utilization_percentage: float
    by_type: dict


class CuadrillaListResponse(BaseModel):
    """Response schema for cuadrilla list"""

    total: int
    page: int
    page_size: int
    data: List[CuadrillaResponse]


@router.get("/", response_model=CuadrillaListResponse)
async def list_cuadrillas(
    type_filter: Optional[str] = Query(None, alias="type", description="Filter by type (PRINCIPAL or RESERVA)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> CuadrillaListResponse:
    """
    List all cuadrillas with optional type filtering and pagination.

    Query Parameters:
    - type: Filter by cuadrilla type (PRINCIPAL or RESERVA)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)

    Returns:
        CuadrillaListResponse: List of cuadrillas with pagination info
    """
    try:
        # Build query
        query = select(Cuadrilla)

        # Apply type filter
        if type_filter:
            try:
                type_enum = CuadrillaType[type_filter]
                query = query.where(Cuadrilla.type == type_enum)
            except KeyError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid type: {type_filter}. Must be PRINCIPAL or RESERVA",
                )

        # Get total count
        count_query = select(Cuadrilla)
        if type_filter:
            count_query = count_query.where(Cuadrilla.type == type_enum)
        
        count_result = await db.execute(count_query)
        total = len(count_result.scalars().all())

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        cuadrillas = result.scalars().all()

        cuadrilla_responses = [CuadrillaResponse.from_orm(c) for c in cuadrillas]

        logger.info(f"Listed {len(cuadrillas)} cuadrillas (page {page}, total {total})")
        return CuadrillaListResponse(
            total=total,
            page=page,
            page_size=page_size,
            data=cuadrilla_responses,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing cuadrillas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error listing cuadrillas")


@router.get("/{cuadrilla_id}", response_model=CuadrillaDetailResponse)
async def get_cuadrilla(
    cuadrilla_id: int,
    db: AsyncSession = Depends(get_db),
) -> CuadrillaDetailResponse:
    """
    Get a single cuadrilla by ID with full details and assigned OTs.

    Path Parameters:
    - cuadrilla_id: Cuadrilla ID

    Returns:
        CuadrillaDetailResponse: Full cuadrilla details with OT count and capacity info
    """
    try:
        result = await db.execute(
            select(Cuadrilla).where(Cuadrilla.id == cuadrilla_id).options(joinedload(Cuadrilla.ots))
        )
        cuadrilla = result.scalars().first()

        if not cuadrilla:
            raise HTTPException(status_code=404, detail=f"Cuadrilla {cuadrilla_id} not found")

        assigned_ots_count = len(cuadrilla.ots)
        available_capacity = cuadrilla.max_daily_capacity - cuadrilla.current_load
        utilization_percentage = (
            (cuadrilla.current_load / cuadrilla.max_daily_capacity * 100)
            if cuadrilla.max_daily_capacity > 0
            else 0
        )

        logger.info(f"Retrieved cuadrilla {cuadrilla_id}")
        return CuadrillaDetailResponse(
            id=cuadrilla.id,
            name=cuadrilla.name,
            type=cuadrilla.type.value,
            last_centroid_lat=cuadrilla.last_centroid_lat,
            last_centroid_long=cuadrilla.last_centroid_long,
            max_daily_capacity=cuadrilla.max_daily_capacity,
            current_load=cuadrilla.current_load,
            assigned_ots_count=assigned_ots_count,
            available_capacity=available_capacity,
            utilization_percentage=utilization_percentage,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cuadrilla {cuadrilla_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error getting cuadrilla")


@router.get("/{cuadrilla_id}/centroid", response_model=CentroidResponse)
async def get_cuadrilla_centroid(
    cuadrilla_id: int,
    db: AsyncSession = Depends(get_db),
) -> CentroidResponse:
    """
    Get the current centroid coordinates for a cuadrilla.

    The centroid is calculated from the assigned OTs' coordinates and is used
    for proximity-based planning decisions.

    Path Parameters:
    - cuadrilla_id: Cuadrilla ID

    Returns:
        CentroidResponse: Centroid coordinates (latitude, longitude)
    """
    try:
        result = await db.execute(
            select(Cuadrilla).where(Cuadrilla.id == cuadrilla_id)
        )
        cuadrilla = result.scalars().first()

        if not cuadrilla:
            raise HTTPException(status_code=404, detail=f"Cuadrilla {cuadrilla_id} not found")

        if cuadrilla.last_centroid_lat is None or cuadrilla.last_centroid_long is None:
            return CentroidResponse(
                latitude=0.0,
                longitude=0.0,
                updated_at=None,
            )

        logger.info(f"Retrieved centroid for cuadrilla {cuadrilla_id}")
        return CentroidResponse(
            latitude=cuadrilla.last_centroid_lat,
            longitude=cuadrilla.last_centroid_long,
            updated_at=cuadrilla.updated_at.isoformat() if cuadrilla.updated_at else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting centroid for cuadrilla {cuadrilla_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error getting centroid")


@router.post("/", response_model=CuadrillaResponse)
async def create_cuadrilla(
    request: CreateCuadrillaRequest,
    db: AsyncSession = Depends(get_db),
) -> CuadrillaResponse:
    """
    Create a new cuadrilla.

    Request Body:
    - name: Unique cuadrilla name
    - type: Cuadrilla type (PRINCIPAL or RESERVA)
    - max_daily_capacity: Maximum daily OT capacity (default: 10)

    Returns:
        CuadrillaResponse: Created cuadrilla data
    """
    try:
        # Validate type
        try:
            type_enum = CuadrillaType[request.type]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid type: {request.type}. Must be PRINCIPAL or RESERVA",
            )

        # Check if name already exists
        existing = await db.execute(
            select(Cuadrilla).where(Cuadrilla.name == request.name)
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=400,
                detail=f"Cuadrilla with name '{request.name}' already exists",
            )

        # Create new cuadrilla
        cuadrilla = Cuadrilla(
            name=request.name,
            type=type_enum,
            max_daily_capacity=request.max_daily_capacity,
            current_load=0,
        )

        db.add(cuadrilla)
        await db.commit()
        await db.refresh(cuadrilla)

        logger.info(f"Created cuadrilla {request.name} with id {cuadrilla.id}")
        return CuadrillaResponse.from_orm(cuadrilla)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating cuadrilla: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error creating cuadrilla")


@router.patch("/{cuadrilla_id}", response_model=CuadrillaResponse)
async def update_cuadrilla(
    cuadrilla_id: int,
    request: UpdateCuadrillaRequest,
    db: AsyncSession = Depends(get_db),
) -> CuadrillaResponse:
    """
    Update a cuadrilla's configuration.

    Path Parameters:
    - cuadrilla_id: Cuadrilla ID

    Request Body:
    - name: New cuadrilla name (optional)
    - max_daily_capacity: New capacity (optional)

    Returns:
        CuadrillaResponse: Updated cuadrilla data
    """
    try:
        result = await db.execute(
            select(Cuadrilla).where(Cuadrilla.id == cuadrilla_id)
        )
        cuadrilla = result.scalars().first()

        if not cuadrilla:
            raise HTTPException(status_code=404, detail=f"Cuadrilla {cuadrilla_id} not found")

        # Update fields if provided
        if request.name:
            # Check if new name already exists
            existing = await db.execute(
                select(Cuadrilla).where(
                    Cuadrilla.name == request.name,
                    Cuadrilla.id != cuadrilla_id,
                )
            )
            if existing.scalars().first():
                raise HTTPException(
                    status_code=400,
                    detail=f"Cuadrilla with name '{request.name}' already exists",
                )
            cuadrilla.name = request.name

        if request.max_daily_capacity is not None:
            if request.max_daily_capacity < 1:
                raise HTTPException(
                    status_code=400,
                    detail="max_daily_capacity must be at least 1",
                )
            cuadrilla.max_daily_capacity = request.max_daily_capacity

        await db.commit()
        await db.refresh(cuadrilla)

        logger.info(f"Updated cuadrilla {cuadrilla_id}")
        return CuadrillaResponse.from_orm(cuadrilla)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cuadrilla {cuadrilla_id}: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error updating cuadrilla")


@router.get("/stats")
async def get_capacity_stats(
    db: AsyncSession = Depends(get_db),
) -> CapacityStats:
    """
    Get aggregate capacity utilization statistics.

    Returns overall system capacity metrics and breakdown by cuadrilla type.

    Returns:
        CapacityStats: Overall and per-type capacity statistics
    """
    try:
        # Get all cuadrillas
        result = await db.execute(select(Cuadrilla))
        cuadrillas = result.scalars().all()

        total_capacity = sum(c.max_daily_capacity for c in cuadrillas)
        used_capacity = sum(c.current_load for c in cuadrillas)
        available_capacity = total_capacity - used_capacity

        utilization_percentage = (
            (used_capacity / total_capacity * 100) if total_capacity > 0 else 0
        )

        # Calculate by type
        by_type = {}
        for cuad_type in CuadrillaType:
            type_cuadrillas = [c for c in cuadrillas if c.type == cuad_type]
            type_total = sum(c.max_daily_capacity for c in type_cuadrillas)
            type_used = sum(c.current_load for c in type_cuadrillas)
            type_available = type_total - type_used
            type_utilization = (
                (type_used / type_total * 100) if type_total > 0 else 0
            )

            by_type[cuad_type.value] = {
                "total_capacity": type_total,
                "used_capacity": type_used,
                "available_capacity": type_available,
                "utilization_percentage": type_utilization,
                "count": len(type_cuadrillas),
            }

        logger.info(f"Retrieved capacity stats: {used_capacity}/{total_capacity} ({utilization_percentage:.1f}%)")
        return CapacityStats(
            total_capacity=total_capacity,
            used_capacity=used_capacity,
            available_capacity=available_capacity,
            utilization_percentage=utilization_percentage,
            by_type=by_type,
        )

    except Exception as e:
        logger.error(f"Error getting capacity stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Error getting capacity stats")

