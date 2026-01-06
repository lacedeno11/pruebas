# DERCAS-ONCO-XAI V1 - Case Service API Endpoints
# FastAPI endpoints for patients and cases

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from oncology_xai_common.auth import UserContext, get_user_context
from oncology_xai_common.middleware import get_correlation_id

from .database import get_db_session
from .crud import PatientCRUD, CaseCRUD
from .schemas import (
    PatientCreate, PatientUpdate, PatientResponse, PatientSummary, PatientFilters,
    CaseCreate, CaseUpdate, CaseResponse, CaseSummary, CaseFilters,
    PaginationParams, PaginatedPatients, PaginatedCases,
    CaseStatusEnum, CasePriorityEnum, ProcessingStatusEnum
)
from .events import get_event_emitter

logger = structlog.get_logger(__name__)

# Create routers
patients_router = APIRouter(prefix="/patients", tags=["Patients"])
cases_router = APIRouter(prefix="/cases", tags=["Cases"])


# Patient Endpoints

@patients_router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_data: PatientCreate,
    db: AsyncSession = Depends(get_db_session),
    user_context: UserContext = Depends(get_user_context)
):
    """
    Create a new patient.
    
    Args:
        patient_data: Patient creation data
        db: Database session
        user_context: Current user context
        
    Returns:
        Created patient
        
    Raises:
        HTTPException: If patient creation fails
    """
    try:
        # Check if patient with external_id already exists
        if patient_data.external_id:
            existing_patient = await PatientCRUD.get_by_external_id(db, patient_data.external_id)
            if existing_patient:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Patient with external_id '{patient_data.external_id}' already exists"
                )
        
        # Check if patient with MRN already exists
        if patient_data.medical_record_number:
            existing_patient = await PatientCRUD.get_by_mrn(db, patient_data.medical_record_number)
            if existing_patient:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Patient with MRN '{patient_data.medical_record_number}' already exists"
                )
        
        # Create patient
        patient = await PatientCRUD.create(db, patient_data, user_context.user_id)
        await db.commit()
        
        # Emit event
        event_emitter = await get_event_emitter()
        await event_emitter.emit_patient_created(patient, get_correlation_id())
        
        logger.info(
            "Patient created successfully",
            patient_id=patient.id,
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        
        return patient
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create patient",
            error=str(e),
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create patient"
        )


@patients_router.get("/", response_model=PaginatedPatients)
async def list_patients(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search in name or MRN"),
    gender: Optional[str] = Query(None, description="Filter by gender"),
    created_after: Optional[str] = Query(None, description="Created after date (ISO format)"),
    created_before: Optional[str] = Query(None, description="Created before date (ISO format)"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_desc: bool = Query(True, description="Order descending"),
    db: AsyncSession = Depends(get_db_session),
    user_context: UserContext = Depends(get_user_context)
):
    """
    List patients with pagination and filtering.
    
    Args:
        page: Page number
        size: Page size
        search: Search term
        gender: Gender filter
        created_after: Created after date
        created_before: Created before date
        order_by: Field to order by
        order_desc: Order descending
        db: Database session
        user_context: Current user context
        
    Returns:
        Paginated list of patients
    """
    try:
        # Parse dates
        from datetime import datetime
        created_after_dt = None
        created_before_dt = None
        
        if created_after:
            created_after_dt = datetime.fromisoformat(created_after.replace('Z', '+00:00'))
        if created_before:
            created_before_dt = datetime.fromisoformat(created_before.replace('Z', '+00:00'))
        
        # Create filters
        filters = PatientFilters(
            search=search,
            gender=gender,
            created_after=created_after_dt,
            created_before=created_before_dt,
            is_active=True
        )
        
        pagination = PaginationParams(page=page, size=size)
        
        # Get patients
        patients, total_count = await PatientCRUD.list_patients(
            db, pagination, filters, order_by, order_desc
        )
        
        # Convert to summary format with case counts
        patient_summaries = []
        for patient in patients:
            case_count = len(patient.cases) if patient.cases else 0
            summary = PatientSummary(
                id=patient.id,
                full_name=patient.full_name,
                age=patient.age,
                gender=patient.gender,
                medical_record_number=patient.medical_record_number,
                case_count=case_count,
                created_at=patient.created_at
            )
            patient_summaries.append(summary)
        
        return PaginatedPatients(
            items=patient_summaries,
            total=total_count,
            page=page,
            size=size
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {e}"
        )
    except Exception as e:
        logger.error(
            "Failed to list patients",
            error=str(e),
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list patients"
        )


@patients_router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db_session),
    user_context: UserContext = Depends(get_user_context)
):
    """
    Get patient by ID.
    
    Args:
        patient_id: Patient ID
        db: Database session
        user_context: Current user context
        
    Returns:
        Patient details
        
    Raises:
        HTTPException: If patient not found
    """
    try:
        patient = await PatientCRUD.get_by_id(db, patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        return patient
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get patient",
            patient_id=patient_id,
            error=str(e),
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get patient"
        )


@patients_router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    patient_data: PatientUpdate,
    db: AsyncSession = Depends(get_db_session),
    user_context: UserContext = Depends(get_user_context)
):
    """
    Update patient.
    
    Args:
        patient_id: Patient ID
        patient_data: Patient update data
        db: Database session
        user_context: Current user context
        
    Returns:
        Updated patient
        
    Raises:
        HTTPException: If patient not found or update fails
    """
    try:
        # Get existing patient
        patient = await PatientCRUD.get_by_id(db, patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        # Check for conflicts with external_id or MRN
        if patient_data.external_id and patient_data.external_id != patient.external_id:
            existing_patient = await PatientCRUD.get_by_external_id(db, patient_data.external_id)
            if existing_patient and existing_patient.id != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Patient with external_id '{patient_data.external_id}' already exists"
                )
        
        if patient_data.medical_record_number and patient_data.medical_record_number != patient.medical_record_number:
            existing_patient = await PatientCRUD.get_by_mrn(db, patient_data.medical_record_number)
            if existing_patient and existing_patient.id != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Patient with MRN '{patient_data.medical_record_number}' already exists"
                )
        
        # Update patient
        updated_patient = await PatientCRUD.update(db, patient, patient_data, user_context.user_id)
        await db.commit()
        
        # Emit event
        event_emitter = await get_event_emitter()
        await event_emitter.emit_patient_updated(updated_patient, get_correlation_id())
        
        logger.info(
            "Patient updated successfully",
            patient_id=patient_id,
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        
        return updated_patient
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update patient",
            patient_id=patient_id,
            error=str(e),
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update patient"
        )


@patients_router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db_session),
    user_context: UserContext = Depends(get_user_context)
):
    """
    Delete patient (soft delete).
    
    Args:
        patient_id: Patient ID
        db: Database session
        user_context: Current user context
        
    Raises:
        HTTPException: If patient not found or has active cases
    """
    try:
        # Get existing patient
        patient = await PatientCRUD.get_by_id(db, patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        # Check if patient has active cases
        if patient.cases and any(case.is_active for case in patient.cases):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete patient with active cases"
            )
        
        # Delete patient
        await PatientCRUD.delete(db, patient, user_context.user_id)
        await db.commit()
        
        logger.info(
            "Patient deleted successfully",
            patient_id=patient_id,
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete patient",
            patient_id=patient_id,
            error=str(e),
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete patient"
        )


# Case Endpoints

@cases_router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    db: AsyncSession = Depends(get_db_session),
    user_context: UserContext = Depends(get_user_context)
):
    """
    Create a new case.
    
    Args:
        case_data: Case creation data
        db: Database session
        user_context: Current user context
        
    Returns:
        Created case
        
    Raises:
        HTTPException: If case creation fails
    """
    try:
        # Verify patient exists
        patient = await PatientCRUD.get_by_id(db, case_data.patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        # Check if case with external_id already exists
        if case_data.external_id:
            existing_case = await CaseCRUD.get_by_external_id(db, case_data.external_id)
            if existing_case:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Case with external_id '{case_data.external_id}' already exists"
                )
        
        # Create case
        case = await CaseCRUD.create(db, case_data, user_context.user_id)
        await db.commit()
        
        # Emit event
        event_emitter = await get_event_emitter()
        await event_emitter.emit_case_created(case, get_correlation_id())
        
        logger.info(
            "Case created successfully",
            case_id=case.id,
            patient_id=case.patient_id,
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        
        return case
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create case",
            error=str(e),
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create case"
        )


@cases_router.get("/", response_model=PaginatedCases)
async def list_cases(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search in title or description"),
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    status: Optional[CaseStatusEnum] = Query(None, description="Filter by status"),
    priority: Optional[CasePriorityEnum] = Query(None, description="Filter by priority"),
    processing_status: Optional[ProcessingStatusEnum] = Query(None, description="Filter by processing status"),
    has_images: Optional[bool] = Query(None, description="Filter by image availability"),
    has_inference_results: Optional[bool] = Query(None, description="Filter by inference results"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_desc: bool = Query(True, description="Order descending"),
    db: AsyncSession = Depends(get_db_session),
    user_context: UserContext = Depends(get_user_context)
):
    """
    List cases with pagination and filtering.
    
    Args:
        page: Page number
        size: Page size
        search: Search term
        patient_id: Patient ID filter
        status: Status filter
        priority: Priority filter
        processing_status: Processing status filter
        has_images: Images filter
        has_inference_results: Inference results filter
        order_by: Field to order by
        order_desc: Order descending
        db: Database session
        user_context: Current user context
        
    Returns:
        Paginated list of cases
    """
    try:
        # Create filters
        filters = CaseFilters(
            search=search,
            patient_id=patient_id,
            status=status,
            priority=priority,
            processing_status=processing_status,
            has_images=has_images,
            has_inference_results=has_inference_results,
            is_active=True
        )
        
        pagination = PaginationParams(page=page, size=size)
        
        # Get cases
        cases, total_count = await CaseCRUD.list_cases(
            db, pagination, filters, order_by, order_desc
        )
        
        # Convert to summary format
        case_summaries = []
        for case in cases:
            summary = CaseSummary(
                id=case.id,
                title=case.title,
                status=case.status,
                priority=case.priority,
                processing_status=case.processing_status,
                processing_progress=case.processing_progress,
                case_date=case.case_date,
                created_at=case.created_at,
                patient_name=case.patient.full_name if case.patient else "Unknown",
                has_images=case.has_images,
                has_inference_results=case.has_inference_results
            )
            case_summaries.append(summary)
        
        return PaginatedCases(
            items=case_summaries,
            total=total_count,
            page=page,
            size=size
        )
        
    except Exception as e:
        logger.error(
            "Failed to list cases",
            error=str(e),
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list cases"
        )


@cases_router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    db: AsyncSession = Depends(get_db_session),
    user_context: UserContext = Depends(get_user_context)
):
    """
    Get case by ID.
    
    Args:
        case_id: Case ID
        db: Database session
        user_context: Current user context
        
    Returns:
        Case details
        
    Raises:
        HTTPException: If case not found
    """
    try:
        case = await CaseCRUD.get_by_id(db, case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        return case
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get case",
            case_id=case_id,
            error=str(e),
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get case"
        )


@cases_router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: str,
    case_data: CaseUpdate,
    db: AsyncSession = Depends(get_db_session),
    user_context: UserContext = Depends(get_user_context)
):
    """
    Update case.
    
    Args:
        case_id: Case ID
        case_data: Case update data
        db: Database session
        user_context: Current user context
        
    Returns:
        Updated case
        
    Raises:
        HTTPException: If case not found or update fails
    """
    try:
        # Get existing case
        case = await CaseCRUD.get_by_id(db, case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        # Store old values for event emission
        old_status = case.status
        old_processing_status = case.processing_status
        
        # Check for conflicts with external_id
        if case_data.external_id and case_data.external_id != case.external_id:
            existing_case = await CaseCRUD.get_by_external_id(db, case_data.external_id)
            if existing_case and existing_case.id != case_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Case with external_id '{case_data.external_id}' already exists"
                )
        
        # Update case
        updated_case = await CaseCRUD.update(db, case, case_data, user_context.user_id)
        await db.commit()
        
        # Emit events
        event_emitter = await get_event_emitter()
        await event_emitter.emit_case_updated(updated_case, get_correlation_id())
        
        # Emit specific status change events if status changed
        if case_data.status and case_data.status != old_status:
            await event_emitter.emit_case_status_changed(
                updated_case, old_status, case_data.status, get_correlation_id()
            )
        
        if case_data.processing_status and case_data.processing_status != old_processing_status:
            await event_emitter.emit_case_processing_status_changed(
                updated_case, old_processing_status, case_data.processing_status, get_correlation_id()
            )
        
        logger.info(
            "Case updated successfully",
            case_id=case_id,
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        
        return updated_case
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update case",
            case_id=case_id,
            error=str(e),
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update case"
        )


@cases_router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    db: AsyncSession = Depends(get_db_session),
    user_context: UserContext = Depends(get_user_context)
):
    """
    Delete case (soft delete).
    
    Args:
        case_id: Case ID
        db: Database session
        user_context: Current user context
        
    Raises:
        HTTPException: If case not found
    """
    try:
        # Get existing case
        case = await CaseCRUD.get_by_id(db, case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        # Delete case
        await CaseCRUD.delete(db, case, user_context.user_id)
        await db.commit()
        
        logger.info(
            "Case deleted successfully",
            case_id=case_id,
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete case",
            case_id=case_id,
            error=str(e),
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete case"
        )


# Additional endpoints

@patients_router.get("/{patient_id}/cases", response_model=PaginatedCases)
async def list_patient_cases(
    patient_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_desc: bool = Query(True, description="Order descending"),
    db: AsyncSession = Depends(get_db_session),
    user_context: UserContext = Depends(get_user_context)
):
    """
    List cases for a specific patient.
    
    Args:
        patient_id: Patient ID
        page: Page number
        size: Page size
        order_by: Field to order by
        order_desc: Order descending
        db: Database session
        user_context: Current user context
        
    Returns:
        Paginated list of cases for the patient
    """
    try:
        # Verify patient exists
        patient = await PatientCRUD.get_by_id(db, patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        pagination = PaginationParams(page=page, size=size)
        
        # Get cases for patient
        cases, total_count = await CaseCRUD.list_cases_by_patient(
            db, patient_id, pagination, order_by, order_desc
        )
        
        # Convert to summary format
        case_summaries = []
        for case in cases:
            summary = CaseSummary(
                id=case.id,
                title=case.title,
                status=case.status,
                priority=case.priority,
                processing_status=case.processing_status,
                processing_progress=case.processing_progress,
                case_date=case.case_date,
                created_at=case.created_at,
                patient_name=patient.full_name,
                has_images=case.has_images,
                has_inference_results=case.has_inference_results
            )
            case_summaries.append(summary)
        
        return PaginatedCases(
            items=case_summaries,
            total=total_count,
            page=page,
            size=size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to list patient cases",
            patient_id=patient_id,
            error=str(e),
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list patient cases"
        )


@cases_router.get("/statistics/summary")
async def get_case_statistics(
    db: AsyncSession = Depends(get_db_session),
    user_context: UserContext = Depends(get_user_context)
):
    """
    Get case statistics summary.
    
    Args:
        db: Database session
        user_context: Current user context
        
    Returns:
        Case statistics
    """
    try:
        statistics = await CaseCRUD.get_case_statistics(db)
        
        logger.info(
            "Case statistics retrieved",
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        
        return statistics
        
    except Exception as e:
        logger.error(
            "Failed to get case statistics",
            error=str(e),
            user_id=user_context.user_id,
            correlation_id=get_correlation_id()
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get case statistics"
        )
