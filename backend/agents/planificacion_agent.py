"""Planning Agent for OT assignment and route optimization (UC-PEI-02)"""

import logging
from typing import List, Tuple, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database.models import OT, Cuadrilla, Asignacion, LogAgente
from backend.utils.geo import calculate_centroid, calculate_distance, is_within_radius
from backend.utils.constants import MAX_DISTANCE_KM, OT_STATUS, CUADRILLA_TYPES
from backend.models.proyecto import PlanningResult, AssignmentResult
from backend.agents.graph import PEIState

logger = logging.getLogger(__name__)


class PlanificacionAgent:
    """
    Planning Agent for OT assignment and route optimization.

    This agent implements UC-PEI-02 (Planning) with a 3-phase algorithm:
    1. Balance Phase: Assign 1 OT to each cuadrilla for workload balance
    2. Proximity Phase: Assign remaining OTs to nearest cuadrilla (<10km)
    3. Normalization Phase: Optimize routes by recalculating centroids

    The algorithm ensures:
    - All cuadrillas have at least 1 OT
    - OTs are assigned to nearest cuadrilla within 10km radius
    - Reserva teams are only activated if Principal teams are saturated
    - All assignments are tracked with distance metrics
    """

    def __init__(self, db_session: Session):
        """
        Initialize PlanificacionAgent with database session.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session

        logger.info("PlanificacionAgent initialized")

    async def execute(self, state: PEIState) -> PEIState:
        """
        Execute OT planning pipeline (UC-PEI-02).

        Orchestrates the 3-phase planning algorithm:
        1. Balance Phase: Assign 1 OT to each cuadrilla
        2. Proximity Phase: Assign remaining OTs to nearest cuadrilla
        3. Update state with results

        Args:
            state: Current PEI state

        Returns:
            Updated state with PlanningResult

        Raises:
            Exception: If database errors occur (wrapped and logged)
        """
        try:
            logger.info("PlanificacionAgent: Starting OT planning")

            # Get unassigned OTs
            unassigned_ots = (
                self.db_session.query(OT)
                .filter(OT.status == OT_STATUS["PREPLANIFICADA"])
                .all()
            )

            logger.info(f"PlanificacionAgent: Found {len(unassigned_ots)} unassigned OTs")

            if not unassigned_ots:
                logger.info("PlanificacionAgent: No unassigned OTs to plan")
                return state

            # Get active cuadrillas
            cuadrillas = (
                self.db_session.query(Cuadrilla)
                .filter(Cuadrilla.active == True)
                .order_by(Cuadrilla.id)
                .all()
            )

            logger.info(f"PlanificacionAgent: Found {len(cuadrillas)} active cuadrillas")

            if not cuadrillas:
                logger.warning("PlanificacionAgent: No active cuadrillas available")
                state["error"] = "No active cuadrillas available for planning"
                return state

            # Phase 1: Balance Initial
            assignments = []
            remaining_ots = await self.balance_initial(
                unassigned_ots, cuadrillas, assignments
            )

            logger.info(
                f"PlanificacionAgent: Balance phase complete - "
                f"{len(assignments)} assignments, {len(remaining_ots)} remaining OTs"
            )

            # Phase 2: Proximity Assignment
            remaining_ots = await self.proximity_assignment(
                remaining_ots, cuadrillas, assignments
            )

            logger.info(
                f"PlanificacionAgent: Proximity phase complete - "
                f"{len(assignments)} total assignments, {len(remaining_ots)} unassigned"
            )

            # Update state with results
            state["validation_result"] = {
                "total": len(unassigned_ots),
                "assigned": len(assignments),
                "unassigned": len(remaining_ots),
            }

            # Create PlanningResult
            planning_result = PlanningResult(
                assignments=assignments,
                total_assigned=len(assignments),
                unassigned=[ot.id for ot in remaining_ots],
            )

            # Add to agent logs
            state["agent_logs"].append(
                {
                    "agent": "planning",
                    "action": "plan_ots",
                    "result": "success",
                    "total": len(unassigned_ots),
                    "assigned": len(assignments),
                    "unassigned": len(remaining_ots),
                    "timestamp": datetime.now().isoformat(),
                }
            )

            logger.info(
                f"PlanificacionAgent: Planning complete - "
                f"Total: {len(unassigned_ots)}, Assigned: {len(assignments)}, "
                f"Unassigned: {len(remaining_ots)}"
            )

            return state

        except Exception as e:
            logger.error(f"PlanificacionAgent: Fatal error during planning: {str(e)}")

            self.db_session.rollback()

            # Set error state
            state["error"] = f"Planning agent error: {str(e)}"

            # Add error to agent logs
            state["agent_logs"].append(
                {
                    "agent": "planning",
                    "action": "plan_ots",
                    "result": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )

            return state

    async def balance_initial(
        self,
        unassigned_ots: List[OT],
        cuadrillas: List[Cuadrilla],
        assignments: List[dict],
    ) -> List[OT]:
        """
        Phase 1: Balance Initial - Assign 1 OT to each cuadrilla.

        This ensures all cuadrillas have at least 1 OT and workload is balanced.

        Args:
            unassigned_ots: List of OTs with status PREPLANIFICADA
            cuadrillas: List of active cuadrillas
            assignments: List to append assignments to

        Returns:
            List of remaining unassigned OTs after balance phase
        """
        logger.info("PlanificacionAgent: Starting balance phase")

        remaining_ots = list(unassigned_ots)

        # Assign 1 OT to each cuadrilla
        for cuadrilla in cuadrillas:
            if not remaining_ots:
                break

            # Find OT with valid coordinates nearest to cuadrilla centroid
            best_ot = None
            best_distance = float("inf")

            for ot in remaining_ots:
                # Skip OTs without coordinates
                if ot.lat is None or ot.long is None:
                    continue

                # Calculate distance to cuadrilla centroid (or (0,0) if not set)
                if (
                    cuadrilla.last_centroid_lat is not None
                    and cuadrilla.last_centroid_long is not None
                ):
                    distance = calculate_distance(
                        (ot.lat, ot.long),
                        (
                            cuadrilla.last_centroid_lat,
                            cuadrilla.last_centroid_long,
                        ),
                    )
                else:
                    distance = 0.0

                # Track best (closest) OT
                if distance < best_distance:
                    best_distance = distance
                    best_ot = ot

            # Assign best OT to cuadrilla
            if best_ot:
                assignment = await self._create_assignment(
                    best_ot, cuadrilla, best_distance
                )
                assignments.append(assignment)
                remaining_ots.remove(best_ot)

                logger.info(
                    f"PlanificacionAgent: Assigned OT {best_ot.id} to "
                    f"cuadrilla {cuadrilla.id} (distance: {best_distance:.2f}km)"
                )

        logger.info(
            f"PlanificacionAgent: Balance phase complete - "
            f"Assigned {len(unassigned_ots) - len(remaining_ots)} OTs"
        )

        return remaining_ots

    async def proximity_assignment(
        self,
        unassigned_ots: List[OT],
        cuadrillas: List[Cuadrilla],
        assignments: List[dict],
    ) -> List[OT]:
        """
        Phase 2: Proximity Assignment - Assign remaining OTs to nearest cuadrilla.

        For each remaining OT:
        - Calculate distance to each cuadrilla's centroid
        - Assign to nearest if within MAX_DISTANCE_KM (10km)
        - Activate Reserva cuadrillas if Principal are saturated

        Args:
            unassigned_ots: List of unassigned OTs
            cuadrillas: List of active cuadrillas
            assignments: List to append assignments to

        Returns:
            List of remaining unassigned OTs after proximity phase
        """
        logger.info("PlanificacionAgent: Starting proximity phase")

        remaining_ots = list(unassigned_ots)

        # Separate Principal and Reserva cuadrillas
        principal_cuadrillas = [
            c for c in cuadrillas if c.type == CUADRILLA_TYPES["PRINCIPAL"]
        ]
        reserva_cuadrillas = [
            c for c in cuadrillas if c.type == CUADRILLA_TYPES["RESERVA"]
        ]

        # Assign OTs to nearest cuadrilla
        for ot in list(remaining_ots):
            # Skip OTs without coordinates
            if ot.lat is None or ot.long is None:
                logger.warning(
                    f"PlanificacionAgent: Skipping OT {ot.id} "
                    f"- missing coordinates"
                )
                continue

            # Find nearest Principal cuadrilla
            nearest_cuadrilla = self._find_nearest_cuadrilla(
                (ot.lat, ot.long), principal_cuadrillas
            )

            # If no Principal cuadrilla within range, try Reserva
            if not nearest_cuadrilla and reserva_cuadrillas:
                nearest_cuadrilla = self._find_nearest_cuadrilla(
                    (ot.lat, ot.long), reserva_cuadrillas
                )

            # Assign OT to nearest cuadrilla
            if nearest_cuadrilla:
                distance = calculate_distance(
                    (ot.lat, ot.long),
                    (
                        nearest_cuadrilla.last_centroid_lat
                        or 0,
                        nearest_cuadrilla.last_centroid_long
                        or 0,
                    ),
                )

                assignment = await self._create_assignment(
                    ot, nearest_cuadrilla, distance
                )
                assignments.append(assignment)
                remaining_ots.remove(ot)

                logger.info(
                    f"PlanificacionAgent: Assigned OT {ot.id} to "
                    f"cuadrilla {nearest_cuadrilla.id} (distance: {distance:.2f}km)"
                )
            else:
                logger.warning(
                    f"PlanificacionAgent: No cuadrilla within range for OT {ot.id}"
                )

        logger.info(
            f"PlanificacionAgent: Proximity phase complete - "
            f"Assigned {len(unassigned_ots) - len(remaining_ots)} OTs"
        )

        return remaining_ots

    async def normalize_routes(self) -> dict:
        """
        Phase 3: Normalize Routes - Optimize all assignments nightly.

        Called by scheduled task at 00:00 daily to:
        - Recalculate all cuadrilla centroids
        - Optimize assignment distances
        - Update centroid coordinates in database

        Returns:
            Dictionary with optimization results
        """
        try:
            logger.info("PlanificacionAgent: Starting route normalization")

            optimization_results = {
                "cuadrillas_optimized": 0,
                "total_distance_before": 0.0,
                "total_distance_after": 0.0,
                "optimization_savings_km": 0.0,
            }

            # Get all cuadrillas with active assignments
            cuadrillas = (
                self.db_session.query(Cuadrilla)
                .filter(Cuadrilla.active == True)
                .all()
            )

            for cuadrilla in cuadrillas:
                # Get all active assignments for this cuadrilla
                assignments = (
                    self.db_session.query(Asignacion)
                    .filter(
                        Asignacion.cuadrilla_id == cuadrilla.id,
                        Asignacion.is_active == True,
                    )
                    .all()
                )

                if not assignments:
                    continue

                # Get OTs for these assignments
                ot_ids = [a.ot_id for a in assignments]
                ots = self.db_session.query(OT).filter(OT.id.in_(ot_ids)).all()

                # Calculate new centroid
                coordinates = [
                    (ot.lat, ot.long)
                    for ot in ots
                    if ot.lat is not None and ot.long is not None
                ]

                if coordinates:
                    old_centroid = (
                        cuadrilla.last_centroid_lat,
                        cuadrilla.last_centroid_long,
                    )

                    new_centroid = calculate_centroid(coordinates)

                    # Update centroid
                    cuadrilla.last_centroid_lat = new_centroid[0]
                    cuadrilla.last_centroid_long = new_centroid[1]

                    # Calculate distance change
                    old_distance = 0.0
                    new_distance = 0.0

                    for ot in ots:
                        if ot.lat and ot.long:
                            old_distance += calculate_distance(
                                (ot.lat, ot.long), old_centroid
                            )
                            new_distance += calculate_distance(
                                (ot.lat, ot.long), new_centroid
                            )

                    optimization_results["total_distance_before"] += old_distance
                    optimization_results["total_distance_after"] += new_distance
                    optimization_results["cuadrillas_optimized"] += 1

                    logger.info(
                        f"PlanificacionAgent: Optimized cuadrilla {cuadrilla.id} - "
                        f"Old centroid: {old_centroid}, New: {new_centroid}"
                    )

            # Commit changes
            self.db_session.commit()

            optimization_results["optimization_savings_km"] = (
                optimization_results["total_distance_before"]
                - optimization_results["total_distance_after"]
            )

            logger.info(
                f"PlanificacionAgent: Route normalization complete - "
                f"Savings: {optimization_results['optimization_savings_km']:.2f}km"
            )

            return optimization_results

        except Exception as e:
            logger.error(f"PlanificacionAgent: Error during route normalization: {str(e)}")
            self.db_session.rollback()
            return {"error": str(e)}

    async def _create_assignment(
        self, ot: OT, cuadrilla: Cuadrilla, distance: float
    ) -> dict:
        """
        Create an assignment record and update OT status.

        Args:
            ot: OT to assign
            cuadrilla: Cuadrilla to assign to
            distance: Distance to cuadrilla centroid in km

        Returns:
            Assignment dictionary for result tracking
        """
        now = datetime.now()

        # Create assignment record
        asignacion = Asignacion(
            ot_id=ot.id,
            cuadrilla_id=cuadrilla.id,
            assigned_at=now,
            assigned_by_agent="PlanificacionAgent",
            distance_to_centroid=distance,
            is_active=True,
        )

        self.db_session.add(asignacion)

        # Update OT status
        ot.status = OT_STATUS["PLANIFICADA"]
        ot.cuadrilla_id = cuadrilla.id
        ot.updated_at = now
        ot.last_status_change = now

        # Create log entry
        log_entry = LogAgente(
            ot_id=ot.id,
            agente_name="PlanificacionAgent",
            accion="assign_ot",
            resultado="SUCCESS",
            raw_llm_response=None,
            metadata={
                "external_id": ot.external_id,
                "cuadrilla_id": cuadrilla.id,
                "distance": round(distance, 2),
            },
        )

        self.db_session.add(log_entry)
        self.db_session.flush()

        return AssignmentResult(
            ot_id=ot.id,
            cuadrilla_id=cuadrilla.id,
            distance_to_centroid=distance,
            assigned_by_agent="PlanificacionAgent",
        ).dict()

    def _find_nearest_cuadrilla(
        self, ot_coords: Tuple[float, float], cuadrillas: List[Cuadrilla]
    ) -> Optional[Cuadrilla]:
        """
        Find nearest cuadrilla within MAX_DISTANCE_KM.

        Args:
            ot_coords: Tuple of (lat, long) for OT
            cuadrillas: List of cuadrillas to search

        Returns:
            Nearest cuadrilla or None if all are >MAX_DISTANCE_KM away
        """
        nearest = None
        min_distance = MAX_DISTANCE_KM

        for cuadrilla in cuadrillas:
            # Skip if no centroid set
            if (
                cuadrilla.last_centroid_lat is None
                or cuadrilla.last_centroid_long is None
            ):
                # Use (0,0) as default centroid
                centroid = (0.0, 0.0)
            else:
                centroid = (
                    cuadrilla.last_centroid_lat,
                    cuadrilla.last_centroid_long,
                )

            distance = calculate_distance(ot_coords, centroid)

            if distance < min_distance:
                min_distance = distance
                nearest = cuadrilla

        return nearest

    async def get_planning_stats(self) -> dict:
        """
        Get statistics about current planning state.

        Returns:
            Dictionary with planning statistics
        """
        try:
            total_ots = self.db_session.query(OT).count()

            planned_ots = (
                self.db_session.query(OT)
                .filter(OT.status.in_([OT_STATUS["PLANIFICADA"], OT_STATUS["ASIGNADO_TAREA"]]))
                .count()
            )

            preplanificada_ots = (
                self.db_session.query(OT)
                .filter(OT.status == OT_STATUS["PREPLANIFICADA"])
                .count()
            )

            logger.info(
                f"PlanificacionAgent: Planning stats - Total: {total_ots}, "
                f"Planned: {planned_ots}, Preplanificada: {preplanificada_ots}"
            )

            return {
                "total_ots": total_ots,
                "planned_ots": planned_ots,
                "preplanificada_ots": preplanificada_ots,
                "planning_completion_pct": (
                    (planned_ots / total_ots * 100) if total_ots > 0 else 0
                ),
            }

        except Exception as e:
            logger.error(f"PlanificacionAgent: Error getting planning stats: {str(e)}")
            return {"error": str(e)}

