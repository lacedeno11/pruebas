import math
from typing import List, Tuple


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on the earth (specified in decimal degrees).
    
    Args:
        lat1: Latitude of first point in decimal degrees
        lon1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lon2: Longitude of second point in decimal degrees
    
    Returns:
        Distance in kilometers
    """
    # Earth's radius in kilometers
    EARTH_RADIUS_KM = 6371.0
    
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    distance = EARTH_RADIUS_KM * c
    
    return distance


def calculate_centroid(coordinates: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Calculate the geographic centroid from a list of (latitude, longitude) tuples.
    
    Args:
        coordinates: List of tuples containing (lat, lon) pairs
    
    Returns:
        Tuple of (centroid_lat, centroid_lon)
    
    Raises:
        ValueError: If coordinates list is empty
    """
    if not coordinates:
        raise ValueError("Coordinates list cannot be empty")
    
    total_lat = sum(coord[0] for coord in coordinates)
    total_lon = sum(coord[1] for coord in coordinates)
    count = len(coordinates)
    
    centroid_lat = total_lat / count
    centroid_lon = total_lon / count
    
    return centroid_lat, centroid_lon


def is_within_radius(
    center_lat: float,
    center_lon: float,
    point_lat: float,
    point_lon: float,
    radius_km: float,
) -> bool:
    """
    Check if a point is within a specified radius of a center point.
    
    Args:
        center_lat: Latitude of center point in decimal degrees
        center_lon: Longitude of center point in decimal degrees
        point_lat: Latitude of point to check in decimal degrees
        point_lon: Longitude of point to check in decimal degrees
        radius_km: Radius in kilometers
    
    Returns:
        True if point is within radius, False otherwise
    """
    distance = haversine_distance(center_lat, center_lon, point_lat, point_lon)
    return distance <= radius_km

