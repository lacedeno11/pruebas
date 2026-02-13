"""
LangChain validation tools for agent use.
Provides functions for validating OT completion, inactivity, and crew capacity.
"""

from typing import Any, Dict, Optional

# from langchain.tools import tool


# @tool
async def validate_proyecto_completion(ot_id: str) -> Dict[str, Any]:
    """
    Check if PUBLICO project can be finalized (29 documents).

    Args:
        ot_id: UUID of OT

    Returns:
        Dictionary with document count and can_finalize flag
    """
    # TODO: Query OT, check project type, get document count from telcos_client
    return {
        "ot_id": ot_id,
        "document_count": 0,
        "required_count": 29,
        "can_finalize": False,
    }


# @tool
async def check_ot_inactivity(ot_id: str) -> Dict[str, Any]:
    """
    Check how many days OT has been in current status.

    Args:
        ot_id: UUID of OT

    Returns:
        Dictionary with days_in_status and status
    """
    # TODO: Query OT, calculate days since status change
    return {
        "ot_id": ot_id,
        "status": "PREPLANIFICADA",
        "days_in_status": 0,
        "alert_threshold": 48,
    }


# @tool
async def validate_crew_capacity(cuadrilla_id: str) -> Dict[str, Any]:
    """
    Check crew capacity vs current assignments.

    Args:
        cuadrilla_id: UUID of crew

    Returns:
        Dictionary with capacity stats
    """
    # TODO: Query crew and assignments, calculate utilization
    return {
        "cuadrilla_id": cuadrilla_id,
        "max_capacity": 5,
        "current_assignments": 0,
        "available_slots": 5,
        "at_capacity": False,
    }

