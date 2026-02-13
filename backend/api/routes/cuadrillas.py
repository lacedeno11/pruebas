"""
Cuadrilla (Work Crew) API routes.
Handles crew management and capacity tracking.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db
from backend.api.schemas import CuadrillaResponse
from backend.models import Cuadrilla

router = APIRouter(prefix="/cuadrillas", tags=["Cuadrillas"])


@router.get("", response_model=List[CuadrillaResponse])
async def get_cuadrillas(
    activa: Optional[bool] = Query(None, description="Filter by active status"),
    tipo: Optional[str] = Query(None, description="Filter by type (PRINCIPAL/RESERVA)"),
    db: AsyncSession = Depends(get_db),
) -> List[CuadrillaResponse]:
    """
    Get list of crews with current assignments and centroid.

    Args:
        activa: Filter by active status
        tipo: Filter by crew type
        db: Database session

    Returns:
        List of crew details with capacity info
    """
    # TODO: Implement database query with assignments count
    return []


@router.get("/{cuadrilla_id}", response_model=CuadrillaResponse)
async def get_cuadrilla(
    cuadrilla_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CuadrillaResponse:
    """
    Get crew details with assigned OTs and capacity stats.

    Args:
        cuadrilla_id: Crew ID
        db: Database session

    Returns:
        Crew details with assignment and capacity information
    """
    # TODO: Implement database query with assignment stats
    raise HTTPException(status_code=404, detail="Crew not found")


@router.post("", response_model=CuadrillaResponse)
async def create_cuadrilla(
    cuadrilla: CuadrillaResponse,
    db: AsyncSession = Depends(get_db),
) -> CuadrillaResponse:
    """
    Create new crew.

    Args:
        cuadrilla: Crew data
        db: Database session

    Returns:
        Created crew
    """
    # TODO: Implement crew creation
    raise HTTPException(status_code=400, detail="Failed to create crew")


@router.patch("/{cuadrilla_id}", response_model=CuadrillaResponse)
async def update_cuadrilla(
    cuadrilla_id: UUID,
    updates: dict,
    db: AsyncSession = Depends(get_db),
) -> CuadrillaResponse:
    """
    Update crew (nombre, tipo, capacidad_diaria, activa).

    Args:
        cuadrilla_id: Crew ID
        updates: Fields to update
        db: Database session

    Returns:
        Updated crew
    """
    # TODO: Implement crew update
    raise HTTPException(status_code=404, detail="Crew not found")

