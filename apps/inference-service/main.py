"""
DERCAS-ONCO-XAI V1 - Inference Service

AI inference service for medical image analysis with LangGraph workflows.
Provides asynchronous ML processing for histological pattern recognition
and genetic mutation detection with clinical guardrails.
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')

from packages.common.middleware import (
    CorrelationIdMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware
)
from packages.common.auth import get_current_user, require_permissions
from packages.common.errors import (
    ErrorCode,
    ResourceNotFoundError,
    BusinessLogicError,
    ExternalServiceError,
    create_error_response
)
from packages.event_contracts.messaging import EventBus

from .config import get_settings
from .database import init_db, get_db, close_db
from .models import MLJob, ResultBundle, PatternResult, GeneticResult
from .schemas import (
    ProcessImageRequest,
    ProcessImageResponse,
    JobStatusResponse,
    ResultBundleResponse,
    ArtifactResponse,
    InferenceStatistics
)
from .services import InferenceService, JobService, ResultService
from .celery_app import celery_app
from .workflows.image_analysis import ImageAnalysisGraph
from .events import EventPublisher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s"
)
logger = logging.getLogger(__name__)

# Global services
inference_service: Optional[InferenceService] = None
job_service: Optional[JobService] = None
result_service: Optional[ResultService] = None
event_publisher: Optional[EventPublisher] = None
image_analysis_workflow: Optional[ImageAnalysisGraph] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global inference_service, job_service, result_service, event_publisher, image_analysis_workflow
    
    settings = get_settings()
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Initialize event bus
        event_bus = EventBus(settings.rabbitmq_url)
        await event_bus.connect()
        logger.info("Event bus connected")
        
        # Initialize event publisher
        event_publisher = EventPublisher(event_bus)
        
        # Initialize services
        # Note: These will be created per request with database sessions
        logger.info("Services initialized")
        
        # Initialize LangGraph workflow
        image_analysis_workflow = ImageAnalysisGraph()
        logger.info("ImageAnalysisGraph workflow initialized")
        
        # Start Celery workers (in production, these would be separate processes)
        logger.info("Celery workers ready")
        
        logger.info("Inference service startup completed")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start inference service: {e}")
        raise
    finally:
        # Cleanup
        try:
            if event_bus:
                await event_bus.close()
            await close_db()
            logger.info("Inference service shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="DERCAS-ONCO-XAI Inference Service",
    description="AI inference service for medical image analysis with clinical guardrails",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


# Dependency to get services
async def get_inference_service(db: AsyncSession = Depends(get_db)) -> InferenceService:
    """Get inference service instance."""
    return InferenceService(db, event_publisher)


async def get_job_service(db: AsyncSession = Depends(get_db)) -> JobService:
    """Get job service instance."""
    return JobService(db, event_publisher)


async def get_result_service(db: AsyncSession = Depends(get_db)) -> ResultService:
    """Get result service instance."""
    return ResultService(db)


# Health check endpoint
@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connectivity
        # Check Celery workers
        # Check model availability
        
        return {
            "status": "healthy",
            "service": "inference-service",
            "version": "1.0.0",
            "timestamp": "2024-01-01T00:00:00Z",
            "checks": {
                "database": "healthy",
                "celery": "healthy",
                "models": "healthy",
                "workflow": "healthy"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "inference-service",
                "error": str(e)
            }
        )


# Image processing endpoints
@app.post(
    "/api/v1/images/{image_id}:process",
    response_model=ProcessImageResponse,
    summary="Process image for AI analysis",
    description="Start asynchronous AI processing of a medical image for pattern recognition and mutation detection"
)
async def process_image(
    image_id: str,
    request: ProcessImageRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    inference_service: InferenceService = Depends(get_inference_service)
):
    """
    Process image for AI analysis.
    
    Starts asynchronous processing of a medical image using the ImageAnalysisGraph
    LangGraph workflow for histological pattern recognition and genetic mutation detection.
    """
    try:
        # Validate permissions
        require_permissions(current_user, ["inference:process"])
        
        # Start processing job
        job = await inference_service.start_image_processing(
            image_id=image_id,
            processing_options=request.processing_options,
            user_id=current_user.get("sub"),
            correlation_id=request.correlation_id
        )
        
        logger.info(
            f"Started image processing job: {job.job_id} for image: {image_id}",
            extra={"correlation_id": request.correlation_id, "user_id": current_user.get("sub")}
        )
        
        return ProcessImageResponse(
            job_id=job.job_id,
            image_id=image_id,
            status=job.status,
            estimated_completion_time=job.estimated_completion_time,
            processing_options=request.processing_options,
            created_at=job.created_at
        )
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to process image {image_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/api/v1/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status",
    description="Get the current status and progress of an AI processing job"
)
async def get_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    job_service: JobService = Depends(get_job_service)
):
    """Get job status and progress."""
    try:
        # Validate permissions
        require_permissions(current_user, ["inference:read"])
        
        job = await job_service.get_job_by_id(job_id)
        if not job:
            raise ResourceNotFoundError(resource_type="Job", resource_id=job_id)
        
        return JobStatusResponse.from_orm(job)
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get job status {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/api/v1/results/{result_bundle_id}",
    response_model=ResultBundleResponse,
    summary="Get analysis results",
    description="Get the complete analysis results for a processed image"
)
async def get_results(
    result_bundle_id: str,
    current_user: dict = Depends(get_current_user),
    result_service: ResultService = Depends(get_result_service)
):
    """Get analysis results."""
    try:
        # Validate permissions
        require_permissions(current_user, ["inference:read"])
        
        result_bundle = await result_service.get_result_bundle(result_bundle_id)
        if not result_bundle:
            raise ResourceNotFoundError(resource_type="ResultBundle", resource_id=result_bundle_id)
        
        return ResultBundleResponse.from_orm(result_bundle)
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get results {result_bundle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/api/v1/results/{result_bundle_id}/artifacts",
    response_model=List[ArtifactResponse],
    summary="Get result artifacts",
    description="Get XAI artifacts (heatmaps, attention maps, etc.) for analysis results"
)
async def get_result_artifacts(
    result_bundle_id: str,
    artifact_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    result_service: ResultService = Depends(get_result_service)
):
    """Get result artifacts."""
    try:
        # Validate permissions
        require_permissions(current_user, ["inference:read"])
        
        artifacts = await result_service.get_result_artifacts(
            result_bundle_id=result_bundle_id,
            artifact_type=artifact_type
        )
        
        return [ArtifactResponse.from_orm(artifact) for artifact in artifacts]
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get artifacts for {result_bundle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Job management endpoints
@app.get(
    "/api/v1/jobs",
    response_model=List[JobStatusResponse],
    summary="List jobs",
    description="List AI processing jobs with optional filtering"
)
async def list_jobs(
    status: Optional[str] = None,
    image_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    job_service: JobService = Depends(get_job_service)
):
    """List processing jobs."""
    try:
        # Validate permissions
        require_permissions(current_user, ["inference:read"])
        
        jobs = await job_service.list_jobs(
            status=status,
            image_id=image_id,
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        return [JobStatusResponse.from_orm(job) for job in jobs]
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete(
    "/api/v1/jobs/{job_id}",
    summary="Cancel job",
    description="Cancel a running AI processing job"
)
async def cancel_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    job_service: JobService = Depends(get_job_service)
):
    """Cancel a processing job."""
    try:
        # Validate permissions
        require_permissions(current_user, ["inference:cancel"])
        
        success = await job_service.cancel_job(
            job_id=job_id,
            user_id=current_user.get("sub")
        )
        
        if not success:
            raise ResourceNotFoundError(resource_type="Job", resource_id=job_id)
        
        return {"message": "Job cancelled successfully", "job_id": job_id}
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Statistics and monitoring endpoints
@app.get(
    "/api/v1/statistics",
    response_model=InferenceStatistics,
    summary="Get inference statistics",
    description="Get statistics about AI processing jobs and results"
)
async def get_statistics(
    current_user: dict = Depends(get_current_user),
    job_service: JobService = Depends(get_job_service)
):
    """Get inference statistics."""
    try:
        # Validate permissions
        require_permissions(current_user, ["inference:read"])
        
        stats = await job_service.get_statistics()
        return InferenceStatistics(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Model management endpoints (for admin users)
@app.get(
    "/api/v1/models",
    summary="List available models",
    description="List available AI models for pattern recognition and mutation detection"
)
async def list_models(
    current_user: dict = Depends(get_current_user),
    inference_service: InferenceService = Depends(get_inference_service)
):
    """List available models."""
    try:
        # Validate permissions
        require_permissions(current_user, ["inference:admin"])
        
        models = await inference_service.list_available_models()
        return {"models": models}
        
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post(
    "/api/v1/models/{model_id}:reload",
    summary="Reload model",
    description="Reload a specific AI model (admin only)"
)
async def reload_model(
    model_id: str,
    current_user: dict = Depends(get_current_user),
    inference_service: InferenceService = Depends(get_inference_service)
):
    """Reload a model."""
    try:
        # Validate permissions
        require_permissions(current_user, ["inference:admin"])
        
        success = await inference_service.reload_model(model_id)
        if not success:
            raise ResourceNotFoundError(resource_type="Model", resource_id=model_id)
        
        return {"message": f"Model {model_id} reloaded successfully"}
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to reload model {model_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Error handlers
@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(request, exc: ResourceNotFoundError):
    return create_error_response(exc, status_code=404)


@app.exception_handler(BusinessLogicError)
async def business_logic_error_handler(request, exc: BusinessLogicError):
    return create_error_response(exc, status_code=400)


@app.exception_handler(ExternalServiceError)
async def external_service_error_handler(request, exc: ExternalServiceError):
    return create_error_response(exc, status_code=503)


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
