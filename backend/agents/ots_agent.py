"""OTS ingestion agent for fetching and validating work orders."""

from backend.graph.state import PEIState, add_agent_response
from backend.services.telcos_service import TelcosService
from backend.database.models import OT, AgentLog, OTStatus, OTProjectType
from backend.database.db import SessionLocal
from backend.utils.geo import validate_ecuador_bounds
import os
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Try to import LLM provider
try:
    from langchain_openai import ChatOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


INGESTION_SUMMARY_PROMPT = """You are a helpful assistant summarizing work order ingestion results.

Generate a natural language summary of the following OT ingestion results:
- Total OTs fetched: {total_fetched}
- Successfully inserted: {inserted}
- Duplicates skipped: {duplicates}
- Geographic errors: {geo_errors}

Provide a brief, professional summary that could be reported to a project manager. 
If there are errors, highlight them clearly."""


async def ots_ingest_node(state: PEIState) -> PEIState:
    """
    OTS ingestion node that fetches and validates work orders from TELCOS API.
    
    This node:
    1. Instantiates TelcosService (mock or real based on SYSTEM_MODE)
    2. Fetches new OTs from API
    3. Validates geographic coordinates
    4. Checks for duplicates
    5. Creates OT records in database
    6. Logs errors and warnings
    7. Updates state with ingestion summary
    8. Generates natural language summary using LLM
    
    Args:
        state: Current PEIState with INGEST action
    
    Returns:
        Updated PEIState with agent_responses containing ingestion summary
    """
    
    logger.info("OTS Ingest Agent starting")
    
    db = SessionLocal()
    ingestion_stats = {
        "total_fetched": 0,
        "inserted": 0,
        "duplicates": 0,
        "geo_errors": 0,
        "errors": [],
    }
    
    try:
        # Initialize TelcosService based on SYSTEM_MODE
        system_mode = os.getenv("SYSTEM_MODE", "MOCK")
        telcos_url = os.getenv("TELCOS_API_URL", "")
        telcos_key = os.getenv("TELCOS_API_KEY", "")
        mock_mode = (system_mode == "MOCK")
        
        logger.info(f"Using TelcosService in {'MOCK' if mock_mode else 'REAL'} mode")
        
        telcos_service = TelcosService(
            base_url=telcos_url,
            api_key=telcos_key,
            mock_mode=mock_mode,
        )
        
        # Fetch OTs from API
        logger.info("Fetching OTs from TELCOS API...")
        ots_data = await telcos_service.fetch_ots(limit=50)
        ingestion_stats["total_fetched"] = len(ots_data)
        logger.info(f"Fetched {len(ots_data)} OTs")
        
        # Process each OT
        for ot_data in ots_data:
            try:
                external_id = ot_data.get("external_id")
                lat = ot_data.get("lat")
                long = ot_data.get("long")
                project_type = ot_data.get("project_type", "PRIVADO")
                
                # Check for duplicates
                existing_ot = db.query(OT).filter(OT.external_id == external_id).first()
                if existing_ot:
                    logger.debug(f"OT {external_id} already exists, skipping")
                    ingestion_stats["duplicates"] += 1
                    continue
                
                # Validate coordinates
                error_geo = False
                if lat is None or long is None:
                    error_geo = True
                    ingestion_stats["geo_errors"] += 1
                    logger.warning(f"OT {external_id} missing coordinates")
                elif not validate_ecuador_bounds(lat, long):
                    error_geo = True
                    ingestion_stats["geo_errors"] += 1
                    logger.warning(f"OT {external_id} coordinates outside Ecuador bounds: ({lat}, {long})")
                
                # Create OT record
                new_ot = OT(
                    external_id=external_id,
                    status=OTStatus.PREPLANIFICADA.value,
                    project_type=project_type,
                    lat=lat,
                    long=long,
                    cliente_id=ot_data.get("cliente_id", ""),
                    login=ot_data.get("login", ""),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    error_geo=error_geo,
                )
                
                db.add(new_ot)
                ingestion_stats["inserted"] += 1
                
                # Log geographic errors
                if error_geo:
                    agent_log = AgentLog(
                        ot_id=external_id,
                        agente_name="OTS Ingest Agent",
                        accion="Validate Coordinates",
                        resultado="Geographic error: coordinates outside Ecuador bounds or missing",
                        raw_llm_response=f"Lat: {lat}, Long: {long}",
                        timestamp=datetime.utcnow(),
                    )
                    db.add(agent_log)
                    logger.warning(f"Logged geographic error for OT {external_id}")
            
            except Exception as e:
                logger.error(f"Error processing OT {ot_data.get('external_id')}: {str(e)}")
                ingestion_stats["errors"].append(str(e))
                continue
        
        # Commit all OT insertions
        db.commit()
        logger.info(f"Ingestion complete: {ingestion_stats['inserted']} inserted, {ingestion_stats['duplicates']} duplicates, {ingestion_stats['geo_errors']} geo errors")
        
        # Generate natural language summary using LLM
        summary_text = await _generate_ingestion_summary(ingestion_stats)
        
        # Update state with agent response
        state = add_agent_response(
            state,
            agent_name="OTS Ingest Agent",
            response={
                "total_fetched": ingestion_stats["total_fetched"],
                "inserted": ingestion_stats["inserted"],
                "duplicates": ingestion_stats["duplicates"],
                "geo_errors": ingestion_stats["geo_errors"],
                "summary": summary_text,
            },
        )
        
        # Log overall ingestion action
        agent_log = AgentLog(
            agente_name="OTS Ingest Agent",
            accion="Ingest OTs from TELCOS",
            resultado=f"Processed {ingestion_stats['total_fetched']} OTs: {ingestion_stats['inserted']} inserted, {ingestion_stats['duplicates']} duplicates, {ingestion_stats['geo_errors']} geo errors",
            raw_llm_response=summary_text,
            timestamp=datetime.utcnow(),
        )
        db.add(agent_log)
        db.commit()
        
        logger.info("OTS Ingest Agent completed successfully")
        return state
    
    except Exception as e:
        logger.error(f"OTS Ingest Agent error: {str(e)}")
        state["error"] = f"OTS ingestion failed: {str(e)}"
        
        # Log error
        agent_log = AgentLog(
            agente_name="OTS Ingest Agent",
            accion="Ingest OTs from TELCOS",
            resultado=f"ERROR: {str(e)}",
            timestamp=datetime.utcnow(),
        )
        db.add(agent_log)
        db.commit()
        
        return state
    
    finally:
        db.close()


async def _generate_ingestion_summary(stats: dict) -> str:
    """
    Generate natural language summary of ingestion results using LLM.
    
    Falls back to rule-based summary if LLM is unavailable.
    
    Args:
        stats: Dictionary with ingestion statistics
    
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
                
                prompt = INGESTION_SUMMARY_PROMPT.format(
                    total_fetched=stats["total_fetched"],
                    inserted=stats["inserted"],
                    duplicates=stats["duplicates"],
                    geo_errors=stats["geo_errors"],
                )
                
                response = llm.invoke(prompt)
                logger.info("Generated LLM-based ingestion summary")
                return response.content
    
    except Exception as e:
        logger.warning(f"Failed to generate LLM summary: {str(e)}")
    
    # Fallback to rule-based summary
    return _generate_ingestion_summary_rule_based(stats)


def _generate_ingestion_summary_rule_based(stats: dict) -> str:
    """
    Generate rule-based natural language summary of ingestion results.
    
    Fallback when LLM is unavailable.
    
    Args:
        stats: Dictionary with ingestion statistics
    
    Returns:
        str: Natural language summary
    """
    summary_parts = []
    
    summary_parts.append(f"Ingestion Summary Report")
    summary_parts.append(f"─" * 40)
    summary_parts.append(f"Total OTs fetched: {stats['total_fetched']}")
    summary_parts.append(f"Successfully inserted: {stats['inserted']}")
    summary_parts.append(f"Duplicates skipped: {stats['duplicates']}")
    summary_parts.append(f"Geographic errors: {stats['geo_errors']}")
    
    # Add status message
    if stats["inserted"] > 0:
        summary_parts.append(f"\n✓ Successfully added {stats['inserted']} new work orders to the system.")
    
    if stats["duplicates"] > 0:
        summary_parts.append(f"\n⊘ Skipped {stats['duplicates']} duplicate work orders.")
    
    if stats["geo_errors"] > 0:
        summary_parts.append(f"\n⚠ {stats['geo_errors']} work orders have geographic errors and require manual review.")
    
    if not stats["inserted"] and stats["total_fetched"] > 0:
        summary_parts.append(f"\n⚠ No new work orders were added. Check for duplicates or geographic errors.")
    
    if stats["total_fetched"] == 0:
        summary_parts.append(f"\n✓ No new work orders available from TELCOS API.")
    
    return "\n".join(summary_parts)


def get_ingestion_status(db_session=None) -> dict:
    """
    Get statistics about recent OT ingestion.
    
    Args:
        db_session: Optional database session
    
    Returns:
        dict: Ingestion statistics
    """
    if db_session is None:
        from backend.database.db import SessionLocal
        db_session = SessionLocal()
        close_db = True
    else:
        close_db = False
    
    try:
        # Count OTs by status
        total_ots = db_session.query(OT).count()
        geo_error_count = db_session.query(OT).filter(OT.error_geo == True).count()
        preplanificada_count = db_session.query(OT).filter(OT.status == OTStatus.PREPLANIFICADA.value).count()
        
        return {
            "total_ots": total_ots,
            "geo_errors": geo_error_count,
            "preplanificada": preplanificada_count,
        }
    finally:
        if close_db:
            db_session.close()

