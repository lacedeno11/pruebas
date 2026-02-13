"""Governance agent for enforcing business rules and timeouts."""

from backend.graph.state import PEIState, add_agent_response
from backend.database.models import OT, AgentLog, OTStatus
from backend.database.db import SessionLocal
from backend.services.telcos_service import TelcosService
from sqlalchemy import and_
from datetime import datetime, timedelta
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


GOVERNANCE_ALERT_PROMPT = """You are a helpful assistant generating governance alerts for work order management.

Generate a professional alert message for the following situation:
- OT ID: {ot_id}
- Client: {cliente_id}
- Status: {status}
- Days in status: {days_in_status}
- Alert type: {alert_type}

Alert types:
- 48h_preplanificada: OT in PREPLANIFICADA for >48 hours
- 20d_detenida: OT in DETENIDA for 20 days (warning)
- 25d_detenida: OT in DETENIDA for 25 days (urgent)
- 29d_detenida: OT in DETENIDA for 29 days (final notice)
- 30d_cancellation: OT being auto-cancelled after 30 days in DETENIDA

Provide a clear, actionable message suitable for sending to a project manager or coordinator."""


async def governance_node(state: PEIState) -> PEIState:
    """
    Governance node that enforces business rules and timeouts.
    
    This node implements three governance checks:
    
    Check 1 - 48h PREPLANIFICADA Alert:
    - Query OTs with status=PREPLANIFICADA AND created_at < now()-48h
    - For each OT, create alert for Coordinator OPU via Communication Agent
    
    Check 2 - 30-day DETENIDA Auto-cancellation:
    - Query OTs with status=DETENIDA AND updated_at < now()-30 days
    - Auto-change status to ANULADA
    - Call TelcosService.update_ot_status()
    - Log: "Anulada por Governance Agent - Motivo: Exceso de tiempo en estado DETENIDA"
    
    Check 3 - Progressive Escalating Alerts:
    - Query OTs with status=DETENIDA AND days_in_status IN (20, 25, 29)
    - Send escalating alerts: warning (20d), urgent (25d), final notice (29d)
    
    Args:
        state: Current PEIState with GOVERNANCE action
    
    Returns:
        Updated PEIState with governance actions executed
    """
    
    logger.info("Governance Agent starting periodic checks")
    
    db = SessionLocal()
    governance_stats = {
        "check1_alerts": 0,  # 48h PREPLANIFICADA alerts
        "check2_cancellations": 0,  # 30-day DETENIDA auto-cancellations
        "check3_warnings": 0,  # Progressive escalating alerts
        "check3_urgent": 0,
        "check3_final": 0,
        "errors": [],
    }
    
    now = datetime.utcnow()
    
    try:
        # ==================== CHECK 1: 48h PREPLANIFICADA Alert ====================
        logger.info("Check 1: Querying OTs in PREPLANIFICADA for >48 hours")
        
        try:
            threshold_time = now - timedelta(hours=48)
            
            old_preplanificada = db.query(OT).filter(
                and_(
                    OT.status == OTStatus.PREPLANIFICADA.value,
                    OT.created_at < threshold_time,
                )
            ).all()
            
            logger.info(f"Found {len(old_preplanificada)} OTs in PREPLANIFICADA >48h")
            
            for ot in old_preplanificada:
                try:
                    days_in_status = (now - ot.created_at).days
                    
                    # Generate alert message
                    alert_message = await _generate_governance_alert(
                        ot_id=ot.external_id,
                        cliente_id=ot.cliente_id,
                        status=ot.status,
                        days_in_status=days_in_status,
                        alert_type="48h_preplanificada",
                    )
                    
                    # Log governance action
                    agent_log = AgentLog(
                        ot_id=ot.external_id,
                        agente_name="Gobernanza Agent",
                        accion="Check 1: 48h PREPLANIFICADA Alert",
                        resultado=f"Alert generated: OT in PREPLANIFICADA for {days_in_status} days",
                        raw_llm_response=alert_message,
                        timestamp=datetime.utcnow(),
                    )
                    db.add(agent_log)
                    governance_stats["check1_alerts"] += 1
                    
                    logger.info(f"Check 1: Generated alert for OT {ot.external_id}")
                
                except Exception as e:
                    logger.error(f"Check 1 error for OT {ot.external_id}: {str(e)}")
                    governance_stats["errors"].append(f"Check 1 {ot.external_id}: {str(e)}")
            
            db.commit()
            logger.info(f"Check 1 complete: {governance_stats['check1_alerts']} alerts generated")
        
        except Exception as e:
            logger.error(f"Check 1 error: {str(e)}")
            governance_stats["errors"].append(f"Check 1: {str(e)}")
            db.rollback()
        
        # ==================== CHECK 2: 30-day DETENIDA Auto-cancellation ====================
        logger.info("Check 2: Querying OTs in DETENIDA for >30 days")
        
        try:
            threshold_time = now - timedelta(days=30)
            
            old_detenida = db.query(OT).filter(
                and_(
                    OT.status == OTStatus.DETENIDA.value,
                    OT.updated_at < threshold_time,
                )
            ).all()
            
            logger.info(f"Found {len(old_detenida)} OTs in DETENIDA >30 days for auto-cancellation")
            
            # Initialize TelcosService for status updates
            system_mode = os.getenv("SYSTEM_MODE", "MOCK")
            telcos_url = os.getenv("TELCOS_API_URL", "")
            telcos_key = os.getenv("TELCOS_API_KEY", "")
            mock_mode = (system_mode == "MOCK")
            
            telcos_service = TelcosService(
                base_url=telcos_url,
                api_key=telcos_key,
                mock_mode=mock_mode,
            )
            
            for ot in old_detenida:
                try:
                    days_in_status = (now - ot.updated_at).days
                    
                    # Update OT status to ANULADA
                    ot.status = OTStatus.ANULADA.value
                    ot.updated_at = datetime.utcnow()
                    
                    # Call TelcosService to sync status
                    try:
                        await telcos_service.update_ot_status(
                            ot.external_id,
                            OTStatus.ANULADA.value,
                        )
                        logger.info(f"Check 2: Updated OT {ot.external_id} in TELCOS API")
                    except Exception as e:
                        logger.warning(f"Check 2: Failed to update OT {ot.external_id} in TELCOS API: {str(e)}")
                    
                    # Log governance action with required message format
                    agent_log = AgentLog(
                        ot_id=ot.external_id,
                        agente_name="Gobernanza Agent",
                        accion="Check 2: 30-day DETENIDA Auto-cancellation",
                        resultado="Anulada por Governance Agent - Motivo: Exceso de tiempo en estado DETENIDA",
                        raw_llm_response=f"OT was in DETENIDA for {days_in_status} days",
                        timestamp=datetime.utcnow(),
                    )
                    db.add(agent_log)
                    governance_stats["check2_cancellations"] += 1
                    
                    logger.info(f"Check 2: Auto-cancelled OT {ot.external_id} (in DETENIDA for {days_in_status} days)")
                
                except Exception as e:
                    logger.error(f"Check 2 error for OT {ot.external_id}: {str(e)}")
                    governance_stats["errors"].append(f"Check 2 {ot.external_id}: {str(e)}")
                    db.rollback()
                    continue
            
            db.commit()
            logger.info(f"Check 2 complete: {governance_stats['check2_cancellations']} OTs auto-cancelled")
        
        except Exception as e:
            logger.error(f"Check 2 error: {str(e)}")
            governance_stats["errors"].append(f"Check 2: {str(e)}")
            db.rollback()
        
        # ==================== CHECK 3: Progressive Escalating Alerts ====================
        logger.info("Check 3: Querying OTs in DETENIDA for progressive alerts (20d, 25d, 29d)")
        
        try:
            detenida_ots = db.query(OT).filter(OT.status == OTStatus.DETENIDA.value).all()
            
            for ot in detenida_ots:
                try:
                    days_in_status = (now - ot.updated_at).days
                    
                    # Check for 20-day warning
                    if days_in_status == 20:
                        alert_message = await _generate_governance_alert(
                            ot_id=ot.external_id,
                            cliente_id=ot.cliente_id,
                            status=ot.status,
                            days_in_status=days_in_status,
                            alert_type="20d_detenida",
                        )
                        
                        agent_log = AgentLog(
                            ot_id=ot.external_id,
                            agente_name="Gobernanza Agent",
                            accion="Check 3: Progressive Alert - 20 days",
                            resultado=f"Warning alert: OT in DETENIDA for {days_in_status} days",
                            raw_llm_response=alert_message,
                            timestamp=datetime.utcnow(),
                        )
                        db.add(agent_log)
                        governance_stats["check3_warnings"] += 1
                        logger.info(f"Check 3: Generated 20-day warning for OT {ot.external_id}")
                    
                    # Check for 25-day urgent alert
                    elif days_in_status == 25:
                        alert_message = await _generate_governance_alert(
                            ot_id=ot.external_id,
                            cliente_id=ot.cliente_id,
                            status=ot.status,
                            days_in_status=days_in_status,
                            alert_type="25d_detenida",
                        )
                        
                        agent_log = AgentLog(
                            ot_id=ot.external_id,
                            agente_name="Gobernanza Agent",
                            accion="Check 3: Progressive Alert - 25 days",
                            resultado=f"Urgent alert: OT in DETENIDA for {days_in_status} days",
                            raw_llm_response=alert_message,
                            timestamp=datetime.utcnow(),
                        )
                        db.add(agent_log)
                        governance_stats["check3_urgent"] += 1
                        logger.info(f"Check 3: Generated 25-day urgent alert for OT {ot.external_id}")
                    
                    # Check for 29-day final notice
                    elif days_in_status == 29:
                        alert_message = await _generate_governance_alert(
                            ot_id=ot.external_id,
                            cliente_id=ot.cliente_id,
                            status=ot.status,
                            days_in_status=days_in_status,
                            alert_type="29d_detenida",
                        )
                        
                        agent_log = AgentLog(
                            ot_id=ot.external_id,
                            agente_name="Gobernanza Agent",
                            accion="Check 3: Progressive Alert - 29 days",
                            resultado=f"Final notice: OT in DETENIDA for {days_in_status} days, will be cancelled tomorrow",
                            raw_llm_response=alert_message,
                            timestamp=datetime.utcnow(),
                        )
                        db.add(agent_log)
                        governance_stats["check3_final"] += 1
                        logger.info(f"Check 3: Generated 29-day final notice for OT {ot.external_id}")
                
                except Exception as e:
                    logger.error(f"Check 3 error for OT {ot.external_id}: {str(e)}")
                    governance_stats["errors"].append(f"Check 3 {ot.external_id}: {str(e)}")
            
            db.commit()
            total_check3 = governance_stats["check3_warnings"] + governance_stats["check3_urgent"] + governance_stats["check3_final"]
            logger.info(f"Check 3 complete: {total_check3} progressive alerts generated")
        
        except Exception as e:
            logger.error(f"Check 3 error: {str(e)}")
            governance_stats["errors"].append(f"Check 3: {str(e)}")
            db.rollback()
        
        # ==================== Log summary ====================
        try:
            total_actions = (
                governance_stats["check1_alerts"] +
                governance_stats["check2_cancellations"] +
                governance_stats["check3_warnings"] +
                governance_stats["check3_urgent"] +
                governance_stats["check3_final"]
            )
            
            summary_log = AgentLog(
                agente_name="Gobernanza Agent",
                accion="Execute Governance Checks",
                resultado=f"Check 1 alerts: {governance_stats['check1_alerts']}, Check 2 cancellations: {governance_stats['check2_cancellations']}, Check 3 progressive: {governance_stats['check3_warnings'] + governance_stats['check3_urgent'] + governance_stats['check3_final']}",
                raw_llm_response=f"Total actions: {total_actions}",
                timestamp=datetime.utcnow(),
            )
            db.add(summary_log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log governance summary: {str(e)}")
        
        # Update state with agent response
        state = add_agent_response(
            state,
            agent_name="Gobernanza Agent",
            response={
                "check1_alerts": governance_stats["check1_alerts"],
                "check2_cancellations": governance_stats["check2_cancellations"],
                "check3_warnings": governance_stats["check3_warnings"],
                "check3_urgent": governance_stats["check3_urgent"],
                "check3_final": governance_stats["check3_final"],
                "total_actions": (
                    governance_stats["check1_alerts"] +
                    governance_stats["check2_cancellations"] +
                    governance_stats["check3_warnings"] +
                    governance_stats["check3_urgent"] +
                    governance_stats["check3_final"]
                ),
            },
        )
        
        logger.info("Governance Agent completed successfully")
        return state
    
    except Exception as e:
        logger.error(f"Governance Agent error: {str(e)}")
        state["error"] = f"Governance check failed: {str(e)}"
        
        # Log error
        agent_log = AgentLog(
            agente_name="Gobernanza Agent",
            accion="Execute Governance Checks",
            resultado=f"ERROR: {str(e)}",
            timestamp=datetime.utcnow(),
        )
        db.add(agent_log)
        db.commit()
        
        return state
    
    finally:
        db.close()


async def _generate_governance_alert(
    ot_id: str,
    cliente_id: str,
    status: str,
    days_in_status: int,
    alert_type: str,
) -> str:
    """
    Generate governance alert message using LLM.
    
    Falls back to rule-based alert if LLM is unavailable.
    
    Args:
        ot_id: External ID of the OT
        cliente_id: Client ID
        status: Current status
        days_in_status: Number of days in current status
        alert_type: Type of alert (48h_preplanificada, 20d_detenida, etc.)
    
    Returns:
        str: Alert message
    """
    try:
        # Try to use LLM for alert generation
        if HAS_OPENAI:
            llm_model = os.getenv("LLM_MODEL", "gpt-4")
            openai_key = os.getenv("OPENAI_API_KEY")
            
            if openai_key and "gpt" in llm_model.lower():
                llm = ChatOpenAI(model_name=llm_model, api_key=openai_key, temperature=0.7)
                
                prompt = GOVERNANCE_ALERT_PROMPT.format(
                    ot_id=ot_id,
                    cliente_id=cliente_id,
                    status=status,
                    days_in_status=days_in_status,
                    alert_type=alert_type,
                )
                
                response = llm.invoke(prompt)
                logger.info(f"Generated LLM-based alert for OT {ot_id}")
                return response.content
    
    except Exception as e:
        logger.warning(f"Failed to generate LLM alert: {str(e)}")
    
    # Fallback to rule-based alert
    return _generate_governance_alert_rule_based(
        ot_id, cliente_id, status, days_in_status, alert_type
    )


def _generate_governance_alert_rule_based(
    ot_id: str,
    cliente_id: str,
    status: str,
    days_in_status: int,
    alert_type: str,
) -> str:
    """
    Generate rule-based governance alert message.
    
    Fallback when LLM is unavailable.
    
    Args:
        ot_id: External ID of the OT
        cliente_id: Client ID
        status: Current status
        days_in_status: Number of days in current status
        alert_type: Type of alert
    
    Returns:
        str: Alert message
    """
    if alert_type == "48h_preplanificada":
        return f"⚠️ ALERT: OT {ot_id} (Client: {cliente_id}) has been in PREPLANIFICADA status for {days_in_status} hours. Please review and plan assignment."
    
    elif alert_type == "20d_detenida":
        return f"⚠️ WARNING: OT {ot_id} (Client: {cliente_id}) has been DETENIDA (paused) for {days_in_status} days. Please resolve within 10 days to prevent auto-cancellation."
    
    elif alert_type == "25d_detenida":
        return f"🚨 URGENT: OT {ot_id} (Client: {cliente_id}) has been DETENIDA for {days_in_status} days. Action required immediately to prevent auto-cancellation in 5 days."
    
    elif alert_type == "29d_detenida":
        return f"🚨 FINAL NOTICE: OT {ot_id} (Client: {cliente_id}) will be AUTO-CANCELLED tomorrow if still DETENIDA. {days_in_status} days without progress. Take action NOW."
    
    elif alert_type == "30d_cancellation":
        return f"✓ CANCELLED: OT {ot_id} (Client: {cliente_id}) has been automatically cancelled after 30 days in DETENIDA status."
    
    else:
        return f"Governance alert for OT {ot_id}: {alert_type}"


def get_governance_status(db_session=None) -> dict:
    """
    Get current governance status.
    
    Args:
        db_session: Optional database session
    
    Returns:
        dict: Governance status including at-risk OTs
    """
    if db_session is None:
        from backend.database.db import SessionLocal
        db_session = SessionLocal()
        close_db = True
    else:
        close_db = False
    
    try:
        now = datetime.utcnow()
        
        # Count OTs at risk (48h+ in PREPLANIFICADA)
        threshold_48h = now - timedelta(hours=48)
        at_risk_preplanificada = db_session.query(OT).filter(
            and_(
                OT.status == OTStatus.PREPLANIFICADA.value,
                OT.created_at < threshold_48h,
            )
        ).count()
        
        # Count OTs in danger (in DETENIDA with 20+ days)
        threshold_20d = now - timedelta(days=20)
        at_risk_detenida = db_session.query(OT).filter(
            and_(
                OT.status == OTStatus.DETENIDA.value,
                OT.updated_at < threshold_20d,
            )
        ).count()
        
        # Count OTs critical (30+ days, will be auto-cancelled)
        threshold_30d = now - timedelta(days=30)
        at_risk_critical = db_session.query(OT).filter(
            and_(
                OT.status == OTStatus.DETENIDA.value,
                OT.updated_at < threshold_30d,
            )
        ).count()
        
        return {
            "at_risk_preplanificada": at_risk_preplanificada,
            "at_risk_detenida": at_risk_detenida,
            "critical_auto_cancel": at_risk_critical,
            "total_at_risk": at_risk_preplanificada + at_risk_detenida,
        }
    finally:
        if close_db:
            db_session.close()

