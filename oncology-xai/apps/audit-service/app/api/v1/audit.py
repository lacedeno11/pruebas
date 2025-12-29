"""Audit API endpoints."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.audit_event import (
    AuditEventResponse,
    AuditEventListResponse,
    AuditEventFilter
)
from app.services.audit_service import AuditService
from app.core.logger import logger
import math

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "/events",
    response_model=AuditEventListResponse,
    summary="List audit events",
    description="Retrieve a paginated list of audit events with optional filters"
)
async def list_audit_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    case_id: Annotated[str | None, Query(description="Filter by case ID")] = None,
    user_id: Annotated[str | None, Query(description="Filter by user ID")] = None,
    entity_type: Annotated[str | None, Query(description="Filter by entity type")] = None,
    action: Annotated[str | None, Query(description="Filter by action")] = None,
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    from_date: Annotated[str | None, Query(alias="from", description="Filter from this date (ISO 8601)")] = None,
    to_date: Annotated[str | None, Query(alias="to", description="Filter to this date (ISO 8601)")] = None,
    correlation_id: Annotated[str | None, Query(description="Filter by correlation ID")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=1000, description="Number of items per page")] = 50,
) -> AuditEventListResponse:
    """
    List audit events with filters and pagination.

    Args:
        db: Database session
        case_id: Filter by case ID
        user_id: Filter by user ID
        entity_type: Filter by entity type
        action: Filter by action
        status: Filter by status
        from_date: Filter from this date
        to_date: Filter to this date
        correlation_id: Filter by correlation ID
        page: Page number
        page_size: Number of items per page

    Returns:
        Paginated list of audit events
    """
    try:
        # Create filter object
        filters = AuditEventFilter(
            case_id=case_id,
            user_id=user_id,
            entity_type=entity_type,
            action=action,
            status=status,
            correlation_id=correlation_id,
            page=page,
            page_size=page_size
        )

        # Parse date filters if provided
        if from_date:
            from datetime import datetime
            filters.from_date = datetime.fromisoformat(from_date.replace('Z', '+00:00'))

        if to_date:
            from datetime import datetime
            filters.to_date = datetime.fromisoformat(to_date.replace('Z', '+00:00'))

        # Get events and total count
        events, total = await AuditService.list_audit_events(db, filters)

        # Calculate total pages
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return AuditEventListResponse(
            events=[AuditEventResponse.model_validate(event) for event in events],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except ValueError as e:
        logger.error(f"Invalid date format: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Error listing audit events: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/events/{event_id}",
    response_model=AuditEventResponse,
    summary="Get audit event",
    description="Retrieve a specific audit event by ID"
)
async def get_audit_event(
    event_id: str,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> AuditEventResponse:
    """
    Get a specific audit event by ID.

    Args:
        event_id: Event ID
        db: Database session

    Returns:
        Audit event details

    Raises:
        HTTPException: If event not found
    """
    try:
        event = await AuditService.get_audit_event(db, event_id)

        if not event:
            raise HTTPException(status_code=404, detail="Audit event not found")

        return AuditEventResponse.model_validate(event)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit event {event_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
