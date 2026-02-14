"""
Agent API endpoints for PEI Platform.

Provides REST API endpoints for agent interactions:
- Execute agent workflows
- Trigger planning for specific OTs
- Query agent action logs
- Validate OT status transitions
- WebSocket chat interface for real-time agent interaction
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import AgentLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


# Pydantic schemas for request/response
from pydantic import BaseModel
from typing import List


class ExecuteRequest(BaseModel):
    """Request schema for executing agent workflow"""

    input: str
    config: Optional[dict] = None


class ExecuteResponse(BaseModel):
    """Response schema for agent execution"""

    success: bool
    status: str
    data: Optional[dict] = None
    error: Optional[str] = None


class PlanRequest(BaseModel):
    """Request schema for planning trigger"""

    ot_ids: Optional[List[int]] = None
    strategy: str = "balanced"  # balanced, proximity, or nightly


class AgentLogResponse(BaseModel):
    """Response schema for agent log"""

    id: int
    ot_id: Optional[int] = None
    agent_name: str
    accion: str
    resultado: str
    timestamp: datetime
    metadata: Optional[dict] = None

    class Config:
        from_attributes = True


class AgentLogListResponse(BaseModel):
    """Response schema for agent log list"""

    total: int
    page: int
    page_size: int
    data: List[AgentLogResponse]


class ValidateTransitionRequest(BaseModel):
    """Request schema for transition validation"""

    ot_id: int
    new_status: str
    reason: Optional[str] = None


class ValidateTransitionResponse(BaseModel):
    """Response schema for transition validation"""

    valid: bool
    message: str
    errors: Optional[List[str]] = None


@router.post("/execute", response_model=ExecuteResponse)
async def execute_agent(
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
) -> ExecuteResponse:
    """
    Execute agent workflow with user input.

    This endpoint:
    1. Accepts user input (e.g., "Plan OTs for DataLegal project")
    2. Calls PEIAgentExecutor.execute() with the input
    3. Routes to appropriate agent(s) via RouterAgent
    4. Returns final state with results

    Request Body:
    - input: User command or question
    - config: Optional configuration dict for execution

    Returns:
        ExecuteResponse: Execution status and results

    Example:
        POST /api/agents/execute
        {
            "input": "Plan all OTs for project PUBLICO",
            "config": {"verbose": true}
        }
    """
    try:
        logger.info(f"Agent execution requested: {request.input[:100]}")

        # TODO: Integrate with PEIAgentExecutor
        # from src.agents.executor import PEIAgentExecutor
        # executor = PEIAgentExecutor()
        # state = await executor.execute(request.input, db, request.config)

        # For now, return placeholder response
        return ExecuteResponse(
            success=True,
            status="scheduled",
            data={
                "message": "Agent execution scheduled",
                "input": request.input,
            },
        )

    except Exception as e:
        logger.error(f"Error executing agent: {str(e)}")
        return ExecuteResponse(
            success=False,
            status="error",
            error=str(e),
        )


@router.post("/plan", response_model=ExecuteResponse)
async def trigger_planning(
    request: PlanRequest,
    db: AsyncSession = Depends(get_db),
) -> ExecuteResponse:
    """
    Trigger PlanificacionAgent for specific OTs or all OTs.

    This endpoint initiates the planning workflow to assign OTs to cuadrillas
    using the 3-phase algorithm (balance → proximity → nightly normalization).

    Request Body:
    - ot_ids: List of OT IDs to plan (optional, if not provided, plans all PREPLANIFICADA OTs)
    - strategy: Planning strategy (balanced, proximity, or nightly)

    Returns:
        ExecuteResponse: Planning execution status

    Example:
        POST /api/agents/plan
        {
            "ot_ids": [1, 2, 3],
            "strategy": "balanced"
        }
    """
    try:
        logger.info(f"Planning triggered for OT IDs: {request.ot_ids or 'all'}")

        # TODO: Integrate with PEIAgentExecutor
        # executor = PEIAgentExecutor()
        # state = await executor.execute(f"plan_ots:{request.strategy}", db)

        return ExecuteResponse(
            success=True,
            status="scheduled",
            data={
                "message": "Planning job scheduled",
                "ot_count": len(request.ot_ids) if request.ot_ids else "all",
                "strategy": request.strategy,
            },
        )

    except Exception as e:
        logger.error(f"Error triggering planning: {str(e)}")
        return ExecuteResponse(
            success=False,
            status="error",
            error=str(e),
        )


@router.get("/logs", response_model=AgentLogListResponse)
async def get_agent_logs(
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    resultado: Optional[str] = Query(None, description="Filter by resultado (SUCCESS/FAILURE/WARNING)"),
    ot_id: Optional[int] = Query(None, description="Filter by OT ID"),
    days_back: int = Query(7, ge=1, le=90, description="Days of logs to retrieve"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> AgentLogListResponse:
    """
    Query agent action logs with filtering and pagination.

    Query Parameters:
    - agent_name: Filter by agent name (RouterAgent, OTSAgent, etc.)
    - resultado: Filter by result (SUCCESS, FAILURE, WARNING)
    - ot_id: Filter by associated OT ID
    - days_back: Retrieve logs from last N days (default: 7)
    - page: Page number
    - page_size: Items per page

    Returns:
        AgentLogListResponse: Paginated list of agent logs

    Example:
        GET /api/agents/logs?agent_name=OTSAgent&resultado=SUCCESS&page=1
    """
    try:
        # Build query
        query = select(AgentLog)

        # Apply filters
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        query = query.where(AgentLog.timestamp >= cutoff_date)

        if agent_name:
            query = query.where(AgentLog.agent_name == agent_name)

        if resultado:
            query = query.where(AgentLog.resultado == resultado)

        if ot_id:
            query = query.where(AgentLog.ot_id == ot_id)

        # Get total count
        count_result = await db.execute(
            select(AgentLog).where(AgentLog.timestamp >= cutoff_date)
        )
        total = len(count_result.scalars().all())

        # Apply sorting and pagination
        offset = (page - 1) * page_size
        query = (
            query.order_by(AgentLog.timestamp.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await db.execute(query)
        logs = result.scalars().all()

        log_responses = [AgentLogResponse.from_orm(log) for log in logs]

        logger.info(
            f"Retrieved {len(logs)} agent logs "
            f"(filters: agent={agent_name}, resultado={resultado}, ot={ot_id})"
        )
        return AgentLogListResponse(
            total=total,
            page=page,
            page_size=page_size,
            data=log_responses,
        )

    except Exception as e:
        logger.error(f"Error retrieving agent logs: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving agent logs")


@router.post("/validate-transition", response_model=ValidateTransitionResponse)
async def validate_transition(
    request: ValidateTransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> ValidateTransitionResponse:
    """
    Validate OT status transition before allowing it (for drag & drop).

    This endpoint is called before allowing a user to move an OT to a new status
    in the Kanban board. It validates the transition using business rules.

    Request Body:
    - ot_id: OT ID to validate
    - new_status: Target status
    - reason: Optional reason (required for DETENIDA status)

    Returns:
        ValidateTransitionResponse: Validation result with any error messages

    Example:
        POST /api/agents/validate-transition
        {
            "ot_id": 1,
            "new_status": "DETENIDA",
            "reason": "Awaiting equipment delivery"
        }
    """
    try:
        logger.info(f"Validating transition for OT {request.ot_id} to {request.new_status}")

        # TODO: Integrate with GobernanzaAgent.validate_transition()
        # from src.agents.gobernanza_agent import GobernanzaAgent
        # agent = GobernanzaAgent(db)
        # is_valid, errors = await agent.validate_transition(request.ot_id, request.new_status)

        # For now, return placeholder validation
        errors = []

        # Basic validations
        if request.new_status == "DETENIDA" and not request.reason:
            errors.append("Detention reason is required")

        valid = len(errors) == 0

        return ValidateTransitionResponse(
            valid=valid,
            message="Transition is valid" if valid else "Transition validation failed",
            errors=errors if errors else None,
        )

    except Exception as e:
        logger.error(f"Error validating transition: {str(e)}")
        return ValidateTransitionResponse(
            valid=False,
            message="Error validating transition",
            errors=[str(e)],
        )


# WebSocket connection manager for chat
class ConnectionManager:
    """Manages WebSocket connections for real-time chat"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, data: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {str(e)}")


manager = ConnectionManager()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time agent chat.

    Provides bidirectional communication with agent for interactive queries.
    The agent processes messages asynchronously and sends back responses.

    Client → Server: {"type": "message", "content": "user input"}
    Server → Client: {"type": "response", "content": "agent response", "timestamp": "..."}

    Example usage in frontend:
        const ws = new WebSocket('ws://localhost:8000/api/agents/ws/chat');
        ws.onopen = () => {
            ws.send(JSON.stringify({
                type: "message",
                content: "Plan OTs for project PUBLICO"
            }));
        };
        ws.onmessage = (event) => {
            const response = JSON.parse(event.data);
            console.log("Agent:", response.content);
        };
    """
    await manager.connect(websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)

            logger.info(f"WebSocket message received: {message_data.get('content', '')[:100]}")

            # Process message
            if message_data.get("type") == "message":
                user_input = message_data.get("content", "")

                # TODO: Integrate with PEIAgentExecutor for real processing
                # executor = PEIAgentExecutor()
                # state = await executor.execute(user_input, db)

                # For now, send placeholder response
                response = {
                    "type": "response",
                    "content": f"Agent received: {user_input}",
                    "timestamp": datetime.utcnow().isoformat(),
                }

                await websocket.send_json(response)

            elif message_data.get("type") == "ping":
                # Heartbeat
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON received on WebSocket: {str(e)}")
        await websocket.send_json({"error": "Invalid JSON"})

    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket)

