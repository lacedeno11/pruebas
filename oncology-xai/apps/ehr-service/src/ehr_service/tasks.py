"""Celery tasks for EHR processing."""

import asyncio
from uuid import UUID

from celery import Task
from celery.utils.log import get_task_logger

from ehr_service.celery_app import celery_app
from ehr_service.database import async_session_maker
from ehr_service.models import EHRDocument, EHRDocumentStatus, EHREntity, EHRMapping
from ehr_service.services.workflow_service import WorkflowService
from event_contracts import EventType
from oncology_common.clients.rabbitmq import create_event_publisher
from ehr_service.config import settings
from sqlalchemy import select

logger = get_task_logger(__name__)


class AsyncTask(Task):
    """Base task class for async operations."""

    def run(self, *args, **kwargs):
        """Run async task."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.async_run(*args, **kwargs))

    async def async_run(self, *args, **kwargs):
        """Override this method for async tasks."""
        raise NotImplementedError


@celery_app.task(base=AsyncTask, bind=True, max_retries=3)
async def extract_and_map_task(self, ehr_id: str) -> dict:
    """Extract entities and map to ontologies using LangGraph workflow.

    Args:
        ehr_id: EHR document ID

    Returns:
        dict with results
    """
    logger.info(f"Starting extract_and_map_task for EHR {ehr_id}")

    try:
        async with async_session_maker() as db:
            # Get EHR document
            result = await db.execute(
                select(EHRDocument).where(EHRDocument.ehr_id == UUID(ehr_id))
            )
            ehr_doc = result.scalar_one_or_none()

            if not ehr_doc:
                raise ValueError(f"EHR document {ehr_id} not found")

            # Update status
            ehr_doc.status = EHRDocumentStatus.PROCESSING
            await db.commit()

            # Run EHRToOntologyGraph workflow
            workflow_service = WorkflowService()
            workflow_result = await workflow_service.run_ehr_to_ontology_workflow(
                ehr_text=ehr_doc.raw_text,
                ehr_id=ehr_id,
            )

            # Extract results
            outputs = workflow_result.get("outputs", {})
            entities_data = outputs.get("ehr_entities", [])
            mappings_data = outputs.get("ehr_mappings", [])

            # Save normalized text
            ehr_doc.normalized_text = workflow_result.get("_current_ehr_text")

            # Save entities
            for entity_data in entities_data:
                entity = EHREntity(
                    ehr_id=UUID(ehr_id),
                    entity_type=entity_data.get("type", "UNKNOWN"),
                    text=entity_data.get("text", ""),
                    start_position=entity_data.get("start"),
                    end_position=entity_data.get("end"),
                    confidence=entity_data.get("confidence", 1.0),
                    section=entity_data.get("section"),
                    metadata_=entity_data,
                )
                db.add(entity)

            await db.flush()

            # Get entity ID mapping
            entities_result = await db.execute(
                select(EHREntity).where(EHREntity.ehr_id == UUID(ehr_id))
            )
            entities = list(entities_result.scalars().all())

            # Save mappings
            for mapping_data in mappings_data:
                # Find the entity by matching text or entity_id in metadata
                entity = None
                for e in entities:
                    if e.metadata_.get("entity_id") == mapping_data.get("entity_id"):
                        entity = e
                        break

                if entity:
                    mapping = EHRMapping(
                        ehr_id=UUID(ehr_id),
                        entity_id=entity.entity_id,
                        ontology=mapping_data.get("ontology", ""),
                        iri=mapping_data.get("iri", ""),
                        label=mapping_data.get("label", ""),
                        confidence=mapping_data.get("confidence", 1.0),
                        mapping_method=mapping_data.get("mapping_method", "automatic"),
                        evidence=mapping_data.get("evidence", {}),
                    )
                    db.add(mapping)

            # Update status
            execution = workflow_result.get("execution", {})
            if execution.get("status") == "completed":
                ehr_doc.status = EHRDocumentStatus.MAPPED
            elif execution.get("status") == "failed":
                ehr_doc.status = EHRDocumentStatus.FAILED
            else:
                ehr_doc.status = EHRDocumentStatus.ENTITIES_EXTRACTED

            ehr_doc.processing_metadata = {
                "execution": execution,
                "entity_count": len(entities_data),
                "mapping_count": len(mappings_data),
            }

            await db.commit()

            # Publish event
            try:
                publisher = create_event_publisher(settings.rabbitmq_url, settings.service_name)
                publisher.publish(
                    event_type=EventType.EHR_PROCESSED,
                    payload={
                        "ehr_id": ehr_id,
                        "case_id": str(ehr_doc.case_id),
                        "status": ehr_doc.status.value,
                        "entity_count": len(entities_data),
                        "mapping_count": len(mappings_data),
                    },
                    case_id=str(ehr_doc.case_id),
                )
            except Exception as e:
                logger.warning(f"Failed to publish event: {e}")

            logger.info(f"Completed extract_and_map_task for EHR {ehr_id}")

            return {
                "ehr_id": ehr_id,
                "status": ehr_doc.status.value,
                "entity_count": len(entities_data),
                "mapping_count": len(mappings_data),
            }

    except Exception as e:
        logger.error(f"Error in extract_and_map_task for EHR {ehr_id}: {e}", exc_info=True)

        # Update status to failed
        async with async_session_maker() as db:
            result = await db.execute(
                select(EHRDocument).where(EHRDocument.ehr_id == UUID(ehr_id))
            )
            ehr_doc = result.scalar_one_or_none()
            if ehr_doc:
                ehr_doc.status = EHRDocumentStatus.FAILED
                ehr_doc.processing_metadata = {
                    "error": str(e),
                    "task_id": self.request.id,
                }
                await db.commit()

        raise


@celery_app.task(base=AsyncTask, bind=True, max_retries=3)
async def generate_explanation_task(self, case_id: str, context: dict) -> dict:
    """Generate clinical explanation using ExplanationComposerGraph workflow.

    Args:
        case_id: Case ID
        context: Additional context for explanation generation

    Returns:
        dict with explanation results
    """
    logger.info(f"Starting generate_explanation_task for case {case_id}")

    try:
        # Run ExplanationComposerGraph workflow
        workflow_service = WorkflowService()
        workflow_result = await workflow_service.run_explanation_composer_workflow(
            case_id=case_id,
            context=context,
        )

        outputs = workflow_result.get("outputs", {})

        # Publish event
        try:
            publisher = create_event_publisher(settings.rabbitmq_url, settings.service_name)
            publisher.publish(
                event_type=EventType.EXPLANATION_GENERATED,
                payload={
                    "case_id": case_id,
                    "report_id": outputs.get("explanation_report_id"),
                    "report_uri": outputs.get("report_uri"),
                    "guardrails_passed": outputs.get("guardrails_passed"),
                },
                case_id=case_id,
            )
        except Exception as e:
            logger.warning(f"Failed to publish event: {e}")

        logger.info(f"Completed generate_explanation_task for case {case_id}")

        return {
            "case_id": case_id,
            "report_id": outputs.get("explanation_report_id"),
            "report_uri": outputs.get("report_uri"),
            "guardrails_passed": outputs.get("guardrails_passed"),
            "conflicts": outputs.get("conflicts", []),
        }

    except Exception as e:
        logger.error(f"Error in generate_explanation_task for case {case_id}: {e}", exc_info=True)
        raise
