from typing import Tuple


# Valid OT status transitions
STATUS_TRANSITIONS = {
    "PREPLANIFICADA": ["PLANIFICADA", "ANULADA"],
    "PLANIFICADA": ["ASIGNADO_TAREA", "PREPLANIFICADA", "DETENIDA", "ANULADA"],
    "ASIGNADO_TAREA": ["DETENIDA", "FINALIZADA", "ANULADA"],
    "DETENIDA": ["PLANIFICADA", "ANULADA"],
    "ANULADA": [],
    "FINALIZADA": [],
}

# PUBLICO projects require specific validation
PROJECT_TYPE_REQUIREMENTS = {
    "PUBLICO": {
        "required_documents": 29,
        "allowed_transitions": {
            "ASIGNADO_TAREA": ["FINALIZADA"]
        }
    },
    "PRIVADO": {
        "required_documents": 0,
    },
    "TERCERIZADO": {
        "required_documents": 0,
    }
}


def can_transition_status(
    current_status: str,
    new_status: str,
    project_type: str
) -> Tuple[bool, str]:
    """
    Validate OT status transition based on state machine rules
    """
    # Check if transition is valid
    if current_status not in STATUS_TRANSITIONS:
        return False, f"Unknown current status: {current_status}"
    
    if new_status not in STATUS_TRANSITIONS[current_status]:
        allowed = STATUS_TRANSITIONS[current_status]
        return False, f"Cannot transition from {current_status} to {new_status}. Allowed: {allowed}"
    
    # Check project-specific requirements
    if project_type in PROJECT_TYPE_REQUIREMENTS:
        requirements = PROJECT_TYPE_REQUIREMENTS[project_type]
        
        if "allowed_transitions" in requirements:
            if current_status in requirements["allowed_transitions"]:
                allowed = requirements["allowed_transitions"][current_status]
                if new_status not in allowed:
                    return False, f"Project type {project_type} requires transition to {allowed} from {current_status}"
    
    return True, "Transition valid"


def validate_cuadrilla_capacity(cuadrilla_load: int, capacity: int) -> bool:
    """
    Validate that cuadrilla load doesn't exceed capacity
    """
    return cuadrilla_load < capacity


def get_project_priority(project_type: str) -> int:
    """
    Return priority value for sorting (lower = higher priority)
    PUBLICO: 1 (highest)
    PRIVADO: 2
    TERCERIZADO: 3 (lowest)
    """
    priorities = {
        "PUBLICO": 1,
        "PRIVADO": 2,
        "TERCERIZADO": 3,
    }
    return priorities.get(project_type, 999)

