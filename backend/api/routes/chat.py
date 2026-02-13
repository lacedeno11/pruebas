"""Conversational agent endpoints for chat interface."""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from backend.database.db import get_db
from backend.database.models import OT, Cuadrilla, OTStatus
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import os
from datetime import datetime

# Initialize router
router = APIRouter()

# In-memory conversation cache (TODO: move to database for persistence)
CONVERSATION_CACHE: Dict[str, List[Dict[str, Any]]] = {}


# Pydantic models for request/response
class ChatRequest(BaseModel):
    """Chat message request model."""
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    conversation_id: str
    suggested_actions: List[str] = []


# Tool functions for LLM agent
def get_ots_summary(status: Optional[str] = None, db: Session = None) -> Dict[str, Any]:
    """
    Get summary of OTs grouped by status.
    
    Args:
        status: Optional filter by status
        db: Database session
    
    Returns:
        Dictionary with OT counts by status
    """
    if db is None:
        from backend.database.db import SessionLocal
        db = SessionLocal()
        close_db = True
    else:
        close_db = False
    
    try:
        if status:
            count = db.query(OT).filter(OT.status == status).count()
            return {
                status: count,
            }
        
        summary = {}
        for s in OTStatus:
            count = db.query(OT).filter(OT.status == s.value).count()
            summary[s.value] = count
        
        return summary
    finally:
        if close_db:
            db.close()


def get_crew_status(db: Session = None) -> List[Dict[str, Any]]:
    """
    Get status of all crews (utilization, assigned OTs).
    
    Args:
        db: Database session
    
    Returns:
        List of crew status dictionaries
    """
    if db is None:
        from backend.database.db import SessionLocal
        db = SessionLocal()
        close_db = True
    else:
        close_db = False
    
    try:
        cuadrillas = db.query(Cuadrilla).all()
        crew_status = []
        
        for crew in cuadrillas:
            utilization_percent = (crew.ots_asignadas_count / crew.capacidad_diaria * 100) if crew.capacidad_diaria > 0 else 0
            crew_status.append({
                "crew_id": crew.id,
                "crew_name": crew.name,
                "total_capacity": crew.capacidad_diaria,
                "ots_assigned": crew.ots_asignadas_count,
                "utilization_percent": round(utilization_percent, 1),
                "available_capacity": crew.capacidad_diaria - crew.ots_asignadas_count,
            })
        
        return crew_status
    finally:
        if close_db:
            db.close()


def trigger_planning(db: Session = None) -> Dict[str, Any]:
    """
    Trigger automatic planning algorithm.
    
    Args:
        db: Database session
    
    Returns:
        Result dictionary with success status and message
    """
    # TODO: Integrate with actual planning workflow
    return {
        "success": True,
        "message": "Automatic planning has been triggered. Check planning dashboard for results.",
    }


def get_ot_details(ot_id: int, db: Session = None) -> Dict[str, Any]:
    """
    Get detailed information about a specific OT.
    
    Args:
        ot_id: OT ID
        db: Database session
    
    Returns:
        Dictionary with OT details or error message
    """
    if db is None:
        from backend.database.db import SessionLocal
        db = SessionLocal()
        close_db = True
    else:
        close_db = False
    
    try:
        ot = db.query(OT).filter(OT.id == ot_id).first()
        
        if not ot:
            return {
                "success": False,
                "error": f"OT with id {ot_id} not found",
            }
        
        return {
            "success": True,
            "ot_id": ot.id,
            "external_id": ot.external_id,
            "status": ot.status,
            "project_type": ot.project_type,
            "client_id": ot.cliente_id,
            "login": ot.login,
            "latitude": ot.lat,
            "longitude": ot.long,
            "created_at": ot.created_at.isoformat(),
            "updated_at": ot.updated_at.isoformat(),
            "cuadrilla_name": ot.cuadrilla.name if ot.cuadrilla else "Unassigned",
            "days_in_status": (datetime.utcnow() - ot.updated_at).days,
        }
    finally:
        if close_db:
            db.close()


def get_pending_ots(db: Session = None) -> Dict[str, Any]:
    """
    Get count of pending (unassigned) OTs.
    
    Args:
        db: Database session
    
    Returns:
        Dictionary with pending OT count
    """
    if db is None:
        from backend.database.db import SessionLocal
        db = SessionLocal()
        close_db = True
    else:
        close_db = False
    
    try:
        pending_count = db.query(OT).filter(OT.cuadrilla_id == None).count()
        return {
            "pending_ots": pending_count,
            "message": f"There are {pending_count} OTs waiting for assignment",
        }
    finally:
        if close_db:
            db.close()


# Endpoints

@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    Send message to conversational agent.
    
    Request Body:
    - message: User message
    - conversation_id: Optional conversation ID for continuing conversation
    
    Returns:
    - response: Agent's response message
    - conversation_id: Unique conversation ID
    - suggested_actions: List of suggested follow-up actions
    
    The agent has access to tool functions:
    - get_ots_summary(): Get OT counts by status
    - get_crew_status(): Get crew utilization
    - trigger_planning(): Start automatic planning
    - get_ot_details(ot_id): Get details about specific OT
    - get_pending_ots(): Get count of unassigned OTs
    """
    
    # Initialize or retrieve conversation
    conversation_id = request.conversation_id or str(uuid.uuid4())
    
    if conversation_id not in CONVERSATION_CACHE:
        CONVERSATION_CACHE[conversation_id] = []
    
    # Add user message to conversation history
    CONVERSATION_CACHE[conversation_id].append({
        "role": "user",
        "content": request.message,
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    try:
        # Parse user intent and determine suggested actions
        suggested_actions = _determine_suggested_actions(request.message)
        
        # Generate agent response using simple logic (TODO: integrate with LLM/LangGraph)
        agent_response = _generate_agent_response(request.message, db)
        
        # Add assistant response to conversation history
        CONVERSATION_CACHE[conversation_id].append({
            "role": "assistant",
            "content": agent_response,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        return ChatResponse(
            response=agent_response,
            conversation_id=conversation_id,
            suggested_actions=suggested_actions,
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


def _determine_suggested_actions(message: str) -> List[str]:
    """
    Determine suggested follow-up actions based on user message.
    
    Args:
        message: User message
    
    Returns:
        List of suggested action phrases
    """
    message_lower = message.lower()
    suggested = []
    
    # Suggest planning-related actions
    if any(word in message_lower for word in ["planifica", "asigna", "assign"]):
        suggested.append("Planifica las OTs del proyecto DataLegal")
        suggested.append("Muéstrame el estado de las cuadrillas")
    
    # Suggest status check actions
    if any(word in message_lower for word in ["estado", "status", "cuántas", "how many"]):
        suggested.append("¿Cuántas OTs están detenidas?")
        suggested.append("Muéstrame el resumen de OTs")
    
    # Suggest crew actions
    if any(word in message_lower for word in ["cuadrilla", "crew", "equipo"]):
        suggested.append("Muéstrame el estado de las cuadrillas")
        suggested.append("¿Cuál es la utilización de las cuadrillas?")
    
    # Default suggestions if none matched
    if not suggested:
        suggested = [
            "Muéstrame el estado de las cuadrillas",
            "¿Cuántas OTs están pendientes?",
            "Planifica las OTs del proyecto DataLegal",
        ]
    
    return suggested[:3]  # Return max 3 suggestions


def _generate_agent_response(message: str, db: Session) -> str:
    """
    Generate agent response based on user message.
    
    This is a simplified implementation. TODO: Replace with full LLM/LangGraph integration.
    
    Args:
        message: User message
        db: Database session
    
    Returns:
        Agent response message
    """
    message_lower = message.lower()
    
    # Response to planning requests
    if any(word in message_lower for word in ["planifica", "asigna", "assign"]):
        return "He iniciado el algoritmo de planificación automática. Las OTs serán asignadas a las cuadrillas considerando su centroide geográfico y capacidad disponible. Puedes revisar el dashboard de planificación para ver el progreso."
    
    # Response to status checks
    if any(word in message_lower for word in ["detenida", "detenidas", "parada", "stopped"]):
        paused_count = db.query(OT).filter(OT.status == OTStatus.DETENIDA.value).count()
        return f"Actualmente hay {paused_count} OTs en estado DETENIDA. Estas OTs requieren atención: si llevan más de 30 días en este estado, serán canceladas automáticamente."
    
    # Response to crew status
    if any(word in message_lower for word in ["cuadrilla", "crew", "equipo", "utilización", "utilization"]):
        crew_data = get_crew_status(db)
        total_capacity = sum(c["total_capacity"] for c in crew_data)
        total_assigned = sum(c["ots_assigned"] for c in crew_data)
        overall_util = (total_assigned / total_capacity * 100) if total_capacity > 0 else 0
        return f"Hay {len(crew_data)} cuadrillas activas. Utilización general: {overall_util:.1f}%. Puedes ver el detalle en el dashboard de planificación."
    
    # Response to pending OTs
    if any(word in message_lower for word in ["pendiente", "pending", "asignar", "sin asignar"]):
        pending_data = get_pending_ots(db)
        return f"{pending_data['message']} que necesitan ser asignadas a una cuadrilla."
    
    # Response to summary requests
    if any(word in message_lower for word in ["resumen", "summary", "total", "cuántas", "how many"]):
        summary = get_ots_summary(None, db)
        response_parts = ["Aquí está el resumen de OTs por estado:"]
        for status, count in summary.items():
            response_parts.append(f"- {status}: {count}")
        return "\n".join(response_parts)
    
    # Default response
    return "Soy tu asistente de gestión de OTs. Puedo ayudarte a:\n- Ver el estado de las OTs\n- Verificar la utilización de las cuadrillas\n- Iniciar la planificación automática\n- Consultar detalles de OTs específicas\n\n¿En qué puedo ayudarte?"


@router.websocket("/api/chat/stream")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat responses.
    
    This is optional and lower priority. Allows real-time chat with streaming.
    
    Note: This endpoint requires additional implementation with asyncio streaming.
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("message", "")
            conversation_id = data.get("conversation_id", str(uuid.uuid4()))
            
            if not message:
                continue
            
            # Send back conversation ID
            await websocket.send_json({
                "type": "conversation_id",
                "conversation_id": conversation_id,
            })
            
            # Send back response (TODO: implement streaming with real LLM)
            response = "WebSocket streaming not yet implemented. Please use POST /api/chat endpoint."
            await websocket.send_json({
                "type": "response",
                "response": response,
                "suggested_actions": [],
            })
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e),
        })

