"""
Cuadrilla (Work Crew) API Endpoints

Manages crew registration, assignment tracking, and centroid calculations
for the automatic 3-phase crew assignment algorithm.

Endpoints:
- GET /cuadrillas - List all crews with optional type filtering
- POST /cuadrillas - Create new crew
- GET /cuadrillas/{id} - Get crew details with assignment summary
- GET /cuadrillas/{id}/ots - Get all OTs assigned to crew
- PATCH /cuadrillas/{id} - Update crew capacity or other fields
- POST /cuadrillas/{id}/recalculate-centroid - Manual centroid recalculation
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models import Cuadrilla, OT
from app.schemas import (
    CuadrillaCreate,
    CuadrillaResponse,
    CuadrillaUpdate,
    CuadrillaWithOTs,
    CuadrillaType,
)
from app.utils.geo import calculate_centroid

router = APIRouter(prefix="/cuadrillas", tags=["cuadrillas"])


@router.get("/", response_model=list[CuadrillaResponse])
async def list_cuadrillas(
    type: Optional[CuadrillaType] = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[CuadrillaResponse]:
    """
    List all work crews with optional type filtering.
    
    Query Parameters:
        type: Filter by crew type (PRINCIPAL or RESERVA)
    
    Returns:
        List of CuadrillaResponse with assigned OT counts
    """
    query = select(Cuadrilla)
    
    if type:
        query = query.where(Cuadrilla.type == type)
    
    result = await session.execute(query)
    cuadrillas = result.scalars().all()
    
    return [CuadrillaResponse.from_orm(c) for c in cuadrillas]


@router.post("/", response_model=CuadrillaResponse, status_code=status.HTTP_201_CREATED)
async def create_cuadrilla(
    cuadrilla_data: CuadrillaCreate,
    session: AsyncSession = Depends(get_db_session),
) -> CuadrillaResponse:
    """
    Create a new work crew.
    
    Request Body:
        name: Unique crew name
        type: PRINCIPAL or RESERVA
        max_capacity: Maximum OT assignments (default: 10)
    
    Returns:
        Created CuadrillaResponse
    """
    # Check if crew with same name already exists
    existing = await session.execute(
        select(Cuadrilla).where(Cuadrilla.name == cuadrilla_data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Crew with name '{cuadrilla_data.name}' already exists",
        )
    
    # Create new crew
    new_cuadrilla = Cuadrilla(
        name=cuadrilla_data.name,
        type=cuadrilla_data.type,
        max_capacity=cuadrilla_data.max_capacity or 10,
    )
    
    session.add(new_cuadrilla)
    await session.commit()
    await session.refresh(new_cuadrilla)
    
    return CuadrillaResponse.from_orm(new_cuadrilla)


@router.get("/{cuadrilla_id}", response_model=CuadrillaResponse)
async def get_cuadrilla(
    cuadrilla_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> CuadrillaResponse:
    """
    Get crew details by ID.
    
    Path Parameters:
        cuadrilla_id: Crew database ID
    
    Returns:
        CuadrillaResponse with crew details and OT count
    """
    cuadrilla = await session.execute(
        select(Cuadrilla).where(Cuadrilla.id == cuadrilla_id)
    )
    crew = cuadrilla.scalar_one_or_none()
    
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew with ID {cuadrilla_id} not found",
        )
    
    return CuadrillaResponse.from_orm(crew)


@router.get("/{cuadrilla_id}/ots", response_model=CuadrillaWithOTs)
async def get_cuadrilla_ots(
    cuadrilla_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> CuadrillaWithOTs:
    """
    Get all OTs assigned to a crew.
    
    Path Parameters:
        cuadrilla_id: Crew database ID
    
    Returns:
        CuadrillaWithOTs including list of assigned OT responses
    """
    cuadrilla = await session.execute(
        select(Cuadrilla).where(Cuadrilla.id == cuadrilla_id)
    )
    crew = cuadrilla.scalar_one_or_none()
    
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew with ID {cuadrilla_id} not found",
        )
    
    # Get all OTs assigned to this crew
    ots = await session.execute(
        select(OT).where(OT.cuadrilla_id == cuadrilla_id)
    )
    assigned_ots = ots.scalars().all()
    
    return CuadrillaWithOTs(
        id=crew.id,
        name=crew.name,
        type=crew.type,
        max_capacity=crew.max_capacity,
        last_centroid_lat=crew.last_centroid_lat,
        last_centroid_long=crew.last_centroid_long,
        assigned_ots_count=len(assigned_ots),
        created_at=crew.created_at,
        updated_at=crew.updated_at,
        assigned_ots=assigned_ots,
    )


@router.patch("/{cuadrilla_id}", response_model=CuadrillaResponse)
async def update_cuadrilla(
    cuadrilla_id: int,
    cuadrilla_data: CuadrillaUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> CuadrillaResponse:
    """
    Update crew information.
    
    Path Parameters:
        cuadrilla_id: Crew database ID
    
    Request Body:
        name: (optional) New crew name
        type: (optional) New crew type
        max_capacity: (optional) New capacity
    
    Returns:
        Updated CuadrillaResponse
    """
    cuadrilla = await session.execute(
        select(Cuadrilla).where(Cuadrilla.id == cuadrilla_id)
    )
    crew = cuadrilla.scalar_one_or_none()
    
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew with ID {cuadrilla_id} not found",
        )
    
    # Update fields
    if cuadrilla_data.name:
        crew.name = cuadrilla_data.name
    if cuadrilla_data.type:
        crew.type = cuadrilla_data.type
    if cuadrilla_data.max_capacity:
        crew.max_capacity = cuadrilla_data.max_capacity
    
    await session.commit()
    await session.refresh(crew)
    
    return CuadrillaResponse.from_orm(crew)


@router.post("/{cuadrilla_id}/recalculate-centroid", status_code=status.HTTP_200_OK)
async def recalculate_centroid(
    cuadrilla_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Manually recalculate crew centroid from assigned OTs.
    
    This endpoint recalculates the geographic center of all OTs
    assigned to a crew, updating last_centroid_lat and last_centroid_long.
    
    Path Parameters:
        cuadrilla_id: Crew database ID
    
    Returns:
        Dict with new centroid coordinates and update status
    """
    cuadrilla = await session.execute(
        select(Cuadrilla).where(Cuadrilla.id == cuadrilla_id)
    )
    crew = cuadrilla.scalar_one_or_none()
    
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew with ID {cuadrilla_id} not found",
        )
    
    # Get all OTs assigned to crew with valid coordinates
    ots = await session.execute(
        select(OT).where(
            OT.cuadrilla_id == cuadrilla_id,
            OT.lat.isnot(None),
            OT.long.isnot(None),
        )
    )
    assigned_ots = ots.scalars().all()
    
    if not assigned_ots:
        return {
            "status": "no_ots",
            "message": "No OTs with valid coordinates assigned to crew",
            "centroid_lat": None,
            "centroid_lon": None,
        }
    
    # Calculate new centroid
    locations = [(ot.lat, ot.long) for ot in assigned_ots]
    new_centroid = calculate_centroid(locations)
    
    # Update crew centroid
    crew.last_centroid_lat = new_centroid[0]
    crew.last_centroid_lon = new_centroid[1]
    
    await session.commit()
    await session.refresh(crew)
    
    return {
        "status": "success",
        "message": f"Centroid recalculated from {len(assigned_ots)} OTs",
        "centroid_lat": crew.last_centroid_lat,
        "centroid_lon": crew.last_centroid_lon,
        "ot_count": len(assigned_ots),
    }


__all__ = ["router"]


