"""
LangChain tool definitions for agent operations.

Defines tools that agents can use to interact with the database and
external systems. Each tool is decorated with @tool and can be used
by agents through the LangChain framework.

Tools available:
- get_ot_details: Retrieve full OT information
- get_cuadrilla_info: Retrieve cuadrilla details and workload
- calculate_centroid_tool: Calculate centroid for a cuadrilla's OTs
- check_distance_constraint: Verify OT is within 10km of cuadrilla
- get_documents_count: Check TelcoDrive document status
- update_ot_status_tool: Update OT status and notify TELCOS
"""

import logging
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy.orm import Session
from langchain.tools import tool

from backend.app.models.ot import OrdenTrabajo, OTStatus, ProjectType
from backend.app.models.cuadrilla import Cuadrilla
from backend.app.models.asignacion import Asignacion
from backend.app.utils.geo_utils import (
    calculate_distance,
    calculate_centroid,
    validate_coordinates,
)
from backend.app.services.telcos_api_client import TelcosApiClient

logger = logging.getLogger(__name__)


# Global database session (will be set by agent executor)
_db_session: Optional[Session] = None


def set_tool_db_session(db_session: Session) -> None:
    """
    Set the database session for tools.
    
    This is called by the agent executor to provide tools with database access.
    
    Args:
        db_session: SQLAlchemy database session
    """
    global _db_session
    _db_session = db_session
    logger.debug("Set database session for tools")


def _get_db() -> Session:
    """Get the current database session."""
    if _db_session is None:
        raise RuntimeError("Database session not initialized for tools")
    return _db_session


# ============================================================================
# Tool: get_ot_details - Retrieve OT Information
# ============================================================================

@tool
def get_ot_details(ot_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific OT.
    
    Args:
        ot_id: UUID of the OT to retrieve
    
    Returns:
        Dict containing OT details: id, external_id, status, project_type,
        lat, long, cliente_id, login_id, cuadrilla_id, error_geo, created_at, updated_at
    
    Raises:
        Exception: If OT not found
    
    Example:
        >>> ot = get_ot_details("550e8400-e29b-41d4-a716-446655440000")
        >>> print(ot['external_id'])  # 'OT-2024-001'
        >>> print(ot['status'])  # 'PREPLANIFICADA'
    """
    try:
        db = _get_db()
        ot = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == ot_id).first()
        
        if not ot:
            return {
                "error": f"OT {ot_id} not found",
                "success": False,
            }
        
        return {
            "success": True,
            "ot": {
                "id": str(ot.id),
                "external_id": ot.external_id,
                "status": ot.status.value if hasattr(ot.status, 'value') else ot.status,
                "project_type": ot.project_type.value if hasattr(ot.project_type, 'value') else ot.project_type,
                "lat": ot.lat,
                "long": ot.long,
                "cliente_id": ot.cliente_id,
                "login_id": ot.login_id,
                "cuadrilla_id": str(ot.cuadrilla_id) if ot.cuadrilla_id else None,
                "error_geo": ot.error_geo,
                "created_at": ot.created_at.isoformat() if ot.created_at else None,
                "updated_at": ot.updated_at.isoformat() if ot.updated_at else None,
            },
        }
    
    except Exception as e:
        logger.error(f"Error getting OT details: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "success": False,
        }


# ============================================================================
# Tool: get_cuadrilla_info - Retrieve Cuadrilla Information
# ============================================================================

@tool
def get_cuadrilla_info(cuadrilla_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a cuadrilla including its workload.
    
    Args:
        cuadrilla_id: UUID of the cuadrilla
    
    Returns:
        Dict containing cuadrilla details, current load, capacity, and assigned OT count
    
    Raises:
        Exception: If cuadrilla not found
    
    Example:
        >>> info = get_cuadrilla_info("550e8400-e29b-41d4-a716-446655440001")
        >>> print(info['name'])  # 'Cuadrilla A'
        >>> print(info['current_load'])  # 7
        >>> print(info['capacity_daily'])  # 10
    """
    try:
        db = _get_db()
        cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
        
        if not cuadrilla:
            return {
                "error": f"Cuadrilla {cuadrilla_id} not found",
                "success": False,
            }
        
        # Count active assignments
        active_count = db.query(Asignacion).filter(
            Asignacion.cuadrilla_id == cuadrilla_id,
            Asignacion.is_active == True
        ).count()
        
        return {
            "success": True,
            "cuadrilla": {
                "id": str(cuadrilla.id),
                "name": cuadrilla.name,
                "type": cuadrilla.type.value if hasattr(cuadrilla.type, 'value') else cuadrilla.type,
                "capacity_daily": cuadrilla.capacity_daily,
                "current_load": cuadrilla.current_load,
                "active_assignments": active_count,
                "available_slots": max(0, cuadrilla.capacity_daily - cuadrilla.current_load),
                "last_centroid_lat": cuadrilla.last_centroid_lat,
                "last_centroid_long": cuadrilla.last_centroid_long,
                "is_active": cuadrilla.is_active,
                "created_at": cuadrilla.created_at.isoformat() if cuadrilla.created_at else None,
            },
        }
    
    except Exception as e:
        logger.error(f"Error getting cuadrilla info: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "success": False,
        }


# ============================================================================
# Tool: calculate_centroid_tool - Calculate Centroid for Cuadrilla
# ============================================================================

@tool
def calculate_centroid_tool(cuadrilla_id: str) -> Dict[str, Any]:
    """
    Calculate the centroid of all OTs assigned to a cuadrilla.
    
    This tool retrieves all active OTs assigned to a cuadrilla and calculates
    the weighted average of their coordinates (centroid).
    
    Args:
        cuadrilla_id: UUID of the cuadrilla
    
    Returns:
        Dict containing centroid coordinates and number of OTs used
    
    Example:
        >>> centroid = calculate_centroid_tool("550e8400-e29b-41d4-a716-446655440001")
        >>> print(centroid['lat'])  # -1.5
        >>> print(centroid['long'])  # -78.5
        >>> print(centroid['ot_count'])  # 5
    """
    try:
        db = _get_db()
        
        # Get all active assignments for cuadrilla
        assignments = db.query(Asignacion).filter(
            Asignacion.cuadrilla_id == cuadrilla_id,
            Asignacion.is_active == True
        ).all()
        
        if not assignments:
            return {
                "error": f"No active assignments found for cuadrilla {cuadrilla_id}",
                "success": False,
            }
        
        # Get OT details
        ot_ids = [a.ot_id for a in assignments]
        ots = db.query(OrdenTrabajo).filter(OrdenTrabajo.id.in_(ot_ids)).all()
        
        # Extract valid coordinates
        valid_coords = [
            (ot.lat, ot.long) for ot in ots
            if ot.lat is not None and ot.long is not None
        ]
        
        if not valid_coords:
            return {
                "error": "No OTs with valid coordinates found",
                "success": False,
                "ot_count": len(ots),
                "valid_coord_count": 0,
            }
        
        # Calculate centroid
        centroid = calculate_centroid(valid_coords)
        
        return {
            "success": True,
            "lat": centroid[0],
            "long": centroid[1],
            "ot_count": len(ots),
            "valid_coord_count": len(valid_coords),
        }
    
    except Exception as e:
        logger.error(f"Error calculating centroid: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "success": False,
        }


# ============================================================================
# Tool: check_distance_constraint - Verify Proximity Constraint
# ============================================================================

@tool
def check_distance_constraint(ot_id: str, cuadrilla_id: str, threshold_km: float = 10.0) -> Dict[str, Any]:
    """
    Check if an OT is within the distance threshold of a cuadrilla's centroid.
    
    This tool calculates the distance from an OT to a cuadrilla's last known
    centroid and verifies it's within the threshold (default 10km).
    
    Args:
        ot_id: UUID of the OT
        cuadrilla_id: UUID of the cuadrilla
        threshold_km: Maximum allowed distance in kilometers (default: 10.0)
    
    Returns:
        Dict containing distance, within_threshold (bool), and constraint result
    
    Example:
        >>> result = check_distance_constraint(
        ...     "550e8400-e29b-41d4-a716-446655440000",
        ...     "550e8400-e29b-41d4-a716-446655440001"
        ... )
        >>> print(result['distance'])  # 5.23
        >>> print(result['within_threshold'])  # True
    """
    try:
        db = _get_db()
        
        # Get OT
        ot = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == ot_id).first()
        if not ot:
            return {
                "error": f"OT {ot_id} not found",
                "success": False,
            }
        
        # Get cuadrilla
        cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
        if not cuadrilla:
            return {
                "error": f"Cuadrilla {cuadrilla_id} not found",
                "success": False,
            }
        
        # Check if OT has valid coordinates
        if ot.lat is None or ot.long is None:
            return {
                "success": False,
                "error": "OT has invalid coordinates",
                "ot_error_geo": ot.error_geo,
            }
        
        # Check if cuadrilla has centroid
        if cuadrilla.last_centroid_lat is None or cuadrilla.last_centroid_long is None:
            return {
                "success": False,
                "error": "Cuadrilla centroid not yet calculated",
                "distance": None,
                "within_threshold": False,
            }
        
        # Calculate distance
        distance = calculate_distance(
            ot.lat, ot.long,
            cuadrilla.last_centroid_lat, cuadrilla.last_centroid_long
        )
        
        within_threshold = distance <= threshold_km
        
        return {
            "success": True,
            "distance": round(distance, 2),
            "threshold_km": threshold_km,
            "within_threshold": within_threshold,
            "ot_id": str(ot.id),
            "cuadrilla_id": str(cuadrilla.id),
            "cuadrilla_name": cuadrilla.name,
        }
    
    except Exception as e:
        logger.error(f"Error checking distance constraint: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "success": False,
        }


# ============================================================================
# Tool: get_documents_count - Check Document Status
# ============================================================================

@tool
async def get_documents_count(ot_id: str) -> Dict[str, Any]:
    """
    Get the document status for an OT from TelcoDrive API.
    
    For PUBLICO projects, retrieves the count of uploaded documents.
    For other project types, returns 0.
    
    Args:
        ot_id: UUID of the OT
    
    Returns:
        Dict containing document count, required count, and progress info
    
    Example:
        >>> docs = get_documents_count("550e8400-e29b-41d4-a716-446655440000")
        >>> print(docs['document_count'])  # 25
        >>> print(docs['required_count'])  # 29
        >>> print(docs['progress_percentage'])  # 86.21
    """
    try:
        db = _get_db()
        
        # Get OT
        ot = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == ot_id).first()
        if not ot:
            return {
                "error": f"OT {ot_id} not found",
                "success": False,
            }
        
        # If not PUBLICO, return 0 documents
        if ot.project_type != ProjectType.PUBLICO:
            return {
                "success": True,
                "project_type": ot.project_type.value if hasattr(ot.project_type, 'value') else ot.project_type,
                "document_count": 0,
                "required_count": 0,
                "progress_percentage": 100.0,
                "message": f"Document check not required for {ot.project_type.value} projects",
            }
        
        # Get documents from TELCOS API
        telcos_client = TelcosApiClient()
        doc_status = await telcos_client.get_documents_status(ot_id, ProjectType.PUBLICO)
        
        return {
            "success": True,
            "ot_id": str(ot.id),
            "project_type": ProjectType.PUBLICO.value,
            "document_count": doc_status.get('document_count', 0),
            "required_count": doc_status.get('required_count', 29),
            "documents_missing": max(0, doc_status.get('required_count', 29) - doc_status.get('document_count', 0)),
            "progress_percentage": round(
                (doc_status.get('document_count', 0) / doc_status.get('required_count', 29) * 100)
                if doc_status.get('required_count', 29) > 0 else 0,
                2
            ),
        }
    
    except Exception as e:
        logger.error(f"Error getting documents count: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "success": False,
        }


# ============================================================================
# Tool: update_ot_status_tool - Update OT Status
# ============================================================================

@tool
async def update_ot_status_tool(ot_id: str, new_status: str) -> Dict[str, Any]:
    """
    Update the status of an OT and notify the TELCOS system.
    
    This tool updates the OT status in the database and calls the TELCOS API
    to notify the external system of the change.
    
    Args:
        ot_id: UUID of the OT
        new_status: New status value (PREPLANIFICADA, PLANIFICADA, ASIGNADO_TAREA, DETENIDA, ANULADA, FINALIZADA)
    
    Returns:
        Dict containing update result and new OT details
    
    Raises:
        Exception: If OT not found or status invalid
    
    Example:
        >>> result = update_ot_status_tool(
        ...     "550e8400-e29b-41d4-a716-446655440000",
        ...     "PLANIFICADA"
        ... )
        >>> print(result['success'])  # True
        >>> print(result['new_status'])  # 'PLANIFICADA'
    """
    try:
        db = _get_db()
        
        # Get OT
        ot = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == ot_id).first()
        if not ot:
            return {
                "error": f"OT {ot_id} not found",
                "success": False,
            }
        
        # Convert status to enum
        try:
            target_status = OTStatus[new_status.upper()]
        except KeyError:
            return {
                "error": f"Invalid status: {new_status}",
                "success": False,
            }
        
        old_status = ot.status
        
        # Update OT status
        ot.status = target_status
        ot.updated_at = __import__('datetime').datetime.utcnow()
        db.commit()
        
        # Notify TELCOS API
        try:
            telcos_client = TelcosApiClient()
            await telcos_client.update_status(ot.external_id, new_status)
        except Exception as e:
            logger.warning(f"Could not notify TELCOS for OT {ot.external_id}: {str(e)}")
            # Don't fail if TELCOS notification fails
        
        return {
            "success": True,
            "ot_id": str(ot.id),
            "external_id": ot.external_id,
            "old_status": old_status.value if hasattr(old_status, 'value') else old_status,
            "new_status": target_status.value if hasattr(target_status, 'value') else target_status,
            "updated_at": ot.updated_at.isoformat() if ot.updated_at else None,
        }
    
    except Exception as e:
        logger.error(f"Error updating OT status: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "success": False,
        }


# ============================================================================
# Tool Exports
# ============================================================================

__all__ = [
    "set_tool_db_session",
    "get_ot_details",
    "get_cuadrilla_info",
    "calculate_centroid_tool",
    "check_distance_constraint",
    "get_documents_count",
    "update_ot_status_tool",
]

