import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from backend.app.models.ot import OT, OTStatus
from backend.app.models.cuadrilla import Cuadrilla
from backend.app.models.log_agente import LogAgente
from backend.app.utils.geo import haversine_distance, calculate_centroid
from backend.app.core.database import get_db

logger = logging.getLogger(__name__)


class PlanificacionAgent:
    """
    PlanificacionAgent handles intelligent assignment of OTs to cuadrillas (teams).
    
    Uses a 3-phase algorithm:
    - Phase 1: Balanced assignment (1 OT per cuadrilla) for load distribution
    - Phase 2: Centroid-based proximity assignment (<10km) for geographic optimization
    - Phase 3: Nocturnal optimization stub (future enhancement)
    
    Responsibilities:
    - Query available cuadrillas and unassigned OTs
    - Calculate geographic centroid for each cuadrilla
    - Assign OTs based on capacity and proximity
    - Update database with assignments
    - Log all assignment actions
    """

    def __init__(self):
        """Initialize PlanificacionAgent."""
        self.agent_name = "PlanificacionAgent"
        self.proximity_radius_km = 10.0  # Max distance for Phase 2 assignment

    async def assign_ots(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the 3-phase OT assignment algorithm.
        
        Algorithm:
        1. Phase 1: Balanced assignment - assign 1 OT per cuadrilla for load balance
        2. Phase 2: Proximity-based assignment - assign remaining OTs within 10km of centroid
        3. Phase 3: Nocturnal optimization - stub for future feature
        
        Args:
            state: AgentState dictionary
        
        Returns:
            Updated state with assignment results
        """
        assignment_results = {
            "phase_1_assigned": 0,
            "phase_2_assigned": 0,
            "phase_3_assigned": 0,
            "total_assigned": 0,
            "unassigned_ots": 0,
            "cuadrillas_processed": 0,
            "messages": []
        }

        db = next(get_db())
        try:
            logger.info("Starting OT assignment process (3-phase algorithm)")

            # Get available cuadrillas
            cuadrillas = db.query(Cuadrilla).filter(
                Cuadrilla.capacity > Cuadrilla.current_load
            ).all()

            if not cuadrillas:
                message = "No available cuadrillas with capacity"
                logger.warning(message)
                assignment_results["messages"].append(message)
                
                self._log_action(
                    db,
                    accion="assign_ots_start",
                    resultado="NO_CAPACITY",
                    message="No cuadrillas available"
                )
                
                return {
                    **state,
                    "action": "ASSIGNMENT_COMPLETE",
                    "result": assignment_results
                }

            assignment_results["cuadrillas_processed"] = len(cuadrillas)
            logger.info(f"Found {len(cuadrillas)} cuadrillas with available capacity")

            # Phase 1: Balanced assignment (1 OT per cuadrilla)
            logger.info("Phase 1: Balanced assignment")
            phase1_results = await self._phase1_balanced_assignment(db, cuadrillas)
            assignment_results["phase_1_assigned"] = phase1_results["assigned"]
            assignment_results["messages"].append(f"Phase 1: {phase1_results['assigned']} OTs assigned")

            # Phase 2: Proximity-based assignment
            logger.info("Phase 2: Proximity-based assignment")
            phase2_results = await self._phase2_proximity_assignment(db, cuadrillas)
            assignment_results["phase_2_assigned"] = phase2_results["assigned"]
            assignment_results["messages"].append(f"Phase 2: {phase2_results['assigned']} OTs assigned")

            # Phase 3: Nocturnal optimization (stub)
            logger.info("Phase 3: Nocturnal optimization (stub)")
            phase3_results = await self._phase3_nocturnal_optimization(db, cuadrillas)
            assignment_results["phase_3_assigned"] = phase3_results["assigned"]
            assignment_results["messages"].append(f"Phase 3: {phase3_results['assigned']} OTs assigned")

            # Calculate unassigned OTs
            unassigned_count = db.query(OT).filter(OT.cuadrilla_id.is_(None)).count()
            assignment_results["unassigned_ots"] = unassigned_count
            assignment_results["total_assigned"] = (
                assignment_results["phase_1_assigned"] +
                assignment_results["phase_2_assigned"] +
                assignment_results["phase_3_assigned"]
            )

            # Log final results
            self._log_action(
                db,
                accion="assign_ots_complete",
                resultado="SUCCESS",
                message=f"Phase 1: {assignment_results['phase_1_assigned']}, Phase 2: {assignment_results['phase_2_assigned']}, Phase 3: {assignment_results['phase_3_assigned']}"
            )

            # Commit changes
            db.commit()
            logger.info(
                f"Assignment completed: {assignment_results['total_assigned']} OTs assigned, "
                f"{assignment_results['unassigned_ots']} unassigned"
            )

            return {
                **state,
                "action": "ASSIGNMENT_COMPLETE",
                "result": assignment_results
            }

        except Exception as e:
            db.rollback()
            error_msg = f"Error during OT assignment: {str(e)}"
            logger.error(error_msg)
            assignment_results["messages"].append(error_msg)

            self._log_action(
                db,
                accion="assign_ots",
                resultado="ERROR",
                message=error_msg
            )

            return {
                **state,
                "action": "ASSIGNMENT_ERROR",
                "result": assignment_results,
                "errors": [error_msg]
            }
        finally:
            db.close()

    async def _phase1_balanced_assignment(
        self,
        db: Session,
        cuadrillas: List[Cuadrilla]
    ) -> Dict[str, int]:
        """
        Phase 1: Balanced assignment - assign 1 OT per cuadrilla for load balance.
        
        Process:
        1. For each cuadrilla, assign one unassigned OT
        2. Update OT.cuadrilla_id and Cuadrilla.current_load
        3. Prefer OTs without geographic errors
        4. Log each assignment
        
        Args:
            db: SQLAlchemy session
            cuadrillas: List of available cuadrillas
        
        Returns:
            Dict with count of assigned OTs
        """
        assigned_count = 0

        for cuadrilla in cuadrillas:
            # Get unassigned OT, preferring ones without geo errors
            unassigned_ot = db.query(OT).filter(
                OT.cuadrilla_id.is_(None),
                OT.status.in_([OTStatus.PREPLANIFICADA, OTStatus.PLANIFICADA])
            ).order_by(OT.error_geo.asc(), OT.created_at.asc()).first()

            if not unassigned_ot:
                logger.debug(f"No more unassigned OTs for cuadrilla {cuadrilla.name}")
                break

            # Assign OT to cuadrilla
            unassigned_ot.cuadrilla_id = cuadrilla.id
            unassigned_ot.status = OTStatus.PLANIFICADA
            unassigned_ot.updated_at = datetime.utcnow()

            # Update cuadrilla load
            cuadrilla.current_load += 1

            db.add(unassigned_ot)
            db.add(cuadrilla)

            assigned_count += 1

            logger.info(
                f"Phase 1: Assigned OT {unassigned_ot.external_id} to "
                f"cuadrilla {cuadrilla.name} (load: {cuadrilla.current_load}/{cuadrilla.capacity})"
            )

            # Log assignment
            self._log_action(
                db,
                accion="assign_ot_phase1",
                resultado="SUCCESS",
                message=f"OT {unassigned_ot.external_id} -> {cuadrilla.name}"
            )

        return {"assigned": assigned_count}

    async def _phase2_proximity_assignment(
        self,
        db: Session,
        cuadrillas: List[Cuadrilla]
    ) -> Dict[str, int]:
        """
        Phase 2: Proximity-based assignment using geographic centroid.
        
        Process:
        1. Calculate centroid for each cuadrilla based on assigned OTs
        2. For remaining unassigned OTs, find closest cuadrilla within radius
        3. Update cuadrilla.last_centroid_lat/long
        4. Log assignments
        
        Args:
            db: SQLAlchemy session
            cuadrillas: List of available cuadrillas
        
        Returns:
            Dict with count of assigned OTs
        """
        assigned_count = 0

        # Calculate centroid for each cuadrilla
        cuadrilla_centroids = {}
        for cuadrilla in cuadrillas:
            assigned_ots = db.query(OT).filter(
                OT.cuadrilla_id == cuadrilla.id,
                OT.lat.isnot(None),
                OT.long.isnot(None)
            ).all()

            if assigned_ots:
                # Calculate centroid from assigned OTs
                coordinates = [(ot.lat, ot.long) for ot in assigned_ots]
                centroid_lat, centroid_long = calculate_centroid(coordinates)

                cuadrilla_centroids[cuadrilla.id] = (centroid_lat, centroid_long)
                cuadrilla.last_centroid_lat = centroid_lat
                cuadrilla.last_centroid_long = centroid_long
                db.add(cuadrilla)

                logger.debug(
                    f"Cuadrilla {cuadrilla.name} centroid: ({centroid_lat:.4f}, {centroid_long:.4f})"
                )

        # Get remaining unassigned OTs with valid coordinates
        unassigned_ots = db.query(OT).filter(
            OT.cuadrilla_id.is_(None),
            OT.lat.isnot(None),
            OT.long.isnot(None),
            OT.status.in_([OTStatus.PREPLANIFICADA, OTStatus.PLANIFICADA])
        ).all()

        logger.info(f"Phase 2: Processing {len(unassigned_ots)} unassigned OTs with valid coordinates")

        for ot in unassigned_ots:
            # Find closest cuadrilla within proximity radius
            best_cuadrilla = None
            best_distance = self.proximity_radius_km + 1  # Start above radius

            for cuadrilla in cuadrillas:
                if cuadrilla.current_load >= cuadrilla.capacity:
                    continue  # Skip full cuadrillas

                if cuadrilla.id in cuadrilla_centroids:
                    centroid_lat, centroid_long = cuadrilla_centroids[cuadrilla.id]
                    distance = haversine_distance(
                        centroid_lat, centroid_long,
                        ot.lat, ot.long
                    )

                    if distance < best_distance:
                        best_distance = distance
                        best_cuadrilla = cuadrilla

            # Assign to closest cuadrilla if within radius
            if best_cuadrilla and best_distance <= self.proximity_radius_km:
                ot.cuadrilla_id = best_cuadrilla.id
                ot.status = OTStatus.ASIGNADO_TAREA
                ot.updated_at = datetime.utcnow()

                best_cuadrilla.current_load += 1

                db.add(ot)
                db.add(best_cuadrilla)

                assigned_count += 1

                logger.info(
                    f"Phase 2: Assigned OT {ot.external_id} to "
                    f"cuadrilla {best_cuadrilla.name} ({best_distance:.2f}km away)"
                )

                # Log assignment
                self._log_action(
                    db,
                    accion="assign_ot_phase2",
                    resultado="SUCCESS",
                    message=f"OT {ot.external_id} -> {best_cuadrilla.name} ({best_distance:.2f}km)"
                )

        return {"assigned": assigned_count}

    async def _phase3_nocturnal_optimization(
        self,
        db: Session,
        cuadrillas: List[Cuadrilla]
    ) -> Dict[str, int]:
        """
        Phase 3: Nocturnal optimization stub for future enhancement.
        
        Future capabilities:
        - Optimize routes for nighttime installation teams
        - Consider traffic patterns and safety factors
        - Adjust assignments for emergency/high-priority OTs
        
        Args:
            db: SQLAlchemy session
            cuadrillas: List of available cuadrillas
        
        Returns:
            Dict with count of assigned OTs (0 for now)
        """
        logger.debug("Phase 3: Nocturnal optimization (stub)")
        
        # Placeholder for future nocturnal optimization
        # Current implementation does not assign any OTs in Phase 3
        
        self._log_action(
            db,
            accion="phase3_optimization",
            resultado="STUB",
            message="Nocturnal optimization feature (future enhancement)"
        )

        return {"assigned": 0}

    def _log_action(
        self,
        db: Session,
        accion: str,
        resultado: str,
        message: str = None
    ) -> None:
        """
        Log an agent action to the logs_agentes table.
        
        Args:
            db: SQLAlchemy session
            accion: Action performed
            resultado: Result of the action
            message: Additional message details
        """
        try:
            log_entry = LogAgente(
                ot_id=None,
                agente_name=self.agent_name,
                accion=accion,
                resultado=resultado,
                raw_llm_response=message,
                timestamp=datetime.utcnow()
            )
            db.add(log_entry)
            db.flush()
        except Exception as e:
            logger.error(f"Failed to log action: {str(e)}")

