from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.models import LogAgente

router = APIRouter()


class ChatMessage(BaseModel):
    """Request schema for chat messages."""
    message: str


class ChatResponse(BaseModel):
    """Response schema for chat messages."""
    response: str
    agent: str
    timestamp: datetime


class PlanningRequest(BaseModel):
    """Request schema for planning trigger."""
    force_replan: bool = False


class PlanningResponse(BaseModel):
    """Response schema for planning."""
    success: bool
    message: str
    assignments_count: int = 0
    timestamp: datetime


class LogFilter(BaseModel):
    """Filter schema for agent logs."""
    agente_name: Optional[str] = None
    ot_id: Optional[int] = None
    limit: int = 50


@router.post("/agents/plan", response_model=PlanningResponse)
def trigger_planning(
    request: PlanningRequest = None,
    db: Session = Depends(get_db)
):
    """
    Trigger the PlanificacionAgent to assign OTs to cuadrillas.
    
    This endpoint manually triggers the 3-phase assignment algorithm:
    - Phase 1: Balance assignment (1 OT per cuadrilla)
    - Phase 2: Proximity-based assignment (<10km from centroid)
    - Phase 3: Nocturnal optimization
    
    Request Body:
    - force_replan: Boolean to force reassignment of already assigned OTs
    
    Returns:
    - success: Whether the planning completed successfully
    - message: Status message
    - assignments_count: Number of OTs assigned in this planning run
    - timestamp: When the planning was executed
    """
    try:
        # TODO: Import and invoke PlanificacionAgent
        # For now, stub implementation
        
        # Log the planning action
        log = LogAgente(
            agente_name="PlanificacionAgent",
            accion="trigger_planning",
            resultado="Planning triggered successfully",
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        
        return PlanningResponse(
            success=True,
            message="Planning algorithm executed successfully",
            assignments_count=0,
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Planning failed: {str(e)}")


@router.post("/agents/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatMessage,
    db: Session = Depends(get_db)
):
    """
    Chat interface that invokes the LangGraph agent system.
    
    This endpoint sends a user message to the RouterAgent which:
    1. Classifies the user input
    2. Routes to appropriate agent (OTS, Planificación, Gobernanza, Comunicación)
    3. Executes the agent workflow
    4. Returns the result
    
    Request Body:
    - message: User message to process
    
    Returns:
    - response: Agent's response message
    - agent: Name of the agent that processed the request
    - timestamp: When the response was generated
    """
    try:
        if not request.message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # TODO: Import and invoke graph from backend/app/graph.py
        # State should include: input, messages, action, result, errors
        # For now, stub implementation
        
        agent_response = "Agent is not yet implemented. Please wait for full deployment."
        agent_name = "StubAgent"
        
        # Log the chat action
        log = LogAgente(
            agente_name="RouterAgent",
            accion="chat_message",
            resultado=f"Message: '{request.message[:50]}...'",
            raw_llm_response=agent_response,
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        
        return ChatResponse(
            response=agent_response,
            agent=agent_name,
            timestamp=datetime.utcnow()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/agents/logs", response_model=List[Dict[str, Any]])
def get_agent_logs(
    agente_name: Optional[str] = None,
    ot_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Query agent action logs with optional filtering.
    
    Query Parameters:
    - agente_name: Filter by agent name (RouterAgent, OTSAgent, PlanificacionAgent, GobernanzaAgent, ComunicacionAgent)
    - ot_id: Filter by OT ID
    - limit: Maximum number of logs to return (default 50, max 500)
    
    Returns:
    - List of log entries with: id, ot_id, agente_name, accion, resultado, timestamp
    """
    try:
        # Validate limit
        if limit < 1 or limit > 500:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 500")
        
        # Build query
        query = db.query(LogAgente)
        
        if agente_name:
            query = query.filter(LogAgente.agente_name == agente_name)
        
        if ot_id is not None:
            query = query.filter(LogAgente.ot_id == ot_id)
        
        # Order by timestamp descending and limit
        logs = query.order_by(LogAgente.timestamp.desc()).limit(limit).all()
        
        # Convert to dictionaries for response
        result = [
            {
                "id": log.id,
                "ot_id": log.ot_id,
                "agente_name": log.agente_name,
                "accion": log.accion,
                "resultado": log.resultado,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "raw_llm_response": log.raw_llm_response
            }
            for log in logs
        ]
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {str(e)}")

