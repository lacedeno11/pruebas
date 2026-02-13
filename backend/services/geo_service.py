"""
Geographic Service for distance calculations and coordinate validation.
Provides geospatial utilities for the planning algorithm.
"""

from typing import List, Tuple, Optional
from statistics import mean
from geopy.distance import distance as geopy_distance
from geopy.point import Point


class GeoService:
    """
    Service for geographic calculations and coordinate validation.
    
    Provides methods for:
    - Distance calculation between two points using Haversine formula
    - Centroid calculation from multiple coordinates
    - Radius checking for proximity-based assignment
    - Coordinate validation
    """

    # Earth coordinates limits
    LAT_MIN = -90.0
    LAT_MAX = 90.0
    LONG_MIN = -180.0
    LONG_MAX = 180.0

    @staticmethod
    def validate_coordinates(lat: Optional[float], long: Optional[float]) -> bool:
        """
        Validate geographic coordinates.
        
        Args:
            lat: Latitude coordinate
            long: Longitude coordinate
            
        Returns:
            True if coordinates are valid, False otherwise
        """
        if lat is None or long is None:
            return False
        
        try:
            lat_float = float(lat)
            long_float = float(long)
            
            return (
                GeoService.LAT_MIN <= lat_float <= GeoService.LAT_MAX and
                GeoService.LONG_MIN <= long_float <= GeoService.LONG_MAX
            )
        except (TypeError, ValueError):
            return False

    @staticmethod
    def calculate_distance_km(
        lat1: float, long1: float, lat2: float, long2: float
    ) -> float:
        """
        Calculate distance between two geographic points using Haversine formula.
        
        Args:
            lat1: First point latitude
            long1: First point longitude
            lat2: Second point latitude
            long2: Second point longitude
            
        Returns:
            Distance in kilometers (float)
            
        Raises:
            ValueError: If any coordinate is invalid
        """
        if not GeoService.validate_coordinates(lat1, long1):
            raise ValueError(f"Invalid coordinates for first point: ({lat1}, {long1})")
        if not GeoService.validate_coordinates(lat2, long2):
            raise ValueError(f"Invalid coordinates for second point: ({lat2}, {long2})")
        
        try:
            point1 = Point(latitude=lat1, longitude=long1)
            point2 = Point(latitude=lat2, longitude=long2)
            
            # distance() returns a Distance object; .km gives kilometers
            distance_km = geopy_distance(point1, point2).km
            return round(distance_km, 4)
        except Exception as e:
            raise ValueError(f"Error calculating distance: {str(e)}")

    @staticmethod
    def calculate_centroid(
        coordinates: List[Tuple[float, float]]
    ) -> Tuple[float, float]:
        """
        Calculate geographic centroid from a list of coordinates.
        
        The centroid is computed as the mean of all latitudes and longitudes.
        This provides a simple center point for proximity calculations.
        
        Args:
            coordinates: List of (latitude, longitude) tuples
            
        Returns:
            Tuple of (centroid_latitude, centroid_longitude)
            
        Raises:
            ValueError: If coordinates list is empty or contains invalid coordinates
        """
        if not coordinates:
            raise ValueError("Coordinates list cannot be empty")
        
        # Validate all coordinates
        for lat, long in coordinates:
            if not GeoService.validate_coordinates(lat, long):
                raise ValueError(
                    f"Invalid coordinate in list: ({lat}, {long})"
                )
        
        try:
            latitudes = [coord[0] for coord in coordinates]
            longitudes = [coord[1] for coord in coordinates]
            
            centroid_lat = round(mean(latitudes), 4)
            centroid_long = round(mean(longitudes), 4)
            
            return (centroid_lat, centroid_long)
        except Exception as e:
            raise ValueError(f"Error calculating centroid: {str(e)}")

    @staticmethod
    def is_within_radius(
        point_lat: float,
        point_long: float,
        centroid_lat: float,
        centroid_long: float,
        radius_km: float = 10.0,
    ) -> bool:
        """
        Check if a point is within a specified radius of a centroid.
        
        This is used in Phase 2 of the planning algorithm to determine if
        a new OT can be assigned to a crew based on proximity to their
        current work centroid.
        
        Args:
            point_lat: Point latitude
            point_long: Point longitude
            centroid_lat: Centroid latitude
            centroid_long: Centroid longitude
            radius_km: Radius in kilometers (default: 10.0)
            
        Returns:
            True if point is within radius, False otherwise
            
        Raises:
            ValueError: If any coordinate is invalid or radius is negative
        """
        if radius_km < 0:
            raise ValueError("Radius cannot be negative")
        
        if not GeoService.validate_coordinates(point_lat, point_long):
            raise ValueError(f"Invalid point coordinates: ({point_lat}, {point_long})")
        
        if not GeoService.validate_coordinates(centroid_lat, centroid_long):
            raise ValueError(
                f"Invalid centroid coordinates: ({centroid_lat}, {centroid_long})"
            )
        
        try:
            distance = GeoService.calculate_distance_km(
                point_lat, point_long, centroid_lat, centroid_long
            )
            return distance < radius_km
        except ValueError as e:
            raise ValueError(f"Error checking radius: {str(e)}")

    @staticmethod
    def get_bounding_box(
        coordinates: List[Tuple[float, float]]
    ) -> Tuple[float, float, float, float]:
        """
        Calculate bounding box for a set of coordinates.
        
        Useful for map visualization and geographic analysis.
        
        Args:
            coordinates: List of (latitude, longitude) tuples
            
        Returns:
            Tuple of (min_lat, max_lat, min_long, max_long)
            
        Raises:
            ValueError: If coordinates list is empty or contains invalid coordinates
        """
        if not coordinates:
            raise ValueError("Coordinates list cannot be empty")
        
        # Validate all coordinates
        for lat, long in coordinates:
            if not GeoService.validate_coordinates(lat, long):
                raise ValueError(f"Invalid coordinate: ({lat}, {long})")
        
        latitudes = [coord[0] for coord in coordinates]
        longitudes = [coord[1] for coord in coordinates]
        
        return (
            min(latitudes),
            max(latitudes),
            min(longitudes),
            max(longitudes),
        )

    @staticmethod
    def interpolate_point(
        lat1: float, long1: float, lat2: float, long2: float, ratio: float = 0.5
    ) -> Tuple[float, float]:
        """
        Interpolate a point between two coordinates.
        
        Useful for visualizing paths or intermediate waypoints.
        
        Args:
            lat1: First point latitude
            long1: First point longitude
            lat2: Second point latitude
            long2: Second point longitude
            ratio: Interpolation ratio (0.0 to 1.0, default: 0.5 for midpoint)
            
        Returns:
            Tuple of interpolated (latitude, longitude)
            
        Raises:
            ValueError: If coordinates are invalid or ratio is out of range
        """
        if not 0.0 <= ratio <= 1.0:
            raise ValueError("Ratio must be between 0.0 and 1.0")
        
        if not GeoService.validate_coordinates(lat1, long1):
            raise ValueError(f"Invalid first point: ({lat1}, {long1})")
        
        if not GeoService.validate_coordinates(lat2, long2):
            raise ValueError(f"Invalid second point: ({lat2}, {long2})")
        
        interpolated_lat = lat1 + (lat2 - lat1) * ratio
        interpolated_long = long1 + (long2 - long1) * ratio
        
        return (round(interpolated_lat, 4), round(interpolated_long, 4))


# Global instance
geo_service = GeoService()

