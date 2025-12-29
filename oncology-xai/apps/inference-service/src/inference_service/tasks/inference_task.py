"""Celery task for running inference using LangGraph workflows."""

import json
import logging
from datetime import datetime
from typing import Any, Dict

import pika
from celery import Task

from inference_service.celery_app import celery_app
from inference_service.config import get_settings
from inference_service.database import get_sync_db
from inference_service.models.job import JobStatus, MLJob
from inference_service.models.result import GeneticResult, PatternResult, ResultBundle, XAIArtifact

logger = logging.getLogger(__name__)
settings = get_settings()


class InferenceTask(Task):
    """Base task class for inference tasks."""

    def on_failure(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: Any) -> None:
        """Handle task failure.

        Args:
            exc: Exception that caused the failure
            task_id: Task ID
            args: Task arguments
            kwargs: Task keyword arguments
            einfo: Exception info
        """
        logger.error(f"Task {task_id} failed: {exc}", exc_info=einfo)

        # Update job status in database
        if args and len(args) > 0:
            job_id = args[0]
            db = get_sync_db()
            try:
                job = db.query(MLJob).filter(MLJob.id == job_id).first()
                if job:
                    job.status = JobStatus.FAILED
                    job.error_message = str(exc)
                    job.error_details = {"error_type": type(exc).__name__, "traceback": str(einfo)}
                    job.completed_at = datetime.utcnow()
                    db.commit()
            except Exception as e:
                logger.error(f"Failed to update job status: {e}")
                db.rollback()
            finally:
                db.close()


def emit_job_completed_event(job_id: str, image_id: str, result_bundle_id: str) -> None:
    """Emit job completed event to RabbitMQ.

    Args:
        job_id: Job ID
        image_id: Image ID
        result_bundle_id: Result bundle ID
    """
    try:
        connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
        channel = connection.channel()

        # Declare exchange
        channel.exchange_declare(
            exchange=settings.rabbitmq_exchange,
            exchange_type="topic",
            durable=True,
        )

        # Prepare message
        message = {
            "event_type": "inference.completed",
            "job_id": job_id,
            "image_id": image_id,
            "result_bundle_id": result_bundle_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Publish message
        channel.basic_publish(
            exchange=settings.rabbitmq_exchange,
            routing_key=settings.rabbitmq_routing_key,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type="application/json",
            ),
        )

        connection.close()
        logger.info(f"Emitted job completed event for job {job_id}")

    except Exception as e:
        logger.error(f"Failed to emit job completed event: {e}")


def run_langgraph_workflow(image_id: str) -> Dict[str, Any]:
    """Run LangGraph ImageAnalysisGraph workflow.

    This is a mock implementation that simulates the workflow.
    In production, this would integrate with the actual LangGraph workflow.

    Args:
        image_id: Image ID to process

    Returns:
        Workflow results
    """
    logger.info(f"Running LangGraph workflow for image {image_id}")

    # Mock workflow results
    # In production, this would call the actual ImageAnalysisGraph
    results = {
        "overall_confidence": 0.87,
        "summary": "Analysis completed successfully. Multiple patterns detected with high confidence.",
        "patterns": [
            {
                "pattern_type": "morphological",
                "pattern_name": "Nuclear Atypia",
                "confidence": 0.92,
                "location": {"x": 150, "y": 200, "z": 10},
                "bounding_box": {"x1": 100, "y1": 150, "x2": 200, "y2": 250},
                "description": "Irregular nuclear morphology detected in epithelial cells",
                "severity": "high",
                "clinical_significance": "May indicate dysplasia or early malignant transformation",
            },
            {
                "pattern_type": "architectural",
                "pattern_name": "Glandular Disorganization",
                "confidence": 0.85,
                "location": {"x": 300, "y": 400, "z": 15},
                "bounding_box": {"x1": 250, "y1": 350, "x2": 350, "y2": 450},
                "description": "Loss of normal glandular architecture",
                "severity": "moderate",
                "clinical_significance": "Consistent with adenocarcinoma",
            },
        ],
        "genetic_markers": [
            {
                "marker_name": "HER2",
                "marker_type": "receptor_overexpression",
                "presence_probability": 0.78,
                "clinical_relevance": "HER2 overexpression indicates potential for targeted therapy",
                "therapeutic_implications": "Trastuzumab (Herceptin) may be effective",
                "evidence": {
                    "staining_intensity": "3+",
                    "percentage_positive": 85,
                },
            },
            {
                "marker_name": "ER",
                "marker_type": "hormone_receptor",
                "presence_probability": 0.65,
                "clinical_relevance": "Estrogen receptor positivity",
                "therapeutic_implications": "Hormonal therapy may be beneficial",
                "evidence": {
                    "staining_intensity": "2+",
                    "percentage_positive": 70,
                },
            },
        ],
        "xai_artifacts": [
            {
                "artifact_type": "heatmap",
                "artifact_name": "Attention Heatmap",
                "artifact_url": f"s3://oncology-xai/artifacts/{image_id}/heatmap.png",
                "description": "Visual attention map showing regions of interest",
                "interpretation": "Model focused primarily on nuclear and glandular patterns",
                "metadata": {"resolution": "1024x1024", "colormap": "jet"},
            },
            {
                "artifact_type": "feature_importance",
                "artifact_name": "Feature Attribution",
                "artifact_data": {
                    "nuclear_size": 0.35,
                    "chromatin_pattern": 0.28,
                    "glandular_structure": 0.22,
                    "cellular_density": 0.15,
                },
                "description": "Quantitative feature importance scores",
                "interpretation": "Nuclear size and chromatin patterns were most influential",
            },
            {
                "artifact_type": "grad_cam",
                "artifact_name": "GradCAM Visualization",
                "artifact_url": f"s3://oncology-xai/artifacts/{image_id}/gradcam.png",
                "description": "Gradient-based class activation mapping",
                "interpretation": "Highlights discriminative regions for classification",
                "metadata": {"layer": "conv5", "target_class": "adenocarcinoma"},
            },
        ],
        "metadata": {
            "workflow_version": "1.0.0",
            "model_versions": {
                "pattern_detection": "v2.1.0",
                "genetic_marker": "v1.5.0",
                "xai_generator": "v1.0.0",
            },
            "processing_time_seconds": 45.2,
        },
    }

    logger.info(f"LangGraph workflow completed for image {image_id}")
    return results


@celery_app.task(bind=True, base=InferenceTask, name="inference_service.tasks.inference_task.run_inference_task")
def run_inference_task(self: Task, job_id: str, image_id: str) -> Dict[str, Any]:
    """Run inference task for an image.

    Args:
        job_id: Job ID
        image_id: Image ID

    Returns:
        Inference results
    """
    logger.info(f"Starting inference task for job {job_id}, image {image_id}")

    db = get_sync_db()
    try:
        # Update job status to processing
        job = db.query(MLJob).filter(MLJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        db.commit()

        # Run LangGraph workflow
        workflow_results = run_langgraph_workflow(image_id)

        # Create result bundle
        result_bundle = ResultBundle(
            ml_job_id=job_id,
            image_id=image_id,
            overall_confidence=workflow_results["overall_confidence"],
            summary=workflow_results.get("summary"),
            metadata=workflow_results.get("metadata", {}),
        )
        db.add(result_bundle)
        db.flush()

        # Add pattern results
        for pattern in workflow_results.get("patterns", []):
            pattern_result = PatternResult(
                result_bundle_id=result_bundle.id,
                pattern_type=pattern["pattern_type"],
                pattern_name=pattern["pattern_name"],
                confidence=pattern["confidence"],
                location=pattern.get("location"),
                bounding_box=pattern.get("bounding_box"),
                description=pattern.get("description"),
                severity=pattern.get("severity"),
                clinical_significance=pattern.get("clinical_significance"),
            )
            db.add(pattern_result)

        # Add genetic results
        for marker in workflow_results.get("genetic_markers", []):
            genetic_result = GeneticResult(
                result_bundle_id=result_bundle.id,
                marker_name=marker["marker_name"],
                marker_type=marker["marker_type"],
                presence_probability=marker["presence_probability"],
                clinical_relevance=marker.get("clinical_relevance"),
                therapeutic_implications=marker.get("therapeutic_implications"),
                evidence=marker.get("evidence"),
            )
            db.add(genetic_result)

        # Add XAI artifacts
        for artifact in workflow_results.get("xai_artifacts", []):
            xai_artifact = XAIArtifact(
                result_bundle_id=result_bundle.id,
                artifact_type=artifact["artifact_type"],
                artifact_name=artifact["artifact_name"],
                artifact_url=artifact.get("artifact_url"),
                artifact_data=artifact.get("artifact_data"),
                description=artifact.get("description"),
                interpretation=artifact.get("interpretation"),
                metadata=artifact.get("metadata"),
            )
            db.add(xai_artifact)

        db.commit()

        # Update job status to completed
        job.status = JobStatus.COMPLETED
        job.result_bundle_id = result_bundle.id
        job.completed_at = datetime.utcnow()
        db.commit()

        logger.info(f"Inference task completed for job {job_id}")

        # Emit job completed event
        emit_job_completed_event(job_id, image_id, result_bundle.id)

        return {
            "job_id": job_id,
            "image_id": image_id,
            "result_bundle_id": result_bundle.id,
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"Inference task failed for job {job_id}: {e}")
        db.rollback()

        # Update job status to failed
        job = db.query(MLJob).filter(MLJob.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.error_details = {"error_type": type(e).__name__}
            job.completed_at = datetime.utcnow()
            db.commit()

        raise

    finally:
        db.close()
