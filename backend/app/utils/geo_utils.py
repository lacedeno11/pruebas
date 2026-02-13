import math
from typing import List, Tuple


def calculate_centroid(coordinates: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Calculate the centroid of a list of coordinates using weighted average.

    Args:
        coordinates: List of tuples (lat, long)

    Returns:
        Tuple of (centroid_lat, centroid_long)
    """
    if not coordinates:
        return (0.0, 0.0)

    total_lat = sum(coord[0] for coord in coordinates)
    total_long = sum(coord[1] for coord in coordinates)

    centroid_lat = total_lat / len(coordinates)
    centroid_long = total_long / len(coordinates)

    return (centroid_lat, centroid_long)


def calculate_distance(
    lat1: float, long1: float, lat2: float, long2: float
) -> float:
    """
    Calculate distance between two geographic points using Haversine formula.

    Args:
        lat1, long1: First point coordinates
        lat2, long2: Second point coordinates

    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_long = math.radians(long2 - long1)

    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_long / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def is_within_radius(
    point: Tuple[float, float], centroid: Tuple[float, float], radius_km: float
) -> bool:
    """
    Check if a point is within a given radius of a centroid.

    Args:
        point: Tuple of (lat, long)
        centroid: Tuple of (lat, long)
        radius_km: Radius in kilometers

    Returns:
        True if point is within radius, False otherwise
    """
    distance = calculate_distance(point[0], point[1], centroid[0], centroid[1])
    return distance < radius_km


def validate_coordinates(lat: float, long: float) -> bool:
    """
    Validate that coordinates are within Ecuador's geographical bounds.

    Ecuador bounds:
    - Latitude: -2 to 1
    - Longitude: -81 to -75

    Args:
        lat: Latitude coordinate
        long: Longitude coordinate

    Returns:
        True if coordinates are valid, False otherwise
    """
    lat_min, lat_max = -2.0, 1.0
    long_min, long_max = -81.0, -75.0

    return (lat_min <= lat <= lat_max) and (long_min <= long <= long_max)

