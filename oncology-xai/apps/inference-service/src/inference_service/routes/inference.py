"""Inference API routes."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from inference_service.database import get_db
from inference_service.models.job import JobStatus
from inference_service.services.job_service import JobService
from inference_service.tasks.inference_task import run_inference_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["inference"])


# Request/Response Models
class ProcessImageRequest(BaseModel):
    """Request model for processing an image."""

    priority: int = Field(default=0, ge=0, le=10, description="Job priority (0-10)")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )


class JobResponse(BaseModel):
    """Response model for job information."""

    id: str
    image_id: str
    celery_task_id: Optional[str]
    status: str
    result_bundle_id: Optional[str]
    priority: int
    retry_count: int
    max_retries: int
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    updated_at: str
    error_message: Optional[str]
    error_details: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]

    class Config:
        """Pydantic config."""

        from_attributes = True


class PatternResultResponse(BaseModel):
    """Response model for pattern results."""

    id: str
    pattern_type: str
    pattern_name: str
    confidence: float
    location: Optional[Dict[str, Any]]
    bounding_box: Optional[Dict[str, Any]]
    description: Optional[str]
    severity: Optional[str]
    clinical_significance: Optional[str]
    metadata: Optional[Dict[str, Any]]
    created_at: str

    class Config:
        """Pydantic config."""

        from_attributes = True


class GeneticResultResponse(BaseModel):
    """Response model for genetic results."""

    id: str
    marker_name: str
    marker_type: str
    presence_probability: float
    clinical_relevance: Optional[str]
    therapeutic_implications: Optional[str]
    evidence: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    created_at: str

    class Config:
        """Pydantic config."""

        from_attributes = True


class XAIArtifactResponse(BaseModel):
    """Response model for XAI artifacts."""

    id: str
    artifact_type: str
    artifact_name: str
    artifact_url: Optional[str]
    artifact_data: Optional[Dict[str, Any]]
    description: Optional[str]
    interpretation: Optional[str]
    metadata: Optional[Dict[str, Any]]
    created_at: str

    class Config:
        """Pydantic config."""

        from_attributes = True


class ResultBundleResponse(BaseModel):
    """Response model for result bundles."""

    id: str
    ml_job_id: str
    image_id: str
    overall_confidence: float
    summary: Optional[str]
    metadata: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str
    pattern_results: List[PatternResultResponse]
    genetic_results: List[GeneticResultResponse]
    xai_artifacts: List[XAIArtifactResponse]

    class Config:
        """Pydantic config."""

        from_attributes = True


# Endpoints
@router.post(
    "/images/{image_id}/process",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def process_image(
    image_id: str,
    request: ProcessImageRequest = ProcessImageRequest(),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Start inference job for an image.

    Args:
        image_id: ID of the image to process
        request: Process request parameters
        db: Database session

    Returns:
        Created job information
    """
    job_service = JobService(db)

    # Create job
    job = await job_service.create_job(
        image_id=image_id,
        priority=request.priority,
        metadata=request.metadata,
    )

    # Start Celery task
    try:
        task = run_inference_task.apply_async(
            args=[job.id, image_id],
            priority=request.priority,
        )

        # Update job with Celery task ID
        await job_service.update_job_status(
            job_id=job.id,
            status=JobStatus.PENDING,
            celery_task_id=task.id,
        )

        logger.info(f"Started inference task {task.id} for job {job.id}")

    except Exception as e:
        logger.error(f"Failed to start Celery task for job {job.id}: {e}")
        await job_service.update_job_status(
            job_id=job.id,
            status=JobStatus.FAILED,
            error_message="Failed to start processing task",
            error_details={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start processing task",
        )

    # Refresh job to get updated data
    job = await job_service.get_job(job.id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found after creation",
        )

    return JobResponse.model_validate(job)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get job status and information.

    Args:
        job_id: Job ID
        db: Database session

    Returns:
        Job information
    """
    job_service = JobService(db)
    job = await job_service.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return JobResponse.model_validate(job)


@router.get("/images/{image_id}/results/latest", response_model=ResultBundleResponse)
async def get_latest_results(
    image_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get latest results for an image.

    Args:
        image_id: Image ID
        db: Database session

    Returns:
        Latest result bundle
    """
    job_service = JobService(db)
    result_bundle = await job_service.get_latest_result_for_image(image_id)

    if not result_bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No results found for image {image_id}",
        )

    return ResultBundleResponse.model_validate(result_bundle)


@router.get("/results/{result_bundle_id}", response_model=ResultBundleResponse)
async def get_result_bundle(
    result_bundle_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get result bundle by ID.

    Args:
        result_bundle_id: Result bundle ID
        db: Database session

    Returns:
        Result bundle with all related data
    """
    job_service = JobService(db)
    result_bundle = await job_service.get_result_bundle(result_bundle_id)

    if not result_bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result bundle {result_bundle_id} not found",
        )

    return ResultBundleResponse.model_validate(result_bundle)


@router.get("/results/{result_bundle_id}/artifacts", response_model=List[XAIArtifactResponse])
async def get_xai_artifacts(
    result_bundle_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get XAI artifacts for a result bundle.

    Args:
        result_bundle_id: Result bundle ID
        db: Database session

    Returns:
        List of XAI artifacts
    """
    job_service = JobService(db)
    result_bundle = await job_service.get_result_bundle(result_bundle_id)

    if not result_bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result bundle {result_bundle_id} not found",
        )

    return [XAIArtifactResponse.model_validate(artifact) for artifact in result_bundle.xai_artifacts]
