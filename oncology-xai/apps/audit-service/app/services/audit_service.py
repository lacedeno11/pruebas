"""Audit Service for managing audit events."""
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent
from app.schemas.audit_event import AuditEventCreate, AuditEventFilter
from app.core.logger import logger


class AuditService:
    """Service for managing audit events."""

    @staticmethod
    async def create_audit_event(
        db: AsyncSession,
        event_data: AuditEventCreate
    ) -> AuditEvent:
        """
        Create a new audit event.

        Args:
            db: Database session
            event_data: Audit event data

        Returns:
            Created audit event
        """
        try:
            audit_event = AuditEvent(**event_data.model_dump(exclude_none=False))
            db.add(audit_event)
            await db.commit()
            await db.refresh(audit_event)
            logger.info(
                f"Audit event created: {audit_event.event_id}",
                extra={
                    "event_id": audit_event.event_id,
                    "action": audit_event.action,
                    "entity_type": audit_event.entity_type
                }
            )
            return audit_event
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating audit event: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def get_audit_event(
        db: AsyncSession,
        event_id: str
    ) -> Optional[AuditEvent]:
        """
        Get a specific audit event by ID.

        Args:
            db: Database session
            event_id: Event ID

        Returns:
            Audit event or None if not found
        """
        try:
            result = await db.execute(
                select(AuditEvent).where(AuditEvent.event_id == event_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting audit event {event_id}: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def list_audit_events(
        db: AsyncSession,
        filters: AuditEventFilter
    ) -> Tuple[List[AuditEvent], int]:
        """
        List audit events with filters and pagination.

        Args:
            db: Database session
            filters: Filter criteria

        Returns:
            Tuple of (list of events, total count)
        """
        try:
            # Build query conditions
            conditions = []

            if filters.case_id:
                conditions.append(AuditEvent.case_id == filters.case_id)

            if filters.user_id:
                conditions.append(AuditEvent.user_id == filters.user_id)

            if filters.entity_type:
                conditions.append(AuditEvent.entity_type == filters.entity_type)

            if filters.action:
                conditions.append(AuditEvent.action == filters.action)

            if filters.status:
                conditions.append(AuditEvent.status == filters.status)

            if filters.correlation_id:
                conditions.append(AuditEvent.correlation_id == filters.correlation_id)

            if filters.from_date:
                conditions.append(AuditEvent.timestamp >= filters.from_date)

            if filters.to_date:
                conditions.append(AuditEvent.timestamp <= filters.to_date)

            # Build base query
            query = select(AuditEvent)
            if conditions:
                query = query.where(and_(*conditions))

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar_one()

            # Add ordering and pagination
            query = query.order_by(AuditEvent.timestamp.desc())
            offset = (filters.page - 1) * filters.page_size
            query = query.offset(offset).limit(filters.page_size)

            # Execute query
            result = await db.execute(query)
            events = list(result.scalars().all())

            logger.info(
                f"Retrieved {len(events)} audit events (total: {total})",
                extra={
                    "total": total,
                    "page": filters.page,
                    "page_size": filters.page_size
                }
            )

            return events, total

        except Exception as e:
            logger.error(f"Error listing audit events: {str(e)}", exc_info=True)
            raise
