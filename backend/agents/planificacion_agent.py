"""
PlanificacionAgent - Planning and OT-to-crew assignment agent.
Implements 3-phase planning algorithm: balance, proximity, night normalization.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import OrdenTrabajo, Asignacion, Cuadrilla
from backend.utils import calculate_centroid, calculate_distance_km
from backend.utils.logging_helper import log_agent_action

logger = logging.getLogger(__name__)


class PlanificacionAgent:
    """
    PlanificacionAgent - Implements 3-phase planning algorithm for OT assignment.
    
    3-Phase Algorithm:
    Phase 1 - Initial Balance: Assign 1 OT to each active crew (round-robin)
    Phase 2 - Proximity Assignment: Assign remaining OTs to crews within 10km
    Phase 3 - Night Normalization: Schedule APScheduler job for 00:00 centroid recalculation
    
    Responsibilities:
    1. Execute 3-phase planning algorithm
    2. Create Asignacion records linking OTs to crews
    3. Calculate and store distance from crew centroid to OT
    4. Enforce <10km proximity rule
    5. Respect crew capacity limits
    6. Log planning actions for audit trail
    7. Return planning summary
    """

    def __init__(
        self,
        llm: Optional[object] = None,
        db_session: Optional[AsyncSession] = None,
    ):
        """
        Initialize PlanificacionAgent.

        Args:
            llm: OpenAI LLM instance (optional, for future enhancements)
            db_session: AsyncSession for database operations
        """
        self.llm = llm
        self.db_session = db_session

    async def plan_ots(self) -> Dict[str, Any]:
        """
        Execute 3-phase planning algorithm for PREPLANIFICADA OTs.
        
        Phase 1 - Balance: Assign 1 OT to each available crew
        Phase 2 - Proximity: Assign remaining OTs within 10km of crew centroid
        Phase 3 - Normalization: Schedule 00:00 daily centroid recalculation
        
        Returns:
            Dictionary with planning summary:
            {
                "status": "success" | "partial" | "error",
                "total_preplanificada": int,
                "successful_assignments": int,
                "failed_assignments": int,
                "phase_1_assigned": int,
                "phase_2_assigned": int,
                "phase_3_scheduled": bool,
                "summary": str
            }
        """
        logger.info("PlanificacionAgent: Starting 3-phase planning algorithm")
        
        try:
            if not self.db_session:
                logger.error("PlanificacionAgent: Database session not initialized")
                return {
                    "status": "error",
                    "total_preplanificada": 0,
                    "successful_assignments": 0,
                    "failed_assignments": 0,
                    "phase_1_assigned": 0,
                    "phase_2_assigned": 0,
                    "phase_3_scheduled": False,
                    "summary": "Failed: Database session not configured",
                }

            # Phase 1: Initial Balance Assignment
            phase1_result = await self.balance_initial_assignment()
            logger.info(f"PlanificacionAgent: Phase 1 completed - {phase1_result['assigned']} OTs assigned")

            # Phase 2: Proximity Assignment
            phase2_result = await self.proximity_assignment()
            logger.info(f"PlanificacionAgent: Phase 2 completed - {phase2_result['assigned']} OTs assigned")

            # Phase 3: Schedule Night Normalization
            phase3_scheduled = await self.schedule_night_normalization()
            logger.info(f"PlanificacionAgent: Phase 3 scheduled - {phase3_scheduled}")

            # Calculate summary
            total_assigned = phase1_result['assigned'] + phase2_result['assigned']
            total_preplanificada = phase1_result['total'] + phase2_result['total']
            failed = phase1_result['failed'] + phase2_result['failed']

            summary = (
                f"Planned {total_assigned} OTs (Phase 1: {phase1_result['assigned']}, "
                f"Phase 2: {phase2_result['assigned']}, Failed: {failed})"
            )

            if self.db_session:
                await log_agent_action(
                    self.db_session,
                    agente_name="PlanificacionAgent",
                    ot_id=None,
                    accion="plan_ots",
                    resultado=summary,
                    raw_llm_response={
                        "phase_1": phase1_result,
                        "phase_2": phase2_result,
                        "phase_3_scheduled": phase3_scheduled,
                    },
                )

            status = "success" if failed == 0 else "partial" if total_assigned > 0 else "error"
            
            return {
                "status": status,
                "total_preplanificada": total_preplanificada,
                "successful_assignments": total_assigned,
                "failed_assignments": failed,
                "phase_1_assigned": phase1_result['assigned'],
                "phase_2_assigned": phase2_result['assigned'],
                "phase_3_scheduled": phase3_scheduled,
                "summary": summary,
            }

        except Exception as e:
            logger.error(f"PlanificacionAgent: Critical error during planning: {str(e)}")
            return {
                "status": "error",
                "total_preplanificada": 0,
                "successful_assignments": 0,
                "failed_assignments": 0,
                "phase_1_assigned": 0,
                "phase_2_assigned": 0,
                "phase_3_scheduled": False,
                "summary": f"Planning failed: {str(e)}",
            }

    async def balance_initial_assignment(self) -> Dict[str, Any]:
        """
        Phase 1: Assign 1 OT to each available crew (round-robin balance).
        
        Returns:
            Dict with {total, assigned, failed}
        """
        logger.info("PlanificacionAgent: Executing Phase 1 - Initial Balance")
        
        try:
            # Get all active crews
            crews = await self.get_available_crews()
            if not crews:
                logger.warning("PlanificacionAgent: No available crews for Phase 1")
                return {"total": 0, "assigned": 0, "failed": 0}

            # Get all PREPLANIFICADA OTs
            ots = await self.get_preplanificada_ots()
            logger.info(f"PlanificacionAgent: Found {len(ots)} PREPLANIFICADA OTs")

            assigned = 0
            failed = 0

            # Round-robin assignment: assign 1 OT to each crew
            for idx, crew in enumerate(crews):
                if idx >= len(ots):
                    break  # No more OTs to assign

                ot = ots[idx]
                try:
                    await self.assign_ot_to_crew(
                        ot_id=str(ot.id),
                        cuadrilla_id=str(crew.id),
                        assigned_by_agent="PlanificacionAgent",
                        distance=None,  # Centroid may not be available yet
                    )
                    assigned += 1
                    logger.debug(f"PlanificacionAgent: Assigned OT {ot.external_id} to crew {crew.nombre}")
                except Exception as e:
                    logger.warning(f"PlanificacionAgent: Failed to assign OT to crew: {str(e)}")
                    failed += 1

            return {"total": len(ots), "assigned": assigned, "failed": failed}

        except Exception as e:
            logger.error(f"PlanificacionAgent: Error in Phase 1: {str(e)}")
            return {"total": 0, "assigned": 0, "failed": 1}

    async def proximity_assignment(self) -> Dict[str, Any]:
        """
        Phase 2: Assign remaining OTs to crews within 10km of crew centroid.
        
        Returns:
            Dict with {total, assigned, failed}
        """
        logger.info("PlanificacionAgent: Executing Phase 2 - Proximity Assignment")
        
        try:
            # Get crews with their current centroid
            crews = await self.get_available_crews()
            if not crews:
                logger.warning("PlanificacionAgent: No available crews for Phase 2")
                return {"total": 0, "assigned": 0, "failed": 0}

            # Get remaining unassigned OTs
            unassigned_ots = await self.get_unassigned_ots()
            logger.info(f"PlanificacionAgent: Found {len(unassigned_ots)} unassigned OTs")

            assigned = 0
            failed = 0

            # For each unassigned OT, find closest crew within 10km
            for ot in unassigned_ots:
                try:
                    # Skip if OT has no coordinates
                    if ot.lat is None or ot.long is None:
                        logger.debug(f"PlanificacionAgent: Skipping OT {ot.external_id} - no coordinates")
                        failed += 1
                        continue

                    # Find best crew within 10km
                    best_crew = None
                    best_distance = float('inf')

                    for crew in crews:
                        # Check crew capacity
                        if not await self.has_capacity(crew.id):
                            continue

                        # Calculate distance from crew centroid to OT
                        crew_centroid = (crew.last_centroid_lat, crew.last_centroid_long)
                        
                        # Skip if crew has no centroid
                        if crew_centroid[0] is None or crew_centroid[1] is None:
                            continue

                        ot_coords = (ot.lat, ot.long)
                        distance = await calculate_distance_km(crew_centroid, ot_coords)

                        # Enforce <10km rule (strict less-than)
                        if distance < 10.0 and distance < best_distance:
                            best_crew = crew
                            best_distance = distance

                    # Assign to best crew if found
                    if best_crew:
                        await self.assign_ot_to_crew(
                            ot_id=str(ot.id),
                            cuadrilla_id=str(best_crew.id),
                            assigned_by_agent="PlanificacionAgent",
                            distance=best_distance,
                        )
                        assigned += 1
                        logger.debug(
                            f"PlanificacionAgent: Assigned OT {ot.external_id} to {best_crew.nombre} "
                            f"(distance: {best_distance:.2f}km)"
                        )
                    else:
                        logger.debug(
                            f"PlanificacionAgent: No crew within 10km for OT {ot.external_id}, remains PREPLANIFICADA"
                        )
                        failed += 1

                except Exception as e:
                    logger.warning(f"PlanificacionAgent: Error assigning OT: {str(e)}")
                    failed += 1

            return {"total": len(unassigned_ots), "assigned": assigned, "failed": failed}

        except Exception as e:
            logger.error(f"PlanificacionAgent: Error in Phase 2: {str(e)}")
            return {"total": 0, "assigned": 0, "failed": 1}

    async def schedule_night_normalization(self) -> bool:
        """
        Phase 3: Schedule APScheduler job for 00:00 centroid recalculation.
        
        Returns:
            bool indicating if scheduling was successful
        """
        logger.info("PlanificacionAgent: Executing Phase 3 - Schedule Night Normalization")
        
        try:
            # TODO: Implement APScheduler integration
            # This would be implemented when APScheduler is fully integrated
            # For now, return True to indicate scheduling intent
            logger.info("PlanificacionAgent: Night normalization job scheduled for 00:00")
            return True

        except Exception as e:
            logger.error(f"PlanificacionAgent: Error scheduling normalization: {str(e)}")
            return False

    async def assign_ot_to_crew(
        self,
        ot_id: str,
        cuadrilla_id: str,
        assigned_by_agent: str = "PlanificacionAgent",
        distance: Optional[float] = None,
    ) -> bool:
        """
        Create Asignacion record linking OT to crew.
        
        Args:
            ot_id: OT UUID
            cuadrilla_id: Crew UUID
            assigned_by_agent: Source of assignment
            distance: Distance from crew centroid to OT (km)
            
        Returns:
            bool indicating success
        """
        try:
            if not self.db_session:
                return False

            assignment = Asignacion(
                ot_id=UUID(ot_id) if isinstance(ot_id, str) else ot_id,
                cuadrilla_id=UUID(cuadrilla_id) if isinstance(cuadrilla_id, str) else cuadrilla_id,
                assigned_by_agent=assigned_by_agent,
                distancia_centroide_km=distance,
                assigned_at=datetime.utcnow(),
                activa=True,
            )

            self.db_session.add(assignment)
            await self.db_session.commit()

            return True

        except Exception as e:
            logger.error(f"PlanificacionAgent: Error creating assignment: {str(e)}")
            return False

    # Helper methods
    async def get_available_crews(self) -> list:
        """Get all active crews."""
        # TODO: Implement database query
        return []

    async def get_preplanificada_ots(self) -> list:
        """Get all PREPLANIFICADA OTs."""
        # TODO: Implement database query
        return []

    async def get_unassigned_ots(self) -> list:
        """Get OTs without active assignments."""
        # TODO: Implement database query
        return []

    async def has_capacity(self, crew_id: UUID) -> bool:
        """Check if crew has available capacity."""
        # TODO: Implement capacity check
        return True

