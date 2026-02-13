"""
Geographic utility functions for crew assignment and location calculations.

This module provides:
- Haversine distance calculation between two geographic points
- Centroid calculation for multiple coordinates
- Input validation for geographic data

Used by:
- PlanningService: Distance validation in <10km proximity assignment (Phase 2)
- CuadrillaService: Centroid updates for crew assignment zones
- Planning algorithms: Route optimization and crew allocation
"""

import math
from typing import List, Tuple


# Earth's radius in kilometers (WGS84)
EARTH_RADIUS_KM = 6371.0


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate distance between two geographic points using Haversine formula.
    
    The Haversine formula provides accurate distance calculations for points
    on a sphere, accounting for the Earth's curvature. It avoids issues with
    small distance approximations that occur with other methods.
    
    Formula:
        a = sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlon/2)
        c = 2 * atan2(√a, √(1−a))
        d = R * c
    
    Where:
        R = Earth radius (6371 km)
        Δlat = lat2 - lat1 (in radians)
        Δlon = lon2 - lon1 (in radians)
    
    Args:
        lat1: Latitude of first point in decimal degrees (-90 to 90)
        lon1: Longitude of first point in decimal degrees (-180 to 180)
        lat2: Latitude of second point in decimal degrees (-90 to 90)
        lon2: Longitude of second point in decimal degrees (-180 to 180)
    
    Returns:
        Distance in kilometers (float)
    
    Raises:
        ValueError: If coordinates are outside valid ranges
    
    Example:
        >>> # Distance between two points in Quito, Ecuador
        >>> distance = haversine_distance(-0.1807, -78.4678, -0.2265, -78.5245)
        >>> print(f"{distance:.2f} km")  # ~7.5 km
        
        >>> # Distance from point to itself
        >>> distance = haversine_distance(-0.1807, -78.4678, -0.1807, -78.4678)
        >>> print(distance)  # 0.0
    """
    # Validate input coordinates
    if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90):
        raise ValueError("Latitude must be between -90 and 90 degrees")
    if not (-180 <= lon1 <= 180 and -180 <= lon2 <= 180):
        raise ValueError("Longitude must be between -180 and 180 degrees")

    # Convert decimal degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Calculate differences
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )

    # Ensure 'a' is in valid range for sqrt [0, 1]
    # Due to floating-point errors, a might be slightly > 1
    a = min(1.0, a)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Calculate final distance
    distance = EARTH_RADIUS_KM * c

    return distance


def calculate_centroid(locations: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Calculate the centroid (average location) of multiple geographic points.
    
    The centroid is computed as the simple average of all latitude and longitude
    coordinates. This approach is suitable for small geographic areas (< 100 km)
    like a city region. For larger areas, a more sophisticated approach
    (converting to Cartesian coordinates) might be necessary.
    
    Args:
        locations: List of (latitude, longitude) tuples in decimal degrees.
                   Each tuple should have valid coordinates:
                   - Latitude: -90 to 90
                   - Longitude: -180 to 180
    
    Returns:
        Tuple of (centroid_latitude, centroid_longitude) in decimal degrees
    
    Raises:
        ValueError: If locations list is empty or contains invalid coordinates
    
    Example:
        >>> # Three points in Quito area
        >>> points = [
        ...     (-0.1807, -78.4678),  # Downtown Quito
        ...     (-0.2265, -78.5245),  # South Quito
        ...     (-0.1500, -78.5000),  # East Quito
        ... ]
        >>> centroid = calculate_centroid(points)
        >>> print(f"Centroid: {centroid[0]:.4f}, {centroid[1]:.4f}")
        # Centroid: -0.1857, -78.4975
        
        >>> # Single point
        >>> centroid = calculate_centroid([(-0.1807, -78.4678)])
        >>> print(centroid)  # (-0.1807, -78.4678)
        
        >>> # Empty list raises error
        >>> centroid = calculate_centroid([])  # ValueError: locations list cannot be empty
    """
    # Validate input
    if not locations:
        raise ValueError("locations list cannot be empty")

    if len(locations) == 0:
        raise ValueError("locations list cannot be empty")

    # Validate each coordinate
    for i, (lat, lon) in enumerate(locations):
        if not (-90 <= lat <= 90):
            raise ValueError(
                f"Invalid latitude {lat} at index {i}: must be between -90 and 90"
            )
        if not (-180 <= lon <= 180):
            raise ValueError(
                f"Invalid longitude {lon} at index {i}: must be between -180 and 180"
            )

    # Calculate average latitude and longitude
    avg_lat = sum(lat for lat, lon in locations) / len(locations)
    avg_lon = sum(lon for lat, lon in locations) / len(locations)

    return (avg_lat, avg_lon)


def is_within_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    distance_km: float,
) -> bool:
    """
    Check if two points are within a specified distance of each other.
    
    Convenience function that combines haversine_distance with a threshold check.
    Used primarily in Phase 2 of the planning algorithm to validate if an OT
    is within the <10km centroid proximity rule.
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
        distance_km: Maximum distance threshold in kilometers
    
    Returns:
        True if distance is less than or equal to threshold, False otherwise
    
    Example:
        >>> # Check if OT is within 10km of crew centroid
        >>> within_range = is_within_distance(
        ...     ot_lat=-0.1807, ot_lon=-78.4678,
        ...     centroid_lat=-0.1900, centroid_lon=-78.4700,
        ...     distance_km=10.0
        ... )
    """
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    return distance <= distance_km


def bearing_between_points(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate initial bearing (direction) from point 1 to point 2.
    
    Useful for route optimization to understand direction of OT movement
    from crew centroid. Returns bearing in degrees (0-360), where:
    - 0° = North
    - 90° = East
    - 180° = South
    - 270° = West
    
    Args:
        lat1: Latitude of starting point
        lon1: Longitude of starting point
        lat2: Latitude of destination point
        lon2: Longitude of destination point
    
    Returns:
        Bearing in degrees (0-360)
    
    Example:
        >>> bearing = bearing_between_points(-0.1807, -78.4678, -0.2265, -78.5245)
        >>> print(f"Direction: {bearing:.1f}°")  # ~225° = Southwest
    """
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    delta_lon = lon2_rad - lon1_rad

    y = math.sin(delta_lon) * math.cos(lat2_rad)
    x = (
        math.cos(lat1_rad) * math.sin(lat2_rad)
        - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
    )

    bearing_rad = math.atan2(y, x)
    bearing_deg = math.degrees(bearing_rad)

    # Normalize to 0-360 range
    bearing_deg = (bearing_deg + 360) % 360

    return bearing_deg


def distance_to_line(
    point_lat: float,
    point_lon: float,
    line_start_lat: float,
    line_start_lon: float,
    line_end_lat: float,
    line_end_lon: float,
) -> float:
    """
    Calculate perpendicular distance from a point to a line defined by two points.
    
    Useful for route optimization to determine optimal assignment of OTs
    to minimize crew travel distance between assignments.
    
    Args:
        point_lat: Latitude of the point
        point_lon: Longitude of the point
        line_start_lat: Latitude of line start point
        line_start_lon: Longitude of line start point
        line_end_lat: Latitude of line end point
        line_end_lon: Longitude of line end point
    
    Returns:
        Perpendicular distance in kilometers
    
    Note:
        This is an approximation suitable for small geographic areas.
        For higher precision over larger areas, consider geodetic methods.
    """
    # Distance from point to line start
    dist_start = haversine_distance(
        point_lat, point_lon, line_start_lat, line_start_lon
    )

    # Distance from point to line end
    dist_end = haversine_distance(
        point_lat, point_lon, line_end_lat, line_end_lon
    )

    # Distance along the line
    line_dist = haversine_distance(
        line_start_lat, line_start_lon, line_end_lat, line_end_lon
    )

    # Use triangle inequality to estimate perpendicular distance
    # For a more accurate calculation, this could use the cross product method
    # But for operational purposes, this gives a reasonable approximation
    if line_dist == 0:
        return dist_start

    # Semi-perimeter of triangle
    s = (dist_start + dist_end + line_dist) / 2

    # Heron's formula for triangle area
    area = math.sqrt(
        max(0, s * (s - dist_start) * (s - dist_end) * (s - line_dist))
    )

    # Perpendicular distance = 2 * Area / base
    perp_distance = (2 * area) / line_dist if line_dist > 0 else dist_start

    return perp_distance

