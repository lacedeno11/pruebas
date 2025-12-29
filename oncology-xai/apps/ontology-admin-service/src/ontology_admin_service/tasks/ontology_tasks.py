"""Celery tasks for ontology operations."""

import logging
from uuid import UUID

from celery import Task
from sqlalchemy import select

from ontology_admin_service.tasks.celery_app import celery_app
from ontology_admin_service.database import async_session_maker
from ontology_admin_service.models import OntologyUpdateProposal, ProposalStatus
from ontology_admin_service.services.ontology_service import OntologyService
from ontology_admin_service.services.event_publisher import event_publisher
from langgraph_workflows.graphs.ontology_update import create_ontology_update_graph
from langgraph_workflows.state import GraphState

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session."""

    _session = None

    @property
    def session(self):
        if self._session is None:
            self._session = async_session_maker()
        return self._session


@celery_app.task(name="ontology_admin_service.run_ontology_workflow", bind=True)
def run_ontology_workflow(self, proposal_id: str):
    """Run the OntologyUpdateWorkflow LangGraph for a proposal."""
    import asyncio

    async def _run():
        async with async_session_maker() as session:
            try:
                # Get proposal
                result = await session.execute(
                    select(OntologyUpdateProposal).where(
                        OntologyUpdateProposal.proposal_id == UUID(proposal_id)
                    )
                )
                proposal = result.scalar_one_or_none()

                if not proposal:
                    logger.error(f"Proposal {proposal_id} not found")
                    return {"error": "Proposal not found"}

                # Update status
                proposal.status = ProposalStatus.VALIDATING
                await session.commit()

                # Create workflow
                workflow = create_ontology_update_graph()

                # Prepare initial state
                initial_state: GraphState = {
                    "execution_id": f"exec_{proposal_id}",
                    "inputs": {
                        "ontology_targets": proposal.ontology_sources,
                        "mode": proposal.mode,
                    },
                    "execution": {
                        "status": "running",
                        "progress": 0.0,
                        "current_node": None,
                        "error": None,
                    },
                    "outputs": {},
                    "_intermediate_results": {},
                    "identity": {
                        "user_id": proposal.created_by,
                    },
                }

                # Run workflow
                logger.info(f"Starting workflow for proposal {proposal_id}")
                final_state = await workflow.ainvoke(initial_state)

                # Update proposal with results
                proposal.workflow_execution_id = final_state.get("execution_id")
                proposal.diff_summary = final_state.get("_intermediate_results", {}).get("diff", {})
                proposal.impact_analysis = final_state.get("_intermediate_results", {}).get("impact", {})
                proposal.reasoner_results = final_state.get("_intermediate_results", {}).get("reasoner_results", {})

                # Extract ontology data for validation
                uploaded_files = proposal.uploaded_files or {}
                ontology_data = final_state.get("_intermediate_results", {}).get("ontology_data", {})
                uploaded_files["ontology_data"] = ontology_data
                proposal.uploaded_files = uploaded_files

                # Check execution status
                execution_status = final_state.get("execution", {}).get("status")
                if execution_status == "failed":
                    proposal.status = ProposalStatus.REQUIRES_FIX
                    error = final_state.get("execution", {}).get("error", {})
                    proposal.validation_errors = [error]
                elif execution_status == "completed":
                    # Check if auto-approved
                    approved = final_state.get("_intermediate_results", {}).get("approved", False)
                    if approved:
                        proposal.status = ProposalStatus.VALIDATED
                    else:
                        proposal.status = ProposalStatus.PENDING_APPROVAL

                await session.commit()

                # Publish event
                event_publisher.publish_proposal_validated(
                    UUID(proposal_id),
                    proposal.status.value,
                    len(proposal.validation_errors) > 0,
                )

                logger.info(
                    f"Workflow completed for proposal {proposal_id}. Status: {proposal.status}"
                )

                return {
                    "proposal_id": proposal_id,
                    "status": proposal.status.value,
                    "execution_status": execution_status,
                }

            except Exception as e:
                logger.error(f"Error running workflow for proposal {proposal_id}: {e}")
                await session.rollback()
                raise

    return asyncio.run(_run())


@celery_app.task(name="ontology_admin_service.run_validation_task")
def run_validation_task(proposal_id: str):
    """Run reasoner validation on a proposal."""
    import asyncio

    async def _run():
        async with async_session_maker() as session:
            try:
                service = OntologyService(session)
                result = await service.run_validation(UUID(proposal_id))

                # Publish event
                event_publisher.publish_proposal_validated(
                    UUID(proposal_id),
                    result["status"],
                    len(result["errors"]) > 0,
                )

                await session.commit()

                return result

            except Exception as e:
                logger.error(f"Error validating proposal {proposal_id}: {e}")
                await session.rollback()
                raise

    return asyncio.run(_run())


@celery_app.task(name="ontology_admin_service.publish_ontology_task")
def publish_ontology_task(proposal_id: str, approved_by: str, approval_notes: str | None = None):
    """Publish an approved ontology proposal."""
    import asyncio

    async def _run():
        async with async_session_maker() as session:
            try:
                service = OntologyService(session)
                result = await service.approve_and_publish(
                    UUID(proposal_id),
                    approved_by,
                    approval_notes,
                )

                # Publish events for each created version
                for version in result["created_versions"]:
                    event_publisher.publish_ontology_published(
                        UUID(version["version_id"]),
                        version["source"],
                        version["version_tag"],
                    )

                await session.commit()

                return result

            except Exception as e:
                logger.error(f"Error publishing proposal {proposal_id}: {e}")
                await session.rollback()
                raise

    return asyncio.run(_run())
