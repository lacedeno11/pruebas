"""Business rules and validation logic for the PEI Platform"""

from datetime import datetime
from typing import Tuple, Optional
from .constants import (
    OT_STATUS,
    PROJECT_TYPES,
    ALERT_DAYS,
    AUTO_CANCEL_DAYS,
    DOCUMENT_REQUIREMENT_PUBLICO,
    ALERT_TYPES,
    ALLOWED_TRANSITIONS,
)


def validate_status_transition(
    current: str, new: str, role: str = "USER"
) -> Tuple[bool, str]:
    """
    Validate if a status transition is allowed.

    Args:
        current: Current OT status
        new: New OT status
        role: User role (for future role-based validation)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if current not in ALLOWED_TRANSITIONS:
        return False, f"Unknown current status: {current}"

    if new not in OT_STATUS.values():
        return False, f"Unknown new status: {new}"

    if new not in ALLOWED_TRANSITIONS[current]:
        return (
            False,
            f"Cannot transition from {current} to {new}. "
            f"Allowed transitions from {current}: {ALLOWED_TRANSITIONS[current]}",
        )

    return True, ""


def get_document_requirement(project_type: str) -> int:
    """
    Get the minimum number of required documents for a project type.

    Args:
        project_type: Type of project (PUBLICO, PRIVADO, TERCERIZADO)

    Returns:
        Number of required documents
    """
    if project_type == PROJECT_TYPES["PUBLICO"]:
        return DOCUMENT_REQUIREMENT_PUBLICO
    return 0


def calculate_days_inactive(last_change: datetime) -> int:
    """
    Calculate the number of days since the last status change.

    Args:
        last_change: datetime of last status change

    Returns:
        Number of days inactive
    """
    return (datetime.now() - last_change).days


def should_send_alert(days_inactive: int) -> Optional[str]:
    """
    Determine if an alert should be sent based on days of inactivity.

    Args:
        days_inactive: Number of days in current status

    Returns:
        Alert type string if alert should be sent, None otherwise
    """
    if days_inactive == 20:
        return ALERT_TYPES["WARNING_20"]
    elif days_inactive == 25:
        return ALERT_TYPES["WARNING_25"]
    elif days_inactive == 29:
        return ALERT_TYPES["FINAL_WARNING"]
    return None


def should_auto_cancel(days_inactive: int) -> bool:
    """
    Determine if an OT should be automatically cancelled.

    Args:
        days_inactive: Number of days in current status

    Returns:
        True if OT should be auto-cancelled, False otherwise
    """
    return days_inactive >= AUTO_CANCEL_DAYS


def validate_public_project_complete(document_count: int) -> Tuple[bool, str]:
    """
    Validate if a PUBLIC project has all required documents.

    Args:
        document_count: Number of documents uploaded

    Returns:
        Tuple of (is_valid, error_message)
    """
    required = get_document_requirement(PROJECT_TYPES["PUBLICO"])
    if document_count < required:
        missing = required - document_count
        return (
            False,
            f"Public project requires {required} documents. Missing: {missing}",
        )
    return True, ""


def get_inactivity_alert_threshold() -> int:
    """
    Get the threshold for PREPLANIFICADA inactivity alerts (in hours).

    Returns:
        Number of hours before alert is triggered
    """
    return 48  # Hardcoded for now, could be moved to settings

