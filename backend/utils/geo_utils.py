"""
Geographic utility functions for the PEI Platform.
Provides distance calculations and centroid computations for OT assignments.
"""

import math
from typing import List, Tuple


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two geographic coordinates using Haversine formula.
    
    The Haversine formula calculates the great-circle distance between two points
    on a sphere given their longitudes and latitudes. This is the most accurate
    method for calculating distances on Earth without accounting for elevation.
    
    Args:
        lat1: Latitude of first point in degrees
        lon1: Longitude of first point in degrees
        lat2: Latitude of second point in degrees
        lon2: Longitude of second point in degrees
        
    Returns:
        Distance in kilometers between the two points
        
    Example:
        >>> distance = calculate_distance(-0.22, -78.51, -0.25, -78.48)
        >>> print(f"Distance: {distance:.2f} km")
        Distance: 3.45 km
    """
    # Earth's radius in kilometers
    earth_radius_km = 6371.0

    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Differences in coordinates
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Haversine formula
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    # Calculate the distance
    distance = earth_radius_km * c

    return distance


def calculate_centroid(coordinates_list: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Calculate the geographic centroid of a list of coordinates.
    
    Computes the average latitude and longitude of a list of (lat, lon) tuples.
    This is a simple arithmetic mean, suitable for small geographic areas
    (e.g., within a city or region). For very large areas or globally
    distributed points, more sophisticated methods may be needed.
    
    Args:
        coordinates_list: List of (latitude, longitude) tuples in degrees
        
    Returns:
        Tuple of (centroid_latitude, centroid_longitude)
        Returns (0.0, 0.0) if the list is empty
        
    Example:
        >>> coords = [(-0.22, -78.51), (-0.25, -78.48), (-0.20, -78.50)]
        >>> centroid = calculate_centroid(coords)
        >>> print(f"Centroid: {centroid[0]:.4f}, {centroid[1]:.4f}")
        Centroid: -0.2233, -78.4967
    """
    # Handle empty list
    if not coordinates_list or len(coordinates_list) == 0:
        return (0.0, 0.0)

    # Sum all latitudes and longitudes
    total_lat = sum(coord[0] for coord in coordinates_list)
    total_lon = sum(coord[1] for coord in coordinates_list)

    # Calculate average
    num_points = len(coordinates_list)
    centroid_lat = total_lat / num_points
    centroid_lon = total_lon / num_points

    return (centroid_lat, centroid_lon)


def is_within_radius(
    point_lat: float,
    point_lon: float,
    centroid_lat: float,
    centroid_lon: float,
    max_distance_km: float,
) -> bool:
    """
    Check if a point is within a specified radius of a centroid.
    
    Uses the Haversine formula to calculate distance and compares it against
    the maximum allowed distance for OT assignment to a cuadrilla.
    
    Args:
        point_lat: Latitude of the point to check (in degrees)
        point_lon: Longitude of the point to check (in degrees)
        centroid_lat: Latitude of the centroid (in degrees)
        centroid_lon: Longitude of the centroid (in degrees)
        max_distance_km: Maximum allowed distance in kilometers
        
    Returns:
        True if distance <= max_distance_km, False otherwise
        
    Example:
        >>> within = is_within_radius(-0.22, -78.51, -0.25, -78.48, 10.0)
        >>> print(f"Within 10km: {within}")
        Within 10km: True
    """
    distance = calculate_distance(point_lat, point_lon, centroid_lat, centroid_lon)
    return distance <= max_distance_km

