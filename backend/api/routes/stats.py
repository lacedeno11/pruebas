"""Statistics and dashboard API routes"""

import logging
import functools
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database.models import OT, Cuadrilla, Asignacion, Alerta
from backend.api.dependencies import get_db
from backend.utils.constants import OT_STATUS, PROJECT_TYPES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stats", tags=["stats"])

# Cache storage for dashboard statistics (TTL 15 minutes)
_cache = {
    "dashboard": None,
    "cache_time": None,
    "cache_ttl": 15 * 60,  # 15 minutes in seconds
}


def _is_cache_valid() -> bool:
    """Check if cache is still valid"""
    if _cache["dashboard"] is None or _cache["cache_time"] is None:
        return False

    elapsed = (datetime.now() - _cache["cache_time"]).total_seconds()
    return elapsed < _cache["cache_ttl"]


def _get_cached_dashboard() -> Optional[Dict[str, Any]]:
    """Get cached dashboard data if valid"""
    if _is_cache_valid():
        logger.debug("Returning cached dashboard statistics")
        return _cache["dashboard"]
    return None


def _set_cache(data: Dict[str, Any]) -> None:
    """Set cache with current timestamp"""
    _cache["dashboard"] = data
    _cache["cache_time"] = datetime.now()
    logger.debug("Updated dashboard statistics cache")


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Get comprehensive dashboard statistics.

    This endpoint returns aggregated statistics for the PEI platform dashboard including:
    - Total OT counts and distribution by status/project type
    - Cuadrilla workload and utilization metrics
    - Active alerts
    - Recent assignment operations
    - Distance to centroid averages

    Query Parameters:
    - use_cache (bool): Use cached results if available (default True)
      Set to False to force fresh calculation

    Returns:
    - total_ots (int): Total number of OTs in system
    - by_status (Dict[str, int]): OT distribution by status
    - by_project_type (Dict[str, int]): OT distribution by project type
    - cuadrillas_workload (List): Cuadrilla workload with metrics:
      - cuadrilla_id (int): Cuadrilla ID
      - name (str): Cuadrilla name
      - type (str): Principal or Reserva
      - workload (int): Number of currently assigned OTs
      - capacity (int): Maximum capacity
      - utilization_pct (float): Utilization percentage (0-100)
    - alerts_active (int): Number of unread/active alerts
    - recent_assignments (List): Last 10 assignment operations:
      - ot_id (int): Assigned OT ID
      - cuadrilla_id (int): Assigned cuadrilla ID
      - timestamp (str): Assignment timestamp
      - distance (float): Distance to centroid
    - avg_distance_to_centroid (float): Average distance metric
    - cache_info (Dict): Cache status information
      - cached (bool): Whether result was cached
      - cache_age_seconds (float): Age of cache if cached
      - cache_ttl_seconds (int): Cache TTL in seconds
    - timestamp (str): Current server timestamp

    Status Codes:
    - 200: Success
    - 500: Internal server error

    Example Response:
    ```json
    {
      "total_ots": 50,
      "by_status": {
        "PREPLANIFICADA": 10,
        "PLANIFICADA": 15,
        "ASIGNADO_TAREA": 12,
        "DETENIDA": 8,
        "ANULADA": 3,
        "FINALIZADA": 2
      },
      "by_project_type": {
        "PUBLICO": 20,
        "PRIVADO": 20,
        "TERCERIZADO": 10
      },
      "cuadrillas_workload": [
        {
          "cuadrilla_id": 1,
          "name": "Cuadrilla Norte 1",
          "type": "Principal",
          "workload": 5,
          "capacity": 10,
          "utilization_pct": 50.0
        }
      ],
      "alerts_active": 5,
      "recent_assignments": [
        {
          "ot_id": 1,
          "cuadrilla_id": 2,
          "timestamp": "2024-02-13T10:00:00",
          "distance": 3.5
        }
      ],
      "avg_distance_to_centroid": 4.2,
      "cache_info": {
        "cached": false,
        "cache_age_seconds": 0,
        "cache_ttl_seconds": 900
      },
      "timestamp": "2024-02-13T10:05:00"
    }
    ```
    """
    try:
        # Check cache if enabled
        if use_cache:
            cached_data = _get_cached_dashboard()
            if cached_data:
                # Add cache info
                cache_age = (datetime.now() - _cache["cache_time"]).total_seconds()
                cached_data["cache_info"]["cached"] = True
                cached_data["cache_info"]["cache_age_seconds"] = cache_age
                return cached_data

        logger.info("Calculating dashboard statistics")

        # Get total OT count
        total_ots = db.query(func.count(OT.id)).scalar() or 0

        # Get OT counts by status
        status_counts = (
            db.query(OT.status, func.count(OT.id))
            .group_by(OT.status)
            .all()
        )
        by_status = {status: count for status, count in status_counts}

        # Fill in missing statuses with 0
        for status in OT_STATUS.values():
            if status not in by_status:
                by_status[status] = 0

        logger.info(f"OT status distribution: {by_status}")

        # Get OT counts by project type
        project_counts = (
            db.query(OT.project_type, func.count(OT.id))
            .group_by(OT.project_type)
            .all()
        )
        by_project_type = {ptype: count for ptype, count in project_counts}

        # Fill in missing project types with 0
        for ptype in PROJECT_TYPES.values():
            if ptype not in by_project_type:
                by_project_type[ptype] = 0

        logger.info(f"OT project type distribution: {by_project_type}")

        # Get cuadrilla workload
        cuadrillas = db.query(Cuadrilla).all()
        cuadrillas_workload = []

        for cuadrilla in cuadrillas:
            # Count active assignments
            active_count = (
                db.query(func.count(Asignacion.id))
                .filter(
                    Asignacion.cuadrilla_id == cuadrilla.id,
                    Asignacion.is_active == True,
                )
                .scalar() or 0
            )

            utilization_pct = (
                (active_count / cuadrilla.capacity * 100)
                if cuadrilla.capacity > 0
                else 0
            )

            cuadrillas_workload.append(
                {
                    "cuadrilla_id": cuadrilla.id,
                    "name": cuadrilla.name,
                    "type": cuadrilla.type,
                    "workload": active_count,
                    "capacity": cuadrilla.capacity,
                    "utilization_pct": round(utilization_pct, 2),
                }
            )

        logger.info(f"Calculated workload for {len(cuadrillas_workload)} cuadrillas")

        # Get active alerts count
        alerts_active = (
            db.query(func.count(Alerta.id))
            .filter(Alerta.leido == False)
            .scalar() or 0
        )

        logger.info(f"Active alerts: {alerts_active}")

        # Get recent assignments
        recent_assignments = (
            db.query(
                Asignacion.ot_id,
                Asignacion.cuadrilla_id,
                Asignacion.assigned_at,
                Asignacion.distance_to_centroid,
            )
            .filter(Asignacion.is_active == True)
            .order_by(Asignacion.assigned_at.desc())
            .limit(10)
            .all()
        )

        recent_assignments_list = [
            {
                "ot_id": a.ot_id,
                "cuadrilla_id": a.cuadrilla_id,
                "timestamp": a.assigned_at.isoformat() if a.assigned_at else None,
                "distance": round(a.distance_to_centroid, 2) if a.distance_to_centroid else 0,
            }
            for a in recent_assignments
        ]

        logger.info(f"Retrieved {len(recent_assignments_list)} recent assignments")

        # Calculate average distance to centroid
        avg_distance = (
            db.query(func.avg(Asignacion.distance_to_centroid))
            .filter(Asignacion.is_active == True)
            .scalar() or 0.0
        )
        avg_distance = round(float(avg_distance), 2) if avg_distance else 0.0

        logger.info(f"Average distance to centroid: {avg_distance} km")

        # Compile response
        response = {
            "total_ots": total_ots,
            "by_status": by_status,
            "by_project_type": by_project_type,
            "cuadrillas_workload": sorted(
                cuadrillas_workload,
                key=lambda x: x["utilization_pct"],
                reverse=True,
            ),
            "alerts_active": alerts_active,
            "recent_assignments": recent_assignments_list,
            "avg_distance_to_centroid": avg_distance,
            "cache_info": {
                "cached": False,
                "cache_age_seconds": 0,
                "cache_ttl_seconds": _cache["cache_ttl"],
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Cache the result
        _set_cache(response)

        logger.info("Dashboard statistics calculated successfully")
        return response

    except Exception as e:
        logger.error(f"Error calculating dashboard statistics: {str(e)}")
        raise


@router.post("/cache/clear")
async def clear_cache() -> Dict[str, str]:
    """
    Manually clear the dashboard statistics cache.

    This endpoint allows administrators to force a refresh of cached statistics
    without waiting for the TTL to expire.

    Returns:
    - message: Confirmation message
    - timestamp: When cache was cleared

    Status Codes:
    - 200: Cache cleared
    """
    try:
        _cache["dashboard"] = None
        _cache["cache_time"] = None
        logger.info("Dashboard statistics cache cleared")

        return {
            "message": "Cache cleared successfully",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise


@router.get("/ots/by-status", response_model=Dict[str, int])
async def get_ots_by_status(db: Session = Depends(get_db)) -> Dict[str, int]:
    """
    Get OT counts grouped by status.

    Quick endpoint for status distribution without full dashboard data.

    Returns:
    - Dictionary with status -> count mapping

    Status Codes:
    - 200: Success
    """
    try:
        status_counts = (
            db.query(OT.status, func.count(OT.id))
            .group_by(OT.status)
            .all()
        )
        result = {status: count for status, count in status_counts}

        # Fill in missing statuses
        for status in OT_STATUS.values():
            if status not in result:
                result[status] = 0

        logger.info("Retrieved OT counts by status")
        return result

    except Exception as e:
        logger.error(f"Error getting OTs by status: {str(e)}")
        raise


@router.get("/ots/by-project-type", response_model=Dict[str, int])
async def get_ots_by_project_type(
    db: Session = Depends(get_db),
) -> Dict[str, int]:
    """
    Get OT counts grouped by project type.

    Quick endpoint for project type distribution without full dashboard data.

    Returns:
    - Dictionary with project_type -> count mapping

    Status Codes:
    - 200: Success
    """
    try:
        project_counts = (
            db.query(OT.project_type, func.count(OT.id))
            .group_by(OT.project_type)
            .all()
        )
        result = {ptype: count for ptype, count in project_counts}

        # Fill in missing project types
        for ptype in PROJECT_TYPES.values():
            if ptype not in result:
                result[ptype] = 0

        logger.info("Retrieved OT counts by project type")
        return result

    except Exception as e:
        logger.error(f"Error getting OTs by project type: {str(e)}")
        raise


@router.get("/cuadrillas/workload", response_model=List[Dict[str, Any]])
async def get_cuadrillas_workload(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Get workload statistics for all cuadrillas.

    Returns list of cuadrillas sorted by utilization (highest first).

    Returns:
    - List of objects with:
      - cuadrilla_id (int)
      - name (str)
      - type (str)
      - workload (int)
      - capacity (int)
      - utilization_pct (float)

    Status Codes:
    - 200: Success
    """
    try:
        cuadrillas = db.query(Cuadrilla).all()
        result = []

        for cuadrilla in cuadrillas:
            active_count = (
                db.query(func.count(Asignacion.id))
                .filter(
                    Asignacion.cuadrilla_id == cuadrilla.id,
                    Asignacion.is_active == True,
                )
                .scalar() or 0
            )

            utilization_pct = (
                (active_count / cuadrilla.capacity * 100)
                if cuadrilla.capacity > 0
                else 0
            )

            result.append(
                {
                    "cuadrilla_id": cuadrilla.id,
                    "name": cuadrilla.name,
                    "type": cuadrilla.type,
                    "workload": active_count,
                    "capacity": cuadrilla.capacity,
                    "utilization_pct": round(utilization_pct, 2),
                }
            )

        # Sort by utilization descending
        result.sort(key=lambda x: x["utilization_pct"], reverse=True)

        logger.info(f"Retrieved workload for {len(result)} cuadrillas")
        return result

    except Exception as e:
        logger.error(f"Error getting cuadrillas workload: {str(e)}")
        raise


@router.get("/alerts/active", response_model=int)
async def get_active_alerts_count(db: Session = Depends(get_db)) -> int:
    """
    Get count of active (unread) alerts.

    Returns:
    - Integer count of active alerts

    Status Codes:
    - 200: Success
    """
    try:
        count = (
            db.query(func.count(Alerta.id))
            .filter(Alerta.leido == False)
            .scalar() or 0
        )

        logger.info(f"Retrieved active alerts count: {count}")
        return count

    except Exception as e:
        logger.error(f"Error getting active alerts count: {str(e)}")
        raise

