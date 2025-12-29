"""EHR routes."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from oncology_common.clients.rabbitmq import create_event_publisher
from event_contracts import EventType

from ehr_service.database import get_db
from ehr_service.services import EHRService
from ehr_service.models import EHRDocumentStatus
from ehr_service.tasks import extract_and_map_task, generate_explanation_task
from ehr_service.config import settings


router = APIRouter(tags=["EHR"])


# Pydantic schemas
class EHRIngestRequest(BaseModel):
    """Request to ingest EHR text."""
    ehr_text: str = Field(..., min_length=1, description="Raw EHR text")


class EHRIngestResponse(BaseModel):
    """Response from EHR ingest."""
    ehr_id: UUID
    case_id: UUID
    version: int
    status: str
    created_at: str


class EHRVersionResponse(BaseModel):
    """EHR version information."""
    ehr_id: UUID
    version: int
    status: str
    created_at: str
    entity_count: int = 0
    mapping_count: int = 0


class EHRVersionsResponse(BaseModel):
    """List of EHR versions."""
    data: list[EHRVersionResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class EHRDocumentResponse(BaseModel):
    """Full EHR document response."""
    ehr_id: UUID
    case_id: UUID
    version: int
    raw_text: str
    normalized_text: str | None
    status: str
    processing_metadata: dict
    created_by: str | None
    created_at: str
    updated_at: str | None


class ExtractAndMapResponse(BaseModel):
    """Response from extract and map operation."""
    ehr_id: UUID
    task_id: str
    status: str
    message: str


class EHREntityResponse(BaseModel):
    """EHR entity response."""
    entity_id: UUID
    entity_type: str
    text: str
    start_position: int | None
    end_position: int | None
    confidence: float
    section: str | None
    metadata: dict


class EHRMappingResponse(BaseModel):
    """EHR mapping response."""
    mapping_id: UUID
    entity_id: UUID
    ontology: str
    iri: str
    label: str
    confidence: float
    mapping_method: str
    evidence: dict


class GenerateExplanationRequest(BaseModel):
    """Request to generate explanation."""
    context: dict = Field(default_factory=dict, description="Additional context for explanation")


class GenerateExplanationResponse(BaseModel):
    """Response from generate explanation."""
    case_id: UUID
    task_id: str
    status: str
    message: str


def get_event_publisher():
    """Get event publisher."""
    return create_event_publisher(settings.rabbitmq_url, settings.service_name)


@router.post(
    "/cases/{case_id}/ehr:ingest",
    response_model=EHRIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_ehr(
    case_id: UUID,
    request_data: EHRIngestRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EHRIngestResponse:
    """Ingest EHR text for a case.

    Creates a new EHR document version with the provided text.
    """
    user_id = request.headers.get("X-User-Id")

    # Create EHR document
    ehr_service = EHRService(db)
    ehr_doc = await ehr_service.create_document(
        case_id=case_id,
        raw_text=request_data.ehr_text,
        created_by=user_id,
    )

    # Publish event
    try:
        publisher = get_event_publisher()
        publisher.publish(
            event_type=EventType.EHR_INGESTED,
            payload={
                "ehr_id": str(ehr_doc.ehr_id),
                "case_id": str(case_id),
                "version": ehr_doc.version,
                "created_by": user_id,
            },
            case_id=str(case_id),
        )
    except Exception:
        pass  # Don't fail if event publishing fails

    return EHRIngestResponse(
        ehr_id=ehr_doc.ehr_id,
        case_id=ehr_doc.case_id,
        version=ehr_doc.version,
        status=ehr_doc.status.value,
        created_at=ehr_doc.created_at.isoformat(),
    )


@router.get(
    "/cases/{case_id}/ehr/versions",
    response_model=EHRVersionsResponse,
)
async def list_ehr_versions(
    case_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> EHRVersionsResponse:
    """List EHR versions for a case."""
    ehr_service = EHRService(db)
    skip = (page - 1) * page_size
    documents, total = await ehr_service.list_by_case(
        case_id=case_id,
        skip=skip,
        limit=page_size,
    )

    return EHRVersionsResponse(
        data=[
            EHRVersionResponse(
                ehr_id=doc.ehr_id,
                version=doc.version,
                status=doc.status.value,
                created_at=doc.created_at.isoformat(),
                entity_count=len(doc.entities) if doc.entities else 0,
                mapping_count=len(doc.mappings) if doc.mappings else 0,
            )
            for doc in documents
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(skip + len(documents)) < total,
    )


@router.get(
    "/ehr/{ehr_id}",
    response_model=EHRDocumentResponse,
)
async def get_ehr_document(
    ehr_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EHRDocumentResponse:
    """Get EHR document by ID."""
    ehr_service = EHRService(db)
    ehr_doc = await ehr_service.get_by_id(ehr_id)

    if not ehr_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EHR document {ehr_id} not found",
        )

    return EHRDocumentResponse(
        ehr_id=ehr_doc.ehr_id,
        case_id=ehr_doc.case_id,
        version=ehr_doc.version,
        raw_text=ehr_doc.raw_text,
        normalized_text=ehr_doc.normalized_text,
        status=ehr_doc.status.value,
        processing_metadata=ehr_doc.processing_metadata,
        created_by=ehr_doc.created_by,
        created_at=ehr_doc.created_at.isoformat(),
        updated_at=ehr_doc.updated_at.isoformat() if ehr_doc.updated_at else None,
    )


@router.post(
    "/ehr/{ehr_id}:extract-and-map",
    response_model=ExtractAndMapResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def extract_and_map(
    ehr_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExtractAndMapResponse:
    """Extract entities and map to ontologies.

    This endpoint triggers async processing using Celery.
    """
    ehr_service = EHRService(db)
    ehr_doc = await ehr_service.get_by_id(ehr_id)

    if not ehr_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EHR document {ehr_id} not found",
        )

    # Update status and trigger task
    task = extract_and_map_task.delay(str(ehr_id))
    await ehr_service.update_status(
        ehr_id=ehr_id,
        status=EHRDocumentStatus.PROCESSING,
        task_id=task.id,
    )

    return ExtractAndMapResponse(
        ehr_id=ehr_id,
        task_id=task.id,
        status="processing",
        message="Entity extraction and mapping started",
    )


@router.get(
    "/ehr/{ehr_id}/entities",
    response_model=list[EHREntityResponse],
)
async def get_ehr_entities(
    ehr_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    entity_type: str | None = Query(None, description="Filter by entity type"),
) -> list[EHREntityResponse]:
    """Get extracted entities for an EHR document."""
    ehr_service = EHRService(db)
    entities = await ehr_service.get_entities(ehr_id=ehr_id, entity_type=entity_type)

    return [
        EHREntityResponse(
            entity_id=entity.entity_id,
            entity_type=entity.entity_type,
            text=entity.text,
            start_position=entity.start_position,
            end_position=entity.end_position,
            confidence=entity.confidence,
            section=entity.section,
            metadata=entity.metadata_,
        )
        for entity in entities
    ]


@router.get(
    "/ehr/{ehr_id}/mappings",
    response_model=list[EHRMappingResponse],
)
async def get_ehr_mappings(
    ehr_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    ontology: str | None = Query(None, description="Filter by ontology"),
) -> list[EHRMappingResponse]:
    """Get ontology mappings for an EHR document."""
    ehr_service = EHRService(db)
    mappings = await ehr_service.get_mappings(ehr_id=ehr_id, ontology=ontology)

    return [
        EHRMappingResponse(
            mapping_id=mapping.mapping_id,
            entity_id=mapping.entity_id,
            ontology=mapping.ontology,
            iri=mapping.iri,
            label=mapping.label,
            confidence=mapping.confidence,
            mapping_method=mapping.mapping_method,
            evidence=mapping.evidence,
        )
        for mapping in mappings
    ]


@router.post(
    "/cases/{case_id}:generate-explanation",
    response_model=GenerateExplanationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_explanation(
    case_id: UUID,
    request_data: GenerateExplanationRequest = Body(...),
) -> GenerateExplanationResponse:
    """Generate clinical explanation for a case.

    This endpoint triggers async processing using the ExplanationComposerGraph workflow.
    """
    # Trigger task
    task = generate_explanation_task.delay(str(case_id), request_data.context)

    return GenerateExplanationResponse(
        case_id=case_id,
        task_id=task.id,
        status="processing",
        message="Explanation generation started",
    )
