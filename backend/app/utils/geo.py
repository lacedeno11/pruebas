from typing import List, Tuple
from geopy.distance import geodesic


def calculate_centroid(coordinates: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Calculate the centroid (mean) of a list of (lat, long) coordinates
    """
    if not coordinates:
        return (0, 0)
    
    avg_lat = sum(coord[0] for coord in coordinates) / len(coordinates)
    avg_long = sum(coord[1] for coord in coordinates) / len(coordinates)
    
    return (avg_lat, avg_long)


def calculate_distance_km(
    coord1: Tuple[float, float],
    coord2: Tuple[float, float]
) -> float:
    """
    Calculate distance in kilometers between two coordinates using Haversine formula
    """
    distance = geodesic(coord1, coord2).kilometers
    return distance


def is_within_radius(
    point: Tuple[float, float],
    center: Tuple[float, float],
    radius_km: float
) -> bool:
    """
    Check if a point is within a radius (in km) of a center point
    """
    distance = calculate_distance_km(point, center)
    return distance < radius_km


def validate_ecuador_bounds(lat: float, long: float) -> bool:
    """
    Validate that coordinates are within Ecuador geographic bounds
    Ecuador: lat -5 to 2, long -92 to -75
    """
    return -5 <= lat <= 2 and -92 <= long <= -75

