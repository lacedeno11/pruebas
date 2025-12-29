"""Patient service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from case_service.models.patient import Patient


class PatientService:
    """Service for patient operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        external_id: str | None = None,
        demographics: dict | None = None,
    ) -> Patient:
        """Create a new patient."""
        patient = Patient(
            external_id=external_id,
            demographics=demographics or {},
        )
        self.db.add(patient)
        await self.db.flush()
        return patient

    async def get_by_id(self, patient_id: UUID) -> Patient | None:
        """Get patient by ID."""
        result = await self.db.execute(
            select(Patient).where(Patient.patient_id == patient_id)
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(self, external_id: str) -> Patient | None:
        """Get patient by external ID."""
        result = await self.db.execute(
            select(Patient).where(Patient.external_id == external_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        query: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Patient], int]:
        """List patients with optional search."""
        stmt = select(Patient)

        if query:
            stmt = stmt.where(
                Patient.external_id.ilike(f"%{query}%")
            )

        # Count total
        count_stmt = select(Patient.patient_id)
        if query:
            count_stmt = count_stmt.where(Patient.external_id.ilike(f"%{query}%"))
        count_result = await self.db.execute(count_stmt)
        total = len(count_result.all())

        # Get paginated results
        stmt = stmt.offset(skip).limit(limit).order_by(Patient.created_at.desc())
        result = await self.db.execute(stmt)

        return list(result.scalars().all()), total
