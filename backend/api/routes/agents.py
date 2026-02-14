"""
Agent API routes for the PEI Platform.
Provides endpoints for invoking agents, retrieving logs, and triggering manual operations.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.models import LogAgente
from backend.models.log_agente import ActionResult
from backend.config import get_settings

# Note: PEIGraphRunner will be imported after agents are created
# from backend.agents.graph_runner import PEIGraphRunner

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/chat", response_model=dict)
async def chat_with_agent(
    user_input: dict,
    db: Session = Depends(get_db),
) -> dict:
    """
    Send user input to RouterAgent for intelligent routing and processing.

    This endpoint accepts user text input (and optionally voice input) and
    invokes the RouterAgent via PEIGraphRunner to:
    1. Classify user intent
    2. Route to appropriate agent (OTSAgent, PlanificacionAgent, GobernanzaAgent, ComunicacionAgent)
    3. Execute the agent's logic
    4. Return the agent's response

    Request Body:
        - message: User input text (required)
        - event_type: Optional event type (defaults to 'user_input')

    Returns:
        Dictionary containing:
        - response: Agent response message
        - action_result: Result of the action (SUCCESS, FAILURE, PENDING)
        - next_agent: Name of the agent that handled the request
        - logs: Related log entries for the operation

    Example requests:
        - "Download new OTs from TELCOS"
        - "Plan assignments for all unassigned OTs"
        - "Check for inactive or detained OTs"
        - "Send notifications to teams"

    TODO:
        - Integrate PEIGraphRunner once agents are created
        - Handle voice input conversion to text (optional)
        - Implement request/response validation schemas
    """
    # Extract message from request body
    message = user_input.get("message") if isinstance(user_input, dict) else None
    if not message:
        raise HTTPException(
            status_code=400,
            detail="message field is required in request body",
        )

    event_type = user_input.get("event_type", "user_input")

    # TODO: Implement PEIGraphRunner integration
    # graph_runner = PEIGraphRunner(get_settings())
    # initial_state = {
    #     "user_input": message,
    #     "event_type": event_type,
    #     "ot_data": {},
    #     "current_ot_id": None,
    #     "cuadrilla_id": None,
    #     "action_result": "",
    #     "error_message": None,
    #     "agent_logs": [],
    #     "next_agent": None,
    # }
    # final_state = await graph_runner.run_graph(initial_state)

    # Placeholder response
    return {
        "response": f"Received message: {message}",
        "action_result": "PENDING",
        "next_agent": "router",
        "logs": [],
    }


@router.get("/logs", response_model=List[dict])
async def get_agent_logs(
    db: Session = Depends(get_db),
    agente_name: Optional[str] = Query(None, description="Filter by agent name"),
    ot_id: Optional[int] = Query(None, description="Filter by OT ID"),
    resultado: Optional[str] = Query(None, description="Filter by result status"),
    start_date: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    limit: int = Query(100, description="Maximum number of logs to return"),
) -> List[dict]:
    """
    Retrieve agent execution logs with optional filtering.

    This endpoint queries the LogAgente table to retrieve historical records of
    agent actions for auditing, debugging, and monitoring purposes.

    Query Parameters:
        - agente_name: Filter by agent name (e.g., 'OTSAgent', 'PlanificacionAgent')
        - ot_id: Filter by associated OT ID
        - resultado: Filter by result status (SUCCESS, FAILURE, PENDING)
        - start_date: Filter logs from this date (YYYY-MM-DD format)
        - end_date: Filter logs until this date (YYYY-MM-DD format)
        - limit: Maximum number of logs to return (default: 100, max: 1000)

    Returns:
        List of log entries with fields:
        - id: Log entry ID
        - ot_id: Associated OT ID (if applicable)
        - agente_name: Name of the agent
        - accion: Description of the action
        - resultado: Result status (SUCCESS, FAILURE, PENDING)
        - raw_llm_response: Raw LLM response (if applicable)
        - metadata: Additional metadata as JSON
        - created_at: Timestamp of the log entry

    Example filters:
        - GET /api/agents/logs?agente_name=OTSAgent
        - GET /api/agents/logs?resultado=FAILURE
        - GET /api/agents/logs?ot_id=123
        - GET /api/agents/logs?start_date=2024-01-01&end_date=2024-01-31
    """
    # Validate limit
    if limit > 1000:
        limit = 1000
    if limit < 1:
        limit = 1

    # Build query
    query = db.query(LogAgente)

    # Apply filters
    if agente_name:
        query = query.filter(LogAgente.agente_name.ilike(f"%{agente_name}%"))

    if ot_id is not None:
        query = query.filter(LogAgente.ot_id == ot_id)

    if resultado:
        try:
            query = query.filter(LogAgente.resultado == ActionResult[resultado.upper()])
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid resultado: {resultado}. Must be SUCCESS, FAILURE, or PENDING",
            )

    # Parse and apply date filters
    if start_date:
        try:
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(LogAgente.created_at >= start_datetime)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="start_date must be in YYYY-MM-DD format",
            )

    if end_date:
        try:
            end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(LogAgente.created_at < end_datetime)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="end_date must be in YYYY-MM-DD format",
            )

    # Order by most recent first and apply limit
    logs = query.order_by(LogAgente.created_at.desc()).limit(limit).all()

    # Convert to dictionary format
    return [
        {
            "id": log.id,
            "ot_id": log.ot_id,
            "agente_name": log.agente_name,
            "accion": log.accion,
            "resultado": log.resultado.value if log.resultado else None,
            "raw_llm_response": log.raw_llm_response,
            "metadata": log.metadata,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.post("/plan", response_model=dict)
async def trigger_manual_plan(
    plan_data: dict,
    db: Session = Depends(get_db),
) -> dict:
    """
    Manually trigger Planificación Agent to plan OT assignments.

    This endpoint invokes the PlanificacionAgent via PEIGraphRunner to execute
    the 3-phase planning algorithm for OT assignments:
    - PHASE 1: Balance assignments (1 OT per cuadrilla)
    - PHASE 2: Proximity-based assignment (<10km from centroid)
    - PHASE 3: Recalculate centroids for next day optimization

    Request Body (optional):
        - ot_ids: List of specific OT IDs to plan (optional)
                 If not provided, plans all unassigned OTs
        - force_replan: Boolean to force replan even assigned OTs (default: false)

    Returns:
        Dictionary containing:
        - status: Operation status
        - message: Description of planning operation
        - ots_planned: Number of OTs planned/assigned
        - assignments: List of assignment details
        - cuadrillas_updated: Number of cuadrillas with updated centroids

    Examples:
        - POST /api/agents/plan {} (plans all unassigned OTs)
        - POST /api/agents/plan {"ot_ids": [1, 2, 3]} (plans specific OTs)
        - POST /api/agents/plan {"force_replan": true} (replans all OTs)

    TODO:
        - Integrate PEIGraphRunner once agents are created
        - Implement specific OT ID filtering
        - Handle force_replan flag logic
        - Return detailed assignment information
    """
    ot_ids = plan_data.get("ot_ids") if isinstance(plan_data, dict) else None
    force_replan = plan_data.get("force_replan", False) if isinstance(plan_data, dict) else False

    # TODO: Implement PEIGraphRunner integration
    # graph_runner = PEIGraphRunner(get_settings())
    # initial_state = {
    #     "user_input": "",
    #     "event_type": "manual_plan",
    #     "ot_data": {"ot_ids": ot_ids, "force_replan": force_replan},
    #     "current_ot_id": None,
    #     "cuadrilla_id": None,
    #     "action_result": "",
    #     "error_message": None,
    #     "agent_logs": [],
    #     "next_agent": "planificacion",
    # }
    # final_state = await graph_runner.run_graph(initial_state)

    # Placeholder response
    return {
        "status": "plan_initiated",
        "message": "Planificación Agent invoked to plan OT assignments",
        "ots_planned": 0,
        "assignments": [],
        "cuadrillas_updated": 0,
    }


@router.post("/govern", response_model=dict)
async def trigger_governance_check(
    db: Session = Depends(get_db),
) -> dict:
    """
    Manually trigger Gobernanza Agent to check and enforce business rules.

    This endpoint invokes the GobernanzaAgent via PEIGraphRunner to perform
    governance operations:
    1. Check for inactive OTs (PREPLANIFICADA > 48 hours)
    2. Check for OTs in detention (DETENIDA status)
    3. Send alerts on specific days (20, 25, 29)
    4. Auto-cancel OTs after 30 days in DETENIDA status
    5. Validate PUBLICO project document completion
    6. Generate alerts and notifications

    Request Body: None required

    Returns:
        Dictionary containing:
        - status: Operation status
        - message: Description of governance check
        - inactivity_alerts: Number of inactivity alerts sent
        - detention_alerts: Number of detention alerts sent
        - auto_cancellations: Number of OTs auto-cancelled
        - document_warnings: Number of document validation warnings

    Example:
        - POST /api/agents/govern (runs full governance check)

    TODO:
        - Integrate PEIGraphRunner once agents are created
        - Implement alert generation and notification
        - Handle document validation for PUBLICO projects
        - Implement auto-cancellation logic
    """
    # TODO: Implement PEIGraphRunner integration
    # graph_runner = PEIGraphRunner(get_settings())
    # initial_state = {
    #     "user_input": "",
    #     "event_type": "manual_governance",
    #     "ot_data": {},
    #     "current_ot_id": None,
    #     "cuadrilla_id": None,
    #     "action_result": "",
    #     "error_message": None,
    #     "agent_logs": [],
    #     "next_agent": "gobernanza",
    # }
    # final_state = await graph_runner.run_graph(initial_state)

    # Placeholder response
    return {
        "status": "governance_check_initiated",
        "message": "Gobernanza Agent invoked to check and enforce business rules",
        "inactivity_alerts": 0,
        "detention_alerts": 0,
        "auto_cancellations": 0,
        "document_warnings": 0,
    }

