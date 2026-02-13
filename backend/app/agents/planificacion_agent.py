import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from langchain_openai import ChatOpenAI

from app.agents.state import PEIState, add_message, add_error, add_assignment
from app.config import get_settings
from app.models import OT, Cuadrilla, Asignacion, LogAgente
from app.services import PlanningService
from app.database import SessionLocal


class PlanificacionAgent:
    """
    Planificación Agent for implementing the 3-phase crew assignment algorithm
    
    Responsible for:
    - Phase 1: Balanced initial assignment (1 OT per Principal crew for equity)
    - Phase 2: Proximity-based assignment (assign OTs within 10km of crew centroid)
    - Phase 3: Nocturnal route optimization (handled by scheduler)
    - Managing OT-to-Cuadrilla assignments with capacity and distance validation
    - LLM-assisted decision making for edge cases
    """

    def __init__(self):
        """Initialize PlanificacionAgent with OpenAI LLM and planning service"""
        self.settings = get_settings()
        
        # Initialize ChatOpenAI LLM for edge case decisions
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.3,  # Moderate temperature for assignment decisions
            api_key=self.settings.OPENAI_API_KEY,
        )
        
        # Initialize planning service for algorithm implementation
        self.planning_service = PlanningService()

    def assign_ots(self, state: PEIState) -> PEIState:
        """
        Execute the 3-phase planning algorithm for OT-to-Cuadrilla assignment
        
        Args:
            state: Current PEIState from LangGraph
        
        Returns:
            Updated PEIState with assignment results
        """
        db_session = state.get("db_session")
        ot_ids = state.get("ot_ids", [])
        force_balance = state.get("force_balance", False)
        
        # If no session provided, create one temporarily
        if db_session is None:
            db_session = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            # Fetch OTs and Cuadrillas from database
            ots = db_session.query(OT).filter(OT.id.in_(ot_ids)).all() if ot_ids else []
            cuadrillas = db_session.query(Cuadrilla).filter(Cuadrilla.is_active == True).all()
            
            if not ots:
                state = add_message(state, "agent", "No OTs to assign")
                state["assignments"] = []
                return state
            
            if not cuadrillas:
                state = add_error(state, "No active cuadrillas available for assignment")
                state = add_message(state, "agent", "Error: No active cuadrillas available")
                state["assignments"] = []
                return state
            
            assignments = []
            failed_assignments = []
            
            # Phase 1: Balance initial assignment
            # Assign 1 OT to each available Principal cuadrilla for equity
            if force_balance or len(ots) >= len(cuadrillas):
                principal_cuadrillas = [c for c in cuadrillas if c.type == "Principal"]
                
                for idx, ot in enumerate(ots):
                    if idx >= len(principal_cuadrillas):
                        break
                    
                    cuadrilla = principal_cuadrillas[idx]
                    
                    # Check if already assigned
                    existing = db_session.query(Asignacion).filter(
                        Asignacion.ot_id == ot.id
                    ).first()
                    
                    if not existing:
                        # Create assignment
                        assignment = Asignacion(
                            ot_id=ot.id,
                            cuadrilla_id=cuadrilla.id,
                            assigned_at=datetime.utcnow(),
                            assigned_by_agent="PlanificacionAgent",
                            distance_to_centroid=0,
                            priority=self._get_ot_priority(ot),
                        )
                        db_session.add(assignment)
                        
                        # Update cuadrilla load
                        cuadrilla.current_load += 1
                        
                        assignments.append({
                            "ot_id": ot.id,
                            "ot_external_id": ot.external_id,
                            "cuadrilla_id": cuadrilla.id,
                            "cuadrilla_name": cuadrilla.name,
                            "phase": "balance_initial",
                            "distance_km": 0,
                        })
                        
                        # Log assignment
                        self._log_assignment(
                            db_session,
                            ot_id=ot.id,
                            cuadrilla_id=cuadrilla.id,
                            phase="balance_initial",
                            success=True,
                        )
                db_session.commit()
            
            # Phase 2: Proximity-based assignment
            # Assign remaining OTs to cuadrillas within 10km of centroid
            for ot in ots:
                # Skip if already assigned
                existing = db_session.query(Asignacion).filter(
                    Asignacion.ot_id == ot.id
                ).first()
                
                if existing:
                    continue
                
                # Try to assign by proximity
                if ot.lat is None or ot.long is None:
                    failed_assignments.append({
                        "ot_id": ot.id,
                        "ot_external_id": ot.external_id,
                        "reason": "Missing geo coordinates",
                    })
                    state = add_error(state, f"OT {ot.external_id}: Missing geo coordinates")
                    continue
                
                # Find suitable cuadrilla by proximity
                assigned_cuadrilla = self.planning_service.assign_by_proximity(
                    db_session,
                    ot,
                    max_distance_km=self.settings.PROXIMITY_RADIUS_KM,
                )
                
                if assigned_cuadrilla:
                    # Create assignment
                    distance = self._calculate_distance(
                        (ot.lat, ot.long),
                        (assigned_cuadrilla.last_centroid_lat, assigned_cuadrilla.last_centroid_long),
                    )
                    
                    assignment = Asignacion(
                        ot_id=ot.id,
                        cuadrilla_id=assigned_cuadrilla.id,
                        assigned_at=datetime.utcnow(),
                        assigned_by_agent="PlanificacionAgent",
                        distance_to_centroid=distance,
                        priority=self._get_ot_priority(ot),
                    )
                    db_session.add(assignment)
                    
                    # Update cuadrilla load
                    assigned_cuadrilla.current_load += 1
                    
                    assignments.append({
                        "ot_id": ot.id,
                        "ot_external_id": ot.external_id,
                        "cuadrilla_id": assigned_cuadrilla.id,
                        "cuadrilla_name": assigned_cuadrilla.name,
                        "phase": "proximity",
                        "distance_km": round(distance, 2),
                    })
                    
                    # Log assignment
                    self._log_assignment(
                        db_session,
                        ot_id=ot.id,
                        cuadrilla_id=assigned_cuadrilla.id,
                        phase="proximity",
                        success=True,
                        distance_km=distance,
                    )
                    
                    db_session.commit()
                else:
                    # Try LLM-assisted decision for edge cases
                    available_cuadrillas = [
                        c for c in cuadrillas
                        if c.current_load < c.capacity
                    ]
                    
                    if available_cuadrillas:
                        edge_case_cuadrilla = self.use_llm_for_edge_cases(ot, available_cuadrillas)
                        
                        if edge_case_cuadrilla:
                            # Create assignment via LLM recommendation
                            distance = self._calculate_distance(
                                (ot.lat, ot.long),
                                (edge_case_cuadrilla.last_centroid_lat or 0, 
                                 edge_case_cuadrilla.last_centroid_long or 0),
                            )
                            
                            assignment = Asignacion(
                                ot_id=ot.id,
                                cuadrilla_id=edge_case_cuadrilla.id,
                                assigned_at=datetime.utcnow(),
                                assigned_by_agent="PlanificacionAgent",
                                distance_to_centroid=distance,
                                priority=self._get_ot_priority(ot),
                            )
                            db_session.add(assignment)
                            
                            # Update cuadrilla load
                            edge_case_cuadrilla.current_load += 1
                            
                            assignments.append({
                                "ot_id": ot.id,
                                "ot_external_id": ot.external_id,
                                "cuadrilla_id": edge_case_cuadrilla.id,
                                "cuadrilla_name": edge_case_cuadrilla.name,
                                "phase": "llm_edge_case",
                                "distance_km": round(distance, 2),
                            })
                            
                            # Log assignment
                            self._log_assignment(
                                db_session,
                                ot_id=ot.id,
                                cuadrilla_id=edge_case_cuadrilla.id,
                                phase="llm_edge_case",
                                success=True,
                                distance_km=distance,
                            )
                            
                            db_session.commit()
                        else:
                            failed_assignments.append({
                                "ot_id": ot.id,
                                "ot_external_id": ot.external_id,
                                "reason": "LLM could not recommend suitable cuadrilla",
                            })
                            state = add_error(state, f"OT {ot.external_id}: No suitable cuadrilla found")
                    else:
                        failed_assignments.append({
                            "ot_id": ot.id,
                            "ot_external_id": ot.external_id,
                            "reason": "No cuadrillas with available capacity",
                        })
                        state = add_error(state, f"OT {ot.external_id}: No cuadrillas with available capacity")
            
            # Update state with assignment results
            state["assignments"] = assignments
            
            # Add summary message
            summary_msg = (
                f"Planificación Agent: Assigned {len(assignments)} OTs to cuadrillas. "
                f"Failed: {len(failed_assignments)}."
            )
            state = add_message(state, "agent", summary_msg)
            
            return state
            
        except Exception as e:
            # Log critical error
            error_msg = f"Critical error in Planificación Agent: {str(e)}"
            state = add_error(state, error_msg)
            state = add_message(state, "agent", error_msg)
            state["assignments"] = []
            
            self._log_assignment(
                db_session,
                ot_id=None,
                cuadrilla_id=None,
                phase="error",
                success=False,
                error_message=error_msg,
            )
            
            return state
            
        finally:
            if should_close:
                db_session.close()

    def use_llm_for_edge_cases(
        self,
        ot: OT,
        available_cuadrillas: List[Cuadrilla]
    ) -> Optional[Cuadrilla]:
        """
        Use LLM to make assignment decision when no cuadrilla meets proximity criteria
        
        Args:
            ot: OT to assign
            available_cuadrillas: List of cuadrillas with available capacity
        
        Returns:
            Recommended Cuadrilla or None
        """
        if not available_cuadrillas:
            return None
        
        try:
            # Build context for LLM decision
            cuadrilla_options = "\n".join([
                f"- {c.name} ({c.type}): Load {c.current_load}/{c.capacity}, "
                f"Centroid: ({c.last_centroid_lat or 'N/A'}, {c.last_centroid_long or 'N/A'})"
                for c in available_cuadrillas
            ])
            
            prompt = f"""You are an assignment optimizer for the PEI platform.
An OT could not be assigned using proximity rules (within 10km of crew centroid).

OT Details:
- External ID: {ot.external_id}
- Project Type: {ot.project_type}
- Location: ({ot.lat}, {ot.long})
- Status: {ot.status}

Available Cuadrillas (with capacity):
{cuadrilla_options}

Choose the best cuadrilla for this OT considering:
1. Crew type (Principal preferred for PUBLICO projects)
2. Current load (prefer less loaded crews)
3. Project type compatibility
4. Geographic vicinity if available

Respond with ONLY the cuadrilla name, nothing else."""
            
            response = self.llm.invoke(prompt)
            recommended_name = response.content.strip().lower()
            
            # Find matching cuadrilla by name
            for cuadrilla in available_cuadrillas:
                if cuadrilla.name.lower() == recommended_name:
                    return cuadrilla
            
            # If no match, return least loaded cuadrilla as fallback
            return min(available_cuadrillas, key=lambda c: c.current_load)
            
        except Exception as e:
            print(f"Error in LLM edge case decision: {str(e)}")
            # Fallback: return least loaded cuadrilla
            return min(available_cuadrillas, key=lambda c: c.current_load) if available_cuadrillas else None

    def _get_ot_priority(self, ot: OT) -> int:
        """
        Get priority value for OT based on project type
        Lower value = higher priority
        
        Args:
            ot: OT object
        
        Returns:
            Priority value (1-3)
        """
        priorities = {
            "PUBLICO": 1,
            "PRIVADO": 2,
            "TERCERIZADO": 3,
        }
        return priorities.get(ot.project_type, 999)

    def _calculate_distance(self, coord1: tuple, coord2: tuple) -> float:
        """
        Calculate distance between two coordinates in kilometers
        
        Args:
            coord1: (lat, long) tuple
            coord2: (lat, long) tuple
        
        Returns:
            Distance in kilometers
        """
        from geopy.distance import geodesic
        
        try:
            return geodesic(coord1, coord2).kilometers
        except Exception:
            return float('inf')  # Return infinity if calculation fails

    def _log_assignment(
        self,
        db_session: Optional[Session],
        ot_id: Optional[int],
        cuadrilla_id: Optional[int],
        phase: str,
        success: bool,
        distance_km: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log assignment decision to LogAgente table for audit trail
        
        Args:
            db_session: SQLAlchemy session (optional)
            ot_id: OT database ID
            cuadrilla_id: Cuadrilla database ID
            phase: Planning phase (balance_initial, proximity, llm_edge_case, error)
            success: Whether assignment was successful
            distance_km: Distance to cuadrilla centroid
            error_message: Optional error message
        """
        # If no session provided, create one temporarily
        if db_session is None:
            db_session = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            log_entry = LogAgente(
                ot_id=ot_id,
                cuadrilla_id=cuadrilla_id,
                agente_name="PlanificacionAgent",
                accion="assign_ots",
                resultado="ASIGNADO" if success else "FALLO",
                raw_llm_response=json.dumps({
                    "phase": phase,
                    "success": success,
                    "distance_km": distance_km,
                    "error_message": error_message,
                }),
            )
            db_session.add(log_entry)
            db_session.commit()
        except Exception as e:
            # Log error but don't raise - assignment should proceed
            print(f"Error logging assignment: {str(e)}")
            db_session.rollback()
        finally:
            if should_close:
                db_session.close()

