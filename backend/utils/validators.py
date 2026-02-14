"""
Business logic validators for OT data, status transitions, and project constraints.
Implements core business rules and state machine validation.
"""

from typing import Dict, List, Tuple

# OT Status state machine - defines valid transitions
STATUS_TRANSITIONS: Dict[str, List[str]] = {
    "PREPLANIFICADA": ["PLANIFICADA", "ANULADA"],
    "PLANIFICADA": ["ASIGNADO_TAREA", "DETENIDA", "ANULADA"],
    "ASIGNADO_TAREA": ["DETENIDA", "FINALIZADA", "ANULADA"],
    "DETENIDA": ["PLANIFICADA", "ANULADA"],
    "ANULADA": [],  # Terminal state
    "FINALIZADA": [],  # Terminal state
}


def validate_ot_data(ot_dict: dict) -> Tuple[bool, str]:
    """
    Validate required fields in OT data.

    Args:
        ot_dict: OT dictionary to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["external_id", "cliente_id", "login_id"]

    for field in required_fields:
        if field not in ot_dict or not ot_dict[field]:
            return False, f"Missing required field: {field}"

    # Validate coordinates if present
    if "lat" in ot_dict and "long" in ot_dict:
        if ot_dict["lat"] is None or ot_dict["long"] is None:
            return False, "Coordinates must not be null if present"

    return True, ""


def validate_status_transition(
    current_status: str, new_status: str
) -> Tuple[bool, str]:
    """
    Validate if status transition is allowed according to state machine.

    Args:
        current_status: Current OT status
        new_status: Desired new status

    Returns:
        Tuple of (is_valid, error_message)
    """
    if current_status not in STATUS_TRANSITIONS:
        return False, f"Invalid current status: {current_status}"

    if new_status not in STATUS_TRANSITIONS:
        return False, f"Invalid target status: {new_status}"

    allowed_transitions = STATUS_TRANSITIONS[current_status]
    if new_status not in allowed_transitions:
        return (
            False,
            f"Cannot transition from {current_status} to {new_status}. "
            f"Allowed: {', '.join(allowed_transitions)}",
        )

    return True, ""


def validate_proyecto_documents(
    project_type: str, document_count: int
) -> bool:
    """
    Validate if project has required documents for completion.

    For PUBLICO projects: must have exactly 29 documents
    For PRIVADO and TERCERIZADO: no document requirement

    Args:
        project_type: Type of project (PUBLICO, PRIVADO, TERCERIZADO)
        document_count: Number of documents available

    Returns:
        True if project meets document requirements, False otherwise
    """
    if project_type == "PUBLICO":
        return document_count >= 29
    # PRIVADO and TERCERIZADO don't have document requirements
    return True

