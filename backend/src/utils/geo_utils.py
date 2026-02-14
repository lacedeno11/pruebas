"""
Geographic calculation utilities for PEI Platform.

This module provides functions for geographic distance calculations, centroid computation,
and coordinate validation for Ecuador's geographical boundaries. Uses the Haversine formula
for accurate distance calculations on Earth's surface.
"""

import math
from typing import Tuple


# Earth's radius in kilometers (WGS84 mean radius)
EARTH_RADIUS_KM = 6371.0

# Ecuador geographic bounds (with some margin for safety)
ECUADOR_BOUNDS = {
    "min_lat": -5.0,
    "max_lat": 2.0,
    "min_lon": -81.0,
    "max_lon": -75.0,
}


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth using the Haversine formula.

    This formula provides accurate distances for any two points on the Earth's surface
    and is commonly used for geographic calculations in kilometers.

    Args:
        lat1 (float): Latitude of the first point in decimal degrees
        lon1 (float): Longitude of the first point in decimal degrees
        lat2 (float): Latitude of the second point in decimal degrees
        lon2 (float): Longitude of the second point in decimal degrees

    Returns:
        float: Distance between the two points in kilometers

    Example:
        >>> distance = calculate_distance(-0.3157, -78.5125, -0.2186, -78.5097)
        >>> # Returns approximately 10.5 km (Quito to nearby location)

    Raises:
        ValueError: If coordinates are not valid numbers
    """
    try:
        # Convert decimal degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Differences
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # Haversine formula
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # Distance in kilometers
        distance = EARTH_RADIUS_KM * c
        return round(distance, 2)

    except (TypeError, ValueError) as e:
        raise ValueError(
            f"Invalid coordinates: lat1={lat1}, lon1={lon1}, lat2={lat2}, lon2={lon2}"
        ) from e


def calculate_centroid(coordinates: list[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Calculate the geographic centroid (center) of a set of coordinates.

    The centroid is computed as the arithmetic mean of all latitude and longitude values.
    For a small set of points (as in cuadrilla assignments), this simple approach is
    accurate enough for the 10km proximity checks required by the system.

    Args:
        coordinates (list[Tuple[float, float]]): List of (latitude, longitude) tuples

    Returns:
        Tuple[float, float]: (centroid_latitude, centroid_longitude)

    Raises:
        ValueError: If the coordinate list is empty or contains invalid values

    Example:
        >>> points = [(-0.3157, -78.5125), (-0.2186, -78.5097), (-0.1234, -78.4900)]
        >>> centroid = calculate_centroid(points)
        >>> # Returns approximately (-0.2192, -78.5040)
    """
    if not coordinates:
        raise ValueError("Coordinate list cannot be empty")

    if len(coordinates) == 1:
        return coordinates[0]

    try:
        # Sum all latitudes and longitudes
        total_lat = sum(coord[0] for coord in coordinates)
        total_lon = sum(coord[1] for coord in coordinates)

        # Calculate average
        num_coords = len(coordinates)
        centroid_lat = total_lat / num_coords
        centroid_lon = total_lon / num_coords

        return (round(centroid_lat, 4), round(centroid_lon, 4))

    except (TypeError, IndexError) as e:
        raise ValueError(
            f"Invalid coordinate format in list: {coordinates}"
        ) from e


def is_within_radius(
    point_lat: float,
    point_lon: float,
    center_lat: float,
    center_lon: float,
    radius_km: float = 10.0,
) -> bool:
    """
    Check if a point is within a specified radius of a center point.

    This is used by the Planificación Agent to determine if an OT can be assigned
    to a cuadrilla based on proximity to the cuadrilla's centroid. The default
    radius of 10km is the business rule threshold for assignment decisions.

    Args:
        point_lat (float): Latitude of the point to check
        point_lon (float): Longitude of the point to check
        center_lat (float): Latitude of the center/centroid
        center_lon (float): Longitude of the center/centroid
        radius_km (float): Radius threshold in kilometers (default: 10.0)

    Returns:
        bool: True if the point is within the radius of the center, False otherwise

    Example:
        >>> # Check if an OT is within 10km of cuadrilla centroid
        >>> within = is_within_radius(-0.2186, -78.5097, -0.3157, -78.5125, 10.0)
        >>> # Returns True if distance is < 10km

    Raises:
        ValueError: If coordinates or radius are invalid
    """
    try:
        distance = calculate_distance(point_lat, point_lon, center_lat, center_lon)
        return distance < radius_km

    except ValueError as e:
        raise ValueError(
            f"Cannot check radius for point ({point_lat}, {point_lon}) "
            f"around center ({center_lat}, {center_lon})"
        ) from e


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Validate that coordinates fall within Ecuador's geographic boundaries.

    Ecuador's geographic bounds:
    - Latitude: -5.0 to 2.0 degrees
    - Longitude: -81.0 to -75.0 degrees

    This validation is critical for UC-PEI-01 (OT Download & Registration) to identify
    OTs with geographic errors that require PM notification.

    Args:
        lat (float): Latitude coordinate in decimal degrees
        lon (float): Longitude coordinate in decimal degrees

    Returns:
        bool: True if coordinates are valid (within Ecuador bounds), False otherwise

    Example:
        >>> # Valid Quito coordinates
        >>> validate_coordinates(-0.3157, -78.5125)
        >>> # Returns True

        >>> # Invalid coordinates (outside Ecuador)
        >>> validate_coordinates(40.7128, -74.0060)  # New York
        >>> # Returns False
    """
    try:
        # Check if coordinates are numbers
        lat = float(lat)
        lon = float(lon)

        # Check latitude bounds
        if lat < ECUADOR_BOUNDS["min_lat"] or lat > ECUADOR_BOUNDS["max_lat"]:
            return False

        # Check longitude bounds
        if lon < ECUADOR_BOUNDS["min_lon"] or lon > ECUADOR_BOUNDS["max_lon"]:
            return False

        return True

    except (TypeError, ValueError):
        return False


def get_ecuador_bounds() -> dict:
    """
    Get Ecuador's geographic boundaries.

    Returns:
        dict: Dictionary with min_lat, max_lat, min_lon, max_lon keys
    """
    return ECUADOR_BOUNDS.copy()


def format_coordinates(lat: float, lon: float, precision: int = 4) -> str:
    """
    Format coordinates as a human-readable string.

    Args:
        lat (float): Latitude
        lon (float): Longitude
        precision (int): Number of decimal places (default: 4)

    Returns:
        str: Formatted coordinate string (e.g., "-0.3157, -78.5125")
    """
    return f"{lat:.{precision}f}, {lon:.{precision}f}"

