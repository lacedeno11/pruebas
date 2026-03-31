"""
API routes for agent operations.

Endpoints:
- POST /api/agents/chat - Natural language input routing through Router Agent
- GET /api/agents/logs - Query LogAgente table with filters
- POST /api/agents/execute - Direct agent invocation with action_type and parameters
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.db.base import get_db
from backend.app.models.log_agente import LogAgente
from backend.app.schemas.agent_schema import (
    AgentInput,
    AgentResponse,
    ChatMessage,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/agents",
    tags=["Agents"],
    responses={
        400: {"description": "Invalid request"},
        500: {"description": "Server error"},
    },
)


# ============================================================================
# POST /api/agents/chat - Natural Language Input Through Router Agent
# ============================================================================

@router.post("/chat", response_model=Dict[str, Any])
async def chat_with_agent(
    message: ChatMessage,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Send a natural language message to the agent system.
    
    This endpoint:
    1. Accepts natural language input from user or UI
    2. Routes through Router Agent for intent classification
    3. Determines appropriate agent based on intent
    4. Executes agent graph with appropriate state
    5. Returns structured response
    
    Request Body:
    - role: "user" or "assistant"
    - content: Natural language message
    - timestamp: ISO format timestamp (optional)
    
    Returns:
    - Dict with agent response: success, message, data, agent_name, timestamp
    
    Example Inputs:
    - "Plan all outstanding OTs"
    - "Show me DETENIDA orders"
    - "What's the status of OT-2024-001?"
    - "Optimize routes for all cuadrillas"
    - "Check governance rules"
    """
    try:
        logger.info(f"Chat request received: {message.content[:100]}...")
        
        if message.role != "user":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only user messages can be processed in chat endpoint"
            )
        
        # TODO: Integrate with Router Agent from agent graph
        # For now, return a placeholder response that would be implemented
        # when agent graph is complete
        
        # This would be replaced with actual router agent invocation:
        # from backend.app.agents.graph import get_agent_executor
        # executor = get_agent_executor(db)
        # response = await executor.invoke({
        #     "messages": [{"role": "user", "content": message.content}],
        #     "action_type": None,  # Router will determine
        #     "input_data": {"user_message": message.content},
        #     "result": {},
        #     "agent_history": [],
        #     "should_continue": True,
        # })
        
        logger.warning("Router Agent not yet implemented - returning mock response")
        
        return {
            "success": True,
            "message": f"Message received: {message.content}",
            "data": {
                "agent_response": "Agent graph not yet implemented",
                "action_type": "UNKNOWN",
            },
            "agent_name": "RouterAgent",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message"
        )


# ============================================================================
# GET /api/agents/logs - Query LogAgente Table with Filters
# ============================================================================

@router.get("/logs", response_model=Dict[str, Any])
async def get_agent_logs(
    agent_name_filter: Optional[str] = Query(None, alias="agent_name", description="Filter by agent name"),
    ot_id_filter: Optional[str] = Query(None, alias="ot_id", description="Filter by OT ID"),
    resultado_filter: Optional[str] = Query(None, alias="resultado", description="Filter by resultado (success/error/etc)"),
    accion_filter: Optional[str] = Query(None, alias="accion", description="Filter by action type"),
    date_from: Optional[str] = Query(None, description="Date range start (ISO format)"),
    date_to: Optional[str] = Query(None, description="Date range end (ISO format)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Number of records to return"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Query agent logs with multiple filters for audit trail and debugging.
    
    Query Parameters:
    - agent_name: Filter by agent name (RouterAgent, OTSAgent, PlanificacionAgent, etc)
    - ot_id: Filter by associated OT UUID
    - resultado: Filter by resultado (success, error, warning, info, etc)
    - accion: Filter by action type (e.g., SYNC_OTS, PLAN_ASSIGNMENT, etc)
    - date_from: Start of date range (ISO format, e.g., 2024-01-15T00:00:00)
    - date_to: End of date range (ISO format)
    - skip: Number of records to skip for pagination (default: 0)
    - limit: Number of records to return (default: 50, max: 500)
    
    Returns:
    - Dict with logs array and total count
    - Each log includes: id, ot_id, agente_name, accion, resultado, raw_llm_response, created_at
    """
    try:
        # Start with base query
        query = db.query(LogAgente)
        
        # Apply filters
        if agent_name_filter:
            query = query.filter(LogAgente.agente_name == agent_name_filter)
        
        if ot_id_filter:
            query = query.filter(LogAgente.ot_id == ot_id_filter)
        
        if resultado_filter:
            query = query.filter(LogAgente.resultado == resultado_filter)
        
        if accion_filter:
            query = query.filter(LogAgente.accion == accion_filter)
        
        # Apply date range filters
        if date_from:
            try:
                from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                query = query.filter(LogAgente.created_at >= from_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid date_from format: {date_from}. Use ISO format (e.g., 2024-01-15T00:00:00)"
                )
        
        if date_to:
            try:
                to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                query = query.filter(LogAgente.created_at <= to_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid date_to format: {date_to}. Use ISO format (e.g., 2024-01-15T23:59:59)"
                )
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination and ordering
        logs = query.order_by(desc(LogAgente.created_at)).offset(skip).limit(limit).all()
        
        # Build response
        log_items = []
        for log in logs:
            log_items.append({
                'id': str(log.id),
                'ot_id': str(log.ot_id) if log.ot_id else None,
                'agente_name': log.agente_name,
                'accion': log.accion,
                'resultado': log.resultado,
                'raw_llm_response': log.raw_llm_response,
                'metadata': log.metadata,
                'created_at': log.created_at.isoformat() if log.created_at else None,
            })
        
        logger.info(
            f"Retrieved {len(logs)} logs with filters - "
            f"agent: {agent_name_filter}, ot: {ot_id_filter}, resultado: {resultado_filter}"
        )
        
        return {
            "success": True,
            "logs": log_items,
            "total": total,
            "skip": skip,
            "limit": limit,
            "returned": len(logs),
            "filters": {
                "agent_name": agent_name_filter,
                "ot_id": ot_id_filter,
                "resultado": resultado_filter,
                "accion": accion_filter,
                "date_from": date_from,
                "date_to": date_to,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving agent logs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent logs"
        )


# ============================================================================
# POST /api/agents/execute - Direct Agent Invocation for Testing
# ============================================================================

@router.post("/execute", response_model=Dict[str, Any])
async def execute_agent(
    agent_input: AgentInput,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Directly invoke a specific agent with action_type and parameters.
    
    This endpoint is useful for testing and manual agent execution.
    It bypasses the Router Agent and directly invokes the specified agent.
    
    Request Body:
    - action_type: Type of action (INGEST_OT, PLAN_OT, UPDATE_STATUS, QUERY_STATUS, GOVERNANCE_CHECK, CHAT)
    - ot_id: Optional OT UUID for operations targeting specific OT
    - parameters: Dict of action-specific parameters
      Examples:
      - For INGEST_OT: {"source": "telcos_api"}
      - For PLAN_OT: {"strategy": "balanced"}
      - For UPDATE_STATUS: {"new_status": "PLANIFICADA"}
      - For GOVERNANCE_CHECK: {"check_type": "inactivity"}
    
    Returns:
    - Dict with execution result: success, message, data, agent_name, timestamp
    
    Example Requests:
    
    1. Sync OTs from TELCOS:
    POST /api/agents/execute
    {
        "action_type": "INGEST_OT",
        "parameters": {"source": "telcos_api"}
    }
    
    2. Plan OTs:
    POST /api/agents/execute
    {
        "action_type": "PLAN_OT",
        "parameters": {"strategy": "balanced"}
    }
    
    3. Check governance rules:
    POST /api/agents/execute
    {
        "action_type": "GOVERNANCE_CHECK",
        "parameters": {"check_type": "inactivity"}
    }
    """
    try:
        logger.info(f"Direct agent execution: action_type={agent_input.action_type}, ot_id={agent_input.ot_id}")
        
        # Validate action_type
        valid_actions = [
            "INGEST_OT",
            "PLAN_OT",
            "UPDATE_STATUS",
            "QUERY_STATUS",
            "GOVERNANCE_CHECK",
            "CHAT",
        ]
        
        if agent_input.action_type not in valid_actions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action_type: {agent_input.action_type}. Must be one of: {', '.join(valid_actions)}"
            )
        
        # TODO: Route to appropriate agent based on action_type
        # This would be implemented when individual agents are complete:
        
        # Example routing logic (to be implemented):
        # if agent_input.action_type == "INGEST_OT":
        #     from backend.app.agents.ots_agent import OTSAgent
        #     agent = OTSAgent(llm=get_llm(), db_session=db)
        #     result = await agent.execute(state)
        # elif agent_input.action_type == "PLAN_OT":
        #     from backend.app.agents.planificacion_agent import PlanificacionAgent
        #     agent = PlanificacionAgent(llm=get_llm(), db_session=db)
        #     result = await agent.execute(state)
        # ... etc
        
        logger.warning(f"Direct agent execution not yet implemented - returning mock response for {agent_input.action_type}")
        
        return {
            "success": True,
            "message": f"Agent execution requested for action_type: {agent_input.action_type}",
            "data": {
                "action_type": agent_input.action_type,
                "ot_id": agent_input.ot_id,
                "parameters": agent_input.parameters,
                "execution_status": "Agent execution not yet implemented",
            },
            "agent_name": f"{agent_input.action_type}Agent",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute agent"
        )


# ============================================================================
# Helper Endpoints for Agent Status
# ============================================================================

@router.get("/status", response_model=Dict[str, Any])
async def get_agent_status(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get status of all agents in the system.
    
    Returns information about available agents and their current status.
    """
    try:
        # TODO: Implement agent status checking
        # This would check the health of each agent and return status
        
        logger.info("Retrieving agent system status")
        
        return {
            "success": True,
            "agents": {
                "RouterAgent": {
                    "status": "ready",
                    "role": "Route user inputs to appropriate agents",
                },
                "OTSAgent": {
                    "status": "ready",
                    "role": "Ingest OTs from TELCOS API",
                },
                "PlanificacionAgent": {
                    "status": "ready",
                    "role": "Plan OT assignments to cuadrillas",
                },
                "GobernanzaAgent": {
                    "status": "ready",
                    "role": "Monitor governance rules and alerts",
                },
                "ComunicacionAgent": {
                    "status": "ready",
                    "role": "Send notifications and alerts",
                },
            },
            "system_mode": "MOCK",  # TODO: Get from environment
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Error getting agent status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent status"
        )


@router.get("/logs/summary", response_model=Dict[str, Any])
async def get_logs_summary(
    hours: int = Query(24, ge=1, le=720, description="Number of hours to look back"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get a summary of agent logs for the specified time period.
    
    Returns statistics about agent executions: counts by agent name, resultado, action type.
    
    Query Parameters:
    - hours: Number of hours to look back (default: 24, max: 720 = 30 days)
    """
    try:
        # Calculate date range
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Query logs in time range
        logs = db.query(LogAgente).filter(
            LogAgente.created_at >= cutoff_time
        ).all()
        
        # Build summary statistics
        agent_counts = {}
        resultado_counts = {}
        accion_counts = {}
        
        for log in logs:
            # Count by agent
            if log.agente_name not in agent_counts:
                agent_counts[log.agente_name] = 0
            agent_counts[log.agente_name] += 1
            
            # Count by resultado
            if log.resultado not in resultado_counts:
                resultado_counts[log.resultado] = 0
            resultado_counts[log.resultado] += 1
            
            # Count by accion
            if log.accion not in accion_counts:
                accion_counts[log.accion] = 0
            accion_counts[log.accion] += 1
        
        logger.info(f"Retrieved logs summary for last {hours} hours: {len(logs)} total logs")
        
        return {
            "success": True,
            "time_period_hours": hours,
            "total_logs": len(logs),
            "summary": {
                "by_agent": agent_counts,
                "by_resultado": resultado_counts,
                "by_action": accion_counts,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Error getting logs summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get logs summary"
        )

