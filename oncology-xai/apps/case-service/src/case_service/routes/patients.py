"""Patient routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query

from sqlalchemy.ext.asyncio import AsyncSession

from oncology_common.models import Patient as PatientSchema, PatientCreate, PaginatedResponse

from case_service.database import get_db
from case_service.services.patient_service import PatientService


router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post("", response_model=PatientSchema, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_data: PatientCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PatientSchema:
    """Create a new patient."""
    service = PatientService(db)
    patient = await service.create(
        external_id=patient_data.external_id,
        demographics=patient_data.demographics,
    )
    return PatientSchema(
        patient_id=patient.patient_id,
        external_id=patient.external_id,
        demographics=patient.demographics,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )


@router.get("", response_model=PaginatedResponse[PatientSchema])
async def list_patients(
    db: Annotated[AsyncSession, Depends(get_db)],
    query: str | None = Query(None, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[PatientSchema]:
    """List patients."""
    service = PatientService(db)
    skip = (page - 1) * page_size
    patients, total = await service.list(query=query, skip=skip, limit=page_size)

    return PaginatedResponse(
        data=[
            PatientSchema(
                patient_id=p.patient_id,
                external_id=p.external_id,
                demographics=p.demographics,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in patients
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(skip + len(patients)) < total,
    )


@router.get("/{patient_id}", response_model=PatientSchema)
async def get_patient(
    patient_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PatientSchema:
    """Get patient by ID."""
    service = PatientService(db)
    patient = await service.get_by_id(patient_id)

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    return PatientSchema(
        patient_id=patient.patient_id,
        external_id=patient.external_id,
        demographics=patient.demographics,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )
