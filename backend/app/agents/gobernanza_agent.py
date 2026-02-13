import json
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from langchain_openai import ChatOpenAI

from app.agents.state import PEIState, add_message, add_error, add_notification
from app.config import get_settings
from app.models import OT, LogAgente
from app.services import GovernanceService, MockApiService
from app.database import SessionLocal


class GobernanzaAgent:
    """
    Gobernanza (Governance) Agent for auto-governance rules and compliance management
    
    Responsible for:
    - Checking detention alerts (days 20, 25, 29 of detention)
    - Auto-canceling OTs detained beyond 30 days
    - Checking for pre-planned timeout (>48 hours in PREPLANIFICADA status)
    - Validating PUBLICO project finalization requirements
    - Generating contextualized alert messages
    - Logging all governance decisions
    """

    def __init__(self):
        """Initialize GobernanzaAgent with OpenAI LLM and governance service"""
        self.settings = get_settings()
        
        # Initialize ChatOpenAI LLM for message generation
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.2,  # Low temperature for consistent alert messages
            api_key=self.settings.OPENAI_API_KEY,
        )
        
        # Initialize governance service for rule checking
        self.governance_service = GovernanceService()
        self.mock_service = MockApiService()

    def check_governance_rules(self, state: PEIState) -> PEIState:
        """
        Execute governance rule checks: detention alerts, auto-cancellation, pre-planned timeout
        
        Args:
            state: Current PEIState from LangGraph
        
        Returns:
            Updated PEIState with notifications and governance results
        """
        db_session = state.get("db_session")
        
        # If no session provided, create one temporarily
        if db_session is None:
            db_session = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            notifications = []
            governance_summary = {
                "detention_alerts": 0,
                "cancelled_count": 0,
                "preplanned_timeouts": 0,
            }
            
            # Phase 1: Check detention alerts (days 20, 25, 29)
            try:
                alerted_ots = self.governance_service.check_detention_alerts(db_session)
                
                for ot in alerted_ots:
                    days_detained = (datetime.utcnow() - ot.created_at).days
                    
                    # Generate alert message using LLM
                    alert_message = self._generate_detention_alert_message(ot, days_detained)
                    
                    notification = {
                        "type": "detention_alert",
                        "ot_id": ot.id,
                        "ot_external_id": ot.external_id,
                        "recipient_type": "tecnico",  # Technician receives detention alerts
                        "priority": "high",
                        "message": alert_message,
                        "days_detained": days_detained,
                    }
                    notifications.append(notification)
                    state = add_notification(state, notification)
                    governance_summary["detention_alerts"] += 1
                    
                    # Log alert
                    self._log_governance_action(
                        db_session,
                        ot_id=ot.id,
                        action="detention_alert",
                        days_detained=days_detained,
                        success=True,
                    )
                    
            except Exception as e:
                error_msg = f"Error checking detention alerts: {str(e)}"
                state = add_error(state, error_msg)
                self._log_governance_action(
                    db_session,
                    ot_id=None,
                    action="detention_alert",
                    success=False,
                    error_message=error_msg,
                )
            
            # Phase 2: Auto-cancel inactive OTs (>30 days in DETENIDA)
            try:
                cancelled_count = self.governance_service.auto_cancel_inactive(db_session)
                governance_summary["cancelled_count"] = cancelled_count
                
                if cancelled_count > 0:
                    cancel_message = f"Automatically cancelled {cancelled_count} OTs detained for > 30 days"
                    state = add_message(state, "agent", cancel_message)
                    
                    # Log auto-cancellation
                    self._log_governance_action(
                        db_session,
                        ot_id=None,
                        action="auto_cancel",
                        cancelled_count=cancelled_count,
                        success=True,
                    )
                    
            except Exception as e:
                error_msg = f"Error auto-canceling inactive OTs: {str(e)}"
                state = add_error(state, error_msg)
                self._log_governance_action(
                    db_session,
                    ot_id=None,
                    action="auto_cancel",
                    success=False,
                    error_message=error_msg,
                )
            
            # Phase 3: Check for pre-planned timeout (>48 hours in PREPLANIFICADA)
            try:
                timeout_ots = self.governance_service.check_preplanned_timeout(db_session)
                
                for ot in timeout_ots:
                    hours_waiting = (datetime.utcnow() - ot.created_at).total_seconds() / 3600
                    
                    # Generate timeout alert message using LLM
                    alert_message = self._generate_preplanned_timeout_message(ot, hours_waiting)
                    
                    notification = {
                        "type": "preplanned_timeout",
                        "ot_id": ot.id,
                        "ot_external_id": ot.external_id,
                        "recipient_type": "pm",  # Project manager receives planning alerts
                        "priority": "critical",
                        "message": alert_message,
                        "hours_waiting": round(hours_waiting, 1),
                    }
                    notifications.append(notification)
                    state = add_notification(state, notification)
                    governance_summary["preplanned_timeouts"] += 1
                    
                    # Log timeout alert
                    self._log_governance_action(
                        db_session,
                        ot_id=ot.id,
                        action="preplanned_timeout",
                        hours_waiting=hours_waiting,
                        success=True,
                    )
                    
            except Exception as e:
                error_msg = f"Error checking pre-planned timeout: {str(e)}"
                state = add_error(state, error_msg)
                self._log_governance_action(
                    db_session,
                    ot_id=None,
                    action="preplanned_timeout",
                    success=False,
                    error_message=error_msg,
                )
            
            # Update state with notifications and summary
            state["notifications"] = notifications
            
            # Add governance summary message
            summary_msg = (
                f"Gobernanza Agent: {governance_summary['detention_alerts']} detention alerts, "
                f"{governance_summary['cancelled_count']} auto-cancellations, "
                f"{governance_summary['preplanned_timeouts']} pre-planned timeouts."
            )
            state = add_message(state, "agent", summary_msg)
            
            return state
            
        except Exception as e:
            # Log critical error
            error_msg = f"Critical error in Gobernanza Agent: {str(e)}"
            state = add_error(state, error_msg)
            state = add_message(state, "agent", error_msg)
            state["notifications"] = []
            
            self._log_governance_action(
                db_session,
                ot_id=None,
                action="check_governance_rules",
                success=False,
                error_message=error_msg,
            )
            
            return state
            
        finally:
            if should_close:
                db_session.close()

    def validate_finalization(self, ot: OT, session: Session) -> Dict[str, Any]:
        """
        Validate that OT can be finalized based on project type requirements
        For PUBLICO projects, requires exactly 29 documents in TelcoDrive
        
        Args:
            ot: OT object to validate
            session: SQLAlchemy session for database operations
        
        Returns:
            Dictionary with {valid: bool, message: str, document_count: int}
        """
        try:
            # PUBLICO projects require 29 documents
            if ot.project_type == "PUBLICO":
                # Get document count from TelcoDrive (via mock service in development)
                result = asyncio.run(
                    self.mock_service.get_telcodrive_documents(str(ot.id))
                )
                
                document_count = result.get("document_count", 0)
                
                if document_count >= 29:
                    return {
                        "valid": True,
                        "message": f"PUBLICO project has all {document_count} required documents",
                        "document_count": document_count,
                    }
                else:
                    return {
                        "valid": False,
                        "message": f"PUBLICO project requires 29 documents, but has {document_count}",
                        "document_count": document_count,
                    }
            
            # PRIVADO and TERCERIZADO projects have no document requirements
            else:
                return {
                    "valid": True,
                    "message": f"{ot.project_type} project can be finalized",
                    "document_count": 0,
                }
                
        except Exception as e:
            return {
                "valid": False,
                "message": f"Error validating finalization: {str(e)}",
                "document_count": 0,
            }

    def _generate_detention_alert_message(self, ot: OT, days_detained: int) -> str:
        """
        Generate a contextualized detention alert message using LLM
        
        Args:
            ot: OT in detention
            days_detained: Number of days in detention
        
        Returns:
            Natural language alert message
        """
        try:
            project_name_hints = {
                "PUBLICO": "public infrastructure",
                "PRIVADO": "private project",
                "TERCERIZADO": "third-party project",
            }
            project_type_hint = project_name_hints.get(ot.project_type, "project")
            
            prompt = f"""Generate a brief, professional alert message for a detained work order.
OT Details:
- External ID: {ot.external_id}
- Type: {project_type_hint}
- Days in detention: {days_detained}
- Detention reason: {ot.detention_reason or 'Not specified'}

Keep the message under 50 words. Be professional and action-oriented.
Format: A single sentence or brief statement."""
            
            response = self.llm.invoke(prompt)
            return response.content.strip()
            
        except Exception as e:
            # Fallback message if LLM fails
            return f"OT {ot.external_id} has been detained for {days_detained} days. Please review and take action."

    def _generate_preplanned_timeout_message(self, ot: OT, hours_waiting: float) -> str:
        """
        Generate a contextualized pre-planned timeout alert message using LLM
        
        Args:
            ot: OT stuck in PREPLANIFICADA
            hours_waiting: Number of hours waiting for planning
        
        Returns:
            Natural language alert message
        """
        try:
            prompt = f"""Generate a brief, urgent alert message for a work order stuck in pre-planning status.
OT Details:
- External ID: {ot.external_id}
- Project Type: {ot.project_type}
- Hours waiting for planning: {hours_waiting:.1f}

Keep the message under 60 words. Be professional but convey urgency.
Format: A single sentence or brief statement."""
            
            response = self.llm.invoke(prompt)
            return response.content.strip()
            
        except Exception as e:
            # Fallback message if LLM fails
            return f"URGENT: OT {ot.external_id} has been waiting {hours_waiting:.1f} hours for planning. Immediate action required."

    def _log_governance_action(
        self,
        db_session: Optional[Session],
        ot_id: Optional[int] = None,
        action: str = "",
        days_detained: Optional[int] = None,
        hours_waiting: Optional[float] = None,
        cancelled_count: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log governance action to LogAgente table for audit trail
        
        Args:
            db_session: SQLAlchemy session (optional)
            ot_id: OT database ID (optional)
            action: Governance action name (detention_alert, auto_cancel, preplanned_timeout, etc.)
            days_detained: Number of days detained (for detention alerts)
            hours_waiting: Number of hours waiting (for timeout alerts)
            cancelled_count: Number of cancelled OTs (for auto_cancel)
            success: Whether action was successful
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
                agente_name="GobernanzaAgent",
                accion=action,
                resultado="OK" if success else "ERROR",
                raw_llm_response=json.dumps({
                    "action": action,
                    "success": success,
                    "days_detained": days_detained,
                    "hours_waiting": hours_waiting,
                    "cancelled_count": cancelled_count,
                    "error_message": error_message,
                }),
            )
            db_session.add(log_entry)
            db_session.commit()
        except Exception as e:
            # Log error but don't raise - governance actions should proceed
            print(f"Error logging governance action: {str(e)}")
            db_session.rollback()
        finally:
            if should_close:
                db_session.close()

