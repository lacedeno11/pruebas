"""Governance Agent for inactivity management and auto-cancellation (UC-PEI-08)"""

import logging
from typing import Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.database.models import OT, Alerta, LogAgente
from backend.services.notification_service import NotificationService
from backend.services.telcos_service import TelcosService
from backend.utils.business_rules import (
    calculate_days_inactive,
    should_send_alert,
    should_auto_cancel,
)
from backend.utils.constants import (
    OT_STATUS,
    ALERT_DAYS,
    AUTO_CANCEL_DAYS,
    PROJECT_TYPES,
    DOCUMENT_REQUIREMENT_PUBLICO,
    INACTIVITY_ALERT_HOURS,
)
from backend.models.proyecto import GovernanceResult
from backend.agents.graph import PEIState

logger = logging.getLogger(__name__)


class GobernanzaAgent:
    """
    Governance Agent for managing OT lifecycle and compliance.

    This agent implements UC-PEI-08 (Governance) with responsibilities:
    1. Monitor inactive OTs in DETENIDA status
    2. Send alerts at 20, 25, 29 days of inactivity
    3. Auto-cancel OTs after 30 days in DETENIDA
    4. Monitor PREPLANIFICADA inactivity (>48 hours)
    5. Validate PUBLICO projects have required documents for FINALIZADA transition
    """

    def __init__(
        self,
        db_session: Session,
        notification_service: NotificationService,
        telcos_service: Optional[TelcosService] = None,
    ):
        """
        Initialize GobernanzaAgent with database session and services.

        Args:
            db_session: SQLAlchemy database session
            notification_service: Service for sending notifications
            telcos_service: Optional service for updating OT status in TELCOS API
        """
        self.db_session = db_session
        self.notification_service = notification_service
        self.telcos_service = telcos_service

        logger.info("GobernanzaAgent initialized")

    async def execute(self, state: PEIState) -> PEIState:
        """
        Execute governance checks (UC-PEI-08).

        Orchestrates inactivity checks and auto-cancellation:
        1. Check DETENIDA OTs for inactivity (daily at 00:30)
        2. Send alerts at 20, 25, 29 days
        3. Auto-cancel after 30 days
        4. Check PREPLANIFICADA inactivity (hourly)

        Args:
            state: Current PEI state

        Returns:
            Updated state with GovernanceResult

        Raises:
            Exception: If database or service errors occur (wrapped and logged)
        """
        try:
            logger.info("GobernanzaAgent: Starting governance checks")

            # Run inactivity check
            result = await self.check_inactivity()

            # Run PREPLANIFICADA inactivity check
            preplanificada_result = await self.check_preplanificada_inactivity()

            logger.info(
                f"GobernanzaAgent: Governance checks completed - "
                f"Alerts sent: {result['alerts_sent']}, "
                f"OTs cancelled: {result['ots_cancelled']}"
            )

            # Combine results
            combined_result = GovernanceResult(
                alerts_sent=result["alerts_sent"],
                ots_cancelled=result["ots_cancelled"],
                details=result["details"] + preplanificada_result.get("details", []),
            )

            # Update state with results
            state["validation_result"] = {
                "alerts_sent": result["alerts_sent"],
                "ots_cancelled": result["ots_cancelled"],
            }

            # Add to agent logs
            state["agent_logs"].append(
                {
                    "agent": "governance",
                    "action": "check_inactivity",
                    "result": "success",
                    "alerts_sent": result["alerts_sent"],
                    "ots_cancelled": result["ots_cancelled"],
                    "timestamp": datetime.now().isoformat(),
                }
            )

            return state

        except Exception as e:
            logger.error(f"GobernanzaAgent: Fatal error during governance checks: {str(e)}")

            # Set error state
            state["error"] = f"Governance agent error: {str(e)}"

            # Add error to agent logs
            state["agent_logs"].append(
                {
                    "agent": "governance",
                    "action": "check_inactivity",
                    "result": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )

            return state

    async def check_inactivity(self) -> dict:
        """
        Check for inactive OTs in DETENIDA status.

        Queries all DETENIDA OTs and:
        - Sends alerts at 20, 25, 29 days of inactivity
        - Auto-cancels OTs after 30 days

        Returns:
            Dictionary with:
            - alerts_sent: Number of alerts sent
            - ots_cancelled: Number of OTs auto-cancelled
            - details: List of detail dictionaries
        """
        try:
            logger.info("GobernanzaAgent: Starting DETENIDA inactivity check")

            result = {
                "alerts_sent": 0,
                "ots_cancelled": 0,
                "details": [],
            }

            # Get all DETENIDA OTs
            detenida_ots = (
                self.db_session.query(OT)
                .filter(OT.status == OT_STATUS["DETENIDA"])
                .all()
            )

            logger.info(f"GobernanzaAgent: Checking {len(detenida_ots)} DETENIDA OTs")

            for ot in detenida_ots:
                try:
                    # Calculate days inactive
                    days_inactive = calculate_days_inactive(ot.last_status_change)
                    logger.info(f"GobernanzaAgent: OT {ot.id} inactive for {days_inactive} days")

                    # Check if should auto-cancel
                    if should_auto_cancel(days_inactive):
                        await self.auto_cancel(ot)
                        result["ots_cancelled"] += 1

                        detail = {
                            "ot_id": ot.id,
                            "external_id": ot.external_id,
                            "action": "auto_cancelled",
                            "reason": f"Exceeded {AUTO_CANCEL_DAYS} days in DETENIDA status",
                            "days_inactive": days_inactive,
                        }
                        result["details"].append(detail)

                    # Check if should send alert
                    else:
                        alert_type = should_send_alert(days_inactive)
                        if alert_type:
                            await self.send_alert(ot, alert_type)
                            result["alerts_sent"] += 1

                            detail = {
                                "ot_id": ot.id,
                                "external_id": ot.external_id,
                                "action": "alert_sent",
                                "alert_type": alert_type,
                                "days_inactive": days_inactive,
                            }
                            result["details"].append(detail)

                except Exception as ot_error:
                    logger.error(
                        f"GobernanzaAgent: Error processing OT {ot.id}: {str(ot_error)}"
                    )
                    detail = {
                        "ot_id": ot.id,
                        "external_id": ot.external_id,
                        "action": "error",
                        "error": str(ot_error),
                    }
                    result["details"].append(detail)

            self.db_session.commit()

            logger.info(
                f"GobernanzaAgent: DETENIDA inactivity check complete - "
                f"Alerts: {result['alerts_sent']}, Cancelled: {result['ots_cancelled']}"
            )

            return result

        except Exception as e:
            logger.error(f"GobernanzaAgent: Error in check_inactivity: {str(e)}")
            self.db_session.rollback()
            return {
                "alerts_sent": 0,
                "ots_cancelled": 0,
                "details": [{"error": str(e)}],
            }

    async def send_alert(self, ot: OT, alert_type: str) -> None:
        """
        Send alert for OT inactivity.

        Creates Alerta record and sends email/telegram to PM and Coordinador OPU.

        Args:
            ot: OT object
            alert_type: Type of alert (WARNING_20, WARNING_25, FINAL_WARNING)
        """
        try:
            logger.info(f"GobernanzaAgent: Sending {alert_type} alert for OT {ot.id}")

            # Create alert record
            alerta = Alerta(
                ot_id=ot.id,
                tipo=alert_type,
                mensaje=f"OT {ot.external_id} inactivo en estado DETENIDA - Alerta {alert_type}",
                destinatario="PM,Coordinador",
                canal="EMAIL",
                enviado_at=None,
                leido=False,
            )

            self.db_session.add(alerta)

            # Get alert template from notification service
            template = self.notification_service.get_alert_template(alert_type, ot.external_id)

            # Send email to PM
            try:
                await self.notification_service.send_email(
                    recipient="pm@telconet.ec",
                    subject=template["subject"],
                    body=template["body"],
                    html=True,
                )
                logger.info(f"GobernanzaAgent: Alert email sent to PM for OT {ot.id}")
            except Exception as email_error:
                logger.error(
                    f"GobernanzaAgent: Failed to send email alert: {str(email_error)}"
                )

            # Send telegram to Coordinador OPU if configured
            try:
                from backend.config.settings import settings

                if settings.TELEGRAM_COORDINADOR_CHAT_ID:
                    await self.notification_service.send_telegram(
                        chat_id=str(settings.TELEGRAM_COORDINADOR_CHAT_ID),
                        message=template["body"][:300],  # Limit message length
                    )
                    logger.info(
                        f"GobernanzaAgent: Alert telegram sent to "
                        f"Coordinador for OT {ot.id}"
                    )
            except Exception as telegram_error:
                logger.error(
                    f"GobernanzaAgent: Failed to send telegram alert: {str(telegram_error)}"
                )

            # Update alert as sent
            alerta.enviado_at = datetime.now()
            self.db_session.add(alerta)
            self.db_session.flush()

            logger.info(f"GobernanzaAgent: Alert sent for OT {ot.id}")

        except Exception as e:
            logger.error(f"GobernanzaAgent: Error sending alert for OT {ot.id}: {str(e)}")

    async def auto_cancel(self, ot: OT) -> None:
        """
        Auto-cancel an OT due to excessive inactivity.

        Updates OT status to ANULADA and sends notifications.

        Args:
            ot: OT object to cancel
        """
        try:
            logger.info(f"GobernanzaAgent: Auto-cancelling OT {ot.id}")

            # Update OT status
            ot.status = OT_STATUS["ANULADA"]
            ot.updated_at = datetime.now()
            ot.last_status_change = datetime.now()

            # Update status in TELCOS API if service available
            if self.telcos_service:
                try:
                    await self.telcos_service.update_ot_status(
                        ot.external_id, OT_STATUS["ANULADA"]
                    )
                    logger.info(f"GobernanzaAgent: Updated TELCOS API for OT {ot.id}")
                except Exception as api_error:
                    logger.warning(
                        f"GobernanzaAgent: Failed to update TELCOS for OT {ot.id}: "
                        f"{str(api_error)}"
                    )

            # Create log entry
            log_entry = LogAgente(
                ot_id=ot.id,
                agente_name="GobernanzaAgent",
                accion="auto_cancel",
                resultado="SUCCESS",
                raw_llm_response=None,
                metadata={
                    "external_id": ot.external_id,
                    "reason": "Exceeded 30 days in DETENIDA status",
                    "previous_status": OT_STATUS["DETENIDA"],
                },
            )

            self.db_session.add(log_entry)
            self.db_session.flush()

            # Send cancellation notification
            try:
                template = self.notification_service.get_alert_template(
                    "AUTO_CANCELLED", ot.external_id
                )

                await self.notification_service.send_email(
                    recipient="pm@telconet.ec",
                    subject=template["subject"],
                    body=template["body"],
                    html=True,
                )
                logger.info(f"GobernanzaAgent: Cancellation notification sent for OT {ot.id}")
            except Exception as notify_error:
                logger.error(
                    f"GobernanzaAgent: Failed to send cancellation notification: "
                    f"{str(notify_error)}"
                )

            logger.info(f"GobernanzaAgent: OT {ot.id} auto-cancelled successfully")

        except Exception as e:
            logger.error(f"GobernanzaAgent: Error auto-cancelling OT {ot.id}: {str(e)}")

    async def check_preplanificada_inactivity(self) -> dict:
        """
        Check for OTs in PREPLANIFICADA status for >48 hours.

        Sends high-priority alert to Coordinador OPU if found.

        Returns:
            Dictionary with check results and details
        """
        try:
            logger.info("GobernanzaAgent: Checking PREPLANIFICADA inactivity")

            result = {
                "alerts_sent": 0,
                "details": [],
            }

            # Calculate threshold: now - 48 hours
            threshold = datetime.now() - timedelta(hours=INACTIVITY_ALERT_HOURS)

            # Get old PREPLANIFICADA OTs
            old_preplanificada = (
                self.db_session.query(OT)
                .filter(
                    OT.status == OT_STATUS["PREPLANIFICADA"],
                    OT.created_at < threshold,
                )
                .all()
            )

            logger.info(
                f"GobernanzaAgent: Found {len(old_preplanificada)} "
                f"PREPLANIFICADA OTs older than 48 hours"
            )

            for ot in old_preplanificada:
                try:
                    # Create alert
                    alerta = Alerta(
                        ot_id=ot.id,
                        tipo="INACTIVITY_48H",
                        mensaje=f"OT {ot.external_id} sin planificar por más de 48 horas",
                        destinatario="Coordinador OPU",
                        canal="TELEGRAM",
                        enviado_at=None,
                        leido=False,
                    )

                    self.db_session.add(alerta)

                    # Send high-priority alert
                    try:
                        from backend.config.settings import settings

                        if settings.TELEGRAM_COORDINADOR_CHAT_ID:
                            message = (
                                f"🚨 ALERTA URGENTE: OT {ot.external_id} sin planificar "
                                f"por más de 48 horas. Acción requerida inmediatamente."
                            )

                            await self.notification_service.send_telegram(
                                chat_id=str(settings.TELEGRAM_COORDINADOR_CHAT_ID),
                                message=message,
                            )

                            alerta.enviado_at = datetime.now()
                            result["alerts_sent"] += 1

                            logger.info(
                                f"GobernanzaAgent: Sent PREPLANIFICADA alert for OT {ot.id}"
                            )
                    except Exception as notify_error:
                        logger.error(
                            f"GobernanzaAgent: Failed to send PREPLANIFICADA alert: "
                            f"{str(notify_error)}"
                        )

                    result["details"].append(
                        {
                            "ot_id": ot.id,
                            "external_id": ot.external_id,
                            "action": "alert_sent",
                            "alert_type": "INACTIVITY_48H",
                            "hours_inactive": INACTIVITY_ALERT_HOURS,
                        }
                    )

                except Exception as ot_error:
                    logger.error(
                        f"GobernanzaAgent: Error processing PREPLANIFICADA OT {ot.id}: "
                        f"{str(ot_error)}"
                    )

            self.db_session.commit()

            logger.info(
                f"GobernanzaAgent: PREPLANIFICADA check complete - "
                f"Alerts sent: {result['alerts_sent']}"
            )

            return result

        except Exception as e:
            logger.error(f"GobernanzaAgent: Error in check_preplanificada_inactivity: {str(e)}")
            self.db_session.rollback()
            return {
                "alerts_sent": 0,
                "details": [{"error": str(e)}],
            }

    async def validate_public_checklist(self, ot_id: int) -> dict:
        """
        Validate PUBLICO project has required documents for FINALIZADA transition.

        For PUBLICO projects, requires exactly 29 documents from TelcoDrive.

        Args:
            ot_id: OT database ID

        Returns:
            Dictionary with:
            - is_valid: Boolean indicating if checklist is met
            - document_count: Current document count
            - required: Required document count
            - message: Status message
        """
        try:
            logger.info(f"GobernanzaAgent: Validating PUBLICO checklist for OT {ot_id}")

            # Get OT
            ot = self.db_session.query(OT).filter(OT.id == ot_id).first()

            if not ot:
                return {
                    "is_valid": False,
                    "document_count": 0,
                    "required": DOCUMENT_REQUIREMENT_PUBLICO,
                    "message": "OT not found",
                }

            # Only check for PUBLICO projects
            if ot.project_type != PROJECT_TYPES["PUBLICO"]:
                return {
                    "is_valid": True,
                    "document_count": 0,
                    "required": 0,
                    "message": "Not a PUBLICO project, no validation required",
                }

            # Get documents from TelcoDrive if service available
            if not self.telcos_service:
                logger.warning(
                    f"GobernanzaAgent: TelcosService not available, "
                    f"cannot validate documents for OT {ot_id}"
                )
                return {
                    "is_valid": False,
                    "document_count": 0,
                    "required": DOCUMENT_REQUIREMENT_PUBLICO,
                    "message": "Document validation service unavailable",
                }

            try:
                doc_result = await self.telcos_service.get_ot_documents(ot.external_id)
                document_count = doc_result.get("document_count", 0)

                is_valid = document_count >= DOCUMENT_REQUIREMENT_PUBLICO

                logger.info(
                    f"GobernanzaAgent: OT {ot_id} has {document_count} documents, "
                    f"required {DOCUMENT_REQUIREMENT_PUBLICO}"
                )

                return {
                    "is_valid": is_valid,
                    "document_count": document_count,
                    "required": DOCUMENT_REQUIREMENT_PUBLICO,
                    "message": (
                        "Checklist met - FINALIZADA transition allowed"
                        if is_valid
                        else f"Missing {DOCUMENT_REQUIREMENT_PUBLICO - document_count} "
                        f"documents for FINALIZADA transition"
                    ),
                }

            except Exception as api_error:
                logger.error(
                    f"GobernanzaAgent: Error fetching documents for OT {ot_id}: "
                    f"{str(api_error)}"
                )
                return {
                    "is_valid": False,
                    "document_count": 0,
                    "required": DOCUMENT_REQUIREMENT_PUBLICO,
                    "message": f"Error validating documents: {str(api_error)}",
                }

        except Exception as e:
            logger.error(f"GobernanzaAgent: Error in validate_public_checklist: {str(e)}")
            return {
                "is_valid": False,
                "document_count": 0,
                "required": DOCUMENT_REQUIREMENT_PUBLICO,
                "message": f"Validation error: {str(e)}",
            }

    async def get_governance_stats(self) -> dict:
        """
        Get statistics about governance state.

        Returns:
            Dictionary with governance statistics
        """
        try:
            logger.info("GobernanzaAgent: Calculating governance statistics")

            # Count OTs by alert status
            detenida_ots = (
                self.db_session.query(OT)
                .filter(OT.status == OT_STATUS["DETENIDA"])
                .all()
            )

            stats = {
                "total_detenida": len(detenida_ots),
                "alert_warning_20": 0,
                "alert_warning_25": 0,
                "alert_final_warning": 0,
                "at_risk_auto_cancel": 0,
            }

            for ot in detenida_ots:
                days_inactive = calculate_days_inactive(ot.last_status_change)

                if days_inactive >= AUTO_CANCEL_DAYS:
                    stats["at_risk_auto_cancel"] += 1
                elif days_inactive >= 29:
                    stats["alert_final_warning"] += 1
                elif days_inactive >= 25:
                    stats["alert_warning_25"] += 1
                elif days_inactive >= 20:
                    stats["alert_warning_20"] += 1

            # Count PREPLANIFICADA OTs >48 hours
            threshold = datetime.now() - timedelta(hours=INACTIVITY_ALERT_HOURS)

            old_preplanificada = (
                self.db_session.query(OT)
                .filter(
                    OT.status == OT_STATUS["PREPLANIFICADA"],
                    OT.created_at < threshold,
                )
                .count()
            )

            stats["preplanificada_over_48h"] = old_preplanificada

            logger.info(f"GobernanzaAgent: Governance stats calculated: {stats}")

            return stats

        except Exception as e:
            logger.error(f"GobernanzaAgent: Error in get_governance_stats: {str(e)}")
            return {"error": str(e)}

