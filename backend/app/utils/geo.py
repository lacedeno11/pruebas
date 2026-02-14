"""
Geographic calculation utilities for PEI Agentic Platform.
Provides geospatial functions for crew assignment planning and validation.

Functions in this module are used by:
- PlanificacionAgent: For centroid calculations and distance validation
- Geo tools in LangGraph: For assignment constraint checking
- OTS Agent: For coordinate validation
"""

import math
from typing import List, Optional, Tuple

# ============================================================================
# CONSTANTS
# ============================================================================

# Earth's radius in kilometers (for Haversine formula)
EARTH_RADIUS_KM = 6371.0

# Valid coordinate ranges
LAT_MIN = -90.0
LAT_MAX = 90.0
LONG_MIN = -180.0
LONG_MAX = 180.0

# Ecuador-specific bounds (for reference/validation)
ECUADOR_LAT_MIN = -5.5
ECUADOR_LAT_MAX = 1.5
ECUADOR_LONG_MIN = -81.5
ECUADOR_LONG_MAX = -74.5


# ============================================================================
# COORDINATE VALIDATION
# ============================================================================


def validate_coordinates(lat: float, long: float) -> bool:
    """
    Validate that coordinates are within valid ranges.
    
    Checks:
    - Latitude: -90 to 90 degrees
    - Longitude: -180 to 180 degrees
    
    Args:
        lat: Latitude coordinate in decimal degrees
        long: Longitude coordinate in decimal degrees
        
    Returns:
        bool: True if coordinates are valid, False otherwise
        
    Example:
        >>> validate_coordinates(-0.22, -78.51)  # Quito, Ecuador
        True
        >>> validate_coordinates(91.0, 0.0)  # Invalid latitude
        False
        >>> validate_coordinates(0.0, 181.0)  # Invalid longitude
        False
    """
    return (
        LAT_MIN <= lat <= LAT_MAX and
        LONG_MIN <= long <= LONG_MAX
    )


def validate_coordinates_ecuador(lat: float, long: float) -> bool:
    """
    Validate that coordinates are within Ecuador bounds.
    
    Stricter validation for Ecuador-specific operations.
    
    Args:
        lat: Latitude coordinate in decimal degrees
        long: Longitude coordinate in decimal degrees
        
    Returns:
        bool: True if coordinates are within Ecuador, False otherwise
        
    Example:
        >>> validate_coordinates_ecuador(-0.22, -78.51)  # Quito
        True
        >>> validate_coordinates_ecuador(40.0, -100.0)  # USA
        False
    """
    return (
        ECUADOR_LAT_MIN <= lat <= ECUADOR_LAT_MAX and
        ECUADOR_LONG_MIN <= long <= ECUADOR_LONG_MAX
    )


def are_coordinates_valid(coordinates: List[Tuple[float, float]]) -> bool:
    """
    Validate a list of coordinates.
    
    Args:
        coordinates: List of (lat, long) tuples
        
    Returns:
        bool: True if all coordinates are valid
        
    Example:
        >>> coords = [(-0.22, -78.51), (-1.83, -78.18), (-2.20, -79.87)]
        >>> are_coordinates_valid(coords)
        True
    """
    return all(
        validate_coordinates(lat, long)
        for lat, long in coordinates
    )


# ============================================================================
# CENTROID CALCULATION
# ============================================================================


def calculate_centroid(
    coordinates: List[Tuple[float, float]],
) -> Tuple[float, float]:
    """
    Calculate the geographic centroid of a list of coordinates.
    
    Uses arithmetic mean of latitude and longitude.
    Simple but effective for clusters within <50km radius.
    
    Args:
        coordinates: List of (lat, long) tuples
        
    Returns:
        Tuple[float, float]: (centroid_lat, centroid_long)
        
    Raises:
        ValueError: If coordinates list is empty
        
    Example:
        >>> coords = [(-0.22, -78.51), (-1.83, -78.18), (-2.20, -79.87)]
        >>> lat, long = calculate_centroid(coords)
        >>> round(lat, 2), round(long, 2)
        (-1.42, -78.85)
    """
    if not coordinates:
        raise ValueError("Coordinates list cannot be empty")

    if not are_coordinates_valid(coordinates):
        raise ValueError("Invalid coordinates in list")

    # Calculate arithmetic mean
    n = len(coordinates)
    lat_sum = sum(lat for lat, _ in coordinates)
    long_sum = sum(long for _, long in coordinates)

    centroid_lat = lat_sum / n
    centroid_long = long_sum / n

    return (centroid_lat, centroid_long)


def calculate_centroid_cartesian(
    coordinates: List[Tuple[float, float]],
) -> Tuple[float, float]:
    """
    Calculate geographic centroid using Cartesian coordinates.
    
    More accurate for large geographic areas by converting to 3D Cartesian,
    computing mean, and converting back to lat/long.
    
    Useful for clusters spanning >50km, though arithmetic mean is typically
    sufficient for crew assignments (max 10km constraint).
    
    Args:
        coordinates: List of (lat, long) tuples
        
    Returns:
        Tuple[float, float]: (centroid_lat, centroid_long)
        
    Raises:
        ValueError: If coordinates list is empty or invalid
        
    Example:
        >>> coords = [(-0.22, -78.51), (-1.83, -78.18), (-2.20, -79.87)]
        >>> lat, long = calculate_centroid_cartesian(coords)
        >>> isinstance(lat, float) and isinstance(long, float)
        True
    """
    if not coordinates:
        raise ValueError("Coordinates list cannot be empty")

    if not are_coordinates_valid(coordinates):
        raise ValueError("Invalid coordinates in list")

    # Convert to radians
    n = len(coordinates)
    x_sum = 0.0
    y_sum = 0.0
    z_sum = 0.0

    for lat_deg, long_deg in coordinates:
        # Convert to radians
        lat_rad = math.radians(lat_deg)
        long_rad = math.radians(long_deg)

        # Convert to Cartesian coordinates on unit sphere
        x = math.cos(lat_rad) * math.cos(long_rad)
        y = math.cos(lat_rad) * math.sin(long_rad)
        z = math.sin(lat_rad)

        x_sum += x
        y_sum += y
        z_sum += z

    # Calculate mean
    x_mean = x_sum / n
    y_mean = y_sum / n
    z_mean = z_sum / n

    # Convert back to lat/long
    centroid_long_rad = math.atan2(y_mean, x_mean)
    centroid_lat_rad = math.atan2(z_mean, math.sqrt(x_mean**2 + y_mean**2))

    centroid_lat = math.degrees(centroid_lat_rad)
    centroid_long = math.degrees(centroid_long_rad)

    return (centroid_lat, centroid_long)


# ============================================================================
# DISTANCE CALCULATION (HAVERSINE FORMULA)
# ============================================================================


def haversine_distance(
    coord1: Tuple[float, float],
    coord2: Tuple[float, float],
) -> float:
    """
    Calculate the great-circle distance between two points using Haversine formula.
    
    Returns distance in kilometers.
    Accurate for distances up to several thousand kilometers.
    
    Formula:
        a = sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlong/2)
        c = 2 * atan2(√a, √(1−a))
        d = R * c
    
    Args:
        coord1: (lat, long) tuple for first point in decimal degrees
        coord2: (lat, long) tuple for second point in decimal degrees
        
    Returns:
        float: Distance in kilometers
        
    Raises:
        ValueError: If coordinates are invalid
        
    Example:
        >>> # Distance from Quito to Guayaquil
        >>> quito = (-0.22, -78.51)
        >>> guayaquil = (-2.20, -79.87)
        >>> distance = haversine_distance(quito, guayaquil)
        >>> 180 < distance < 200  # Approximately 190km
        True
    """
    lat1, long1 = coord1
    lat2, long2 = coord2

    # Validate coordinates
    if not validate_coordinates(lat1, long1):
        raise ValueError(f"Invalid first coordinate: ({lat1}, {long1})")
    if not validate_coordinates(lat2, long2):
        raise ValueError(f"Invalid second coordinate: ({lat2}, {long2})")

    # Convert to radians
    lat1_rad = math.radians(lat1)
    long1_rad = math.radians(long1)
    lat2_rad = math.radians(lat2)
    long2_rad = math.radians(long2)

    # Haversine formula
    delta_lat = lat2_rad - lat1_rad
    delta_long = long2_rad - long1_rad

    a = (
        math.sin(delta_lat / 2) ** 2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_long / 2) ** 2
    )

    c = 2 * math.asin(math.sqrt(a))

    # Distance in kilometers
    distance = EARTH_RADIUS_KM * c

    return distance


def bearing_between(
    coord1: Tuple[float, float],
    coord2: Tuple[float, float],
) -> float:
    """
    Calculate the bearing (initial direction) from coord1 to coord2.
    
    Returns bearing in degrees (0-360), where:
    - 0° = North
    - 90° = East
    - 180° = South
    - 270° = West
    
    Args:
        coord1: (lat, long) tuple for starting point
        coord2: (lat, long) tuple for ending point
        
    Returns:
        float: Bearing in degrees (0-360)
        
    Example:
        >>> quito = (-0.22, -78.51)
        >>> guayaquil = (-2.20, -79.87)
        >>> bearing = bearing_between(quito, guayaquil)
        >>> 190 < bearing < 230  # Southwest direction
        True
    """
    lat1, long1 = coord1
    lat2, long2 = coord2

    # Convert to radians
    lat1_rad = math.radians(lat1)
    long1_rad = math.radians(long1)
    lat2_rad = math.radians(lat2)
    long2_rad = math.radians(long2)

    # Calculate bearing
    delta_long = long2_rad - long1_rad

    x = math.sin(delta_long) * math.cos(lat2_rad)
    y = (
        math.cos(lat1_rad) * math.sin(lat2_rad) -
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_long)
    )

    bearing_rad = math.atan2(x, y)
    bearing_deg = math.degrees(bearing_rad)

    # Normalize to 0-360 range
    bearing_deg = (bearing_deg + 360) % 360

    return bearing_deg


# ============================================================================
# DISTANCE CONSTRAINT CHECKING
# ============================================================================


def is_within_radius(
    center: Tuple[float, float],
    point: Tuple[float, float],
    radius_km: float,
) -> bool:
    """
    Check if a point is within a radius of a center point.
    
    Used by PlanificacionAgent Phase 2 to verify distance constraints.
    
    Args:
        center: (lat, long) center point
        point: (lat, long) point to check
        radius_km: Radius in kilometers
        
    Returns:
        bool: True if point is within radius, False otherwise
        
    Example:
        >>> quito = (-0.22, -78.51)
        >>> nearby_point = (-0.30, -78.45)
        >>> is_within_radius(quito, nearby_point, 10.0)
        True
    """
    distance = haversine_distance(center, point)
    return distance <= radius_km


def get_distance_from_radius(
    center: Tuple[float, float],
    point: Tuple[float, float],
    radius_km: float,
) -> float:
    """
    Get how far a point is from being outside a radius.
    
    Positive value means point is within radius.
    Negative value means point is outside radius.
    
    Args:
        center: (lat, long) center point
        point: (lat, long) point to check
        radius_km: Radius in kilometers
        
    Returns:
        float: Difference between radius and actual distance (km)
        
    Example:
        >>> quito = (-0.22, -78.51)
        >>> nearby = (-0.30, -78.45)
        >>> margin = get_distance_from_radius(quito, nearby, 10.0)
        >>> margin > 0  # Within radius
        True
    """
    distance = haversine_distance(center, point)
    return radius_km - distance


# ============================================================================
# BOUNDING BOX OPERATIONS
# ============================================================================


def get_bounding_box(
    center: Tuple[float, float],
    radius_km: float,
) -> Tuple[float, float, float, float]:
    """
    Get bounding box (lat_min, lat_max, long_min, long_max) for a circular area.
    
    Useful for approximate geographic queries before detailed calculations.
    
    Args:
        center: (lat, long) center point
        radius_km: Radius in kilometers
        
    Returns:
        Tuple[float, float, float, float]: (lat_min, lat_max, long_min, long_max)
        
    Example:
        >>> quito = (-0.22, -78.51)
        >>> bbox = get_bounding_box(quito, 10.0)
        >>> len(bbox)
        4
    """
    lat, long = center

    # Approximate degrees per km
    # At equator: 1° latitude ≈ 111 km, 1° longitude varies by latitude
    lat_delta = radius_km / 111.0
    long_delta = radius_km / (111.0 * math.cos(math.radians(lat)))

    lat_min = lat - lat_delta
    lat_max = lat + lat_delta
    long_min = long - long_delta
    long_max = long + long_delta

    return (lat_min, lat_max, long_min, long_max)


def point_in_bounding_box(
    point: Tuple[float, float],
    bbox: Tuple[float, float, float, float],
) -> bool:
    """
    Check if a point is within a bounding box.
    
    Args:
        point: (lat, long) point to check
        bbox: (lat_min, lat_max, long_min, long_max) bounding box
        
    Returns:
        bool: True if point is within bounding box
        
    Example:
        >>> point = (-0.25, -78.50)
        >>> bbox = (-1.0, 1.0, -79.0, -78.0)
        >>> point_in_bounding_box(point, bbox)
        True
    """
    lat, long = point
    lat_min, lat_max, long_min, long_max = bbox

    return (
        lat_min <= lat <= lat_max and
        long_min <= long <= long_max
    )


# ============================================================================
# POINT IN POLYGON (FOR ADVANCED GEOGRAPHIC OPERATIONS)
# ============================================================================


def point_in_polygon(
    point: Tuple[float, float],
    polygon: List[Tuple[float, float]],
) -> bool:
    """
    Check if a point is inside a polygon using ray casting algorithm.
    
    Useful for checking if coordinates are within geographic regions.
    
    Args:
        point: (lat, long) point to check
        polygon: List of (lat, long) tuples forming polygon boundary
                 (must be closed: first point == last point)
        
    Returns:
        bool: True if point is inside polygon
        
    Example:
        >>> # Triangle polygon
        >>> polygon = [(0, 0), (1, 0), (0.5, 1), (0, 0)]
        >>> point_in_polygon((0.3, 0.3), polygon)
        True
    """
    if len(polygon) < 3:
        return False

    lat, long = point

    # Ray casting algorithm
    inside = False
    j = len(polygon) - 1

    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]

        if (
            ((yi > long) != (yj > long)) and
            (lat < (xj - xi) * (long - yi) / (yj - yi) + xi)
        ):
            inside = not inside

        j = i

    return inside


# ============================================================================
# DEBUGGING & FORMATTING
# ============================================================================


def format_coordinates(
    lat: float,
    long: float,
    decimal_places: int = 4,
) -> str:
    """
    Format coordinates as human-readable string with degree symbols.
    
    Args:
        lat: Latitude
        long: Longitude
        decimal_places: Number of decimal places
        
    Returns:
        str: Formatted coordinate string
        
    Example:
        >>> format_coordinates(-0.22, -78.51)
        '-0.22°, -78.51°'
    """
    format_str = f"{{:.{decimal_places}f}}"
    lat_str = format_str.format(lat)
    long_str = format_str.format(long)
    return f"{lat_str}°, {long_str}°"


def distance_string(distance_km: float) -> str:
    """
    Format distance for display.
    
    Args:
        distance_km: Distance in kilometers
        
    Returns:
        str: Formatted distance string
        
    Example:
        >>> distance_string(190.5)
        '190.5 km'
    """
    return f"{distance_km:.1f} km"

