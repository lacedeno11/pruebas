"""Geographic calculation utilities for PEI Agéntico platform."""

from math import radians, cos, sin, asin, sqrt
from typing import List, Tuple, Optional


class GeoError(Exception):
    """Custom exception for geographic calculation errors."""
    pass


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on earth (specified in decimal degrees).
    
    Args:
        lat1: Latitude of first point in decimal degrees
        lon1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lon2: Longitude of second point in decimal degrees
    
    Returns:
        Distance in kilometers
    """
    try:
        # Convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r
    except (TypeError, ValueError) as e:
        raise GeoError(f"Invalid coordinates for distance calculation: {e}")


def calculate_centroid(coordinates_list: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Calculate the centroid (center point) of a list of coordinates.
    
    Args:
        coordinates_list: List of (latitude, longitude) tuples
    
    Returns:
        Tuple of (centroid_latitude, centroid_longitude)
    
    Raises:
        GeoError: If the list is empty or contains invalid coordinates
    """
    if not coordinates_list:
        raise GeoError("Cannot calculate centroid for empty coordinate list")
    
    if len(coordinates_list) == 1:
        return coordinates_list[0]
    
    try:
        total_lat = sum(lat for lat, lon in coordinates_list)
        total_lon = sum(lon for lat, lon in coordinates_list)
        
        centroid_lat = total_lat / len(coordinates_list)
        centroid_lon = total_lon / len(coordinates_list)
        
        return (centroid_lat, centroid_lon)
    except (TypeError, ValueError) as e:
        raise GeoError(f"Invalid coordinates in list: {e}")


def validate_ecuador_bounds(lat: float, lon: float) -> bool:
    """
    Validate if coordinates are within Ecuador's approximate geographic bounds.
    
    Ecuador bounds (approximate):
    - Latitude: -5 to 2 (north-south)
    - Longitude: -92 to -75 (east-west)
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
    
    Returns:
        True if coordinates are within Ecuador bounds, False otherwise
    """
    try:
        # Ecuador approximate bounds
        lat_min, lat_max = -5.0, 2.0
        lon_min, lon_max = -92.0, -75.0
        
        lat = float(lat)
        lon = float(lon)
        
        return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max
    except (TypeError, ValueError):
        return False

