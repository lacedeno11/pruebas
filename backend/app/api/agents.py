from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
from app.database import get_db
from app.models import LogAgente
from app.schemas import AgentRequest, AgentResponse, PlanningRequest, PlanningResponse

router = APIRouter()


@router.post("/chat", response_model=AgentResponse)
async def chat_with_agent(
    request: AgentRequest,
    db: Session = Depends(get_db)
):
    """
    Chat endpoint for natural language commands
    Routes to appropriate agent based on intent
    """
    # TODO: Implement RouterAgent logic
    return AgentResponse(
        success=True,
        message="Agent command received",
        data={"action": request.action},
        agent_name="RouterAgent",
        timestamp=datetime.utcnow()
    )


@router.post("/plan", response_model=PlanningResponse)
async def trigger_planning(
    request: PlanningRequest,
    db: Session = Depends(get_db)
):
    """
    Trigger planning algorithm for OT assignment
    """
    # TODO: Implement PlanificacionAgent logic
    return PlanningResponse(
        assigned_count=0,
        failed_count=0,
        assignments=[],
        errors=[]
    )


@router.post("/govern")
async def trigger_governance(db: Session = Depends(get_db)):
    """
    Manually trigger governance checks
    """
    # TODO: Implement GobernanzaAgent logic
    return {
        "success": True,
        "alerts_sent": 0,
        "cancelled_count": 0,
        "message": "Governance check completed"
    }


@router.get("/logs")
def get_agent_logs(
    agent_name: Optional[str] = Query(None),
    ot_id: Optional[int] = Query(None),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Get agent logs with optional filters
    """
    query = db.query(LogAgente)
    
    if agent_name:
        query = query.filter(LogAgente.agente_name == agent_name)
    
    if ot_id:
        query = query.filter(LogAgente.ot_id == ot_id)
    
    # Filter by date range
    since = datetime.utcnow() - timedelta(days=days)
    query = query.filter(LogAgente.created_at >= since)
    
    logs = query.order_by(LogAgente.created_at.desc()).limit(100).all()
    
    return {
        "total": len(logs),
        "logs": logs,
        "filters": {
            "agent_name": agent_name,
            "ot_id": ot_id,
            "days": days
        }
    }


agents_router = router

