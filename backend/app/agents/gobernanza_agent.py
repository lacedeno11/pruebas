import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from backend.app.models.ot import OT, OTStatus
from backend.app.models.log_agente import LogAgente
from backend.app.services.telcodrive_service import TelcoDriveService
from backend.app.core.database import get_db

logger = logging.getLogger(__name__)


class GobernanzaAgent:
    """
    GobernanzaAgent handles governance, compliance checks, and alerts.
    
    Responsibilities:
    - Monitor OTs in DETENIDA status and trigger alerts at key milestones (days 20, 25, 29)
    - Auto-cancel OTs detained for more than 30 days
    - Monitor OTs in PREPLANIFICADA status for more than 48 hours
    - Validate document requirements for PUBLICO projects (require exactly 29 documents)
    - Log all governance actions and alerts
    """

    def __init__(self):
        """Initialize GobernanzaAgent with TelcoDriveService."""
        self.telcodrive_service = TelcoDriveService()
        self.agent_name = "GobernanzaAgent"
        self.detention_alert_days = [20, 25, 29]  # Days to trigger alerts
        self.detention_auto_cancel_days = 30  # Auto-cancel after this many days

    async def check_detained_ots(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check OTs in DETENIDA status and trigger alerts at key milestones.
        
        Process:
        1. Query all OTs with status DETENIDA
        2. Calculate days_detained since created_at or status change
        3. Trigger alerts on days 20, 25, 29
        4. Log alert actions
        5. Return updated state with results
        
        Args:
            state: AgentState dictionary
        
        Returns:
            Updated state with alert results
        """
        alert_results = {
            "detained_ots_checked": 0,
            "alerts_triggered": 0,
            "alert_details": [],
            "messages": []
        }

        db = next(get_db())
        try:
            logger.info("Starting detained OT check")

            # Query all OTs in DETENIDA status
            detained_ots = db.query(OT).filter(
                OT.status == OTStatus.DETENIDA
            ).all()

            alert_results["detained_ots_checked"] = len(detained_ots)
            logger.info(f"Found {len(detained_ots)} detained OTs")

            if not detained_ots:
                message = "No detained OTs found"
                logger.info(message)
                alert_results["messages"].append(message)
                
                self._log_action(
                    db,
                    accion="check_detained_ots",
                    resultado="NO_DATA",
                    message=message
                )
                
                return {
                    **state,
                    "action": "CHECK_DETAINED_COMPLETE",
                    "result": alert_results
                }

            # Check each detained OT
            for ot in detained_ots:
                days_detained = self._calculate_days_detained(ot)
                
                # Check if alert should be triggered
                if days_detained in self.detention_alert_days:
                    alert_message = (
                        f"ALERT: OT {ot.external_id} detained for {days_detained} days. "
                        f"Cliente: {ot.cliente_id}, Login: {ot.login_id}"
                    )
                    
                    alert_results["alerts_triggered"] += 1
                    alert_results["alert_details"].append({
                        "ot_id": ot.external_id,
                        "days_detained": days_detained,
                        "alert_level": "HIGH" if days_detained >= 29 else "MEDIUM"
                    })
                    
                    logger.warning(alert_message)
                    
                    # Log alert
                    self._log_action(
                        db,
                        accion="detention_alert",
                        resultado="ALERT_TRIGGERED",
                        message=alert_message
                    )

            if alert_results["alerts_triggered"] > 0:
                alert_results["messages"].append(
                    f"{alert_results['alerts_triggered']} detention alerts triggered"
                )
            else:
                alert_results["messages"].append("No alerts triggered")

            db.commit()
            logger.info(
                f"Detention check completed: {alert_results['alerts_triggered']} "
                f"alerts triggered for {alert_results['detained_ots_checked']} detained OTs"
            )

            return {
                **state,
                "action": "CHECK_DETAINED_COMPLETE",
                "result": alert_results
            }

        except Exception as e:
            db.rollback()
            error_msg = f"Error checking detained OTs: {str(e)}"
            logger.error(error_msg)
            alert_results["messages"].append(error_msg)

            self._log_action(
                db,
                accion="check_detained_ots",
                resultado="ERROR",
                message=error_msg
            )

            return {
                **state,
                "action": "CHECK_DETAINED_ERROR",
                "result": alert_results,
                "errors": [error_msg]
            }
        finally:
            db.close()

    async def auto_cancel_ots(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically cancel OTs detained for more than 30 days.
        
        Process:
        1. Query OTs in DETENIDA status
        2. Calculate days_detained
        3. Change status to ANULADA for OTs with days_detained > 30
        4. Log cancellations
        5. Return updated state
        
        Args:
            state: AgentState dictionary
        
        Returns:
            Updated state with cancellation results
        """
        cancellation_results = {
            "detained_ots_checked": 0,
            "ots_cancelled": 0,
            "cancelled_details": [],
            "messages": []
        }

        db = next(get_db())
        try:
            logger.info("Starting auto-cancellation of detained OTs")

            # Query all OTs in DETENIDA status
            detained_ots = db.query(OT).filter(
                OT.status == OTStatus.DETENIDA
            ).all()

            cancellation_results["detained_ots_checked"] = len(detained_ots)
            logger.info(f"Found {len(detained_ots)} detained OTs for cancellation review")

            if not detained_ots:
                message = "No detained OTs to review for cancellation"
                logger.info(message)
                cancellation_results["messages"].append(message)
                
                self._log_action(
                    db,
                    accion="auto_cancel_ots",
                    resultado="NO_DATA",
                    message=message
                )
                
                return {
                    **state,
                    "action": "AUTO_CANCEL_COMPLETE",
                    "result": cancellation_results
                }

            # Check each detained OT and cancel if > 30 days
            for ot in detained_ots:
                days_detained = self._calculate_days_detained(ot)
                
                if days_detained > self.detention_auto_cancel_days:
                    # Update status to ANULADA
                    ot.status = OTStatus.ANULADA
                    ot.updated_at = datetime.utcnow()
                    
                    db.add(ot)
                    
                    cancellation_message = (
                        f"AUTO-CANCELLED: OT {ot.external_id} cancelled after "
                        f"{days_detained} days detention. Cliente: {ot.cliente_id}"
                    )
                    
                    cancellation_results["ots_cancelled"] += 1
                    cancellation_results["cancelled_details"].append({
                        "ot_id": ot.external_id,
                        "days_detained": days_detained,
                        "cancelled_at": datetime.utcnow().isoformat()
                    })
                    
                    logger.warning(cancellation_message)
                    
                    # Log cancellation
                    self._log_action(
                        db,
                        accion="auto_cancel_ot",
                        resultado="CANCELLED",
                        message=cancellation_message
                    )

            if cancellation_results["ots_cancelled"] > 0:
                cancellation_results["messages"].append(
                    f"{cancellation_results['ots_cancelled']} OTs auto-cancelled"
                )
            else:
                cancellation_results["messages"].append(
                    "No OTs eligible for auto-cancellation"
                )

            db.commit()
            logger.info(
                f"Auto-cancellation completed: {cancellation_results['ots_cancelled']} "
                f"OTs cancelled out of {cancellation_results['detained_ots_checked']} detained"
            )

            return {
                **state,
                "action": "AUTO_CANCEL_COMPLETE",
                "result": cancellation_results
            }

        except Exception as e:
            db.rollback()
            error_msg = f"Error during auto-cancellation: {str(e)}"
            logger.error(error_msg)
            cancellation_results["messages"].append(error_msg)

            self._log_action(
                db,
                accion="auto_cancel_ots",
                resultado="ERROR",
                message=error_msg
            )

            return {
                **state,
                "action": "AUTO_CANCEL_ERROR",
                "result": cancellation_results,
                "errors": [error_msg]
            }
        finally:
            db.close()

    async def check_preplanificada_alerts(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check for OTs in PREPLANIFICADA status for more than 48 hours.
        
        Process:
        1. Query OTs in PREPLANIFICADA status
        2. Calculate hours since created_at
        3. Trigger alerts for OTs > 48 hours
        4. Log alerts
        5. Return updated state
        
        Args:
            state: AgentState dictionary
        
        Returns:
            Updated state with alert results
        """
        alert_results = {
            "preplanificada_ots_checked": 0,
            "alerts_triggered": 0,
            "alert_details": [],
            "messages": []
        }

        db = next(get_db())
        try:
            logger.info("Starting PREPLANIFICADA status alerts check")

            # Query all OTs in PREPLANIFICADA status
            preplanificada_ots = db.query(OT).filter(
                OT.status == OTStatus.PREPLANIFICADA
            ).all()

            alert_results["preplanificada_ots_checked"] = len(preplanificada_ots)
            logger.info(f"Found {len(preplanificada_ots)} OTs in PREPLANIFICADA status")

            if not preplanificada_ots:
                message = "No OTs in PREPLANIFICADA status"
                logger.info(message)
                alert_results["messages"].append(message)
                
                self._log_action(
                    db,
                    accion="check_preplanificada_alerts",
                    resultado="NO_DATA",
                    message=message
                )
                
                return {
                    **state,
                    "action": "PREPLANIFICADA_CHECK_COMPLETE",
                    "result": alert_results
                }

            # Check each PREPLANIFICADA OT
            threshold = timedelta(hours=48)
            now = datetime.utcnow()

            for ot in preplanificada_ots:
                time_in_status = now - ot.created_at
                
                if time_in_status > threshold:
                    hours_in_status = int(time_in_status.total_seconds() / 3600)
                    alert_message = (
                        f"ALERT: OT {ot.external_id} in PREPLANIFICADA for {hours_in_status} hours. "
                        f"Cliente: {ot.cliente_id}, Login: {ot.login_id}"
                    )
                    
                    alert_results["alerts_triggered"] += 1
                    alert_results["alert_details"].append({
                        "ot_id": ot.external_id,
                        "hours_in_status": hours_in_status,
                        "created_at": ot.created_at.isoformat()
                    })
                    
                    logger.warning(alert_message)
                    
                    # Log alert
                    self._log_action(
                        db,
                        accion="preplanificada_alert",
                        resultado="ALERT_TRIGGERED",
                        message=alert_message
                    )

            if alert_results["alerts_triggered"] > 0:
                alert_results["messages"].append(
                    f"{alert_results['alerts_triggered']} PREPLANIFICADA alerts triggered"
                )
            else:
                alert_results["messages"].append("No PREPLANIFICADA alerts")

            db.commit()
            logger.info(
                f"PREPLANIFICADA check completed: {alert_results['alerts_triggered']} "
                f"alerts triggered for {alert_results['preplanificada_ots_checked']} OTs"
            )

            return {
                **state,
                "action": "PREPLANIFICADA_CHECK_COMPLETE",
                "result": alert_results
            }

        except Exception as e:
            db.rollback()
            error_msg = f"Error checking PREPLANIFICADA alerts: {str(e)}"
            logger.error(error_msg)
            alert_results["messages"].append(error_msg)

            self._log_action(
                db,
                accion="check_preplanificada_alerts",
                resultado="ERROR",
                message=error_msg
            )

            return {
                **state,
                "action": "PREPLANIFICADA_CHECK_ERROR",
                "result": alert_results,
                "errors": [error_msg]
            }
        finally:
            db.close()

    async def validate_publico_documents(self, ot_id: str) -> Dict[str, Any]:
        """
        Validate that a PUBLICO project has all required documents (exactly 29).
        
        This is called before allowing an OT to transition to FINALIZADA status
        if it's a PUBLICO project.
        
        Args:
            ot_id: External OT ID to validate
        
        Returns:
            Dict with validation results:
            - is_valid: Boolean indicating if document count == 29
            - document_count: Current document count
            - required_count: Required document count (29)
            - message: Validation message
        """
        try:
            logger.info(f"Validating documents for OT {ot_id}")

            # Get document count from TelcoDrive service
            document_count = await self.telcodrive_service.get_document_count(ot_id)
            
            required_count = 29
            is_valid = document_count == required_count

            result = {
                "is_valid": is_valid,
                "document_count": document_count,
                "required_count": required_count,
                "message": (
                    f"OT {ot_id}: {document_count}/{required_count} documents. "
                    f"Status: {'VALID' if is_valid else 'INCOMPLETE'}"
                )
            }

            log_message = f"Document validation for OT {ot_id}: {result['message']}"
            logger.info(log_message)

            return result

        except Exception as e:
            error_msg = f"Error validating documents for OT {ot_id}: {str(e)}"
            logger.error(error_msg)
            
            return {
                "is_valid": False,
                "document_count": 0,
                "required_count": 29,
                "message": error_msg,
                "error": True
            }

    def _calculate_days_detained(self, ot: OT) -> int:
        """
        Calculate the number of days an OT has been in DETENIDA status.
        
        Args:
            ot: OT model instance
        
        Returns:
            Number of days detained (rounded down)
        """
        now = datetime.utcnow()
        # Use created_at as detention start date
        # In production, could track status change timestamp instead
        detained_duration = now - ot.created_at
        days_detained = int(detained_duration.days)
        return days_detained

    def _log_action(
        self,
        db: Session,
        accion: str,
        resultado: str,
        message: str = None
    ) -> None:
        """
        Log a governance action to the logs_agentes table.
        
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

