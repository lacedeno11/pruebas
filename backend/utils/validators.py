"""Business rule validators for PEI Agéntico platform."""

from typing import Tuple, Optional
import os


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


# Allowed state transitions
ALLOWED_TRANSITIONS = {
    "PREPLANIFICADA": ["PLANIFICADA", "ANULADA"],
    "PLANIFICADA": ["ASIGNADO_TAREA", "DETENIDA", "ANULADA"],
    "ASIGNADO_TAREA": ["DETENIDA", "FINALIZADA", "ANULADA"],
    "DETENIDA": ["PLANIFICADA", "ANULADA"],
    "FINALIZADA": ["ANULADA"],
    "ANULADA": [],
}


def validate_state_transition(from_status: str, to_status: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if a state transition is allowed according to business rules.
    
    Args:
        from_status: Current status of the OT
        to_status: Target status for the OT
    
    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])
    """
    # ANULADA can be the target from any state
    if to_status == "ANULADA":
        return (True, None)
    
    # Check if transition is allowed
    if from_status not in ALLOWED_TRANSITIONS:
        return (False, f"Unknown status: {from_status}")
    
    if to_status not in ALLOWED_TRANSITIONS[from_status]:
        allowed = ", ".join(ALLOWED_TRANSITIONS[from_status]) or "none"
        return (
            False,
            f"Cannot transition from {from_status} to {to_status}. Allowed: {allowed}"
        )
    
    return (True, None)


def validate_crew_capacity(cuadrilla: object, new_ot_count: int = 1) -> bool:
    """
    Validate if adding OTs to a crew would exceed MAX_CUADRILLA_CAPACITY.
    
    Args:
        cuadrilla: Cuadrilla object with ots_asignadas_count attribute
        new_ot_count: Number of new OTs to add (default 1)
    
    Returns:
        True if adding OTs is within capacity, False otherwise
    """
    try:
        max_capacity = int(os.getenv("MAX_CUADRILLA_CAPACITY", "20"))
        current_count = cuadrilla.ots_asignadas_count or 0
        
        return (current_count + new_ot_count) <= max_capacity
    except (AttributeError, TypeError, ValueError):
        return False


def validate_publico_documents(document_count: int) -> bool:
    """
    Validate if a PÚBLICO project has the required 29 documents.
    
    Args:
        document_count: Number of documents in TelcoDrive
    
    Returns:
        True if document_count >= 29, False otherwise
    """
    try:
        return int(document_count) >= 29
    except (TypeError, ValueError):
        return False

