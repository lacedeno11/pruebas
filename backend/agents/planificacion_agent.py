"""Planning agent implementing 3-phase assignment algorithm."""

from backend.graph.state import PEIState, add_agent_response
from backend.database.models import OT, Cuadrilla, Assignment, AgentLog, OTStatus, OTProjectType
from backend.database.db import SessionLocal
from backend.utils.geo import calculate_centroid, haversine_distance
from backend.utils.validators import validate_crew_capacity
from sqlalchemy import and_
from datetime import datetime
import logging
import os

# Configure logging
logger = logging.getLogger(__name__)

# Try to import LLM provider
try:
    from langchain_openai import ChatOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


PLANNING_SUMMARY_PROMPT = """You are a helpful assistant summarizing work order planning results.

Generate a natural language summary of the following OT planning algorithm execution:
- Total unassigned OTs: {total_unassigned}
- Phase 1 assignments (initial balance): {phase1_assignments}
- Phase 2 assignments (centroid proximity): {phase2_assignments}
- OTs pending manual review (no crew in range): {pending_manual}
- Total assignments created: {total_assignments}

Provide a brief, professional summary suitable for a project manager report. 
Highlight critical information like unassigned OTs and crews at capacity."""


async def planning_node(state: PEIState) -> PEIState:
    """
    Planning node implementing 3-phase assignment algorithm.
    
    Phase 1 - Initial Balance:
    - Query all OTs with status=PREPLANIFICADA
    - Query all Cuadrillas
    - For each crew with ots_asignadas_count=0:
      - Assign 1 OT, prioritizing PUBLICO projects
    
    Phase 2 - Centroid Proximity:
    - For remaining unassigned OTs:
      - Calculate each crew's centroid from assigned OTs
      - Find crews within MAX_DISTANCE_KM (10km)
      - Assign to crew with most remaining capacity
      - If no crew in range, mark for manual review
    
    Phase 3 - Route Optimization:
    - Called separately at 00:00 UTC
    - Recalculates all crew centroids
    - Stores new centroids in Cuadrilla.last_centroid_lat/long
    
    Args:
        state: Current PEIState with PLAN action
    
    Returns:
        Updated PEIState with assignment results
    """
    
    logger.info("Planning Agent starting 3-phase algorithm")
    
    db = SessionLocal()
    planning_stats = {
        "total_unassigned": 0,
        "phase1_assignments": 0,
        "phase2_assignments": 0,
        "pending_manual": 0,
        "total_assignments": 0,
        "errors": [],
    }
    
    try:
        # Get configuration
        max_distance_km = float(os.getenv("MAX_DISTANCE_KM", "10"))
        
        # ==================== PHASE 1: Initial Balance ====================
        logger.info("Phase 1: Initial Balance starting")
        
        try:
            # Get all unassigned OTs with PREPLANIFICADA status
            unassigned_ots = db.query(OT).filter(
                and_(
                    OT.status == OTStatus.PREPLANIFICADA.value,
                    OT.cuadrilla_id == None,
                )
            ).all()
            
            planning_stats["total_unassigned"] = len(unassigned_ots)
            logger.info(f"Found {len(unassigned_ots)} unassigned OTs for Phase 1")
            
            # Get all cuadrillas
            cuadrillas = db.query(Cuadrilla).all()
            logger.info(f"Found {len(cuadrillas)} cuadrillas for assignment")
            
            # Sort OTs: PUBLICO first (priority), then others
            public_ots = [ot for ot in unassigned_ots if ot.project_type == OTProjectType.PUBLICO.value]
            other_ots = [ot for ot in unassigned_ots if ot.project_type != OTProjectType.PUBLICO.value]
            sorted_ots = public_ots + other_ots
            
            # Phase 1: Assign 1 OT to each crew with zero assignments
            for cuadrilla in cuadrillas:
                if cuadrilla.ots_asignadas_count == 0 and sorted_ots:
                    # Assign first available OT
                    ot = sorted_ots.pop(0)
                    
                    assignment = Assignment(
                        ot_id=ot.id,
                        cuadrilla_id=cuadrilla.id,
                        assigned_by_agent="Planificación Agent - Phase 1",
                    )
                    
                    ot.cuadrilla_id = cuadrilla.id
                    ot.status = OTStatus.PLANIFICADA.value
                    ot.updated_at = datetime.utcnow()
                    cuadrilla.ots_asignadas_count += 1
                    
                    db.add(assignment)
                    planning_stats["phase1_assignments"] += 1
                    
                    logger.info(f"Phase 1: Assigned OT {ot.external_id} to crew {cuadrilla.name}")
            
            db.commit()
            logger.info(f"Phase 1 complete: {planning_stats['phase1_assignments']} assignments")
        
        except Exception as e:
            logger.error(f"Phase 1 error: {str(e)}")
            planning_stats["errors"].append(f"Phase 1: {str(e)}")
            db.rollback()
        
        # ==================== PHASE 2: Centroid Proximity ====================
        logger.info("Phase 2: Centroid Proximity starting")
        
        try:
            # Get remaining unassigned OTs
            remaining_ots = db.query(OT).filter(
                and_(
                    OT.status == OTStatus.PREPLANIFICADA.value,
                    OT.cuadrilla_id == None,
                )
            ).all()
            
            logger.info(f"Found {len(remaining_ots)} remaining unassigned OTs for Phase 2")
            
            # Get all cuadrillas (refresh from DB)
            cuadrillas = db.query(Cuadrilla).all()
            
            for ot in remaining_ots:
                assigned = False
                closest_crew = None
                closest_distance = float('inf')
                closest_crew_capacity = 0
                
                # For each crew, calculate centroid and check distance
                for cuadrilla in cuadrillas:
                    # Check if crew has capacity
                    if cuadrilla.ots_asignadas_count >= cuadrilla.capacidad_diaria:
                        continue
                    
                    # Get assigned OTs for this crew
                    assigned_ots = db.query(OT).filter(OT.cuadrilla_id == cuadrilla.id).all()
                    
                    if not assigned_ots:
                        # Crew has no assignments yet, cannot calculate centroid
                        continue
                    
                    try:
                        # Calculate centroid from assigned OTs
                        coordinates = [(ot_item.lat, ot_item.long) for ot_item in assigned_ots]
                        centroid_lat, centroid_long = calculate_centroid(coordinates)
                        
                        # Calculate distance from OT to crew centroid
                        distance = haversine_distance(
                            centroid_lat,
                            centroid_long,
                            ot.lat,
                            ot.long,
                        )
                        
                        # Check if within range
                        if distance <= max_distance_km:
                            # Track crew with most remaining capacity
                            remaining_capacity = cuadrilla.capacidad_diaria - cuadrilla.ots_asignadas_count
                            if distance < closest_distance or (distance == closest_distance and remaining_capacity > closest_crew_capacity):
                                closest_crew = cuadrilla
                                closest_distance = distance
                                closest_crew_capacity = remaining_capacity
                    
                    except Exception as e:
                        logger.warning(f"Centroid calculation error for crew {cuadrilla.name}: {str(e)}")
                        continue
                
                # If suitable crew found, assign OT
                if closest_crew:
                    assignment = Assignment(
                        ot_id=ot.id,
                        cuadrilla_id=closest_crew.id,
                        assigned_by_agent="Planificación Agent - Phase 2",
                    )
                    
                    ot.cuadrilla_id = closest_crew.id
                    ot.status = OTStatus.PLANIFICADA.value
                    ot.updated_at = datetime.utcnow()
                    closest_crew.ots_asignadas_count += 1
                    
                    db.add(assignment)
                    planning_stats["phase2_assignments"] += 1
                    
                    logger.info(f"Phase 2: Assigned OT {ot.external_id} to crew {closest_crew.name} ({closest_distance:.1f}km)")
                    assigned = True
                
                # If no suitable crew, mark for manual review
                if not assigned:
                    planning_stats["pending_manual"] += 1
                    logger.info(f"Phase 2: OT {ot.external_id} marked for manual review (no crew in range)")
            
            db.commit()
            logger.info(f"Phase 2 complete: {planning_stats['phase2_assignments']} assignments, {planning_stats['pending_manual']} pending manual")
        
        except Exception as e:
            logger.error(f"Phase 2 error: {str(e)}")
            planning_stats["errors"].append(f"Phase 2: {str(e)}")
            db.rollback()
        
        # ==================== PHASE 3: Route Optimization ====================
        # This is called separately at 00:00 UTC via scheduler
        # But we can include it here for completeness
        logger.info("Phase 3: Route Optimization updating centroids")
        
        try:
            cuadrillas = db.query(Cuadrilla).all()
            
            for cuadrilla in cuadrillas:
                assigned_ots = db.query(OT).filter(OT.cuadrilla_id == cuadrilla.id).all()
                
                if assigned_ots and len(assigned_ots) > 0:
                    try:
                        # Calculate new centroid
                        coordinates = [(ot.lat, ot.long) for ot in assigned_ots]
                        centroid_lat, centroid_long = calculate_centroid(coordinates)
                        
                        # Update crew centroid
                        cuadrilla.last_centroid_lat = centroid_lat
                        cuadrilla.last_centroid_long = centroid_long
                        
                        logger.info(f"Phase 3: Updated centroid for {cuadrilla.name}: ({centroid_lat:.4f}, {centroid_long:.4f})")
                    
                    except Exception as e:
                        logger.warning(f"Phase 3: Centroid calculation failed for {cuadrilla.name}: {str(e)}")
            
            db.commit()
            logger.info("Phase 3 complete: Centroids updated")
        
        except Exception as e:
            logger.error(f"Phase 3 error: {str(e)}")
            planning_stats["errors"].append(f"Phase 3: {str(e)}")
            db.rollback()
        
        # ==================== Log all assignments ====================
        try:
            total_assignments = db.query(Assignment).count()
            planning_stats["total_assignments"] = total_assignments
            
            # Log planning action
            agent_log = AgentLog(
                agente_name="Planificación Agent",
                accion="Execute 3-Phase Planning Algorithm",
                resultado=f"Phase 1: {planning_stats['phase1_assignments']}, Phase 2: {planning_stats['phase2_assignments']}, Total: {planning_stats['total_assignments']}",
                raw_llm_response=f"Unassigned: {planning_stats['total_unassigned']}, Pending Manual: {planning_stats['pending_manual']}",
                timestamp=datetime.utcnow(),
            )
            db.add(agent_log)
            db.commit()
        
        except Exception as e:
            logger.error(f"Failed to log planning action: {str(e)}")
        
        # ==================== Generate summary ====================
        summary_text = await _generate_planning_summary(planning_stats)
        
        # Update state with agent response
        state = add_agent_response(
            state,
            agent_name="Planificación Agent",
            response={
                "total_unassigned": planning_stats["total_unassigned"],
                "phase1_assignments": planning_stats["phase1_assignments"],
                "phase2_assignments": planning_stats["phase2_assignments"],
                "pending_manual": planning_stats["pending_manual"],
                "total_assignments": planning_stats["total_assignments"],
                "summary": summary_text,
            },
        )
        
        logger.info("Planning Agent completed successfully")
        return state
    
    except Exception as e:
        logger.error(f"Planning Agent error: {str(e)}")
        state["error"] = f"Planning failed: {str(e)}"
        
        # Log error
        agent_log = AgentLog(
            agente_name="Planificación Agent",
            accion="Execute 3-Phase Planning Algorithm",
            resultado=f"ERROR: {str(e)}",
            timestamp=datetime.utcnow(),
        )
        db.add(agent_log)
        db.commit()
        
        return state
    
    finally:
        db.close()


async def _generate_planning_summary(stats: dict) -> str:
    """
    Generate natural language summary of planning results using LLM.
    
    Falls back to rule-based summary if LLM is unavailable.
    
    Args:
        stats: Dictionary with planning statistics
    
    Returns:
        str: Natural language summary
    """
    try:
        # Try to use LLM for summary generation
        if HAS_OPENAI:
            llm_model = os.getenv("LLM_MODEL", "gpt-4")
            openai_key = os.getenv("OPENAI_API_KEY")
            
            if openai_key and "gpt" in llm_model.lower():
                llm = ChatOpenAI(model_name=llm_model, api_key=openai_key, temperature=0.7)
                
                prompt = PLANNING_SUMMARY_PROMPT.format(
                    total_unassigned=stats["total_unassigned"],
                    phase1_assignments=stats["phase1_assignments"],
                    phase2_assignments=stats["phase2_assignments"],
                    pending_manual=stats["pending_manual"],
                    total_assignments=stats["total_assignments"],
                )
                
                response = llm.invoke(prompt)
                logger.info("Generated LLM-based planning summary")
                return response.content
    
    except Exception as e:
        logger.warning(f"Failed to generate LLM summary: {str(e)}")
    
    # Fallback to rule-based summary
    return _generate_planning_summary_rule_based(stats)


def _generate_planning_summary_rule_based(stats: dict) -> str:
    """
    Generate rule-based natural language summary of planning results.
    
    Fallback when LLM is unavailable.
    
    Args:
        stats: Dictionary with planning statistics
    
    Returns:
        str: Natural language summary
    """
    summary_parts = []
    
    summary_parts.append("Planning Algorithm Summary Report")
    summary_parts.append("─" * 50)
    
    summary_parts.append(f"\nPhase 1 - Initial Balance:")
    summary_parts.append(f"  Assignments: {stats['phase1_assignments']}")
    
    summary_parts.append(f"\nPhase 2 - Centroid Proximity:")
    summary_parts.append(f"  Assignments: {stats['phase2_assignments']}")
    summary_parts.append(f"  Pending Manual Review: {stats['pending_manual']}")
    
    summary_parts.append(f"\nTotal Statistics:")
    summary_parts.append(f"  Total OTs assigned: {stats['phase1_assignments'] + stats['phase2_assignments']}")
    summary_parts.append(f"  Total unassigned: {stats['total_unassigned']}")
    summary_parts.append(f"  Unassigned remaining: {stats['total_unassigned'] - stats['phase1_assignments'] - stats['phase2_assignments']}")
    
    # Add status message
    if stats["pending_manual"] > 0:
        summary_parts.append(f"\n⚠ {stats['pending_manual']} OTs require manual assignment (no crew within {os.getenv('MAX_DISTANCE_KM', '10')}km)")
    
    if stats["phase1_assignments"] + stats["phase2_assignments"] == stats["total_unassigned"]:
        summary_parts.append("\n✓ All unassigned OTs have been successfully distributed!")
    elif stats["phase1_assignments"] + stats["phase2_assignments"] > 0:
        summary_parts.append(f"\n✓ {stats['phase1_assignments'] + stats['phase2_assignments']} OTs assigned to crews")
    else:
        summary_parts.append("\n✓ No unassigned OTs to process")
    
    return "\n".join(summary_parts)


def get_planning_status(db_session=None) -> dict:
    """
    Get current planning status and statistics.
    
    Args:
        db_session: Optional database session
    
    Returns:
        dict: Planning status including assignments and utilization
    """
    if db_session is None:
        from backend.database.db import SessionLocal
        db_session = SessionLocal()
        close_db = True
    else:
        close_db = False
    
    try:
        # Count assignments
        total_assignments = db_session.query(Assignment).count()
        
        # Count OTs by status
        preplanificada = db_session.query(OT).filter(OT.status == OTStatus.PREPLANIFICADA.value).count()
        planificada = db_session.query(OT).filter(OT.status == OTStatus.PLANIFICADA.value).count()
        
        # Get crew utilization
        cuadrillas = db_session.query(Cuadrilla).all()
        total_capacity = sum(c.capacidad_diaria for c in cuadrillas)
        total_assigned = sum(c.ots_asignadas_count for c in cuadrillas)
        utilization_percent = (total_assigned / total_capacity * 100) if total_capacity > 0 else 0
        
        return {
            "total_assignments": total_assignments,
            "preplanificada": preplanificada,
            "planificada": planificada,
            "total_capacity": total_capacity,
            "total_assigned": total_assigned,
            "utilization_percent": utilization_percent,
        }
    finally:
        if close_db:
            db_session.close()

