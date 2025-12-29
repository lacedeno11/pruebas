"""Service layer for managing ML jobs and results."""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from inference_service.models.job import JobStatus, MLJob
from inference_service.models.result import GeneticResult, PatternResult, ResultBundle, XAIArtifact

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing ML jobs and results."""

    def __init__(self, db: AsyncSession):
        """Initialize job service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_job(
        self,
        image_id: str,
        priority: int = 0,
        metadata: Optional[dict] = None,
    ) -> MLJob:
        """Create a new ML job.

        Args:
            image_id: ID of the image to process
            priority: Job priority (higher = more important)
            metadata: Additional metadata

        Returns:
            Created ML job
        """
        job = MLJob(
            image_id=image_id,
            status=JobStatus.PENDING,
            priority=priority,
            metadata=metadata or {},
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        logger.info(f"Created job {job.id} for image {image_id}")
        return job

    async def get_job(self, job_id: str) -> Optional[MLJob]:
        """Get job by ID.

        Args:
            job_id: Job ID

        Returns:
            ML job or None if not found
        """
        result = await self.db.execute(select(MLJob).where(MLJob.id == job_id))
        return result.scalar_one_or_none()

    async def get_job_by_celery_task_id(self, celery_task_id: str) -> Optional[MLJob]:
        """Get job by Celery task ID.

        Args:
            celery_task_id: Celery task ID

        Returns:
            ML job or None if not found
        """
        result = await self.db.execute(
            select(MLJob).where(MLJob.celery_task_id == celery_task_id)
        )
        return result.scalar_one_or_none()

    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        celery_task_id: Optional[str] = None,
        result_bundle_id: Optional[str] = None,
        error_message: Optional[str] = None,
        error_details: Optional[dict] = None,
    ) -> Optional[MLJob]:
        """Update job status.

        Args:
            job_id: Job ID
            status: New status
            celery_task_id: Celery task ID
            result_bundle_id: Result bundle ID
            error_message: Error message if failed
            error_details: Error details if failed

        Returns:
            Updated ML job or None if not found
        """
        job = await self.get_job(job_id)
        if not job:
            return None

        job.status = status
        if celery_task_id:
            job.celery_task_id = celery_task_id
        if result_bundle_id:
            job.result_bundle_id = result_bundle_id
        if error_message:
            job.error_message = error_message
        if error_details:
            job.error_details = error_details

        # Update timestamps
        if status == JobStatus.PROCESSING and not job.started_at:
            job.started_at = datetime.utcnow()
        elif status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            job.completed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(job)
        logger.info(f"Updated job {job_id} status to {status}")
        return job

    async def get_latest_result_for_image(self, image_id: str) -> Optional[ResultBundle]:
        """Get latest result bundle for an image.

        Args:
            image_id: Image ID

        Returns:
            Latest result bundle or None if not found
        """
        result = await self.db.execute(
            select(ResultBundle)
            .where(ResultBundle.image_id == image_id)
            .order_by(ResultBundle.created_at.desc())
            .limit(1)
            .options(
                selectinload(ResultBundle.pattern_results),
                selectinload(ResultBundle.genetic_results),
                selectinload(ResultBundle.xai_artifacts),
            )
        )
        return result.scalar_one_or_none()

    async def get_result_bundle(self, result_bundle_id: str) -> Optional[ResultBundle]:
        """Get result bundle by ID with all related data.

        Args:
            result_bundle_id: Result bundle ID

        Returns:
            Result bundle or None if not found
        """
        result = await self.db.execute(
            select(ResultBundle)
            .where(ResultBundle.id == result_bundle_id)
            .options(
                selectinload(ResultBundle.pattern_results),
                selectinload(ResultBundle.genetic_results),
                selectinload(ResultBundle.xai_artifacts),
            )
        )
        return result.scalar_one_or_none()

    async def create_result_bundle(
        self,
        ml_job_id: str,
        image_id: str,
        overall_confidence: float,
        summary: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ResultBundle:
        """Create a result bundle.

        Args:
            ml_job_id: ML job ID
            image_id: Image ID
            overall_confidence: Overall confidence score
            summary: Summary text
            metadata: Additional metadata

        Returns:
            Created result bundle
        """
        result_bundle = ResultBundle(
            ml_job_id=ml_job_id,
            image_id=image_id,
            overall_confidence=overall_confidence,
            summary=summary,
            metadata=metadata or {},
        )
        self.db.add(result_bundle)
        await self.db.commit()
        await self.db.refresh(result_bundle)
        logger.info(f"Created result bundle {result_bundle.id} for job {ml_job_id}")
        return result_bundle

    async def add_pattern_result(
        self,
        result_bundle_id: str,
        pattern_type: str,
        pattern_name: str,
        confidence: float,
        location: Optional[dict] = None,
        bounding_box: Optional[dict] = None,
        description: Optional[str] = None,
        severity: Optional[str] = None,
        clinical_significance: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> PatternResult:
        """Add a pattern result to a result bundle.

        Args:
            result_bundle_id: Result bundle ID
            pattern_type: Type of pattern
            pattern_name: Name of pattern
            confidence: Confidence score
            location: Location information
            bounding_box: Bounding box coordinates
            description: Pattern description
            severity: Severity level
            clinical_significance: Clinical significance
            metadata: Additional metadata

        Returns:
            Created pattern result
        """
        pattern_result = PatternResult(
            result_bundle_id=result_bundle_id,
            pattern_type=pattern_type,
            pattern_name=pattern_name,
            confidence=confidence,
            location=location,
            bounding_box=bounding_box,
            description=description,
            severity=severity,
            clinical_significance=clinical_significance,
            metadata=metadata or {},
        )
        self.db.add(pattern_result)
        await self.db.commit()
        await self.db.refresh(pattern_result)
        return pattern_result

    async def add_genetic_result(
        self,
        result_bundle_id: str,
        marker_name: str,
        marker_type: str,
        presence_probability: float,
        clinical_relevance: Optional[str] = None,
        therapeutic_implications: Optional[str] = None,
        evidence: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> GeneticResult:
        """Add a genetic result to a result bundle.

        Args:
            result_bundle_id: Result bundle ID
            marker_name: Name of genetic marker
            marker_type: Type of marker
            presence_probability: Probability of presence
            clinical_relevance: Clinical relevance
            therapeutic_implications: Therapeutic implications
            evidence: Supporting evidence
            metadata: Additional metadata

        Returns:
            Created genetic result
        """
        genetic_result = GeneticResult(
            result_bundle_id=result_bundle_id,
            marker_name=marker_name,
            marker_type=marker_type,
            presence_probability=presence_probability,
            clinical_relevance=clinical_relevance,
            therapeutic_implications=therapeutic_implications,
            evidence=evidence,
            metadata=metadata or {},
        )
        self.db.add(genetic_result)
        await self.db.commit()
        await self.db.refresh(genetic_result)
        return genetic_result

    async def add_xai_artifact(
        self,
        result_bundle_id: str,
        artifact_type: str,
        artifact_name: str,
        artifact_url: Optional[str] = None,
        artifact_data: Optional[dict] = None,
        description: Optional[str] = None,
        interpretation: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> XAIArtifact:
        """Add an XAI artifact to a result bundle.

        Args:
            result_bundle_id: Result bundle ID
            artifact_type: Type of artifact
            artifact_name: Name of artifact
            artifact_url: URL to artifact
            artifact_data: Artifact data
            description: Description
            interpretation: Interpretation
            metadata: Additional metadata

        Returns:
            Created XAI artifact
        """
        xai_artifact = XAIArtifact(
            result_bundle_id=result_bundle_id,
            artifact_type=artifact_type,
            artifact_name=artifact_name,
            artifact_url=artifact_url,
            artifact_data=artifact_data,
            description=description,
            interpretation=interpretation,
            metadata=metadata or {},
        )
        self.db.add(xai_artifact)
        await self.db.commit()
        await self.db.refresh(xai_artifact)
        return xai_artifact
