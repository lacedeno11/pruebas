"""Geographic calculation utilities for OT and Cuadrilla coordination"""

from typing import List, Tuple, Optional
from geopy.distance import geodesic


def calculate_centroid(coordinates: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Calculate the geographic centroid (center point) of a list of coordinates.

    Args:
        coordinates: List of (latitude, longitude) tuples

    Returns:
        Tuple of (centroid_latitude, centroid_longitude)
        Returns (0, 0) if list is empty
    """
    if not coordinates:
        return (0.0, 0.0)

    avg_lat = sum(coord[0] for coord in coordinates) / len(coordinates)
    avg_long = sum(coord[1] for coord in coordinates) / len(coordinates)

    return (avg_lat, avg_long)


def calculate_distance(
    point1: Tuple[float, float], point2: Tuple[float, float]
) -> float:
    """
    Calculate the geodesic distance between two geographic points.

    Uses the Haversine formula via geopy for accurate distance calculation.

    Args:
        point1: (latitude, longitude) tuple
        point2: (latitude, longitude) tuple

    Returns:
        Distance in kilometers
    """
    # geodesic returns distance with .km property
    distance = geodesic(point1, point2)
    return distance.km


def is_within_radius(
    ot_coords: Tuple[float, float],
    centroid: Tuple[float, float],
    max_km: float = 10.0,
) -> bool:
    """
    Check if an OT is within a specified radius of a centroid.

    Args:
        ot_coords: (latitude, longitude) tuple of OT location
        centroid: (latitude, longitude) tuple of cuadrilla centroid
        max_km: Maximum distance in kilometers (default 10.0)

    Returns:
        True if distance <= max_km, False otherwise
    """
    distance = calculate_distance(ot_coords, centroid)
    return distance <= max_km


def get_nearest_cuadrilla(
    ot_coords: Tuple[float, float],
    cuadrillas: List,  # Would be List[Cuadrilla] in actual usage
    max_km: float = 10.0,
) -> Optional:
    """
    Find the nearest cuadrilla to an OT location within a maximum distance.

    Args:
        ot_coords: (latitude, longitude) tuple of OT location
        cuadrillas: List of Cuadrilla objects with last_centroid_lat/long
        max_km: Maximum distance to consider (default 10.0)

    Returns:
        The Cuadrilla object with minimum distance, or None if all > max_km
    """
    if not cuadrillas:
        return None

    nearest_cuadrilla = None
    min_distance = float("inf")

    for cuadrilla in cuadrillas:
        if (
            cuadrilla.last_centroid_lat is None
            or cuadrilla.last_centroid_long is None
        ):
            continue

        centroid = (cuadrilla.last_centroid_lat, cuadrilla.last_centroid_long)
        distance = calculate_distance(ot_coords, centroid)

        if distance < min_distance and distance <= max_km:
            min_distance = distance
            nearest_cuadrilla = cuadrilla

    return nearest_cuadrilla

