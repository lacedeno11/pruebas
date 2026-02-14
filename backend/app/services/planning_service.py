from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from geopy.distance import geodesic
from app.models import OT, Cuadrilla, Asignacion
from app.config import get_settings
from app.utils.geo import calculate_centroid, calculate_distance_km


class PlanningService:
    """Service for implementing 3-phase crew planning algorithm"""

    def __init__(self):
        self.settings = get_settings()

    def balance_initial_assignment(self, session: Session, ots: List[OT]) -> List[Dict]:
        """
        Phase 1: Assign 1 OT to each available Principal cuadrilla for equity
        """
        assignments = []
        
        # Get all active Principal cuadrillas
        principal_cuadrillas = session.query(Cuadrilla).filter(
            Cuadrilla.type == "Principal",
            Cuadrilla.is_active == True
        ).all()
        
        # Assign OTs that don't have assignments yet
        unassigned_ots = [ot for ot in ots if not ot.asignaciones]
        
        for idx, ot in enumerate(unassigned_ots):
            if idx >= len(principal_cuadrillas):
                break
            
            cuadrilla = principal_cuadrillas[idx]
            assignment = {
                "ot_id": ot.id,
                "cuadrilla_id": cuadrilla.id,
                "distance": 0,
                "phase": "balance_initial",
            }
            assignments.append(assignment)
        
        return assignments

    def assign_by_proximity(
        self,
        session: Session,
        ot: OT,
        max_distance_km: Optional[float] = None
    ) -> Optional[Cuadrilla]:
        """
        Phase 2: Assign OT if < max_distance_km from crew's centroid
        """
        if max_distance_km is None:
            max_distance_km = self.settings.PROXIMITY_RADIUS_KM
        
        if not ot.lat or not ot.long:
            return None
        
        # Get all active cuadrillas
        cuadrillas = session.query(Cuadrilla).filter(
            Cuadrilla.is_active == True
        ).all()
        
        ot_coord = (ot.lat, ot.long)
        
        for cuadrilla in cuadrillas:
            if not cuadrilla.last_centroid_lat or not cuadrilla.last_centroid_long:
                continue
            
            centroid_coord = (cuadrilla.last_centroid_lat, cuadrilla.last_centroid_long)
            distance = calculate_distance_km(ot_coord, centroid_coord)
            
            if distance < max_distance_km:
                # Check capacity
                if cuadrilla.current_load < cuadrilla.capacity:
                    return cuadrilla
        
        return None

    def normalize_routes_nocturnal(self, session: Session) -> None:
        """
        Phase 3: Recalculate centroids for all cuadrillas at 00:00 daily
        """
        cuadrillas = session.query(Cuadrilla).filter(
            Cuadrilla.is_active == True
        ).all()
        
        for cuadrilla in cuadrillas:
            self.update_cuadrilla_centroid(session, cuadrilla.id)
        
        session.commit()

    def update_cuadrilla_centroid(self, session: Session, cuadrilla_id: int) -> None:
        """
        Helper: Recalculate centroid for a specific cuadrilla based on assigned OTs
        """
        cuadrilla = session.query(Cuadrilla).filter(
            Cuadrilla.id == cuadrilla_id
        ).first()
        
        if not cuadrilla:
            return
        
        # Get all assigned OTs with valid coordinates
        assigned_ots = session.query(OT).join(Asignacion).filter(
            Asignacion.cuadrilla_id == cuadrilla_id,
            OT.lat.isnot(None),
            OT.long.isnot(None)
        ).all()
        
        if not assigned_ots:
            return
        
        # Calculate centroid
        coordinates = [(ot.lat, ot.long) for ot in assigned_ots]
        centroid_lat, centroid_long = calculate_centroid(coordinates)
        
        cuadrilla.last_centroid_lat = centroid_lat
        cuadrilla.last_centroid_long = centroid_long
        
        session.commit()

