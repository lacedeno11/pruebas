"""
LangChain tools for agent operations.
Provides reusable tools that agents can call to interact with the system.
"""

import logging
from typing import Optional, List, Dict, Any

from langchain.tools import tool
from sqlalchemy.orm import Session

from backend.database.base import SessionLocal
from backend.database import models, schemas
from backend.services.ot_service import OTService
from backend.services.cuadrilla_service import CuadrillaService
from backend.services.geo_service import GeoService
from backend.services.notification_service import NotificationService
from backend.services.mock_api import MockApiService

# Configure logging
logger = logging.getLogger(__name__)

# Initialize services
ot_service = OTService()
cuadrilla_service = CuadrillaService()
geo_service = GeoService()
notification_service = NotificationService()
mock_service = MockApiService()


# ============================================================================
# OT Management Tools
# ============================================================================


@tool
def get_unassigned_ots_tool() -> Dict[str, Any]:
    """
    Get list of unassigned OTs in PREPLANIFICADA status.
    
    Returns:
        Dict with list of unassigned OTs
    """
    try:
        db = SessionLocal()
        try:
            unassigned_ots = ot_service.get_unassigned_ots(db)
            return {
                "success": True,
                "count": len(unassigned_ots),
                "ots": [
                    {
                        "id": ot.id,
                        "external_id": ot.external_id,
                        "lat": ot.lat,
                        "long": ot.long,
                        "status": ot.status.value,
                        "project_type": ot.project_type.value,
                        "geo_error": ot.geo_error,
                    }
                    for ot in unassigned_ots
                ],
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error getting unassigned OTs: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@tool
def get_ot_info_tool(ot_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific OT.
    
    Args:
        ot_id: OT ID
        
    Returns:
        Dict with OT details
    """
    try:
        db = SessionLocal()
        try:
            ot = ot_service.get_ot_by_id(db, ot_id)
            if not ot:
                return {
                    "success": False,
                    "error": f"OT {ot_id} not found",
                }
            
            return {
                "success": True,
                "ot": {
                    "id": ot.id,
                    "external_id": ot.external_id,
                    "status": ot.status.value,
                    "project_type": ot.project_type.value,
                    "lat": ot.lat,
                    "long": ot.long,
                    "cuadrilla_id": ot.cuadrilla_id,
                    "geo_error": ot.geo_error,
                    "created_at": ot.created_at.isoformat(),
                    "updated_at": ot.updated_at.isoformat(),
                },
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error getting OT info: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@tool
def update_ot_status_tool(ot_id: int, new_status: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Update OT status and create audit log.
    
    Args:
        ot_id: OT ID
        new_status: New status value
        reason: Reason for status change
        
    Returns:
        Dict with update result
    """
    try:
        db = SessionLocal()
        try:
            # Convert status string to enum
            status_enum = models.OTStatus(new_status)
            
            updated_ot = ot_service.update_ot_status(db, ot_id, status_enum, reason)
            
            return {
                "success": True,
                "message": f"OT {ot_id} status updated to {new_status}",
                "ot_id": ot_id,
                "new_status": new_status,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error updating OT status: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# Assignment Tools
# ============================================================================


@tool
def assign_ot_to_cuadrilla_tool(ot_id: int, cuadrilla_id: int) -> Dict[str, Any]:
    """
    Assign an OT to a cuadrilla with validation.
    
    Checks:
    - Cuadrilla capacity
    - Distance to centroid (<10km)
    
    Args:
        ot_id: OT ID
        cuadrilla_id: Cuadrilla ID
        
    Returns:
        Dict with assignment result
    """
    try:
        db = SessionLocal()
        try:
            # Get OT and Cuadrilla
            ot = ot_service.get_ot_by_id(db, ot_id)
            if not ot:
                return {
                    "success": False,
                    "error": f"OT {ot_id} not found",
                }
            
            cuadrilla = cuadrilla_service.get_cuadrilla_by_id(db, cuadrilla_id)
            if not cuadrilla:
                return {
                    "success": False,
                    "error": f"Cuadrilla {cuadrilla_id} not found",
                }
            
            # Check capacity
            if cuadrilla.current_load >= cuadrilla.capacity:
                return {
                    "success": False,
                    "error": f"Cuadrilla {cuadrilla.name} is at capacity",
                }
            
            # Calculate distance
            distance_km = None
            if (cuadrilla.last_centroid_lat and cuadrilla.last_centroid_long and 
                ot.lat and ot.long):
                distance_km = geo_service.calculate_distance_km(
                    ot.lat,
                    ot.long,
                    cuadrilla.last_centroid_lat,
                    cuadrilla.last_centroid_long,
                )
                
                # Check proximity
                if not geo_service.is_within_radius(
                    ot.lat,
                    ot.long,
                    cuadrilla.last_centroid_lat,
                    cuadrilla.last_centroid_long,
                    radius_km=10.0,
                ):
                    return {
                        "success": False,
                        "error": f"OT is {distance_km:.1f}km away (limit: 10km)",
                        "distance_km": distance_km,
                    }
            
            # Create assignment
            assignment = models.Asignacion(
                ot_id=ot_id,
                cuadrilla_id=cuadrilla_id,
                assigned_by_agent="planificacion_agent",
                distance_to_centroid_km=distance_km,
            )
            
            # Update OT
            ot.cuadrilla_id = cuadrilla_id
            ot.status = models.OTStatus.ASIGNADO_TAREA
            
            # Update cuadrilla load
            cuadrilla.current_load += 1
            
            # Create log
            log = models.LogAgente(
                ot_id=ot_id,
                agente_name="PlanificacionAgent",
                accion=f"Assigned to cuadrilla {cuadrilla.name}",
                resultado="success",
            )
            
            db.add(assignment)
            db.add(log)
            db.commit()
            
            logger.info(f"Assigned OT {ot_id} to Cuadrilla {cuadrilla_id}")
            
            return {
                "success": True,
                "message": f"OT {ot_id} assigned to {cuadrilla.name}",
                "ot_id": ot_id,
                "cuadrilla_id": cuadrilla_id,
                "distance_km": distance_km,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error assigning OT: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@tool
def calculate_distance_tool(ot_id: int, cuadrilla_id: int) -> Dict[str, Any]:
    """
    Calculate distance between OT and cuadrilla centroid.
    
    Args:
        ot_id: OT ID
        cuadrilla_id: Cuadrilla ID
        
    Returns:
        Dict with distance in km
    """
    try:
        db = SessionLocal()
        try:
            ot = ot_service.get_ot_by_id(db, ot_id)
            cuadrilla = cuadrilla_service.get_cuadrilla_by_id(db, cuadrilla_id)
            
            if not ot or not ot.lat or not ot.long:
                return {
                    "success": False,
                    "error": "OT not found or missing coordinates",
                }
            
            if not cuadrilla or not cuadrilla.last_centroid_lat or not cuadrilla.last_centroid_long:
                return {
                    "success": False,
                    "error": "Cuadrilla not found or missing centroid",
                }
            
            distance_km = geo_service.calculate_distance_km(
                ot.lat,
                ot.long,
                cuadrilla.last_centroid_lat,
                cuadrilla.last_centroid_long,
            )
            
            return {
                "success": True,
                "distance_km": distance_km,
                "within_radius": distance_km <= 10.0,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error calculating distance: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@tool
def validate_proyecto_publico_documents_tool(ot_id: int) -> Dict[str, Any]:
    """
    Check document count for PUBLICO projects.
    
    Args:
        ot_id: OT ID
        
    Returns:
        Dict with document count and validation result
    """
    try:
        db = SessionLocal()
        try:
            ot = ot_service.get_ot_by_id(db, ot_id)
            if not ot:
                return {
                    "success": False,
                    "error": f"OT {ot_id} not found",
                }
            
            if ot.project_type != models.ProjectType.PUBLICO:
                return {
                    "success": True,
                    "is_publico": False,
                    "message": "Not a PUBLICO project",
                }
            
            # TODO: Call MockApiService to get document count
            # For now, return placeholder
            doc_count = 0
            
            return {
                "success": True,
                "is_publico": True,
                "document_count": doc_count,
                "required_count": 29,
                "ready_for_finalization": doc_count >= 29,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error validating PUBLICO documents: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# Cuadrilla Tools
# ============================================================================


@tool
def get_cuadrilla_info_tool(cuadrilla_id: int) -> Dict[str, Any]:
    """
    Get detailed cuadrilla information including workload.
    
    Args:
        cuadrilla_id: Cuadrilla ID
        
    Returns:
        Dict with cuadrilla details
    """
    try:
        db = SessionLocal()
        try:
            cuadrilla = cuadrilla_service.get_cuadrilla_by_id(db, cuadrilla_id)
            if not cuadrilla:
                return {
                    "success": False,
                    "error": f"Cuadrilla {cuadrilla_id} not found",
                }
            
            workload = cuadrilla_service.get_cuadrilla_workload(db, cuadrilla_id)
            
            return {
                "success": True,
                "cuadrilla": {
                    "id": cuadrilla.id,
                    "name": cuadrilla.name,
                    "type": cuadrilla.type.value,
                    "current_load": cuadrilla.current_load,
                    "capacity": cuadrilla.capacity,
                    "available_capacity": cuadrilla.capacity - cuadrilla.current_load,
                    "utilization_percent": (cuadrilla.current_load / cuadrilla.capacity * 100) if cuadrilla.capacity > 0 else 0,
                    "last_centroid_lat": cuadrilla.last_centroid_lat,
                    "last_centroid_long": cuadrilla.last_centroid_long,
                    "is_available": cuadrilla.current_load < cuadrilla.capacity,
                },
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error getting cuadrilla info: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@tool
def get_available_cuadrillas_tool() -> Dict[str, Any]:
    """
    Get list of available cuadrillas (with capacity).
    
    Returns:
        Dict with list of available cuadrillas
    """
    try:
        db = SessionLocal()
        try:
            available = cuadrilla_service.get_available_cuadrillas(db)
            
            return {
                "success": True,
                "count": len(available),
                "cuadrillas": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "type": c.type.value,
                        "current_load": c.current_load,
                        "capacity": c.capacity,
                        "available_capacity": c.capacity - c.current_load,
                    }
                    for c in available
                ],
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error getting available cuadrillas: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# Notification Tools
# ============================================================================


@tool
def send_notification_tool(recipient: str, message: str, channel: str = "email") -> Dict[str, Any]:
    """
    Send a notification via specified channel.
    
    Args:
        recipient: Recipient identifier (email or chat_id)
        message: Message text
        channel: Channel type ('email' or 'telegram')
        
    Returns:
        Dict with notification result
    """
    try:
        # TODO: Integrate with NotificationService
        logger.info(f"Notification queued: {channel} to {recipient}")
        
        return {
            "success": True,
            "message": f"Notification queued for {recipient}",
            "channel": channel,
            "recipient": recipient,
        }
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# Utility Tools
# ============================================================================


@tool
def log_agent_action_tool(agent_name: str, action: str, ot_id: Optional[int] = None, result: str = "success") -> Dict[str, Any]:
    """
    Log agent action for audit trail.
    
    Args:
        agent_name: Name of agent
        action: Action performed
        ot_id: Related OT ID (optional)
        result: Result status
        
    Returns:
        Dict with log result
    """
    try:
        db = SessionLocal()
        try:
            log = models.LogAgente(
                ot_id=ot_id,
                agente_name=agent_name,
                accion=action,
                resultado=result,
            )
            db.add(log)
            db.commit()
            
            return {
                "success": True,
                "log_id": log.id,
                "message": f"Action logged for {agent_name}",
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error logging action: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# Export all tools for use in agents
__all__ = [
    "get_unassigned_ots_tool",
    "get_ot_info_tool",
    "update_ot_status_tool",
    "assign_ot_to_cuadrilla_tool",
    "calculate_distance_tool",
    "validate_proyecto_publico_documents_tool",
    "get_cuadrilla_info_tool",
    "get_available_cuadrillas_tool",
    "send_notification_tool",
    "log_agent_action_tool",
]

