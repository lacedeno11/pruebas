"""Case routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request

from sqlalchemy.ext.asyncio import AsyncSession

from oncology_common.models import Case as CaseSchema, CaseCreate, CaseUpdate, CaseStatus, PaginatedResponse
from oncology_common.clients.rabbitmq import create_event_publisher
from event_contracts import EventType

from case_service.database import get_db
from case_service.services.case_service import CaseService
from case_service.services.patient_service import PatientService
from case_service.config import settings


router = APIRouter(prefix="/cases", tags=["Cases"])


def get_event_publisher():
    """Get event publisher."""
    return create_event_publisher(settings.rabbitmq_url, settings.service_name)


@router.post("", response_model=CaseSchema, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CaseSchema:
    """Create a new case."""
    # Verify patient exists
    patient_service = PatientService(db)
    patient = await patient_service.get_by_id(case_data.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {case_data.patient_id} not found",
        )

    # Get user ID from headers (set by API gateway)
    user_id = request.headers.get("X-User-Id")

    # Create case
    case_service = CaseService(db)
    case = await case_service.create(
        patient_id=case_data.patient_id,
        tags=case_data.tags,
        metadata=case_data.metadata,
        created_by=user_id,
    )

    # Publish event
    try:
        publisher = get_event_publisher()
        publisher.publish(
            event_type=EventType.CASE_CREATED,
            payload={
                "case_id": str(case.case_id),
                "patient_id": str(case.patient_id),
                "created_by": user_id,
            },
            case_id=str(case.case_id),
        )
    except Exception:
        pass  # Don't fail if event publishing fails

    return CaseSchema(
        case_id=case.case_id,
        patient_id=case.patient_id,
        status=CaseStatus(case.status.value),
        tags=case.tags,
        metadata=case.metadata_,
        created_by=case.created_by,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.get("", response_model=PaginatedResponse[CaseSchema])
async def list_cases(
    db: Annotated[AsyncSession, Depends(get_db)],
    patient_id: UUID = Query(..., description="Patient ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[CaseSchema]:
    """List cases for a patient."""
    case_service = CaseService(db)
    skip = (page - 1) * page_size
    cases, total = await case_service.list_by_patient(
        patient_id=patient_id,
        skip=skip,
        limit=page_size,
    )

    return PaginatedResponse(
        data=[
            CaseSchema(
                case_id=c.case_id,
                patient_id=c.patient_id,
                status=CaseStatus(c.status.value),
                tags=c.tags,
                metadata=c.metadata_,
                created_by=c.created_by,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in cases
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(skip + len(cases)) < total,
    )


@router.get("/{case_id}", response_model=CaseSchema)
async def get_case(
    case_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CaseSchema:
    """Get case by ID."""
    case_service = CaseService(db)
    case = await case_service.get_by_id(case_id)

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )

    return CaseSchema(
        case_id=case.case_id,
        patient_id=case.patient_id,
        status=CaseStatus(case.status.value),
        tags=case.tags,
        metadata=case.metadata_,
        created_by=case.created_by,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.patch("/{case_id}", response_model=CaseSchema)
async def update_case(
    case_id: UUID,
    case_update: CaseUpdate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CaseSchema:
    """Update a case."""
    case_service = CaseService(db)

    from case_service.models.case import CaseStatus as DBCaseStatus

    db_status = None
    if case_update.status:
        db_status = DBCaseStatus(case_update.status.value)

    case = await case_service.update(
        case_id=case_id,
        status=db_status,
        tags=case_update.tags,
        metadata=case_update.metadata,
    )

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )

    # Publish event
    try:
        user_id = request.headers.get("X-User-Id")
        publisher = get_event_publisher()
        publisher.publish(
            event_type=EventType.CASE_UPDATED,
            payload={
                "case_id": str(case.case_id),
                "status": case.status.value,
                "updated_by": user_id,
            },
            case_id=str(case.case_id),
        )
    except Exception:
        pass

    return CaseSchema(
        case_id=case.case_id,
        patient_id=case.patient_id,
        status=CaseStatus(case.status.value),
        tags=case.tags,
        metadata=case.metadata_,
        created_by=case.created_by,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )
