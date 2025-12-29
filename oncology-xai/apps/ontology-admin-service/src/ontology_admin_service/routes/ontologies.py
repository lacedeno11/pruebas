"""Ontology admin API routes."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ontology_admin_service.database import get_db
from ontology_admin_service.models import ProposalStatus
from ontology_admin_service.services.ontology_service import OntologyService
from ontology_admin_service.services.event_publisher import event_publisher
from ontology_admin_service.tasks.ontology_tasks import (
    run_ontology_workflow,
    run_validation_task,
    publish_ontology_task,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ontology Admin"])


# Request/Response Models
class OntologyVersionResponse(BaseModel):
    """Ontology version response."""
    version_id: str = Field(alias="versionId")
    ontology_source: str = Field(alias="ontologySource")
    version_tag: str = Field(alias="versionTag")
    content_hash: str = Field(alias="contentHash")
    statistics: dict[str, Any]
    is_active: bool = Field(alias="isActive")
    published_by: str | None = Field(alias="publishedBy")
    published_at: str = Field(alias="publishedAt")
    metadata: dict[str, Any] | None = None

    class Config:
        populate_by_name = True


class CreateUpdateProposalRequest(BaseModel):
    """Create update proposal request."""
    ontology_sources: list[str] = Field(alias="ontologySources")
    mode: str  # online or offline
    uploaded_files: dict[str, Any] | None = Field(None, alias="uploadedFiles")
    created_by: str | None = Field(None, alias="createdBy")

    class Config:
        populate_by_name = True


class ProposalResponse(BaseModel):
    """Proposal response."""
    proposal_id: str = Field(alias="proposalId")
    ontology_sources: list[str] = Field(alias="ontologySources")
    mode: str
    status: str
    workflow_execution_id: str | None = Field(None, alias="workflowExecutionId")
    diff_summary: dict[str, Any] = Field(alias="diffSummary")
    impact_analysis: dict[str, Any] = Field(alias="impactAnalysis")
    reasoner_results: dict[str, Any] = Field(alias="reasonerResults")
    validation_errors: list[dict] = Field(alias="validationErrors")
    approval_notes: str | None = Field(None, alias="approvalNotes")
    created_by: str | None = Field(None, alias="createdBy")
    created_at: str = Field(alias="createdAt")
    approved_by: str | None = Field(None, alias="approvedBy")
    approved_at: str | None = Field(None, alias="approvedAt")

    class Config:
        populate_by_name = True


class ApproveProposalRequest(BaseModel):
    """Approve proposal request."""
    approved_by: str = Field(alias="approvedBy")
    approval_notes: str | None = Field(None, alias="approvalNotes")

    class Config:
        populate_by_name = True


class RollbackRequest(BaseModel):
    """Rollback request."""
    to_version_id: str | None = Field(None, alias="toVersionId")
    created_by: str = Field(alias="createdBy")

    class Config:
        populate_by_name = True


class TaskResponse(BaseModel):
    """Async task response."""
    task_id: str = Field(alias="taskId")
    status: str
    message: str

    class Config:
        populate_by_name = True


# Endpoints
@router.get(
    "/api/v1/admin/ontologies",
    response_model=list[OntologyVersionResponse],
    summary="List active ontology versions",
)
async def list_ontologies(
    db: AsyncSession = Depends(get_db),
):
    """List all active ontology versions."""
    service = OntologyService(db)
    versions = await service.list_active_ontologies()

    return [
        OntologyVersionResponse(
            versionId=str(v.version_id),
            ontologySource=v.ontology_source,
            versionTag=v.version_tag,
            contentHash=v.content_hash,
            statistics=v.statistics,
            isActive=v.is_active,
            publishedBy=v.published_by,
            publishedAt=v.published_at.isoformat(),
            metadata=v.metadata_,
        )
        for v in versions
    ]


@router.post(
    "/api/v1/admin/ontologies:update-proposal",
    response_model=ProposalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create ontology update proposal",
)
async def create_update_proposal(
    request: CreateUpdateProposalRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create a new ontology update proposal and optionally trigger workflow."""
    try:
        service = OntologyService(db)

        proposal = await service.create_update_proposal(
            ontology_sources=request.ontology_sources,
            mode=request.mode,
            created_by=request.created_by,
            uploaded_files=request.uploaded_files,
        )

        await db.commit()
        await db.refresh(proposal)

        # Publish event
        event_publisher.publish_proposal_created(
            proposal.proposal_id,
            proposal.ontology_sources,
        )

        # Trigger workflow in background
        if request.mode == "online":
            background_tasks.add_task(
                run_ontology_workflow.delay,
                str(proposal.proposal_id),
            )

        return ProposalResponse(
            proposalId=str(proposal.proposal_id),
            ontologySources=proposal.ontology_sources,
            mode=proposal.mode,
            status=proposal.status.value,
            workflowExecutionId=proposal.workflow_execution_id,
            diffSummary=proposal.diff_summary,
            impactAnalysis=proposal.impact_analysis,
            reasonerResults=proposal.reasoner_results,
            validationErrors=proposal.validation_errors,
            approvalNotes=proposal.approval_notes,
            createdBy=proposal.created_by,
            createdAt=proposal.created_at.isoformat(),
            approvedBy=proposal.approved_by,
            approvedAt=proposal.approved_at.isoformat() if proposal.approved_at else None,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/api/v1/admin/ontologies/proposals/{proposal_id}",
    response_model=ProposalResponse,
    summary="Get proposal details",
)
async def get_proposal(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific proposal."""
    service = OntologyService(db)
    proposal = await service.get_proposal(proposal_id)

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        )

    return ProposalResponse(
        proposalId=str(proposal.proposal_id),
        ontologySources=proposal.ontology_sources,
        mode=proposal.mode,
        status=proposal.status.value,
        workflowExecutionId=proposal.workflow_execution_id,
        diffSummary=proposal.diff_summary,
        impactAnalysis=proposal.impact_analysis,
        reasonerResults=proposal.reasoner_results,
        validationErrors=proposal.validation_errors,
        approvalNotes=proposal.approval_notes,
        createdBy=proposal.created_by,
        createdAt=proposal.created_at.isoformat(),
        approvedBy=proposal.approved_by,
        approvedAt=proposal.approved_at.isoformat() if proposal.approved_at else None,
    )


@router.post(
    "/api/v1/admin/ontologies/proposals/{proposal_id}:run-validation",
    response_model=TaskResponse,
    summary="Run reasoner validation on proposal",
)
async def run_validation(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Trigger reasoner validation for a proposal."""
    service = OntologyService(db)
    proposal = await service.get_proposal(proposal_id)

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        )

    # Check status
    if proposal.status not in [ProposalStatus.DRAFT, ProposalStatus.REQUIRES_FIX]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot validate proposal in status {proposal.status}",
        )

    # Trigger validation task
    task = run_validation_task.delay(str(proposal_id))

    return TaskResponse(
        taskId=task.id,
        status="PENDING",
        message=f"Validation task started for proposal {proposal_id}",
    )


@router.post(
    "/api/v1/admin/ontologies/proposals/{proposal_id}:approve-and-publish",
    response_model=TaskResponse,
    summary="Approve and publish proposal",
)
async def approve_and_publish(
    proposal_id: UUID,
    request: ApproveProposalRequest,
    db: AsyncSession = Depends(get_db),
):
    """Approve and publish an ontology proposal."""
    service = OntologyService(db)
    proposal = await service.get_proposal(proposal_id)

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        )

    # Check status
    if proposal.status not in [ProposalStatus.VALIDATED, ProposalStatus.PENDING_APPROVAL]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve proposal in status {proposal.status}. "
                   "Must be VALIDATED or PENDING_APPROVAL",
        )

    # Trigger publish task
    task = publish_ontology_task.delay(
        str(proposal_id),
        request.approved_by,
        request.approval_notes,
    )

    return TaskResponse(
        taskId=task.id,
        status="PENDING",
        message=f"Publish task started for proposal {proposal_id}",
    )


@router.post(
    "/api/v1/admin/ontologies/proposals/{proposal_id}:rollback",
    response_model=dict[str, Any],
    summary="Rollback to previous version",
)
async def rollback_version(
    proposal_id: UUID,
    request: RollbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rollback ontology to a previous version."""
    try:
        service = OntologyService(db)

        # Get the proposal to find the version
        proposal = await service.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proposal {proposal_id} not found",
            )

        if not proposal.created_version_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Proposal has no associated version to rollback",
            )

        to_version_id = UUID(request.to_version_id) if request.to_version_id else None

        result = await service.rollback_version(
            from_version_id=proposal.created_version_id,
            to_version_id=to_version_id,
            created_by=request.created_by,
        )

        await db.commit()

        # Publish rollback event
        event_publisher.publish_ontology_rolled_back(
            UUID(result["rollback_from"]["version_id"]),
            UUID(result["rollback_to"]["version_id"]),
            proposal.ontology_sources[0],
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
