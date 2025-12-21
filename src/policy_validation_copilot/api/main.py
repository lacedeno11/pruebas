"""
FastAPI application for Policy Validation Copilot.

Provides REST API for case validation operations.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from policy_validation_copilot.models.case import Case, CasePriority
from policy_validation_copilot.models.state import PolicyValidationState
from policy_validation_copilot.models.hitl import HITLResponse, HITLAnswer
from policy_validation_copilot.agents.workflow import PolicyValidationWorkflow
from policy_validation_copilot.utils.logging import setup_logging

logger = logging.getLogger(__name__)

# In-memory state store (in production, use Redis/DB)
_state_store: dict[str, PolicyValidationState] = {}
_workflow: Optional[PolicyValidationWorkflow] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global _workflow
    setup_logging()
    _workflow = PolicyValidationWorkflow()
    logger.info("Policy Validation Copilot API started")
    yield
    logger.info("Policy Validation Copilot API stopped")


app = FastAPI(
    title="Policy Validation Copilot API",
    description="DERCAS 01 - Cabina Aseguradoras Policy Validation Copilot (TO-BE)",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ValidationRequest(BaseModel):
    """Request to validate a case."""

    customer_id: str = Field(..., description="Customer identifier")
    contract_id: Optional[str] = Field(None, description="Contract reference")
    insurer_id: str = Field(..., description="Insurance company identifier")
    plan_id: str = Field(..., description="Insurance plan identifier")
    service_code: Optional[str] = Field(None, description="Service catalog code")
    service_description: Optional[str] = Field(None, description="Service description")
    service_date: Optional[str] = Field(None, description="Date of service (YYYY-MM-DD)")
    provider_id: Optional[str] = Field(None, description="Provider identifier")
    priority: str = Field(default="NORMAL", description="Priority: LOW, NORMAL, HIGH, URGENT")
    crm_ticket_id: Optional[str] = Field(None, description="External ticket reference")


class ValidationResponse(BaseModel):
    """Response from validation request."""

    case_id: str
    status: str
    decision_status: Optional[str] = None
    confidence_score: Optional[float] = None
    risk_level: Optional[float] = None
    hitl_required: bool = False
    explanation: Optional[str] = None
    next_actions: list[dict] = []


class HITLSubmitRequest(BaseModel):
    """Request to submit HITL response."""

    case_id: str
    decision: str = Field(..., description="APPROVE, REJECT, RETURN, ESCALATE")
    decision_notes: str = Field(..., description="Explanation of decision")
    answers: list[dict] = Field(default_factory=list, description="Answers to HITL questions")
    responded_by: str = Field(..., description="Reviewer user ID")


class CaseStatusResponse(BaseModel):
    """Response with case status."""

    case_id: str
    case_state: str
    workflow_status: str
    decision_status: Optional[str] = None
    hitl_required: bool = False
    hitl_request_id: Optional[str] = None
    created_at: str
    updated_at: str


# Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "policy-validation-copilot"}


@app.post("/api/v1/validate", response_model=ValidationResponse)
async def validate_case(
    request: ValidationRequest,
    background_tasks: BackgroundTasks,
):
    """
    Submit a case for validation.

    This endpoint creates a new case and starts the validation workflow.
    The workflow may complete synchronously or require HITL review.
    """
    from datetime import datetime

    # Create case from request
    case_id = f"CASE-{uuid4().hex[:8].upper()}"

    service_date = None
    if request.service_date:
        try:
            service_date = datetime.strptime(request.service_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(400, "Invalid service_date format. Use YYYY-MM-DD")

    case = Case(
        case_id=case_id,
        crm_ticket_id=request.crm_ticket_id,
        customer_id=request.customer_id,
        contract_id=request.contract_id,
        insurer_id=request.insurer_id,
        plan_id=request.plan_id,
        service_code=request.service_code,
        service_description=request.service_description,
        service_date=service_date,
        provider_id=request.provider_id,
        priority=CasePriority(request.priority.upper()),
        channel="API",
    )

    logger.info(f"Received validation request for case {case_id}")

    try:
        # Run validation workflow
        final_state = await _workflow.validate_case(case)

        # Store state
        _state_store[case_id] = final_state

        # Build response
        response = ValidationResponse(
            case_id=case_id,
            status=final_state.workflow_status,
            hitl_required=final_state.requires_hitl(),
        )

        if final_state.decision:
            response.decision_status = final_state.decision.status.value
            response.confidence_score = final_state.decision.confidence_score
            response.risk_level = final_state.decision.risk_level
            response.explanation = final_state.decision.explanation_summary
            response.next_actions = [
                action.model_dump() for action in final_state.decision.next_actions
            ]

        return response

    except Exception as e:
        logger.error(f"Validation failed for case {case_id}: {e}")
        raise HTTPException(500, f"Validation failed: {str(e)}")


@app.get("/api/v1/cases/{case_id}", response_model=CaseStatusResponse)
async def get_case_status(case_id: str):
    """
    Get current status of a case.
    """
    state = _state_store.get(case_id)
    if not state:
        raise HTTPException(404, f"Case {case_id} not found")

    return CaseStatusResponse(
        case_id=case_id,
        case_state=state.case.state.value if state.case else "UNKNOWN",
        workflow_status=state.workflow_status,
        decision_status=state.decision.status.value if state.decision else None,
        hitl_required=state.requires_hitl(),
        hitl_request_id=state.hitl_request.request_id if state.hitl_request else None,
        created_at=state.created_at.isoformat(),
        updated_at=state.updated_at.isoformat(),
    )


@app.get("/api/v1/cases/{case_id}/hitl")
async def get_hitl_request(case_id: str):
    """
    Get HITL request details for a case.
    """
    state = _state_store.get(case_id)
    if not state:
        raise HTTPException(404, f"Case {case_id} not found")

    if not state.hitl_request:
        raise HTTPException(404, f"No HITL request for case {case_id}")

    return state.hitl_request.model_dump()


@app.post("/api/v1/cases/{case_id}/hitl")
async def submit_hitl_response(case_id: str, request: HITLSubmitRequest):
    """
    Submit HITL response for a case.

    This endpoint processes the human reviewer's decision and resumes the workflow.
    """
    from datetime import datetime

    state = _state_store.get(case_id)
    if not state:
        raise HTTPException(404, f"Case {case_id} not found")

    if not state.hitl_request:
        raise HTTPException(400, f"No pending HITL request for case {case_id}")

    # Create HITL response
    hitl_response = HITLResponse(
        response_id=str(uuid4()),
        request_id=state.hitl_request.request_id,
        case_id=case_id,
        answers=[
            HITLAnswer(
                question_id=a.get("question_id", ""),
                answer_value=a.get("answer_value", ""),
                answer_notes=a.get("answer_notes"),
                answered_by=request.responded_by,
            )
            for a in request.answers
        ],
        decision=request.decision,
        decision_notes=request.decision_notes,
        responded_by=request.responded_by,
    )

    logger.info(f"Received HITL response for case {case_id}: {request.decision}")

    try:
        # Resume workflow with HITL response
        final_state = await _workflow.resume_after_hitl(state, hitl_response)

        # Update stored state
        _state_store[case_id] = final_state

        return {
            "case_id": case_id,
            "status": final_state.workflow_status,
            "decision_status": final_state.decision.status.value if final_state.decision else None,
        }

    except Exception as e:
        logger.error(f"Failed to process HITL response for case {case_id}: {e}")
        raise HTTPException(500, f"Failed to process HITL response: {str(e)}")


@app.get("/api/v1/cases/{case_id}/audit")
async def get_audit_trail(case_id: str):
    """
    Get audit trail for a case.
    """
    state = _state_store.get(case_id)
    if not state:
        raise HTTPException(404, f"Case {case_id} not found")

    return {
        "case_id": case_id,
        "node_executions": [
            {
                "node_name": e.node_name,
                "status": e.status,
                "duration_ms": e.duration_ms,
                "started_at": e.started_at.isoformat() if e.started_at else None,
            }
            for e in state.node_executions
        ],
        "guardrail_history": [
            {
                "checkpoint": g.checkpoint,
                "decision": g.decision.value,
                "flags_count": len(g.flags),
            }
            for g in state.guardrail_history
        ],
        "hitl_history": state.hitl_history,
        "errors": state.errors,
    }


@app.get("/api/v1/workflow/diagram")
async def get_workflow_diagram():
    """
    Get Mermaid diagram of the workflow.
    """
    try:
        diagram = _workflow.get_workflow_diagram()
        return {"diagram": diagram}
    except Exception as e:
        return {"error": str(e)}


def run():
    """Run the API server."""
    import uvicorn

    uvicorn.run(
        "policy_validation_copilot.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    run()
