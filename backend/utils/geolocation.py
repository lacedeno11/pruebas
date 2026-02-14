"""
Geolocation utilities using Haversine formula for distance calculations.
Used for crew assignment proximity checks and centroid calculations.
"""

import math
from typing import List, Tuple


def calculate_centroid(
    coordinates: List[Tuple[float, float]],
) -> Tuple[float, float]:
    """
    Calculate the centroid (average) of a list of lat/long coordinates.

    Args:
        coordinates: List of (lat, long) tuples

    Returns:
        Tuple of (centroid_lat, centroid_long)
    """
    if not coordinates:
        return 0.0, 0.0

    avg_lat = sum(coord[0] for coord in coordinates) / len(coordinates)
    avg_long = sum(coord[1] for coord in coordinates) / len(coordinates)

    return avg_lat, avg_long


def calculate_distance_km(
    coord1: Tuple[float, float], coord2: Tuple[float, float]
) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.

    Args:
        coord1: Tuple of (lat, long) for first point
        coord2: Tuple of (lat, long) for second point

    Returns:
        Distance in kilometers
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    # Earth's radius in kilometers
    earth_radius_km = 6371.0

    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    distance = earth_radius_km * c

    return distance


def validate_coordinates(lat: float, long: float) -> bool:
    """
    Validate if coordinates are within valid geographic ranges.

    Args:
        lat: Latitude (-90 to 90)
        long: Longitude (-180 to 180)

    Returns:
        True if coordinates are valid, False otherwise
    """
    if lat < -90 or lat > 90:
        return False
    if long < -180 or long > 180:
        return False
    return True

