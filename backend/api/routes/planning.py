"""
Planning API routes.
Handles automated OT-to-crew assignment and planning statistics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db
from backend.api.schemas import PlanningStatsResponse

router = APIRouter(prefix="/planning", tags=["Planning"])


@router.post("/auto-plan")
async def trigger_auto_planning(
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger automatic planning for all PREPLANIFICADA OTs.
    Uses PlanificacionAgent with 3-phase algorithm.

    Args:
        db: Database session

    Returns:
        Planning result summary
    """
    # TODO: Implement PlanificacionAgent.plan_ots() call
    return {
        "total_planned": 0,
        "successful_assignments": 0,
        "failed_assignments": 0,
        "phase_1_balance": {"assigned": 0, "skipped": 0},
        "phase_2_proximity": {"assigned": 0, "out_of_range": 0},
        "phase_3_normalization": {"scheduled": True},
    }


@router.post("/normalize")
async def trigger_night_normalization(
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger night normalization (route recalculation at 00:00).

    Args:
        db: Database session

    Returns:
        Normalization result
    """
    # TODO: Implement night normalization logic
    return {
        "status": "scheduled",
        "scheduled_time": "2024-02-14 00:00:00",
    }


@router.get("/stats", response_model=PlanningStatsResponse)
async def get_planning_stats(
    db: AsyncSession = Depends(get_db),
) -> PlanningStatsResponse:
    """
    Get planning statistics.

    Args:
        db: Database session

    Returns:
        Planning statistics with OT distribution and crew utilization
    """
    # TODO: Implement statistics calculation
    return PlanningStatsResponse(
        ots_by_status={},
        ots_by_project_type={},
        crew_utilization={},
        average_assignment_distance_km=0.0,
    )

