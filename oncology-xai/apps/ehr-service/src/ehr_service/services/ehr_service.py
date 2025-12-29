"""EHR service for database operations."""

from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ehr_service.models import EHRDocument, EHRDocumentStatus, EHREntity, EHRMapping


class EHRService:
    """Service for EHR document operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_document(
        self,
        case_id: UUID,
        raw_text: str,
        created_by: str | None = None,
    ) -> EHRDocument:
        """Create a new EHR document."""
        # Get version number (increment from existing documents for this case)
        result = await self.db.execute(
            select(func.max(EHRDocument.version))
            .where(EHRDocument.case_id == case_id)
        )
        max_version = result.scalar()
        version = (max_version or 0) + 1

        document = EHRDocument(
            case_id=case_id,
            version=version,
            raw_text=raw_text,
            created_by=created_by,
            status=EHRDocumentStatus.INGESTED,
        )
        self.db.add(document)
        await self.db.flush()
        return document

    async def get_by_id(self, ehr_id: UUID) -> EHRDocument | None:
        """Get EHR document by ID."""
        result = await self.db.execute(
            select(EHRDocument).where(EHRDocument.ehr_id == ehr_id)
        )
        return result.scalar_one_or_none()

    async def list_by_case(
        self,
        case_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[EHRDocument], int]:
        """List EHR documents for a case."""
        stmt = select(EHRDocument).where(EHRDocument.case_id == case_id)

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(EHRDocument)
            .where(EHRDocument.case_id == case_id)
        )
        total = count_result.scalar() or 0

        # Get paginated results
        stmt = stmt.offset(skip).limit(limit).order_by(EHRDocument.version.desc())
        result = await self.db.execute(stmt)

        return list(result.scalars().all()), total

    async def update_status(
        self,
        ehr_id: UUID,
        status: EHRDocumentStatus,
        task_id: str | None = None,
    ) -> EHRDocument | None:
        """Update EHR document status."""
        document = await self.get_by_id(ehr_id)
        if not document:
            return None

        document.status = status
        if task_id is not None:
            document.task_id = task_id

        await self.db.flush()
        return document

    async def get_entities(
        self,
        ehr_id: UUID,
        entity_type: str | None = None,
    ) -> list[EHREntity]:
        """Get entities for an EHR document."""
        stmt = select(EHREntity).where(EHREntity.ehr_id == ehr_id)

        if entity_type:
            stmt = stmt.where(EHREntity.entity_type == entity_type)

        stmt = stmt.order_by(EHREntity.start_position)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_mappings(
        self,
        ehr_id: UUID,
        ontology: str | None = None,
    ) -> list[EHRMapping]:
        """Get ontology mappings for an EHR document."""
        stmt = select(EHRMapping).where(EHRMapping.ehr_id == ehr_id)

        if ontology:
            stmt = stmt.where(EHRMapping.ontology == ontology)

        stmt = stmt.order_by(EHRMapping.confidence.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, ehr_id: UUID) -> bool:
        """Delete an EHR document."""
        document = await self.get_by_id(ehr_id)
        if not document:
            return False

        await self.db.delete(document)
        await self.db.flush()
        return True
