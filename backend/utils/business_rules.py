"""
Business rules and validation functions for the PEI Platform.
Implements OT assignment constraints, project completion validation,
and governance rules for OT lifecycle management.
"""

from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.models import OT, Cuadrilla


def validate_project_completion(ot: "OT", document_count: int) -> bool:
    """
    Validate if a PUBLICO project has completed all required documentation.
    
    PUBLICO (Public) projects must have exactly 29 documents in TelcoDrive
    before they can transition to FINALIZADA status.
    
    Args:
        ot: OT object to validate
        document_count: Number of documents in TelcoDrive
        
    Returns:
        True if project can proceed to FINALIZADA, False if documents incomplete
        
    Rules:
        - PUBLICO projects: Must have >= 29 documents
        - PRIVADO projects: No document requirement
        - TERCERIZADO projects: No document requirement
        
    Example:
        >>> ot.project_type = 'PUBLICO'
        >>> validate_project_completion(ot, 29)  # Returns True
        >>> validate_project_completion(ot, 28)  # Returns False
    """
    # Only PUBLICO projects require document validation
    if ot.project_type != "PUBLICO":
        return True

    # PUBLICO projects must have at least 29 documents
    required_documents = 29
    return document_count >= required_documents


def get_project_priority(project_type: str) -> int:
    """
    Get priority level for a project type for OT assignment ordering.
    
    Priority affects assignment order in the Planificación Agent's 3-phase
    algorithm. Higher priority projects (PUBLICO) should be assigned first.
    
    Args:
        project_type: Type of project (PUBLICO, PRIVADO, or TERCERIZADO)
        
    Returns:
        Priority integer: 1=PUBLICO (highest), 2=PRIVADO, 3=TERCERIZADO (lowest)
        
    Example:
        >>> get_project_priority('PUBLICO')  # Returns 1
        >>> get_project_priority('PRIVADO')  # Returns 2
        >>> get_project_priority('TERCERIZADO')  # Returns 3
    """
    priority_map = {
        "PUBLICO": 1,
        "PRIVADO": 2,
        "TERCERIZADO": 3,
    }
    
    return priority_map.get(project_type.upper(), 3)


def can_assign_to_cuadrilla(
    cuadrilla: "Cuadrilla",
    ot: "OT",
    max_distance_km: float,
) -> tuple[bool, Optional[str]]:
    """
    Validate if an OT can be assigned to a cuadrilla based on constraints.
    
    Checks two critical constraints:
    1. Cuadrilla has available capacity (current_load < daily_capacity)
    2. OT location is within max_distance_km from cuadrilla centroid
    
    Args:
        cuadrilla: Cuadrilla object to assign to
        ot: OT object to assign
        max_distance_km: Maximum distance threshold in kilometers
        
    Returns:
        Tuple of (can_assign: bool, reason: Optional[str])
        - (True, None) if assignment is valid
        - (False, reason_string) if assignment fails with reason
        
    Validation checks:
        1. Cuadrilla is active (is_active=True)
        2. Cuadrilla has available capacity (current_load < daily_capacity)
        3. OT has valid coordinates (lat and long not None)
        4. Distance from OT to cuadrilla centroid <= max_distance_km
        
    Example:
        >>> can_assign, reason = can_assign_to_cuadrilla(cuadrilla, ot, 10.0)
        >>> if can_assign:
        ...     print("Assignment valid")
        >>> else:
        ...     print(f"Cannot assign: {reason}")
    """
    # Check if cuadrilla is active
    if not cuadrilla.is_active:
        return False, "Cuadrilla is not active"

    # Check capacity constraint
    if cuadrilla.current_load >= cuadrilla.daily_capacity:
        return (
            False,
            f"Cuadrilla at full capacity ({cuadrilla.current_load}/{cuadrilla.daily_capacity})",
        )

    # Check OT has valid coordinates
    if ot.lat is None or ot.long is None:
        return False, "OT missing geographic coordinates"

    # Check if cuadrilla has centroid (has been assigned OTs before)
    if cuadrilla.last_centroid_lat is None or cuadrilla.last_centroid_long is None:
        # New cuadrilla with no assignments - assume can assign
        return True, None

    # Calculate distance from OT to cuadrilla centroid
    from backend.utils.geo_utils import calculate_distance

    distance = calculate_distance(
        ot.lat,
        ot.long,
        cuadrilla.last_centroid_lat,
        cuadrilla.last_centroid_long,
    )

    # Check distance constraint
    if distance > max_distance_km:
        return (
            False,
            f"OT too far from cuadrilla ({distance:.2f}km > {max_distance_km}km)",
        )

    return True, None


def calculate_days_in_status(ot: "OT", target_status: str) -> int:
    """
    Calculate number of days an OT has been in a specific status.
    
    Used by GobernanzaAgent to determine when alerts should be sent
    and when auto-cancellation should occur.
    
    Args:
        ot: OT object to check
        target_status: Status to check for (e.g., 'DETENIDA', 'PREPLANIFICADA')
        
    Returns:
        Number of days in the target status
        Returns 0 if OT is not in the target status
        Returns 0 if updated_at timestamp is None
        
    Usage:
        - Check inactivity: if ot.status == 'PREPLANIFICADA' and calculate_days_in_status(ot, 'PREPLANIFICADA') > 2
        - Check detention duration: if ot.status == 'DETENIDA' and calculate_days_in_status(ot, 'DETENIDA') >= 30
        - Send reminders: if days_in_status in [20, 25, 29]
        
    Example:
        >>> ot.status = 'DETENIDA'
        >>> ot.updated_at = datetime.utcnow() - timedelta(days=25)
        >>> days = calculate_days_in_status(ot, 'DETENIDA')
        >>> print(f"Days in DETENIDA: {days}")
        Days in DETENIDA: 25
    """
    # Only count if OT is in the target status
    if ot.status != target_status:
        return 0

    # Handle missing timestamp
    if ot.updated_at is None:
        return 0

    # Calculate difference between now and last status update
    now = datetime.utcnow()
    time_delta = now - ot.updated_at

    # Return number of complete days
    days = time_delta.days

    return days

