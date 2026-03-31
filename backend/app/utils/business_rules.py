from datetime import datetime, timedelta
from typing import Tuple


def get_priority_order(project_type: str) -> int:
    """
    Get priority order for a project type.

    PUBLICO = 1 (highest priority)
    PRIVADO = 2
    TERCERIZADO = 3 (lowest priority)

    Args:
        project_type: Type of project (PUBLICO, PRIVADO, TERCERIZADO)

    Returns:
        Priority order (1-3)
    """
    priority_map = {
        "PUBLICO": 1,
        "PRIVADO": 2,
        "TERCERIZADO": 3,
    }
    return priority_map.get(project_type, 3)


def can_finalize_ot(ot, document_count: int) -> Tuple[bool, str]:
    """
    Check if an OT can be finalized based on document requirements.

    For PUBLICO projects: requires exactly 29 documents
    For other project types: no document requirement

    Args:
        ot: OT object with project_type attribute
        document_count: Number of documents uploaded

    Returns:
        Tuple of (can_finalize: bool, message: str)
    """
    if ot.project_type == "PUBLICO":
        if document_count < 29:
            return (
                False,
                f"PUBLICO projects require 29 documents. Currently have {document_count}.",
            )
        return True, "All documents complete. OT can be finalized."
    else:
        return True, f"No document requirement for {ot.project_type} projects."


def should_alert_inactivity(ot) -> bool:
    """
    Check if an OT should trigger an inactivity alert.

    Alerts if OT has been in PREPLANIFICADA status for more than 48 hours.

    Args:
        ot: OT object with status and created_at/updated_at attributes

    Returns:
        True if alert should be triggered, False otherwise
    """
    if ot.status != "PREPLANIFICADA":
        return False

    # Check time in PREPLANIFICADA status
    time_diff = datetime.utcnow() - ot.updated_at
    return time_diff > timedelta(hours=48)


def days_in_status(ot, current_status: str = None) -> int:
    """
    Calculate number of days an OT has been in its current status.

    Args:
        ot: OT object with status and updated_at attributes
        current_status: Optional override status to check (uses ot.status if None)

    Returns:
        Number of days in status
    """
    if current_status and ot.status != current_status:
        return 0

    time_diff = datetime.utcnow() - ot.updated_at
    return time_diff.days


def requires_governance_action(ot) -> Tuple[bool, str]:
    """
    Check if an OT requires governance action.

    Governance actions needed for:
    - DETENIDA status for more than 30 days (auto-cancel)
    - PREPLANIFICADA status for more than 48 hours (alert)

    Args:
        ot: OT object with status and updated_at attributes

    Returns:
        Tuple of (requires_action: bool, action_description: str)
    """
    days = days_in_status(ot)

    if ot.status == "DETENIDA":
        if days >= 30:
            return True, "AUTO_CANCEL - Exceeded 30 days in DETENIDA status"
        elif days >= 25:
            return True, "ALERT_29 - 5 days remaining before auto-cancel"
        elif days >= 20:
            return True, "ALERT_20 - 10 days remaining before auto-cancel"
        else:
            return False, ""

    if ot.status == "PREPLANIFICADA":
        hours_diff = (datetime.utcnow() - ot.updated_at).total_seconds() / 3600
        if hours_diff >= 48:
            return True, "ALERT_INACTIVITY - OT in PREPLANIFICADA for more than 48 hours"

    return False, ""

