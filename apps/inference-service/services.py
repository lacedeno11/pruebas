"""
DERCAS-ONCO-XAI V1 - Inference Service Business Logic

Business logic services for AI inference processing with clinical guardrails.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

from sqlalchemy import and_, func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')

from packages.common.errors import (
    ErrorCode,
    ResourceNotFoundError,
    BusinessLogicError,
    ExternalServiceError
)

from .models import MLJob, ResultBundle, PatternResult, GeneticResult, XAIArtifact, PolicyDecision
from .schemas import ProcessingOptions
from .workflows.image_analysis import ImageAnalysisGraph, ImageAnalysisState
from .config import get_settings, get_clinical_guardrails
from .events import EventPublisher

logger = logging.getLogger(__name__)


class InferenceService:
    """Service for managing AI inference operations."""
    
    def __init__(self, db: AsyncSession, event_publisher: EventPublisher):
        self.db = db
        self.event_publisher = event_publisher
        self.settings = get_settings()
        self.workflow = ImageAnalysisGraph()
    
    async def start_image_processing(
        self,
        image_id: str,
        processing_options: Dict[str, Any],
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> MLJob:
        """
        Start asynchronous image processing.
        
        Args:
            image_id: Image ID to process
            processing_options: Processing configuration
            user_id: User initiating the processing
            correlation_id: Request correlation ID
            
        Returns:
            MLJob: Created processing job
        """
        try:
            # Validate image exists (in real implementation, check with image service)
            # For mock purposes, we'll assume image exists
            
            # Generate job ID
            job_id = f"job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid4())[:8]}"
            
            # Extract case ID (in real implementation, get from image service)
            case_id = f"case_{image_id.split('_')[1] if '_' in image_id else 'unknown'}"
            
            # Estimate completion time
            estimated_completion = datetime.utcnow() + timedelta(minutes=5)
            
            # Create ML job record
            job = MLJob(
                job_id=job_id,
                image_id=image_id,
                case_id=case_id,
                job_type="image_analysis",
                processing_options=processing_options,
                status="pending",
                estimated_completion_time=estimated_completion,
                user_id=user_id,
                correlation_id=correlation_id
            )
            
            self.db.add(job)
            await self.db.commit()
            await self.db.refresh(job)
            
            # Start async processing (in real implementation, this would be a Celery task)
            # For mock purposes, we'll simulate immediate processing
            await self._process_image_async(job)
            
            # Publish job created event
            if self.event_publisher:
                await self.event_publisher.publish_job_created(
                    job=job,
                    correlation_id=correlation_id,
                    user_id=user_id
                )
            
            logger.info(f"Started image processing job: {job_id} for image: {image_id}")
            return job
            
        except Exception as e:
            logger.error(f"Failed to start image processing for {image_id}: {e}")
            raise BusinessLogicError(f"Failed to start processing: {str(e)}")
    
    async def _process_image_async(self, job: MLJob):
        """Process image using the ImageAnalysisGraph workflow."""
        try:
            # Mark job as started
            job.mark_as_started(worker_id="mock_worker_1")
            await self.db.commit()
            
            # Create initial workflow state
            initial_state = ImageAnalysisState(
                job_id=job.job_id,
                image_id=job.image_id,
                case_id=job.case_id,
                processing_options=job.processing_options or {}
            )
            
            # Execute workflow
            final_state = await self.workflow.execute(initial_state)
            
            if final_state.processing_complete and not final_state.processing_error:
                # Processing successful
                await self._handle_successful_processing(job, final_state)
            else:
                # Processing failed
                await self._handle_failed_processing(job, final_state.processing_error)
            
        except Exception as e:
            logger.error(f"Image processing failed for job {job.job_id}: {e}")
            await self._handle_failed_processing(job, str(e))
    
    async def _handle_successful_processing(self, job: MLJob, final_state: ImageAnalysisState):
        """Handle successful processing completion."""
        try:
            # Create result bundle in database
            result_bundle = await self._create_result_bundle(job, final_state)
            
            # Mark job as completed
            job.mark_as_completed(result_bundle.result_bundle_id)
            await self.db.commit()
            
            # Publish completion event
            if self.event_publisher:
                await self.event_publisher.publish_job_completed(
                    job=job,
                    result_bundle=result_bundle,
                    correlation_id=job.correlation_id,
                    user_id=job.user_id
                )
            
            logger.info(f"Processing completed successfully for job {job.job_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle successful processing for job {job.job_id}: {e}")
            await self._handle_failed_processing(job, f"Post-processing failed: {str(e)}")
    
    async def _handle_failed_processing(self, job: MLJob, error_message: str):
        """Handle failed processing."""
        try:
            job.mark_as_failed(error_message)
            await self.db.commit()
            
            # Publish failure event
            if self.event_publisher:
                await self.event_publisher.publish_job_failed(
                    job=job,
                    error_message=error_message,
                    correlation_id=job.correlation_id,
                    user_id=job.user_id
                )
            
            logger.error(f"Processing failed for job {job.job_id}: {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to handle processing failure for job {job.job_id}: {e}")
    
    async def _create_result_bundle(self, job: MLJob, final_state: ImageAnalysisState) -> ResultBundle:
        """Create result bundle and related records in database."""
        try:
            # Create result bundle
            result_bundle = ResultBundle(
                result_bundle_id=final_state.result_bundle_id,
                job_id=job.job_id,
                image_id=job.image_id,
                case_id=job.case_id,
                model_versions=final_state.result_bundle.get("model_versions", {}),
                processing_metadata=final_state.result_bundle.get("processing_metadata", {}),
                overall_confidence=final_state.overall_confidence,
                analysis_summary=final_state.result_bundle.get("analysis_summary"),
                requires_review=final_state.requires_hitl,
                review_reason=final_state.hitl_reason,
                quality_score=final_state.result_bundle.get("quality_metrics", {}).get("image_quality_score"),
                uncertainty_score=1.0 - final_state.overall_confidence
            )
            
            self.db.add(result_bundle)
            await self.db.flush()  # Get ID without committing
            
            # Create pattern results
            for pattern_pred in final_state.pattern_predictions:
                pattern_result = PatternResult(
                    result_bundle_id=result_bundle.id,
                    pattern_type=pattern_pred.get("pattern_type"),
                    confidence_score=pattern_pred.get("confidence_score"),
                    model_name=pattern_pred.get("model_metadata", {}).get("model_id", "unknown"),
                    model_version=pattern_pred.get("model_metadata", {}).get("version", "1.0"),
                    raw_prediction=pattern_pred.get("raw_prediction"),
                    prediction_metadata=pattern_pred.get("model_metadata"),
                    region_coordinates=pattern_pred.get("region_coordinates"),
                    coverage_percentage=pattern_pred.get("coverage_percentage"),
                    prediction_quality=pattern_pred.get("prediction_quality")
                )
                self.db.add(pattern_result)
            
            # Create genetic results
            for mutation_pred in final_state.mutation_predictions:
                genetic_result = GeneticResult(
                    result_bundle_id=result_bundle.id,
                    mutation_type=mutation_pred.get("mutation_type"),
                    confidence_score=mutation_pred.get("confidence_score"),
                    mutation_status=mutation_pred.get("mutation_status"),
                    model_name=mutation_pred.get("model_metadata", {}).get("model_id", "unknown"),
                    model_version=mutation_pred.get("model_metadata", {}).get("version", "1.0"),
                    raw_prediction=mutation_pred.get("raw_prediction"),
                    prediction_metadata=mutation_pred.get("model_metadata"),
                    clinical_significance=mutation_pred.get("clinical_significance"),
                    therapeutic_implications=mutation_pred.get("therapeutic_implications"),
                    prediction_quality=mutation_pred.get("prediction_quality")
                )
                self.db.add(genetic_result)
            
            # Create XAI artifacts
            for artifact_data in final_state.xai_artifacts:
                xai_artifact = XAIArtifact(
                    result_bundle_id=result_bundle.id,
                    artifact_type=artifact_data.get("artifact_type"),
                    artifact_name=artifact_data.get("artifact_name"),
                    target_type=artifact_data.get("target_type"),
                    target_name=artifact_data.get("target_name"),
                    storage_path=artifact_data.get("storage_path"),
                    file_format=artifact_data.get("file_format"),
                    file_size=artifact_data.get("file_size"),
                    generation_method=artifact_data.get("generation_method"),
                    generation_parameters=artifact_data.get("generation_parameters"),
                    relevance_score=artifact_data.get("relevance_score"),
                    quality_score=artifact_data.get("quality_score")
                )
                self.db.add(xai_artifact)
            
            # Create policy decisions
            for policy_data in final_state.policy_decisions:
                policy_decision = PolicyDecision(
                    result_bundle_id=result_bundle.id,
                    job_id=job.job_id,
                    policy_type=policy_data.get("policy_type"),
                    policy_version=policy_data.get("policy_version"),
                    decision=policy_data.get("decision"),
                    decision_reason=policy_data.get("decision_reason"),
                    confidence_threshold_used=policy_data.get("confidence_threshold_used"),
                    requires_hitl=policy_data.get("requires_hitl", False),
                    hitl_reason=policy_data.get("hitl_reason")
                )
                self.db.add(policy_decision)
            
            await self.db.commit()
            await self.db.refresh(result_bundle)
            
            logger.info(f"Created result bundle: {result_bundle.result_bundle_id}")
            return result_bundle
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create result bundle for job {job.job_id}: {e}")
            raise
    
    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List available ML models."""
        from .models_ml import model_registry
        return model_registry.list_models()
    
    async def reload_model(self, model_id: str) -> bool:
        """Reload a specific model."""
        from .models_ml import model_registry
        return await model_registry.reload_model(model_id)


class JobService:
    """Service for managing processing jobs."""
    
    def __init__(self, db: AsyncSession, event_publisher: EventPublisher):
        self.db = db
        self.event_publisher = event_publisher
        self.settings = get_settings()
    
    async def get_job_by_id(self, job_id: str) -> Optional[MLJob]:
        """Get job by ID."""
        stmt = select(MLJob).where(MLJob.job_id == job_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_jobs(
        self,
        status: Optional[str] = None,
        image_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[MLJob]:
        """List jobs with optional filtering."""
        stmt = select(MLJob)
        
        # Apply filters
        if status:
            stmt = stmt.where(MLJob.status == status)
        if image_id:
            stmt = stmt.where(MLJob.image_id == image_id)
        if user_id:
            stmt = stmt.where(MLJob.user_id == user_id)
        
        # Apply ordering and pagination
        stmt = stmt.order_by(desc(MLJob.created_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def cancel_job(self, job_id: str, user_id: Optional[str] = None) -> bool:
        """Cancel a running job."""
        job = await self.get_job_by_id(job_id)
        if not job:
            return False
        
        if job.is_completed():
            raise BusinessLogicError("Cannot cancel completed job")
        
        # Update job status
        job.status = "cancelled"
        job.completed_at = datetime.utcnow()
        job.error_message = f"Cancelled by user {user_id or 'unknown'}"
        
        await self.db.commit()
        
        # Publish cancellation event
        if self.event_publisher:
            await self.event_publisher.publish_job_cancelled(
                job=job,
                user_id=user_id,
                correlation_id=job.correlation_id
            )
        
        logger.info(f"Job cancelled: {job_id} by user: {user_id}")
        return True
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get job processing statistics."""
        # Total jobs
        total_stmt = select(func.count(MLJob.id))
        total_result = await self.db.execute(total_stmt)
        total_jobs = total_result.scalar()
        
        # Jobs by status
        status_stmt = select(MLJob.status, func.count(MLJob.id)).group_by(MLJob.status)
        status_result = await self.db.execute(status_stmt)
        jobs_by_status = {status: count for status, count in status_result.all()}
        
        # Performance metrics
        completed_jobs = jobs_by_status.get("completed", 0)
        failed_jobs = jobs_by_status.get("failed", 0)
        success_rate = (completed_jobs / max(total_jobs, 1)) * 100
        
        # Average processing time for completed jobs
        avg_time_stmt = select(func.avg(
            func.extract('epoch', MLJob.completed_at - MLJob.started_at)
        )).where(
            and_(
                MLJob.status == "completed",
                MLJob.started_at.is_not(None),
                MLJob.completed_at.is_not(None)
            )
        )
        avg_time_result = await self.db.execute(avg_time_stmt)
        avg_processing_time = avg_time_result.scalar() or 0.0
        
        # Recent activity
        last_24h_stmt = select(func.count(MLJob.id)).where(
            MLJob.created_at >= datetime.utcnow() - timedelta(hours=24)
        )
        last_24h_result = await self.db.execute(last_24h_stmt)
        jobs_last_24h = last_24h_result.scalar()
        
        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "running_jobs": jobs_by_status.get("running", 0),
            "pending_jobs": jobs_by_status.get("pending", 0),
            "success_rate": success_rate,
            "average_processing_time_seconds": avg_processing_time,
            "jobs_last_24h": jobs_last_24h,
            "jobs_last_week": total_jobs,  # Simplified for mock
            "jobs_by_model": {},  # Would need more complex query
            "average_confidence_score": 0.85,  # Mock value
            "high_confidence_results": int(completed_jobs * 0.7),  # Mock value
            "hitl_required_count": int(completed_jobs * 0.15),  # Mock value
            "total_processing_time_hours": (avg_processing_time * completed_jobs) / 3600,
            "average_queue_time_seconds": 30.0  # Mock value
        }


class ResultService:
    """Service for managing analysis results."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
    
    async def get_result_bundle(self, result_bundle_id: str) -> Optional[ResultBundle]:
        """Get result bundle with all related data."""
        stmt = select(ResultBundle).where(
            ResultBundle.result_bundle_id == result_bundle_id
        )
        result = await self.db.execute(stmt)
        bundle = result.scalar_one_or_none()
        
        if bundle:
            # Eagerly load related data
            await self.db.refresh(bundle, ["pattern_results", "genetic_results", "xai_artifacts"])
        
        return bundle
    
    async def get_result_artifacts(
        self,
        result_bundle_id: str,
        artifact_type: Optional[str] = None
    ) -> List[XAIArtifact]:
        """Get XAI artifacts for a result bundle."""
        # First get the result bundle
        bundle = await self.get_result_bundle(result_bundle_id)
        if not bundle:
            raise ResourceNotFoundError(resource_type="ResultBundle", resource_id=result_bundle_id)
        
        stmt = select(XAIArtifact).where(XAIArtifact.result_bundle_id == bundle.id)
        
        if artifact_type:
            stmt = stmt.where(XAIArtifact.artifact_type == artifact_type)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def search_results(
        self,
        case_id: Optional[str] = None,
        pattern_type: Optional[str] = None,
        mutation_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        requires_review: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ResultBundle]:
        """Search result bundles with filters."""
        stmt = select(ResultBundle)
        
        # Apply filters
        if case_id:
            stmt = stmt.where(ResultBundle.case_id == case_id)
        if min_confidence is not None:
            stmt = stmt.where(ResultBundle.overall_confidence >= min_confidence)
        if requires_review is not None:
            stmt = stmt.where(ResultBundle.requires_review == requires_review)
        
        # Apply ordering and pagination
        stmt = stmt.order_by(desc(ResultBundle.created_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class ClinicalGuardrailsService:
    """Service for applying clinical guardrails and HITL policies."""
    
    def __init__(self):
        self.settings = get_settings()
        self.guardrails = get_clinical_guardrails()
    
    def evaluate_confidence_thresholds(
        self,
        pattern_results: List[Dict[str, Any]],
        mutation_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Evaluate confidence threshold policies."""
        decisions = []
        thresholds = self.guardrails["confidence_thresholds"]
        
        # Check pattern confidence thresholds
        for result in pattern_results:
            confidence = result.get("confidence_score", 0.0)
            pattern_type = result.get("pattern_type")
            
            if confidence < thresholds["pattern_low"]:
                decisions.append({
                    "policy_type": "confidence_threshold",
                    "decision": "require_review",
                    "decision_reason": f"Low confidence for pattern {pattern_type}: {confidence:.3f}",
                    "requires_hitl": True,
                    "confidence_threshold_used": thresholds["pattern_low"]
                })
            elif confidence < thresholds["pattern_medium"]:
                decisions.append({
                    "policy_type": "confidence_threshold",
                    "decision": "flag_for_review",
                    "decision_reason": f"Medium confidence for pattern {pattern_type}: {confidence:.3f}",
                    "requires_hitl": False,
                    "confidence_threshold_used": thresholds["pattern_medium"]
                })
        
        # Check mutation confidence thresholds
        for result in mutation_results:
            confidence = result.get("confidence_score", 0.0)
            mutation_type = result.get("mutation_type")
            
            if confidence < thresholds["mutation_low"]:
                decisions.append({
                    "policy_type": "confidence_threshold",
                    "decision": "require_review",
                    "decision_reason": f"Low confidence for mutation {mutation_type}: {confidence:.3f}",
                    "requires_hitl": True,
                    "confidence_threshold_used": thresholds["mutation_low"]
                })
        
        return decisions
    
    def check_prediction_conflicts(
        self,
        pattern_results: List[Dict[str, Any]],
        mutation_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Check for conflicting predictions requiring HITL."""
        decisions = []
        conflict_threshold = self.guardrails["hitl_conflict_threshold"]
        
        # Check pattern conflicts
        if len(pattern_results) >= 2:
            confidences = sorted([r.get("confidence_score", 0.0) for r in pattern_results], reverse=True)
            if confidences[0] - confidences[1] < conflict_threshold:
                decisions.append({
                    "policy_type": "conflict_detection",
                    "decision": "require_review",
                    "decision_reason": f"Conflicting pattern predictions: {confidences[0]:.3f} vs {confidences[1]:.3f}",
                    "requires_hitl": True,
                    "confidence_threshold_used": conflict_threshold
                })
        
        return decisions
    
    def apply_mutation_policies(self, mutation_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply mutation-specific policies."""
        decisions = []
        
        if self.guardrails["require_hitl_for_mutations"]:
            positive_mutations = [
                r for r in mutation_results
                if r.get("mutation_status") == "positive"
            ]
            
            for result in positive_mutations:
                mutation_type = result.get("mutation_type")
                decisions.append({
                    "policy_type": "mutation_hitl_policy",
                    "decision": "require_review",
                    "decision_reason": f"Positive mutation {mutation_type} requires human review",
                    "requires_hitl": True,
                    "confidence_threshold_used": 0.0
                })
        
        return decisions
    
    def validate_clinical_claims(self, analysis_summary: str) -> List[str]:
        """Validate that analysis summary doesn't contain prohibited language."""
        violations = []
        
        # Prohibited definitive diagnosis language
        prohibited_phrases = [
            "diagnosis is",
            "patient has",
            "confirmed diagnosis",
            "definitive diagnosis",
            "certain that",
            "definitely shows",
            "proves that"
        ]
        
        summary_lower = analysis_summary.lower()
        for phrase in prohibited_phrases:
            if phrase in summary_lower:
                violations.append(f"Contains prohibited definitive language: '{phrase}'")
        
        # Required disclaimers
        required_disclaimers = [
            "limitations",
            "disclaimer",
            "not for diagnostic use",
            "research purposes"
        ]
        
        has_disclaimer = any(disclaimer in summary_lower for disclaimer in required_disclaimers)
        if not has_disclaimer:
            violations.append("Missing required limitations/disclaimer language")
        
        return violations
