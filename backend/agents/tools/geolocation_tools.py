"""
LangChain geolocation tools for agent use.
Provides functions for calculating centroids, distances, and nearest crew finding.
"""

from typing import Any, Dict, Optional

# from langchain.tools import tool
from backend.utils import calculate_centroid, calculate_distance_km


# @tool
async def calculate_crew_centroid(cuadrilla_id: str) -> Dict[str, Any]:
    """
    Calculate centroid of all OTs assigned to a crew.

    Args:
        cuadrilla_id: UUID of crew

    Returns:
        Dictionary with lat, long, and assignment count
    """
    # TODO: Query crew assignments and calculate centroid
    return {
        "cuadrilla_id": cuadrilla_id,
        "centroid_lat": None,
        "centroid_long": None,
        "assignments_count": 0,
    }


# @tool
async def check_distance_from_centroid(
    ot_id: str, cuadrilla_id: str
) -> Dict[str, Any]:
    """
    Check distance from OT to crew centroid.

    Args:
        ot_id: UUID of OT
        cuadrilla_id: UUID of crew

    Returns:
        Dictionary with distance_km and within_range flag
    """
    # TODO: Get OT coords, crew centroid, calculate distance
    return {
        "ot_id": ot_id,
        "cuadrilla_id": cuadrilla_id,
        "distance_km": None,
        "within_10km": False,
    }


# @tool
async def find_nearest_crew(
    ot_lat: float, ot_long: float
) -> Optional[Dict[str, Any]]:
    """
    Find nearest available crew to OT coordinates.

    Args:
        ot_lat: OT latitude
        ot_long: OT longitude

    Returns:
        Dictionary with crew info and distance, or None if no crew available
    """
    # TODO: Query all available crews, calculate distances, return closest
    return None

