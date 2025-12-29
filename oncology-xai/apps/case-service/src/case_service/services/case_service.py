"""Case service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from case_service.models.case import Case, CaseStatus


class CaseService:
    """Service for case operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        patient_id: UUID,
        tags: list[str] | None = None,
        metadata: dict | None = None,
        created_by: str | None = None,
    ) -> Case:
        """Create a new case."""
        case = Case(
            patient_id=patient_id,
            tags=tags or [],
            metadata_=metadata or {},
            created_by=created_by,
        )
        self.db.add(case)
        await self.db.flush()
        return case

    async def get_by_id(self, case_id: UUID) -> Case | None:
        """Get case by ID."""
        result = await self.db.execute(
            select(Case).where(Case.case_id == case_id)
        )
        return result.scalar_one_or_none()

    async def list_by_patient(
        self,
        patient_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Case], int]:
        """List cases for a patient."""
        stmt = select(Case).where(Case.patient_id == patient_id)

        # Count total
        count_result = await self.db.execute(
            select(Case.case_id).where(Case.patient_id == patient_id)
        )
        total = len(count_result.all())

        # Get paginated results
        stmt = stmt.offset(skip).limit(limit).order_by(Case.created_at.desc())
        result = await self.db.execute(stmt)

        return list(result.scalars().all()), total

    async def update(
        self,
        case_id: UUID,
        status: CaseStatus | None = None,
        tags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> Case | None:
        """Update a case."""
        case = await self.get_by_id(case_id)
        if not case:
            return None

        if status is not None:
            case.status = status
        if tags is not None:
            case.tags = tags
        if metadata is not None:
            case.metadata_ = metadata

        await self.db.flush()
        return case
