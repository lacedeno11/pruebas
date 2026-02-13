"""Cuadrilla (Work Teams) API routes"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database.models import Cuadrilla, OT, Asignacion
from backend.models.cuadrilla import CuadrillaCreate, CuadrillaInDB, CuadrillaWithWorkload
from backend.models.ot import OTInDB
from backend.api.dependencies import get_db
from backend.utils.geo import calculate_centroid
from backend.utils.constants import OT_STATUS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cuadrillas", tags=["cuadrillas"])


@router.get("", response_model=List[CuadrillaWithWorkload])
async def list_cuadrillas(
    db: Session = Depends(get_db),
):
    """
    Get list of all cuadrillas with workload information.

    Returns:
    - List of CuadrillaWithWorkload objects including:
      - Cuadrilla details (id, name, type, capacity, centroid, active)
      - current_workload: Count of currently assigned active OTs
      - assigned_ots: List of assigned OT objects
    """
    try:
        cuadrillas = db.query(Cuadrilla).order_by(Cuadrilla.created_at.desc()).all()

        result = []
        for cuadrilla in cuadrillas:
            # Get active assignments for this cuadrilla
            active_assignments = (
                db.query(Asignacion)
                .filter(
                    Asignacion.cuadrilla_id == cuadrilla.id,
                    Asignacion.is_active == True,
                )
                .all()
            )

            # Get OTs for these assignments
            ot_ids = [a.ot_id for a in active_assignments]
            assigned_ots = []
            if ot_ids:
                assigned_ots = db.query(OT).filter(OT.id.in_(ot_ids)).all()

            current_workload = len(assigned_ots)

            # Create CuadrillaWithWorkload object
            cuadrilla_data = CuadrillaInDB.from_orm(cuadrilla)
            cuadrilla_with_workload = CuadrillaWithWorkload(
                **cuadrilla_data.dict(),
                current_workload=current_workload,
                assigned_ots=[OTInDB.from_orm(ot) for ot in assigned_ots],
            )
            result.append(cuadrilla_with_workload)

        logger.info(f"Retrieved {len(result)} cuadrillas with workload")
        return result
    except Exception as e:
        logger.error(f"Error retrieving cuadrillas: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{cuadrilla_id}/ots", response_model=List[OTInDB])
async def get_cuadrilla_ots(
    cuadrilla_id: int,
    db: Session = Depends(get_db),
):
    """
    Get list of OTs assigned to a specific cuadrilla.

    Parameters:
    - cuadrilla_id: The cuadrilla database ID

    Returns:
    - List of OT objects assigned to the cuadrilla via active asignaciones

    Raises:
    - 404: Cuadrilla not found
    """
    try:
        # Verify cuadrilla exists
        cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
        if not cuadrilla:
            logger.warning(f"Cuadrilla {cuadrilla_id} not found")
            raise HTTPException(status_code=404, detail="Cuadrilla not found")

        # Get active assignments
        active_assignments = (
            db.query(Asignacion)
            .filter(
                Asignacion.cuadrilla_id == cuadrilla_id,
                Asignacion.is_active == True,
            )
            .all()
        )

        # Get OTs for these assignments
        ot_ids = [a.ot_id for a in active_assignments]
        ots = []
        if ot_ids:
            ots = db.query(OT).filter(OT.id.in_(ot_ids)).order_by(OT.created_at.desc()).all()

        logger.info(f"Retrieved {len(ots)} OTs for cuadrilla {cuadrilla_id}")
        return [OTInDB.from_orm(ot) for ot in ots]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving OTs for cuadrilla {cuadrilla_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{cuadrilla_id}/centroid", response_model=CuadrillaInDB)
async def update_cuadrilla_centroid(
    cuadrilla_id: int,
    db: Session = Depends(get_db),
):
    """
    Manually trigger centroid recalculation for a cuadrilla.

    This endpoint recalculates the geographic centroid based on all currently
    assigned OTs and updates the cuadrilla's last_centroid_lat and last_centroid_long.

    Parameters:
    - cuadrilla_id: The cuadrilla database ID

    Returns:
    - Updated CuadrillaInDB object with new centroid coordinates

    Raises:
    - 404: Cuadrilla not found
    """
    try:
        # Get cuadrilla
        cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
        if not cuadrilla:
            logger.warning(f"Cuadrilla {cuadrilla_id} not found for centroid update")
            raise HTTPException(status_code=404, detail="Cuadrilla not found")

        # Get all active assignments for this cuadrilla
        active_assignments = (
            db.query(Asignacion)
            .filter(
                Asignacion.cuadrilla_id == cuadrilla_id,
                Asignacion.is_active == True,
            )
            .all()
        )

        # Get OTs for these assignments
        ot_ids = [a.ot_id for a in active_assignments]
        ots = []
        if ot_ids:
            ots = db.query(OT).filter(OT.id.in_(ot_ids)).all()

        # Calculate centroid from OT coordinates
        coordinates = []
        for ot in ots:
            if ot.lat is not None and ot.long is not None:
                coordinates.append((ot.lat, ot.long))

        if coordinates:
            centroid_lat, centroid_long = calculate_centroid(coordinates)
            cuadrilla.last_centroid_lat = centroid_lat
            cuadrilla.last_centroid_long = centroid_long
            logger.info(
                f"Calculated centroid for cuadrilla {cuadrilla_id}: "
                f"({centroid_lat}, {centroid_long}) from {len(coordinates)} OTs"
            )
        else:
            # No valid coordinates, set centroid to (0, 0)
            cuadrilla.last_centroid_lat = 0.0
            cuadrilla.last_centroid_long = 0.0
            logger.info(
                f"No valid OT coordinates for cuadrilla {cuadrilla_id}, "
                f"setting centroid to (0, 0)"
            )

        db.commit()
        db.refresh(cuadrilla)

        logger.info(f"Updated centroid for cuadrilla {cuadrilla_id}")
        return CuadrillaInDB.from_orm(cuadrilla)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating centroid for cuadrilla {cuadrilla_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("", response_model=CuadrillaInDB, status_code=201)
async def create_cuadrilla(
    cuadrilla_data: CuadrillaCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new cuadrilla (admin only).

    Request Body:
    - name: Cuadrilla name
    - type: Type (Principal or Reserva)
    - capacity: Maximum OT capacity (optional, default 10)
    - last_centroid_lat: Initial centroid latitude (optional)
    - last_centroid_long: Initial centroid longitude (optional)
    - active: Active status (optional, default True)

    Returns:
    - Created CuadrillaInDB object

    Raises:
    - 400: Invalid data (e.g., invalid type)
    """
    try:
        # Create new cuadrilla
        new_cuadrilla = Cuadrilla(
            name=cuadrilla_data.name,
            type=cuadrilla_data.type,
            capacity=cuadrilla_data.capacity or 10,
            last_centroid_lat=cuadrilla_data.last_centroid_lat,
            last_centroid_long=cuadrilla_data.last_centroid_long,
            active=cuadrilla_data.active if cuadrilla_data.active is not None else True,
            created_at=datetime.now(),
        )

        db.add(new_cuadrilla)
        db.commit()
        db.refresh(new_cuadrilla)

        logger.info(f"Created new cuadrilla {new_cuadrilla.id} with name {cuadrilla_data.name}")
        return CuadrillaInDB.from_orm(new_cuadrilla)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating cuadrilla: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{cuadrilla_id}", response_model=CuadrillaWithWorkload)
async def get_cuadrilla(
    cuadrilla_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a single cuadrilla with workload information by ID.

    Parameters:
    - cuadrilla_id: The cuadrilla database ID

    Returns:
    - CuadrillaWithWorkload object with current workload and assigned OTs

    Raises:
    - 404: Cuadrilla not found
    """
    try:
        cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
        if not cuadrilla:
            logger.warning(f"Cuadrilla {cuadrilla_id} not found")
            raise HTTPException(status_code=404, detail="Cuadrilla not found")

        # Get active assignments for this cuadrilla
        active_assignments = (
            db.query(Asignacion)
            .filter(
                Asignacion.cuadrilla_id == cuadrilla_id,
                Asignacion.is_active == True,
            )
            .all()
        )

        # Get OTs for these assignments
        ot_ids = [a.ot_id for a in active_assignments]
        assigned_ots = []
        if ot_ids:
            assigned_ots = db.query(OT).filter(OT.id.in_(ot_ids)).all()

        current_workload = len(assigned_ots)

        # Create CuadrillaWithWorkload object
        cuadrilla_data = CuadrillaInDB.from_orm(cuadrilla)
        cuadrilla_with_workload = CuadrillaWithWorkload(
            **cuadrilla_data.dict(),
            current_workload=current_workload,
            assigned_ots=[OTInDB.from_orm(ot) for ot in assigned_ots],
        )

        logger.info(f"Retrieved cuadrilla {cuadrilla_id} with workload {current_workload}")
        return cuadrilla_with_workload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving cuadrilla {cuadrilla_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

