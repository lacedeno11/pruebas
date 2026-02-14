"""
Governance API routes.
Handles system governance, alerts, and automated decision-making.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db
from backend.api.schemas import AlertResponse, ValidateReasonRequest, ValidateReasonResponse

router = APIRouter(prefix="/governance", tags=["Governance"])


@router.post("/check-inactive")
async def check_inactive_ots(
    db: AsyncSession = Depends(get_db),
):
    """
    Check for inactive OTs and trigger GobernanzaAgent.

    Args:
        db: Database session

    Returns:
        Result of inactivity check
    """
    # TODO: Implement GobernanzaAgent.check_inactive_ots() call
    return {
        "detenida_alerts": 0,
        "preplanificada_alerts": 0,
        "auto_cancelled": 0,
    }


@router.post("/check-preplanificada-timeout")
async def check_preplanificada_timeout(
    db: AsyncSession = Depends(get_db),
):
    """
    Check for PREPLANIFICADA OTs exceeding 48-hour timeout.

    Args:
        db: Database session

    Returns:
        Result of timeout check
    """
    # TODO: Implement 48-hour timeout logic
    return {
        "timeout_ots": 0,
        "alerts_sent": 0,
    }


@router.get("/alerts", response_model=List[AlertResponse])
async def get_governance_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    resolved: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> List[AlertResponse]:
    """
    Get recent governance alerts and actions taken.

    Args:
        skip: Number of records to skip
        limit: Number of records to return
        resolved: Filter by resolved status
        db: Database session

    Returns:
        List of alerts
    """
    # TODO: Implement alert retrieval from LogAgente
    return []


@router.post("/validate-reason", response_model=ValidateReasonResponse)
async def validate_stop_reason(
    request: ValidateReasonRequest,
    db: AsyncSession = Depends(get_db),
) -> ValidateReasonResponse:
    """
    Validate OT stop reason using GobernanzaAgent.
    Used for drag & drop UI validation.

    Args:
        request: Reason to validate
        db: Database session

    Returns:
        Validation result with confidence score
    """
    # TODO: Implement GobernanzaAgent.validate_stop_reason() call
    return ValidateReasonResponse(
        valid=False,
        message="Reason validation not implemented",
        confidence=0.0,
    )

