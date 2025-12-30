"""
DERCAS-ONCO-XAI V1 - Case Service

FastAPI service for managing patients and cases with SQLAlchemy 2.0 and event emission.
"""

import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')

from packages.common.middleware import (
    CorrelationIdMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    get_correlation_id,
    get_user_id
)
from packages.common.models import (
    HealthCheckResponse,
    PaginationParams,
    PaginatedResponse,
    CaseStatus
)
from packages.common.errors import (
    ErrorCode,
    create_http_exception,
    create_case_not_found_error,
    create_patient_not_found_error,
    platform_exception_to_http_exception
)
from packages.event_contracts.events import EventType, create_case_event
from packages.event_contracts.messaging import EventBus

from .config import get_settings
from .database import get_db, init_db
from .models import Patient, Case
from .schemas import (
    PatientCreate,
    PatientResponse,
    PatientUpdate,
    CaseCreate,
    CaseResponse,
    CaseUpdate
)
from .services import PatientService, CaseService
from .events import EventPublisher

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting Case Service...")
    
    settings = get_settings()
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize event bus
    app.state.event_bus = EventBus(
        connection_url=settings.rabbitmq_url,
        service_name="case-service"
    )
    await app.state.event_bus.start()
    logger.info("Event bus initialized")
    
    # Initialize event publisher
    app.state.event_publisher = EventPublisher(app.state.event_bus)
    
    logger.info("Case Service started successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Case Service...")
    await app.state.event_bus.stop()
    logger.info("Case Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="DERCAS-ONCO-XAI Case Service",
    description="Patient and Case Management Service for the Explainable AI Oncology Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware, enable_cors=True)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(CorrelationIdMiddleware)


# Health check endpoint
@app.get("/healthz", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        dependencies={
            "database": "healthy",  # TODO: Add actual health checks
            "rabbitmq": "healthy"
        }
    )


# Patient endpoints
@app.post("/api/v1/patients", response_model=PatientResponse, status_code=201)
async def create_patient(
    patient_data: PatientCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new patient."""
    correlation_id = get_correlation_id(request)
    user_id = get_user_id(request)
    
    logger.info(
        f"Creating patient: {patient_data.patient_id}",
        extra={"correlation_id": correlation_id}
    )
    
    try:
        patient_service = PatientService(db)
        patient = await patient_service.create_patient(patient_data)
        
        # Publish patient created event
        await app.state.event_publisher.publish_patient_created(
            patient=patient,
            correlation_id=correlation_id,
            user_id=user_id
        )
        
        logger.info(
            f"Patient created successfully: {patient.id}",
            extra={"correlation_id": correlation_id}
        )
        
        return PatientResponse.from_orm(patient)
        
    except Exception as e:
        logger.error(
            f"Failed to create patient: {e}",
            extra={"correlation_id": correlation_id},
            exc_info=True
        )
        raise platform_exception_to_http_exception(e)


@app.get("/api/v1/patients", response_model=PaginatedResponse)
async def list_patients(
    request: Request,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """List patients with pagination."""
    correlation_id = get_correlation_id(request)
    
    logger.info(
        f"Listing patients (page {pagination.page}, size {pagination.page_size})",
        extra={"correlation_id": correlation_id}
    )
    
    try:
        patient_service = PatientService(db)
        patients, total = await patient_service.list_patients(
            page=pagination.page,
            page_size=pagination.page_size
        )
        
        patient_responses = [PatientResponse.from_orm(p) for p in patients]
        
        return PaginatedResponse(
            items=patient_responses,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=(total + pagination.page_size - 1) // pagination.page_size
        )
        
    except Exception as e:
        logger.error(
            f"Failed to list patients: {e}",
            extra={"correlation_id": correlation_id},
            exc_info=True
        )
        raise platform_exception_to_http_exception(e)


@app.get("/api/v1/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get a patient by ID."""
    correlation_id = get_correlation_id(request)
    
    logger.info(
        f"Getting patient: {patient_id}",
        extra={"correlation_id": correlation_id}
    )
    
    try:
        patient_service = PatientService(db)
        patient = await patient_service.get_patient_by_id(patient_id)
        
        if not patient:
            raise create_patient_not_found_error(patient_id, correlation_id)
        
        return PatientResponse.from_orm(patient)
        
    except Exception as e:
        logger.error(
            f"Failed to get patient {patient_id}: {e}",
            extra={"correlation_id": correlation_id},
            exc_info=True
        )
        raise platform_exception_to_http_exception(e)


# Case endpoints
@app.post("/api/v1/cases", response_model=CaseResponse, status_code=201)
async def create_case(
    case_data: CaseCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new case."""
    correlation_id = get_correlation_id(request)
    user_id = get_user_id(request)
    
    logger.info(
        f"Creating case: {case_data.case_id} for patient: {case_data.patient_id}",
        extra={"correlation_id": correlation_id}
    )
    
    try:
        case_service = CaseService(db)
        case = await case_service.create_case(case_data)
        
        # Publish case created event
        await app.state.event_publisher.publish_case_created(
            case=case,
            correlation_id=correlation_id,
            user_id=user_id
        )
        
        logger.info(
            f"Case created successfully: {case.id}",
            extra={"correlation_id": correlation_id, "case_id": case.case_id}
        )
        
        return CaseResponse.from_orm(case)
        
    except Exception as e:
        logger.error(
            f"Failed to create case: {e}",
            extra={"correlation_id": correlation_id},
            exc_info=True
        )
        raise platform_exception_to_http_exception(e)


@app.get("/api/v1/cases", response_model=PaginatedResponse)
async def list_cases(
    request: Request,
    pagination: PaginationParams = Depends(),
    status: Optional[CaseStatus] = Query(None, description="Filter by case status"),
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    db: AsyncSession = Depends(get_db)
):
    """List cases with pagination and filtering."""
    correlation_id = get_correlation_id(request)
    
    logger.info(
        f"Listing cases (page {pagination.page}, size {pagination.page_size}, "
        f"status={status}, patient_id={patient_id})",
        extra={"correlation_id": correlation_id}
    )
    
    try:
        case_service = CaseService(db)
        cases, total = await case_service.list_cases(
            page=pagination.page,
            page_size=pagination.page_size,
            status=status,
            patient_id=patient_id
        )
        
        case_responses = [CaseResponse.from_orm(c) for c in cases]
        
        return PaginatedResponse(
            items=case_responses,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=(total + pagination.page_size - 1) // pagination.page_size
        )
        
    except Exception as e:
        logger.error(
            f"Failed to list cases: {e}",
            extra={"correlation_id": correlation_id},
            exc_info=True
        )
        raise platform_exception_to_http_exception(e)


@app.get("/api/v1/cases/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get a case by ID."""
    correlation_id = get_correlation_id(request)
    
    logger.info(
        f"Getting case: {case_id}",
        extra={"correlation_id": correlation_id, "case_id": case_id}
    )
    
    try:
        case_service = CaseService(db)
        case = await case_service.get_case_by_id(case_id)
        
        if not case:
            raise create_case_not_found_error(case_id, correlation_id)
        
        return CaseResponse.from_orm(case)
        
    except Exception as e:
        logger.error(
            f"Failed to get case {case_id}: {e}",
            extra={"correlation_id": correlation_id, "case_id": case_id},
            exc_info=True
        )
        raise platform_exception_to_http_exception(e)


@app.patch("/api/v1/cases/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: str,
    case_update: CaseUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update a case."""
    correlation_id = get_correlation_id(request)
    user_id = get_user_id(request)
    
    logger.info(
        f"Updating case: {case_id}",
        extra={"correlation_id": correlation_id, "case_id": case_id}
    )
    
    try:
        case_service = CaseService(db)
        
        # Get current case for comparison
        current_case = await case_service.get_case_by_id(case_id)
        if not current_case:
            raise create_case_not_found_error(case_id, correlation_id)
        
        # Update case
        updated_case = await case_service.update_case(case_id, case_update)
        
        # Publish case updated event
        await app.state.event_publisher.publish_case_updated(
            case=updated_case,
            previous_case=current_case,
            correlation_id=correlation_id,
            user_id=user_id
        )
        
        logger.info(
            f"Case updated successfully: {case_id}",
            extra={"correlation_id": correlation_id, "case_id": case_id}
        )
        
        return CaseResponse.from_orm(updated_case)
        
    except Exception as e:
        logger.error(
            f"Failed to update case {case_id}: {e}",
            extra={"correlation_id": correlation_id, "case_id": case_id},
            exc_info=True
        )
        raise platform_exception_to_http_exception(e)


if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
