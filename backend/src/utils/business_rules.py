"""
Business Rules and Governance Validators for PEI Platform.

This module implements the core business logic for validating OT transitions,
calculating detention periods, and determining operational priorities. It enforces
compliance with TELCONET's operational requirements and regulatory constraints.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple


class ProjectType:
    """Project type constants matching the OT model enum."""

    PUBLICO = "PUBLICO"
    PRIVADO = "PRIVADO"
    TERCERIZADO = "TERCERIZADO"


class OTStatus:
    """OT status constants matching the OT model enum."""

    PREPLANIFICADA = "PREPLANIFICADA"
    PLANIFICADA = "PLANIFICADA"
    ASIGNADO_TAREA = "ASIGNADO_TAREA"
    DETENIDA = "DETENIDA"
    ANULADA = "ANULADA"
    FINALIZADA = "FINALIZADA"


# Business rule constants
PUBLICO_REQUIRED_DOCUMENTS = 29
PREPLANIFICADA_ALERT_THRESHOLD_HOURS = 48
DETENTION_ALERT_DAYS = [20, 25, 29]
DETENTION_AUTO_CANCEL_DAY = 30
CUADRILLA_MAX_DAILY_CAPACITY = 10
PROXIMITY_RADIUS_KM = 10.0

# Detention reason ontology - valid reasons for detention
DETENTION_REASON_ONTOLOGY = {
    "cliente_no_disponible": {
        "category": "CLIENT_UNAVAILABLE",
        "description": "Cliente no disponible en el horario programado",
        "severity": "LOW",
    },
    "acceso_bloqueado": {
        "category": "ACCESS_DENIED",
        "description": "Acceso a la propiedad bloqueado o denegado",
        "severity": "MEDIUM",
    },
    "equipo_defectuoso": {
        "category": "EQUIPMENT_ISSUE",
        "description": "Equipo defectuoso o dañado requiere reemplazo",
        "severity": "MEDIUM",
    },
    "falta_materiales": {
        "category": "MATERIAL_SHORTAGE",
        "description": "Falta de materiales necesarios para completar la tarea",
        "severity": "MEDIUM",
    },
    "condiciones_climaticas": {
        "category": "WEATHER_CONDITIONS",
        "description": "Condiciones climáticas adversas impiden continuación",
        "severity": "LOW",
    },
    "permiso_municipal": {
        "category": "PERMIT_ISSUE",
        "description": "Espera de permiso municipal o aprobación regulatoria",
        "severity": "HIGH",
    },
    "otro": {
        "category": "OTHER",
        "description": "Otra razón no categorizada",
        "severity": "MEDIUM",
    },
}

# Priority levels
PRIORITY_SCORES = {
    ProjectType.PUBLICO: 1,      # Highest priority
    ProjectType.PRIVADO: 2,      # Medium priority
    ProjectType.TERCERIZADO: 3,  # Lowest priority
}


def can_transition_to_finalizada(ot_id: int, project_type: str, document_count: int) -> Tuple[bool, str]:
    """
    Validate if an OT can transition to FINALIZADA status.

    Business rule: PUBLICO projects require exactly 29 documents in TelcoDrive
    before they can be finalized. PRIVADO and TERCERIZADO projects have no
    document requirements.

    This validates UC-PEI-08 requirement: "No se permite mover a FINALIZADA si el
    conteo de documentos en TelcoDrive es < 29 para proyectos PUBLICO"

    Args:
        ot_id (int): OT identifier
        project_type (str): Type of project (PUBLICO, PRIVADO, TERCERIZADO)
        document_count (int): Number of documents uploaded in TelcoDrive

    Returns:
        Tuple[bool, str]: (can_transition, reason_message)
                         - True if transition is allowed
                         - False with detailed reason if not allowed

    Example:
        >>> # PUBLICO project with insufficient documents
        >>> can_transition_to_finalizada(123, "PUBLICO", 28)
        (False, "PUBLICO projects require 29 documents (found: 28)")

        >>> # PUBLICO project with all documents
        >>> can_transition_to_finalizada(123, "PUBLICO", 29)
        (True, "All validation passed for FINALIZADA transition")

        >>> # PRIVADO project with no document requirement
        >>> can_transition_to_finalizada(123, "PRIVADO", 0)
        (True, "All validation passed for FINALIZADA transition")
    """
    # PUBLICO projects require exactly 29 documents
    if project_type == ProjectType.PUBLICO:
        if document_count < PUBLICO_REQUIRED_DOCUMENTS:
            return (
                False,
                f"PUBLICO projects require {PUBLICO_REQUIRED_DOCUMENTS} documents "
                f"(found: {document_count}). Cannot transition to FINALIZADA.",
            )

    # PRIVADO and TERCERIZADO have no document requirements
    return (True, "All validation passed for FINALIZADA transition")


def should_trigger_preplanificada_alert(ot_id: int, created_at: datetime) -> bool:
    """
    Check if an OT in PREPLANIFICADA status should trigger an alert.

    Business rule: OTs that remain in PREPLANIFICADA status for more than 48 hours
    trigger a high-priority alert to the Coordinador OPU.

    This validates the requirement: "Una OT en PREPLANIFICADA por más de 48 horas
    dispara una notificación de alta prioridad al Coordinador OPU."

    Args:
        ot_id (int): OT identifier
        created_at (datetime): When the OT was created (entered PREPLANIFICADA)

    Returns:
        bool: True if alert should be triggered (OT has been PREPLANIFICADA >48hrs)

    Example:
        >>> # OT created 72 hours ago (3 days)
        >>> now = datetime.utcnow()
        >>> created = now - timedelta(days=3)
        >>> should_trigger_preplanificada_alert(123, created)
        True

        >>> # OT created 24 hours ago
        >>> created = now - timedelta(hours=24)
        >>> should_trigger_preplanificada_alert(123, created)
        False
    """
    now = datetime.utcnow()
    time_in_preplanificada = now - created_at
    threshold = timedelta(hours=PREPLANIFICADA_ALERT_THRESHOLD_HOURS)

    return time_in_preplanificada > threshold


def calculate_detention_alert_day(detention_start: datetime) -> int:
    """
    Calculate how many days an OT has been in DETENIDA status.

    Used to determine when alerts should be sent (days 20, 25, 29) and
    when automatic cancellation should occur (day 30).

    Business rule: OTs in DETENIDA status generate alerts on specific days
    and are auto-cancelled on day 30 if not resolved.

    Args:
        detention_start (datetime): When the OT entered DETENIDA status

    Returns:
        int: Number of complete days (24-hour periods) since DETENIDA

    Example:
        >>> # OT detained 20 days ago
        >>> now = datetime.utcnow()
        >>> detention = now - timedelta(days=20)
        >>> calculate_detention_alert_day(detention)
        20

        >>> # OT detained 20.5 days ago (still day 20)
        >>> detention = now - timedelta(days=20, hours=12)
        >>> calculate_detention_alert_day(detention)
        20
    """
    now = datetime.utcnow()
    time_in_detention = now - detention_start
    days_in_detention = int(time_in_detention.total_seconds() / (24 * 3600))

    return days_in_detention


def should_trigger_detention_alert(days_in_detention: int) -> bool:
    """
    Check if an alert should be triggered based on detention days.

    Alerts are triggered on days 20, 25, and 29. Auto-cancellation occurs on day 30.

    Args:
        days_in_detention (int): Number of days in DETENIDA status

    Returns:
        bool: True if an alert should be triggered

    Example:
        >>> should_trigger_detention_alert(20)
        True
        >>> should_trigger_detention_alert(25)
        True
        >>> should_trigger_detention_alert(29)
        True
        >>> should_trigger_detention_alert(21)
        False
    """
    return days_in_detention in DETENTION_ALERT_DAYS


def should_auto_cancel_detention(days_in_detention: int) -> bool:
    """
    Check if a detention should be auto-cancelled due to inactivity.

    OTs in DETENIDA status for 30+ days are automatically cancelled by the
    Gobernanza Agent as per UC-PEI-08.

    Args:
        days_in_detention (int): Number of days in DETENIDA status

    Returns:
        bool: True if auto-cancellation should occur

    Example:
        >>> should_auto_cancel_detention(30)
        True
        >>> should_auto_cancel_detention(29)
        False
        >>> should_auto_cancel_detention(31)
        True
    """
    return days_in_detention >= DETENTION_AUTO_CANCEL_DAY


def is_valid_detention_reason(reason: str, ontology: Optional[Dict] = None) -> Tuple[bool, Optional[Dict]]:
    """
    Validate a detention reason against the business ontology.

    Used in UC-PEI-13 (Drag & Drop detention): When a PM moves an OT to DETENIDA,
    they must provide a reason. This reason is validated against known categories.

    Reasons must be:
    - At least 10 characters long
    - Either a known ontology key OR a freeform text reason
    - Valid according to the stored ontology

    Args:
        reason (str): The detention reason provided by the user
        ontology (Optional[Dict]): Custom ontology to use (defaults to DETENTION_REASON_ONTOLOGY)

    Returns:
        Tuple[bool, Optional[Dict]]: (is_valid, ontology_entry)
                                    - (True, entry) if reason is valid and matches ontology
                                    - (False, None) if reason is invalid

    Example:
        >>> # Valid ontology key
        >>> is_valid_detention_reason("cliente_no_disponible")
        (True, {ontology_entry})

        >>> # Valid freeform reason (>10 chars)
        >>> is_valid_detention_reason("Esperando confirmación del cliente")
        (True, {default_entry})

        >>> # Invalid reason (too short)
        >>> is_valid_detention_reason("Espera")
        (False, None)

        >>> # Empty reason
        >>> is_valid_detention_reason("")
        (False, None)
    """
    if ontology is None:
        ontology = DETENTION_REASON_ONTOLOGY

    # Validate minimum length
    if not reason or len(reason.strip()) < 10:
        return (False, None)

    # Check if reason matches an ontology key
    reason_lower = reason.lower().strip()
    if reason_lower in ontology:
        return (True, ontology[reason_lower])

    # If not an ontology key, treat as freeform reason (minimum length already validated)
    # Create a default entry for freeform reasons
    default_entry = {
        "category": "CUSTOM_REASON",
        "description": reason,
        "severity": "MEDIUM",
    }
    return (True, default_entry)


def get_priority_score(project_type: str) -> int:
    """
    Get the priority score for a project type.

    Lower scores = Higher priority. Used for sorting and scheduling OTs.

    Priority order (from highest to lowest):
    1. PUBLICO (score: 1) - Public/government projects
    2. PRIVADO (score: 2) - Private enterprise projects
    3. TERCERIZADO (score: 3) - Outsourced/third-party projects

    This implements the business rule: "Prioridad de Atención: 1. Público, 2. Privado, 3. Tercerizado"

    Args:
        project_type (str): Type of project (PUBLICO, PRIVADO, TERCERIZADO)

    Returns:
        int: Priority score (lower is higher priority)
             - 1 for PUBLICO
             - 2 for PRIVADO
             - 3 for TERCERIZADO
             - 99 for unknown types (lowest priority)

    Example:
        >>> get_priority_score("PUBLICO")
        1
        >>> get_priority_score("PRIVADO")
        2
        >>> get_priority_score("TERCERIZADO")
        3
        >>> get_priority_score("UNKNOWN")
        99
    """
    return PRIORITY_SCORES.get(project_type, 99)


def compare_priority(project_type1: str, project_type2: str) -> int:
    """
    Compare priority of two project types.

    Args:
        project_type1 (str): First project type
        project_type2 (str): Second project type

    Returns:
        int: -1 if type1 has higher priority, 0 if equal, 1 if type2 has higher priority

    Example:
        >>> compare_priority("PUBLICO", "PRIVADO")
        -1  # PUBLICO is higher priority
        >>> compare_priority("TERCERIZADO", "PUBLICO")
        1   # PUBLICO is higher priority
    """
    score1 = get_priority_score(project_type1)
    score2 = get_priority_score(project_type2)

    if score1 < score2:
        return -1
    elif score1 > score2:
        return 1
    else:
        return 0


def validate_ot_transition(current_status: str, new_status: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if an OT can transition from current_status to new_status.

    Defines the valid state transitions for OTs in the system.

    Valid transitions:
    - PREPLANIFICADA → PLANIFICADA, ANULADA
    - PLANIFICADA → ASIGNADO_TAREA, DETENIDA, ANULADA
    - ASIGNADO_TAREA → DETENIDA, FINALIZADA, ANULADA
    - DETENIDA → PLANIFICADA, ANULADA (must be within 30 days)
    - ANULADA → (terminal state)
    - FINALIZADA → (terminal state)

    Args:
        current_status (str): Current OT status
        new_status (str): Target OT status

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)

    Example:
        >>> validate_ot_transition("PREPLANIFICADA", "PLANIFICADA")
        (True, None)

        >>> validate_ot_transition("PREPLANIFICADA", "FINALIZADA")
        (False, "Invalid transition from PREPLANIFICADA to FINALIZADA")

        >>> validate_ot_transition("ANULADA", "PLANIFICADA")
        (False, "Cannot transition from terminal state ANULADA")
    """
    # Define valid transitions
    valid_transitions = {
        OTStatus.PREPLANIFICADA: [
            OTStatus.PLANIFICADA,
            OTStatus.ANULADA,
        ],
        OTStatus.PLANIFICADA: [
            OTStatus.ASIGNADO_TAREA,
            OTStatus.DETENIDA,
            OTStatus.ANULADA,
        ],
        OTStatus.ASIGNADO_TAREA: [
            OTStatus.DETENIDA,
            OTStatus.FINALIZADA,
            OTStatus.ANULADA,
        ],
        OTStatus.DETENIDA: [
            OTStatus.PLANIFICADA,
            OTStatus.ANULADA,
        ],
        OTStatus.ANULADA: [],  # Terminal state
        OTStatus.FINALIZADA: [],  # Terminal state
    }

    # Check if current status is known
    if current_status not in valid_transitions:
        return (False, f"Unknown current status: {current_status}")

    # Check if new status is valid
    allowed_transitions = valid_transitions[current_status]
    if new_status not in allowed_transitions:
        if current_status in [OTStatus.ANULADA, OTStatus.FINALIZADA]:
            return (False, f"Cannot transition from terminal state {current_status}")
        else:
            return (False, f"Invalid transition from {current_status} to {new_status}")

    return (True, None)


def get_valid_next_statuses(current_status: str) -> list[str]:
    """
    Get list of valid next statuses from a given current status.

    Args:
        current_status (str): Current OT status

    Returns:
        list[str]: List of valid next statuses

    Example:
        >>> get_valid_next_statuses("PREPLANIFICADA")
        ["PLANIFICADA", "ANULADA"]
    """
    valid_transitions = {
        OTStatus.PREPLANIFICADA: [
            OTStatus.PLANIFICADA,
            OTStatus.ANULADA,
        ],
        OTStatus.PLANIFICADA: [
            OTStatus.ASIGNADO_TAREA,
            OTStatus.DETENIDA,
            OTStatus.ANULADA,
        ],
        OTStatus.ASIGNADO_TAREA: [
            OTStatus.DETENIDA,
            OTStatus.FINALIZADA,
            OTStatus.ANULADA,
        ],
        OTStatus.DETENIDA: [
            OTStatus.PLANIFICADA,
            OTStatus.ANULADA,
        ],
        OTStatus.ANULADA: [],
        OTStatus.FINALIZADA: [],
    }

    return valid_transitions.get(current_status, [])


def get_detention_reason_ontology() -> Dict:
    """
    Get the detention reason ontology for validation and display.

    Returns:
        Dict: Dictionary of valid detention reasons with metadata
    """
    return DETENTION_REASON_ONTOLOGY.copy()

