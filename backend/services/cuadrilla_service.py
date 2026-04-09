"""
Cuadrilla (Crew) Service for crew management and workload calculations.
Handles crew availability, load management, and centroid-based optimization.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    from sqlalchemy.orm import Session
    from sqlalchemy import and_
except ImportError:
    Session = None

from backend.services.geo_service import GeoService

# Configure logging
logger = logging.getLogger(__name__)


class CuadrillaService:
    """
    Service for Cuadrilla (Crew/OPU) management.
    
    Provides methods for:
    - Retrieving available crews for assignment
    - Managing crew workload and capacity
    - Calculating and updating crew centroids
    - Getting crew workload statistics
    """

    @staticmethod
    def get_cuadrilla_by_id(db: Session, cuadrilla_id: int) -> Optional[Any]:
        """
        Retrieve a single crew by ID.
        
        Args:
            db: Database session
            cuadrilla_id: Crew internal ID
            
        Returns:
            Cuadrilla object or None if not found
        """
        if not Session:
            logger.error("SQLAlchemy not available")
            return None

        try:
            from backend.database.models import Cuadrilla

            return db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
        except Exception as e:
            logger.error(f"Error retrieving cuadrilla {cuadrilla_id}: {e}")
            return None

    @staticmethod
    def get_available_cuadrillas(
        db: Session, cuadrilla_type: Optional[str] = None
    ) -> List[Any]:
        """
        Retrieve available crews (not at capacity).
        
        Available crews are those where current_load < capacity.
        These crews are eligible for OT assignment in the planning algorithm.
        
        Args:
            db: Database session
            cuadrilla_type: Optional filter by type (Principal/Reserva)
            
        Returns:
            List of available Cuadrilla objects
        """
        if not Session:
            logger.error("SQLAlchemy not available")
            return []

        try:
            from backend.database.models import Cuadrilla

            query = db.query(Cuadrilla).filter(
                Cuadrilla.current_load < Cuadrilla.capacity
            )

            if cuadrilla_type:
                query = query.filter(Cuadrilla.type == cuadrilla_type)

            # Order by current_load ascending (assign to less loaded crews first)
            query = query.order_by(Cuadrilla.current_load.asc())

            return query.all()
        except Exception as e:
            logger.error(f"Error retrieving available cuadrillas: {e}")
            return []

    @staticmethod
    def get_all_cuadrillas(
        db: Session, cuadrilla_type: Optional[str] = None
    ) -> List[Any]:
        """
        Retrieve all crews, optionally filtered by type.
        
        Args:
            db: Database session
            cuadrilla_type: Optional filter by type (Principal/Reserva)
            
        Returns:
            List of all Cuadrilla objects
        """
        if not Session:
            return []

        try:
            from backend.database.models import Cuadrilla

            query = db.query(Cuadrilla)

            if cuadrilla_type:
                query = query.filter(Cuadrilla.type == cuadrilla_type)

            return query.order_by(Cuadrilla.id).all()
        except Exception as e:
            logger.error(f"Error retrieving all cuadrillas: {e}")
            return []

    @staticmethod
    def update_cuadrilla_load(
        db: Session, cuadrilla_id: int, increment: int
    ) -> Dict[str, Any]:
        """
        Update crew workload (increment or decrement current_load).
        
        Args:
            db: Database session
            cuadrilla_id: Crew ID
            increment: Change in load (positive or negative)
            
        Returns:
            Success/error response with updated load
        """
        if not Session:
            return {
                "success": False,
                "error": "Database not available",
            }

        try:
            from backend.database.models import Cuadrilla

            cuadrilla = db.query(Cuadrilla).filter(
                Cuadrilla.id == cuadrilla_id
            ).first()

            if not cuadrilla:
                return {
                    "success": False,
                    "error": f"Cuadrilla {cuadrilla_id} not found",
                }

            # Calculate new load
            old_load = cuadrilla.current_load
            new_load = old_load + increment

            # Validate new load
            if new_load < 0:
                return {
                    "success": False,
                    "error": f"Cannot reduce load below 0 (current: {old_load}, change: {increment})",
                }

            if new_load > cuadrilla.capacity:
                return {
                    "success": False,
                    "error": f"Load would exceed capacity (current: {old_load}, capacity: {cuadrilla.capacity})",
                }

            # Update load
            cuadrilla.current_load = new_load
            db.commit()
            db.refresh(cuadrilla)

            logger.info(
                f"Cuadrilla {cuadrilla.name} load updated: {old_load} -> {new_load}"
            )

            return {
                "success": True,
                "cuadrilla_id": cuadrilla.id,
                "name": cuadrilla.name,
                "old_load": old_load,
                "new_load": new_load,
                "capacity": cuadrilla.capacity,
                "utilization_percent": round((new_load / cuadrilla.capacity) * 100, 2),
            }
        except Exception as e:
            logger.error(f"Error updating cuadrilla load: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def update_cuadrilla_centroid(db: Session, cuadrilla_id: int) -> Dict[str, Any]:
        """
        Calculate and update crew centroid from assigned OTs.
        
        The centroid is calculated as the mean of all latitude and longitude
        coordinates of OTs currently assigned to the crew.
        
        This is critical for Phase 2 of the planning algorithm (proximity checking).
        
        Args:
            db: Database session
            cuadrilla_id: Crew ID
            
        Returns:
            Success/error response with new centroid coordinates
        """
        if not Session:
            return {
                "success": False,
                "error": "Database not available",
            }

        try:
            from backend.database.models import Cuadrilla, OrdenTrabajo

            # Get crew
            cuadrilla = db.query(Cuadrilla).filter(
                Cuadrilla.id == cuadrilla_id
            ).first()

            if not cuadrilla:
                return {
                    "success": False,
                    "error": f"Cuadrilla {cuadrilla_id} not found",
                }

            # Get assigned OTs with valid coordinates
            assigned_ots = db.query(OrdenTrabajo).filter(
                and_(
                    OrdenTrabajo.cuadrilla_id == cuadrilla_id,
                    OrdenTrabajo.lat.isnot(None),
                    OrdenTrabajo.long.isnot(None),
                )
            ).all()

            if not assigned_ots:
                # No assigned OTs with coordinates - clear centroid
                cuadrilla.last_centroid_lat = None
                cuadrilla.last_centroid_long = None
                db.commit()

                logger.info(
                    f"Cuadrilla {cuadrilla.name} centroid cleared (no assigned OTs)"
                )

                return {
                    "success": True,
                    "cuadrilla_id": cuadrilla.id,
                    "name": cuadrilla.name,
                    "centroid_lat": None,
                    "centroid_long": None,
                    "assigned_ots_count": 0,
                }

            # Calculate centroid from assigned OTs
            coordinates = [(ot.lat, ot.long) for ot in assigned_ots]

            try:
                centroid_lat, centroid_long = GeoService.calculate_centroid(
                    coordinates
                )
            except ValueError as e:
                logger.error(f"Error calculating centroid: {e}")
                return {
                    "success": False,
                    "error": f"Failed to calculate centroid: {e}",
                }

            # Update centroid
            cuadrilla.last_centroid_lat = centroid_lat
            cuadrilla.last_centroid_long = centroid_long
            db.commit()
            db.refresh(cuadrilla)

            logger.info(
                f"Cuadrilla {cuadrilla.name} centroid updated: "
                f"({centroid_lat}, {centroid_long}) from {len(assigned_ots)} OTs"
            )

            return {
                "success": True,
                "cuadrilla_id": cuadrilla.id,
                "name": cuadrilla.name,
                "centroid_lat": centroid_lat,
                "centroid_long": centroid_long,
                "assigned_ots_count": len(assigned_ots),
            }
        except Exception as e:
            logger.error(f"Error updating cuadrilla centroid: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def get_cuadrilla_workload(db: Session, cuadrilla_id: int) -> Dict[str, Any]:
        """
        Get detailed workload information for a crew.
        
        Args:
            db: Database session
            cuadrilla_id: Crew ID
            
        Returns:
            Workload dict with current_load, capacity, utilization, assigned OTs
        """
        if not Session:
            return {}

        try:
            from backend.database.models import Cuadrilla, OrdenTrabajo

            cuadrilla = db.query(Cuadrilla).filter(
                Cuadrilla.id == cuadrilla_id
            ).first()

            if not cuadrilla:
                return {
                    "error": f"Cuadrilla {cuadrilla_id} not found",
                }

            # Get assigned OTs
            assigned_ots = db.query(OrdenTrabajo).filter(
                OrdenTrabajo.cuadrilla_id == cuadrilla_id
            ).all()

            # Calculate statistics
            utilization_percent = round(
                (cuadrilla.current_load / cuadrilla.capacity) * 100, 2
            )
            available_capacity = cuadrilla.capacity - cuadrilla.current_load

            return {
                "cuadrilla_id": cuadrilla.id,
                "name": cuadrilla.name,
                "type": cuadrilla.type,
                "current_load": cuadrilla.current_load,
                "capacity": cuadrilla.capacity,
                "available_capacity": available_capacity,
                "utilization_percent": utilization_percent,
                "assigned_ots_count": len(assigned_ots),
                "assigned_ots": [
                    {
                        "id": ot.id,
                        "external_id": ot.external_id,
                        "status": ot.status,
                        "project_type": ot.project_type,
                        "lat": ot.lat,
                        "long": ot.long,
                    }
                    for ot in assigned_ots
                ],
                "last_centroid_lat": cuadrilla.last_centroid_lat,
                "last_centroid_long": cuadrilla.last_centroid_long,
                "is_available": cuadrilla.current_load < cuadrilla.capacity,
                "created_at": cuadrilla.created_at.isoformat() if cuadrilla.created_at else None,
            }
        except Exception as e:
            logger.error(f"Error getting cuadrilla workload: {e}")
            return {
                "error": str(e),
            }

    @staticmethod
    def get_cuadrilla_statistics(db: Session) -> Dict[str, Any]:
        """
        Get aggregate statistics about all crews.
        
        Args:
            db: Database session
            
        Returns:
            Statistics dict with counts, utilization, etc.
        """
        if not Session:
            return {}

        try:
            from backend.database.models import Cuadrilla
            from sqlalchemy import func

            cuadrillas = db.query(Cuadrilla).all()

            if not cuadrillas:
                return {
                    "total_cuadrillas": 0,
                    "principal_count": 0,
                    "reserva_count": 0,
                    "total_capacity": 0,
                    "total_load": 0,
                    "available_capacity": 0,
                    "average_utilization_percent": 0,
                }

            # Count by type
            principal_count = sum(1 for c in cuadrillas if c.type == "Principal")
            reserva_count = sum(1 for c in cuadrillas if c.type == "Reserva")

            # Calculate totals
            total_capacity = sum(c.capacity for c in cuadrillas)
            total_load = sum(c.current_load for c in cuadrillas)
            available_capacity = total_capacity - total_load

            # Calculate average utilization
            avg_utilization = (
                round((total_load / total_capacity) * 100, 2)
                if total_capacity > 0
                else 0
            )

            # Count available cuadrillas
            available_count = sum(
                1 for c in cuadrillas if c.current_load < c.capacity
            )

            return {
                "total_cuadrillas": len(cuadrillas),
                "principal_count": principal_count,
                "reserva_count": reserva_count,
                "total_capacity": total_capacity,
                "total_load": total_load,
                "available_capacity": available_capacity,
                "average_utilization_percent": avg_utilization,
                "available_cuadrillas_count": available_count,
                "at_capacity_count": len(cuadrillas) - available_count,
            }
        except Exception as e:
            logger.error(f"Error getting cuadrilla statistics: {e}")
            return {}

    @staticmethod
    def calculate_centroid_for_ots(
        ot_ids: List[int],
    ) -> Optional[tuple]:
        """
        Calculate centroid for a list of OT IDs.
        
        Used for map visualization and planning analysis.
        
        Args:
            ot_ids: List of OT IDs
            
        Returns:
            Tuple of (centroid_lat, centroid_long) or None if no valid coordinates
        """
        # Import here to avoid circular imports
        from backend.database import get_db

        try:
            db = next(get_db())
            from backend.database.models import OrdenTrabajo

            ots = db.query(OrdenTrabajo).filter(OrdenTrabajo.id.in_(ot_ids)).all()

            coordinates = [
                (ot.lat, ot.long)
                for ot in ots
                if ot.lat is not None and ot.long is not None
            ]

            if not coordinates:
                return None

            return GeoService.calculate_centroid(coordinates)
        except Exception as e:
            logger.error(f"Error calculating centroid for OTs: {e}")
            return None


# Global instance
cuadrilla_service = CuadrillaService()

