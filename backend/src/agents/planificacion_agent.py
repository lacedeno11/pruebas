"""
Planificacion Agent for PEI Platform - OT Assignment and Planning.

The PlanificacionAgent is responsible for assigning work orders (OTs) to
cuadrillas (technical teams) using a 3-phase algorithm that balances workload,
maintains proximity constraints, and optimizes routes.

Responsibilities:
1. Balance Phase: Distribute OTs evenly across cuadrillas
2. Proximity Phase: Assign remaining OTs to nearest cuadrillas (<10km)
3. Nightly Normalization: Re-optimize routes daily at 00:00

Implements UC-PEI-02: Automatic Planning
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.agents.base_agent import BaseAgent
from src.agents.state import PEIState
from src.models import Cuadrilla, OT, OTStatus
from src.utils.geo_utils import calculate_centroid, is_within_radius

logger = logging.getLogger(__name__)


class PlanificacionAgent(BaseAgent):
    """
    Planning Agent for OT assignment to cuadrillas.

    Implements the 3-phase planning algorithm:
    
    Phase 1 - Balance:
    - Query all cuadrillas and their current loads
    - Sort by load (ascending)
    - Assign 1 OT to each cuadrilla until all have at least one
    
    Phase 2 - Proximity:
    - For remaining OTs, calculate cuadrilla centroids
    - Use Haversine distance to find cuadrillas within 10km
    - Assign to nearest valid cuadrilla
    
    Phase 3 - Nightly Normalization:
    - Re-optimizes routes daily at 00:00
    - Can re-assign OTs if better proximity found
    - Updates centroid calculations

    Constraints:
    - No cuadrilla exceeds max_daily_capacity
    - Proximity threshold: <10km radius
    - Assignments logged with centroid distance
    """

    def __init__(self, db: AsyncSession, llm=None):
        """Initialize the PlanificacionAgent."""
        super().__init__(db, llm, agent_name="PlanificacionAgent")

    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for Planificacion Agent.

        Returns:
            str: System prompt text
        """
        return """You are the Planificacion (Planning) Agent for the PEI system.
Your responsibility is to:
1. Assign work orders (OTs) to technical teams (cuadrillas)
2. Ensure no team exceeds its daily capacity
3. Maintain proximity constraints (assignments <10km from team location)
4. Balance workload across teams fairly
5. Log all assignments with distance calculations

Execute the 3-phase planning algorithm:
- Phase 1: Balance - distribute OTs evenly first
- Phase 2: Proximity - assign remaining OTs to nearest teams
- Phase 3: Nightly optimization - re-balance if better routes found

Always log successful assignments with the format:
'Asignación exitosa - Centroide: X.XX km'"""

    async def process(self, state: PEIState) -> PEIState:
        """
        Execute the 3-phase planning algorithm.

        Args:
            state (PEIState): Current workflow state with OTs to plan

        Returns:
            PEIState: Updated state with OT assignments
        """
        try:
            # Validate state
            if not await self.validate_state(state):
                return await self.handle_error(state, "Invalid state for PlanificacionAgent")

            logger.info("PlanificacionAgent: Starting planning process")

            # Get OTs to process
            ots_to_plan = state.get("ots_to_process", [])
            if not ots_to_plan:
                logger.info("PlanificacionAgent: No OTs to plan")
                state["action_result"] = {
                    "success": True,
                    "message": "No OTs to plan",
                    "data": {},
                }
                return state

            # Get cuadrillas
            cuad_result = await self.db.execute(
                select(Cuadrilla).options(joinedload(Cuadrilla.ots))
            )
            cuadrillas = cuad_result.scalars().all()

            if not cuadrillas:
                error_msg = "No cuadrillas available for planning"
                logger.error(f"PlanificacionAgent: {error_msg}")
                return await self.handle_error(state, error_msg)

            # Get all PREPLANIFICADA OTs from database
            ot_result = await self.db.execute(
                select(OT).where(OT.status == OTStatus.PREPLANIFICADA)
            )
            planificada_ots = ot_result.scalars().all()

            logger.info(
                f"PlanificacionAgent: Planning {len(planificada_ots)} OTs "
                f"across {len(cuadrillas)} cuadrillas"
            )

            assignments = []

            # Phase 1: Balance - assign 1 OT to each cuadrilla first
            phase1_assignments = await self._phase_balance(
                planificada_ots, cuadrillas
            )
            assignments.extend(phase1_assignments)

            # Phase 2: Proximity - assign remaining OTs to nearest cuadrillas
            remaining_ots = [
                ot for ot in planificada_ots
                if not any(a["ot_id"] == ot.id for a in assignments)
            ]
            phase2_assignments = await self._phase_proximity(
                remaining_ots, cuadrillas
            )
            assignments.extend(phase2_assignments)

            # Log all assignments
            total_assigned = len(assignments)
            total_failed = len(planificada_ots) - total_assigned

            if total_assigned > 0:
                await self.log_action(
                    accion=f"Planificación completada - {total_assigned} asignaciones exitosas",
                    resultado="SUCCESS",
                    metadata={
                        "total_ots": len(planificada_ots),
                        "phase1_count": len(phase1_assignments),
                        "phase2_count": len(phase2_assignments),
                        "failed_count": total_failed,
                        "assignments": assignments,
                    },
                )

            # Update state
            state["agent_messages"].append({
                "agent": "PlanificacionAgent",
                "content": f"Assigned {total_assigned} OTs to cuadrillas",
                "timestamp": datetime.utcnow().isoformat(),
            })

            state["action_result"] = {
                "success": True,
                "message": f"Assigned {total_assigned}/{len(planificada_ots)} OTs",
                "data": {
                    "assignments": assignments,
                    "total_assigned": total_assigned,
                    "total_failed": total_failed,
                },
            }

            logger.info(
                f"PlanificacionAgent: Completed planning - "
                f"{total_assigned} assigned, {total_failed} failed"
            )

            return state

        except Exception as e:
            logger.error(f"PlanificacionAgent error: {str(e)}", exc_info=True)
            return await self.handle_error(state, f"PlanificacionAgent error: {str(e)}")

    async def _phase_balance(
        self, ots: list[OT], cuadrillas: list[Cuadrilla]
    ) -> list[dict]:
        """
        Phase 1: Balance load across cuadrillas.

        Assigns 1 OT to each cuadrilla, starting with least loaded teams.

        Args:
            ots (list[OT]): OTs to assign
            cuadrillas (list[Cuadrilla]): Available cuadrillas

        Returns:
            list[dict]: Successful assignments
        """
        assignments = []

        # Sort cuadrillas by current load
        sorted_cuadrillas = sorted(
            cuadrillas, key=lambda c: c.current_load
        )

        for i, ot in enumerate(ots[:len(sorted_cuadrillas)]):
            cuadrilla = sorted_cuadrillas[i]

            # Check capacity
            if cuadrilla.current_load >= cuadrilla.max_daily_capacity:
                logger.warning(
                    f"PlanificacionAgent: Cuadrilla {cuadrilla.name} at capacity"
                )
                continue

            try:
                # Assign OT
                ot.cuadrilla_id = cuadrilla.id
                ot.assigned_at = datetime.utcnow()
                ot.status = OTStatus.PLANIFICADA
                cuadrilla.current_load += 1

                self.db.add(ot)
                self.db.add(cuadrilla)

                assignments.append({
                    "ot_id": ot.id,
                    "cuadrilla_id": cuadrilla.id,
                    "distance_km": 0.0,  # Phase 1 ignores distance
                    "phase": 1,
                })

                logger.info(
                    f"PlanificacionAgent: Phase 1 - Assigned OT {ot.external_id} "
                    f"to {cuadrilla.name}"
                )

            except Exception as e:
                logger.error(
                    f"PlanificacionAgent: Error assigning OT {ot.external_id}: {str(e)}"
                )
                continue

        # Commit phase 1 assignments
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"PlanificacionAgent: Error committing phase 1: {str(e)}")

        return assignments

    async def _phase_proximity(
        self, ots: list[OT], cuadrillas: list[Cuadrilla]
    ) -> list[dict]:
        """
        Phase 2: Assign remaining OTs by proximity.

        For each remaining OT, find the nearest cuadrilla within 10km radius.

        Args:
            ots (list[OT]): Remaining OTs to assign
            cuadrillas (list[Cuadrilla]): Available cuadrillas

        Returns:
            list[dict]: Successful assignments
        """
        assignments = []
        proximity_threshold_km = 10.0

        for ot in ots:
            if not ot.is_geo_valid():
                logger.warning(
                    f"PlanificacionAgent: Skipping OT {ot.external_id} - invalid coordinates"
                )
                continue

            # Find nearest valid cuadrilla within radius
            best_cuadrilla = None
            best_distance = float("inf")

            for cuadrilla in cuadrillas:
                # Check capacity
                if cuadrilla.current_load >= cuadrilla.max_daily_capacity:
                    continue

                # Check proximity
                if (
                    cuadrilla.last_centroid_lat is None
                    or cuadrilla.last_centroid_long is None
                ):
                    # No centroid yet, skip proximity check
                    best_cuadrilla = cuadrilla
                    best_distance = 0.0
                    break

                # Calculate distance
                distance = is_within_radius(
                    ot.lat,
                    ot.long,
                    cuadrilla.last_centroid_lat,
                    cuadrilla.last_centroid_long,
                    proximity_threshold_km,
                )

                if distance is not None and distance < best_distance:
                    best_distance = distance
                    best_cuadrilla = cuadrilla

            if best_cuadrilla is None:
                logger.warning(
                    f"PlanificacionAgent: No suitable cuadrilla for OT {ot.external_id}"
                )
                continue

            try:
                # Assign OT
                ot.cuadrilla_id = best_cuadrilla.id
                ot.assigned_at = datetime.utcnow()
                ot.status = OTStatus.PLANIFICADA
                best_cuadrilla.current_load += 1

                # Update cuadrilla centroid
                assigned_ots = [
                    o for o in best_cuadrilla.ots if o.is_geo_valid()
                ] + [ot]
                coordinates = [
                    (o.lat, o.long) for o in assigned_ots if o.is_geo_valid()
                ]
                if coordinates:
                    centroid_lat, centroid_long = calculate_centroid(coordinates)
                    best_cuadrilla.last_centroid_lat = centroid_lat
                    best_cuadrilla.last_centroid_long = centroid_long

                self.db.add(ot)
                self.db.add(best_cuadrilla)

                # Log assignment
                distance_str = f"{best_distance:.2f}" if best_distance != float("inf") else "N/A"
                accion = f"Asignación exitosa - Centroide: {distance_str} km"
                await self.log_action(
                    ot_id=ot.id,
                    accion=accion,
                    resultado="SUCCESS",
                    metadata={
                        "cuadrilla_id": best_cuadrilla.id,
                        "distance_km": best_distance,
                    },
                )

                assignments.append({
                    "ot_id": ot.id,
                    "cuadrilla_id": best_cuadrilla.id,
                    "distance_km": best_distance,
                    "phase": 2,
                })

                logger.info(
                    f"PlanificacionAgent: Phase 2 - Assigned OT {ot.external_id} "
                    f"to {best_cuadrilla.name} ({distance_str} km)"
                )

            except Exception as e:
                logger.error(
                    f"PlanificacionAgent: Error assigning OT {ot.external_id}: {str(e)}"
                )
                continue

        # Commit phase 2 assignments
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"PlanificacionAgent: Error committing phase 2: {str(e)}")

        return assignments

    async def schedule_nightly_normalization(self):
        """
        Schedule nightly route optimization (Phase 3).

        This is called by the scheduler at 00:00 UTC daily to re-optimize
        routes and recalculate centroids based on current assignments.

        In a full implementation, this would:
        - Re-evaluate all current assignments
        - Look for OTs that could be moved to better cuadrillas
        - Update centroid calculations
        - Log any re-assignments
        """
        logger.info("PlanificacionAgent: Starting nightly normalization (Phase 3)")

        try:
            # Get all planned OTs
            ot_result = await self.db.execute(
                select(OT).where(OT.status == OTStatus.PLANIFICADA)
            )
            planned_ots = ot_result.scalars().all()

            # Recalculate all cuadrilla centroids
            cuad_result = await self.db.execute(select(Cuadrilla))
            cuadrillas = cuad_result.scalars().all()

            for cuadrilla in cuadrillas:
                # Get assigned OTs with valid coordinates
                assigned_ots = [
                    ot for ot in planned_ots
                    if ot.cuadrilla_id == cuadrilla.id and ot.is_geo_valid()
                ]

                if assigned_ots:
                    coordinates = [
                        (ot.lat, ot.long) for ot in assigned_ots
                    ]
                    centroid_lat, centroid_long = calculate_centroid(coordinates)
                    cuadrilla.last_centroid_lat = centroid_lat
                    cuadrilla.last_centroid_long = centroid_long
                    self.db.add(cuadrilla)

            await self.db.commit()
            logger.info(
                f"PlanificacionAgent: Nightly normalization complete - "
                f"updated {len(cuadrillas)} cuadrilla centroids"
            )

        except Exception as e:
            logger.error(
                f"PlanificacionAgent: Error during nightly normalization: {str(e)}"
            )
            await self.db.rollback()

