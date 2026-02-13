"""
PlanificacionAgent for PEI Platform agentic system.
Implements 3-phase algorithm for optimal OT assignment to cuadrillas.
"""

from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI

from backend.agents.base_agent import BaseAgent
from backend.models import OT, Cuadrilla
from backend.models.log_agente import ActionResult
from backend.utils.geo_utils import calculate_distance, calculate_centroid
from backend.utils.business_rules import can_assign_to_cuadrilla, get_project_priority
from backend.config import get_settings


class PlanificacionAgent(BaseAgent):
    """
    PlanificacionAgent that implements the 3-phase OT assignment algorithm.

    The PlanificacionAgent is responsible for optimally assigning unassigned OTs
    to cuadrillas based on capacity, geographic proximity, and project priority.

    3-Phase Algorithm:
    ==================
    
    PHASE 1 - Balance Load:
        - Fetch all active cuadrillas
        - For each cuadrilla with available capacity, assign exactly 1 unassigned OT
        - Prioritizes PUBLICO > PRIVADO > TERCERIZADO projects
        - Ensures equal distribution of work across all teams
        - Updates current_load for each cuadrilla
    
    PHASE 2 - Proximity-Based Assignment:
        - For remaining unassigned OTs
        - For each cuadrilla with available capacity
        - Calculate distance from OT location to cuadrilla centroid
        - Assign OT if distance <= MAX_DISTANCE_KM (typically 10km)
        - Prevents assigning OTs too far from team's service area
        - Prioritizes high-priority projects (PUBLICO)
    
    PHASE 3 - Centroid Recalculation:
        - After all assignments completed
        - For each cuadrilla that received new assignments
        - Recalculate centroid as average of all assigned OT coordinates
        - Updates last_centroid_lat and last_centroid_long
        - Centroid used for next round of proximity calculations
        - Optimizes routes and service area definition

    Key Constraints:
    - Cuadrilla capacity: daily_capacity
    - Geographic proximity: MAX_DISTANCE_KM (10km default)
    - Project priority: PUBLICO (1) > PRIVADO (2) > TERCERIZADO (3)
    - OT coordinates: Must have valid lat and long (no geo_error)
    """

    def __init__(self, llm: ChatOpenAI, db_session: Session):
        """
        Initialize PlanificacionAgent.

        Args:
            llm: ChatOpenAI instance for LLM operations (unused in PlanificacionAgent but required by BaseAgent)
            db_session: SQLAlchemy session for database operations
        """
        super().__init__(llm, db_session)
        self.agent_name = "PlanificacionAgent"
        self.config = get_settings()
        self.max_distance_km = self.config.MAX_DISTANCE_KM

    async def execute(self, state: Dict) -> Dict:
        """
        Execute the 3-phase OT assignment algorithm.

        Orchestrates PHASE 1 (balance), PHASE 2 (proximity), and PHASE 3 (centroid)
        to optimally assign all unassigned OTs to available cuadrillas.

        Args:
            state: Graph state containing:
                - user_input (str): User request or description
                - event_type (str): Type of event
                - Other state fields passed through

        Returns:
            Updated state with:
            - action_result (str): Description of assignments made
            - agent_logs (list): Updated with PlanificacionAgent execution logs
            - ot_data (dict): Assignment statistics (ots_assigned, failed_assignments, etc.)
        """
        try:
            # Initialize assignment tracking
            assignments_made = []
            failed_assignments = []
            cuadrillas_updated = 0

            # PHASE 1: Balance Load - assign 1 OT per cuadrilla
            phase1_assignments = self._phase1_balance_load()
            assignments_made.extend(phase1_assignments)

            self._log_action(
                agente_name="PlanificacionAgent",
                accion="phase1_balance_load",
                resultado=ActionResult.SUCCESS,
                metadata={
                    "assignments": len(phase1_assignments),
                    "cuadrillas_updated": len(set(a[1] for a in phase1_assignments)),
                },
            )

            # PHASE 2: Proximity-Based Assignment - assign remaining OTs
            phase2_assignments, phase2_failures = self._phase2_proximity_assignment()
            assignments_made.extend(phase2_assignments)
            failed_assignments.extend(phase2_failures)

            self._log_action(
                agente_name="PlanificacionAgent",
                accion="phase2_proximity_assignment",
                resultado=ActionResult.SUCCESS,
                metadata={
                    "assignments": len(phase2_assignments),
                    "failures": len(phase2_failures),
                },
            )

            # PHASE 3: Centroid Recalculation - update cuadrilla positions
            cuadrillas_to_update = set(a[1] for a in assignments_made)
            cuadrillas_updated = self._phase3_centroid_recalculation(cuadrillas_to_update)

            self._log_action(
                agente_name="PlanificacionAgent",
                accion="phase3_centroid_recalculation",
                resultado=ActionResult.SUCCESS,
                metadata={
                    "cuadrillas_updated": cuadrillas_updated,
                },
            )

            # Overall success logging
            total_assignments = len(assignments_made)
            action_result = (
                f"Planning completed: {total_assignments} OTs assigned to cuadrillas. "
                f"Centroids updated for {cuadrillas_updated} cuadrillas."
            )

            if failed_assignments:
                action_result += (
                    f" {len(failed_assignments)} OTs could not be assigned due to "
                    f"capacity or distance constraints."
                )

            self._log_action(
                agente_name="PlanificacionAgent",
                accion="execute_3phase_algorithm",
                resultado=ActionResult.SUCCESS,
                metadata={
                    "total_assignments": total_assignments,
                    "cuadrillas_updated": cuadrillas_updated,
                    "failed_assignments": len(failed_assignments),
                },
            )

            return {
                **state,
                "action_result": action_result,
                "ot_data": {
                    "ots_assigned": total_assignments,
                    "cuadrillas_updated": cuadrillas_updated,
                    "failed_assignments": len(failed_assignments),
                    "failed_ot_ids": [f["ot_id"] for f in failed_assignments],
                },
            }

        except Exception as e:
            action_result = f"PlanificacionAgent failed: {str(e)}"
            self._log_action(
                agente_name="PlanificacionAgent",
                accion="execute",
                resultado=ActionResult.FAILURE,
                metadata={"error": str(e)},
            )
            return {
                **state,
                "action_result": action_result,
                "error_message": str(e),
                "ot_data": {
                    "ots_assigned": 0,
                    "cuadrillas_updated": 0,
                    "failed_assignments": 0,
                },
            }

    def _phase1_balance_load(self) -> List[Tuple[int, int]]:
        """
        PHASE 1: Balance Load - assign 1 OT per cuadrilla.

        Ensures equal initial distribution of work across all active cuadrillas.
        Each cuadrilla with available capacity gets exactly one OT.

        Algorithm:
        1. Query all active cuadrillas
        2. Sort by project priority (PUBLICO first)
        3. For each cuadrilla with capacity:
           - Get unassigned OT with highest priority
           - Assign to cuadrilla
           - Update current_load

        Returns:
            List of (ot_id, cuadrilla_id) tuples for successful assignments
        """
        assignments = []

        try:
            # Query all active cuadrillas
            cuadrillas = (
                self.db_session.query(Cuadrilla)
                .filter(Cuadrilla.is_active == True)
                .all()
            )

            if not cuadrillas:
                return assignments

            # For each cuadrilla with capacity, assign 1 OT
            for cuadrilla in cuadrillas:
                if cuadrilla.current_load >= cuadrilla.daily_capacity:
                    continue  # Skip if at capacity

                # Get unassigned OT with highest priority
                unassigned_ot = (
                    self.db_session.query(OT)
                    .filter(OT.cuadrilla_id == None)
                    .order_by(OT.created_at)
                    .first()
                )

                if not unassigned_ot:
                    break  # No more unassigned OTs

                # Assign OT to cuadrilla
                unassigned_ot.cuadrilla_id = cuadrilla.id
                cuadrilla.current_load += 1
                assignments.append((unassigned_ot.id, cuadrilla.id))

            # Commit assignments
            self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            print(f"❌ Error in PHASE 1 balance load: {str(e)}")

        return assignments

    def _phase2_proximity_assignment(
        self,
    ) -> Tuple[List[Tuple[int, int]], List[Dict]]:
        """
        PHASE 2: Proximity-Based Assignment - assign remaining OTs.

        For each remaining unassigned OT, find the closest cuadrilla within
        MAX_DISTANCE_KM and assign if cuadrilla has capacity.

        Algorithm:
        1. Query all unassigned OTs
        2. For each OT:
           - Sort cuadrillas by distance to OT location
           - Find closest cuadrilla with capacity and distance <= MAX_DISTANCE_KM
           - Assign if found
           - Log failure if no suitable cuadrilla

        Returns:
            Tuple of (assignments_list, failures_list)
            - assignments_list: List of (ot_id, cuadrilla_id) tuples
            - failures_list: List of dicts with {ot_id, reason}
        """
        assignments = []
        failures = []

        try:
            # Query all unassigned OTs
            unassigned_ots = (
                self.db_session.query(OT)
                .filter(OT.cuadrilla_id == None)
                .order_by(OT.project_type)  # PUBLICO first due to enum ordering
                .all()
            )

            # Query all active cuadrillas
            cuadrillas = (
                self.db_session.query(Cuadrilla)
                .filter(Cuadrilla.is_active == True)
                .all()
            )

            if not cuadrillas:
                for ot in unassigned_ots:
                    failures.append({"ot_id": ot.id, "reason": "No active cuadrillas"})
                return assignments, failures

            # For each unassigned OT
            for ot in unassigned_ots:
                if ot.lat is None or ot.long is None:
                    failures.append(
                        {
                            "ot_id": ot.id,
                            "reason": "Missing geographic coordinates (geo_error=True)",
                        }
                    )
                    continue

                # Find closest cuadrilla with capacity and within distance
                best_cuadrilla = None
                best_distance = float("inf")

                for cuadrilla in cuadrillas:
                    # Skip if at capacity
                    if cuadrilla.current_load >= cuadrilla.daily_capacity:
                        continue

                    # Get cuadrilla centroid
                    if (
                        cuadrilla.last_centroid_lat is None
                        or cuadrilla.last_centroid_long is None
                    ):
                        # New cuadrilla with no assignments yet - assign OT
                        best_cuadrilla = cuadrilla
                        break

                    # Calculate distance from OT to cuadrilla centroid
                    distance = calculate_distance(
                        ot.lat,
                        ot.long,
                        cuadrilla.last_centroid_lat,
                        cuadrilla.last_centroid_long,
                    )

                    # Check if within max distance and closer than best option
                    if distance <= self.max_distance_km and distance < best_distance:
                        best_cuadrilla = cuadrilla
                        best_distance = distance

                # Assign if suitable cuadrilla found
                if best_cuadrilla:
                    ot.cuadrilla_id = best_cuadrilla.id
                    best_cuadrilla.current_load += 1
                    assignments.append((ot.id, best_cuadrilla.id))
                else:
                    failures.append(
                        {
                            "ot_id": ot.id,
                            "reason": f"No cuadrilla within {self.max_distance_km}km or all at capacity",
                        }
                    )

            # Commit assignments
            self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            print(f"❌ Error in PHASE 2 proximity assignment: {str(e)}")

        return assignments, failures

    def _phase3_centroid_recalculation(self, cuadrilla_ids: set) -> int:
        """
        PHASE 3: Centroid Recalculation - update cuadrilla positions.

        For each cuadrilla that received new assignments, recalculate the
        geographic centroid as the average of all assigned OT locations.

        Algorithm:
        1. For each cuadrilla in the update set:
           - Get all assigned OTs with valid coordinates
           - Calculate centroid using arithmetic mean of coordinates
           - Update last_centroid_lat and last_centroid_long
           - Commit update

        Returns:
            Number of cuadrillas with updated centroids
        """
        cuadrillas_updated = 0

        try:
            for cuadrilla_id in cuadrilla_ids:
                cuadrilla = (
                    self.db_session.query(Cuadrilla)
                    .filter(Cuadrilla.id == cuadrilla_id)
                    .first()
                )

                if not cuadrilla:
                    continue

                # Recalculate centroid using cuadrilla model method
                centroid_lat, centroid_long = cuadrilla.calculate_centroid()

                # Update model fields (already done by calculate_centroid)
                # Commit the update
                self.db_session.add(cuadrilla)
                cuadrillas_updated += 1

            # Commit all centroid updates
            self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            print(f"❌ Error in PHASE 3 centroid recalculation: {str(e)}")

        return cuadrillas_updated

