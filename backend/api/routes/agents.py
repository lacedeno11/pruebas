"""
Agent orchestration endpoints for natural language interaction and agent management.
Provides interface to RouterAgent and monitoring capabilities for all agents.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database.base import get_db
from backend.database import schemas, models

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/agents", tags=["agents"])

# TODO: Import Orchestrator when agents module is implemented
# from backend.agents.orchestrator import Orchestrator


# ============================================================================
# GET Endpoints
# ============================================================================


@router.get("/status", response_model=List[schemas.AgentStatus])
async def get_agents_status(
    db: Session = Depends(get_db),
):
    """
    Get status of all agents including last execution and success rate.
    
    Returns:
        List of agent status objects
    """
    try:
        # TODO: Get actual agent status from Orchestrator
        # For now, return placeholder response
        
        agents = [
            {
                "agent_name": "RouterAgent",
                "last_execution": None,
                "success_rate": 0.0,
                "total_executions": 0,
                "status": "idle",
            },
            {
                "agent_name": "OTSAgent",
                "last_execution": None,
                "success_rate": 0.0,
                "total_executions": 0,
                "status": "idle",
            },
            {
                "agent_name": "PlanificacionAgent",
                "last_execution": None,
                "success_rate": 0.0,
                "total_executions": 0,
                "status": "idle",
            },
            {
                "agent_name": "GobernanzaAgent",
                "last_execution": None,
                "success_rate": 0.0,
                "total_executions": 0,
                "status": "idle",
            },
            {
                "agent_name": "ComunicacionAgent",
                "last_execution": None,
                "success_rate": 0.0,
                "total_executions": 0,
                "status": "idle",
            },
        ]
        
        return agents
    except Exception as e:
        logger.error(f"Error fetching agent status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching agent status",
        )


@router.get("/graph", response_model=dict)
async def get_agent_graph():
    """
    Get Mermaid visualization of the agent orchestration graph.
    
    Returns:
        Mermaid diagram code for visualizing agent flow
    """
    try:
        # TODO: Get actual graph from Orchestrator.get_graph_visualization()
        
        mermaid_diagram = """
        graph TD
            A[User Input] --> B[RouterAgent]
            B -->|ots_ingestion| C[OTSAgent]
            B -->|planning| D[PlanificacionAgent]
            B -->|governance| E[GobernanzaAgent]
            B -->|communication| F[ComunicacionAgent]
            B -->|query| G[Query Handler]
            C --> H[Log & Respond]
            D --> H
            E --> H
            F --> H
            G --> H
            H --> I[User Response]
        """
        
        return {
            "success": True,
            "graph": mermaid_diagram,
            "description": "DERCAS PEI Agent Orchestration Graph",
        }
    except Exception as e:
        logger.error(f"Error fetching agent graph: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching agent graph",
        )


@router.get("/logs", response_model=List[schemas.LogAgenteResponse])
async def get_agent_logs(
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db),
):
    """
    Get agent execution logs with optional filtering.
    
    Query Parameters:
    - agent_name: Filter by specific agent name
    - date_from: Start date for filtering (format: YYYY-MM-DD)
    - date_to: End date for filtering (format: YYYY-MM-DD)
    - skip: Pagination offset
    - limit: Maximum number of results
    
    Returns:
        List of LogAgente objects
    """
    try:
        query = db.query(models.LogAgente)
        
        # Apply filters
        if agent_name:
            query = query.filter(models.LogAgente.agente_name == agent_name)
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(models.LogAgente.created_at >= from_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_from format. Use YYYY-MM-DD",
                )
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
                query = query.filter(models.LogAgente.created_at < to_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_to format. Use YYYY-MM-DD",
                )
        
        # Execute query with pagination
        logs = query.order_by(models.LogAgente.created_at.desc()).offset(skip).limit(limit).all()
        return logs
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching agent logs",
        )


# ============================================================================
# POST Endpoints
# ============================================================================


@router.post("/chat", response_model=schemas.AgentChatResponse)
async def chat_with_agent(
    request: schemas.AgentChatRequest,
    db: Session = Depends(get_db),
):
    """
    Send a natural language message to RouterAgent for processing.
    
    Request Body:
    - message: User message or command
    - context: Optional context dictionary with additional information
    
    Returns:
        Agent response with actions taken and results
    """
    try:
        # TODO: Integrate with Orchestrator.run(input_data)
        # For now, return placeholder response
        
        logger.info(f"Chat request: {request.message}")
        
        # Create log entry
        log = models.LogAgente(
            agente_name="RouterAgent",
            accion="Process user message",
            resultado="pending",
            raw_llm_response=request.message,
        )
        db.add(log)
        db.commit()
        
        return {
            "success": True,
            "agent_response": f"Message received and queued for processing: '{request.message}'",
            "actions_taken": ["classified_input", "logged_request"],
            "result": {
                "log_id": log.id,
                "status": "pending",
            },
            "error": None,
        }
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing chat request",
        )


@router.post("/execute", response_model=dict)
async def execute_agent(
    request: dict,
    db: Session = Depends(get_db),
):
    """
    Manually trigger execution of a specific agent.
    
    Request Body:
    - agent_name: Name of agent to execute (RouterAgent, OTSAgent, PlanificacionAgent, GobernanzaAgent, ComunicacionAgent)
    - input_data: Input data for the agent
    
    Returns:
        Execution result
    """
    try:
        agent_name = request.get("agent_name")
        input_data = request.get("input_data", {})
        
        valid_agents = [
            "RouterAgent",
            "OTSAgent",
            "PlanificacionAgent",
            "GobernanzaAgent",
            "ComunicacionAgent",
        ]
        
        if agent_name not in valid_agents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid agent name. Must be one of: {', '.join(valid_agents)}",
            )
        
        # TODO: Integrate with Orchestrator to execute specific agent
        
        logger.info(f"Executing agent: {agent_name} with input: {input_data}")
        
        # Create log entry
        log = models.LogAgente(
            agente_name=agent_name,
            accion="Manual execution",
            resultado="queued",
            raw_llm_response=str(input_data),
        )
        db.add(log)
        db.commit()
        
        return {
            "success": True,
            "message": f"Agent {agent_name} execution initiated",
            "agent_name": agent_name,
            "log_id": log.id,
            "status": "queued",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing agent: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error executing agent",
        )

