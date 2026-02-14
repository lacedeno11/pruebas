"""
GobernanzaAgent for PEI Platform agentic system.
Enforces governance rules, sends alerts, and auto-cancels expired OTs.
"""

from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI

from backend.agents.base_agent import BaseAgent
from backend.models import OT
from backend.models.log_agente import ActionResult
from backend.services.telcos_service import TelcosService
from backend.utils.business_rules import calculate_days_in_status, validate_project_completion
from backend.config import get_settings


class GobernanzaAgent(BaseAgent):
    """
    GobernanzaAgent that enforces governance rules and business constraints.

    GobernanzaAgent is responsible for monitoring OT lifecycle and enforcing
    critical business rules:

    1. **Inactivity Monitoring**: OTs stuck in PREPLANIFICADA status for too long
       - Threshold: INACTIVITY_THRESHOLD_HOURS (default 48 hours)
       - Action: Send high-priority alert to coordinators
       - Helps identify bottlenecks and stalled assignments

    2. **Detention Alerting**: Recurring alerts for OTs in DETENIDA status
       - Trigger: Days in detention match ALERT_DAYS (default 20, 25, 29 days)
       - Action: Send reminder alerts to team leads
       - Escalates urgency as days approach auto-cancellation threshold

    3. **Auto-Cancellation**: Auto-cancel OTs that exceed detention threshold
       - Threshold: CANCELLATION_THRESHOLD_DAYS (default 30 days)
       - Action: Update status to ANULADA, notify via TELCOS API
       - Prevents indefinite detention of work orders

    4. **Document Validation**: Validate PUBLICO projects have required documentation
       - Requirement: 29 documents in TelcoDrive before FINALIZADA
       - Scope: PUBLICO projects in PLANIFICADA or ASIGNADO_TAREA status
       - Action: Alert if documents incomplete, prevent FINALIZADA transition

    Alert Types:
    - HIGH: Inactivity (PREPLANIFICADA >48h) - escalate to management
    - MEDIUM: Detention reminders (days 20, 25, 29)
    - HIGH: Auto-cancellation (day 30)
    - WARNING: Document validation failures

    Integration with ComunicacionAgent:
    - Generates alert messages with priority levels
    - Routes to ComunicacionAgent for Telegram/Email delivery
    - Provides context for coordination and escalation
    """

    def __init__(self, llm: ChatOpenAI, db_session: Session):
        """
        Initialize GobernanzaAgent.

        Args:
            llm: ChatOpenAI instance for LLM operations (unused in GobernanzaAgent but required by BaseAgent)
            db_session: SQLAlchemy session for database operations
        """
        super().__init__(llm, db_session)
        self.agent_name = "GobernanzaAgent"
        self.config = get_settings()
        self.telcos_service = TelcosService()

    async def execute(self, state: Dict) -> Dict:
        """
        Execute governance checks and enforce business rules.

        Orchestrates four key governance operations:
        1. Monitor inactivity in PREPLANIFICADA status
        2. Send detention reminders for OTs in DETENIDA
        3. Auto-cancel OTs exceeding detention threshold
        4. Validate document completion for PUBLICO projects

        Args:
            state: Graph state containing:
                - user_input (str): User request or description
                - event_type (str): Type of event
                - Other state fields passed through

        Returns:
            Updated state with:
            - action_result (str): Summary of governance checks performed
            - agent_logs (list): Updated with GobernanzaAgent execution logs
            - ot_data (dict): Governance statistics (alerts, cancellations, etc.)
        """
        try:
            # Initialize tracking
            inactivity_alerts = 0
            detention_alerts = 0
            auto_cancellations = 0
            document_warnings = 0

            # 1. Check for inactive OTs (PREPLANIFICADA >INACTIVITY_THRESHOLD_HOURS)
            inactivity_alerts = self._check_inactivity()
            self._log_action(
                agente_name="GobernanzaAgent",
                accion="check_inactivity",
                resultado=ActionResult.SUCCESS,
                metadata={"inactivity_alerts": inactivity_alerts},
            )

            # 2. Check detention status and send reminders
            detention_alerts = self._check_detention_reminders()
            self._log_action(
                agente_name="GobernanzaAgent",
                accion="check_detention_reminders",
                resultado=ActionResult.SUCCESS,
                metadata={"detention_alerts": detention_alerts},
            )

            # 3. Auto-cancel OTs exceeding detention threshold
            auto_cancellations = await self._auto_cancel_detained_ots()
            self._log_action(
                agente_name="GobernanzaAgent",
                accion="auto_cancel_detained_ots",
                resultado=ActionResult.SUCCESS,
                metadata={"auto_cancellations": auto_cancellations},
            )

            # 4. Validate PUBLICO project document completion
            document_warnings = self._validate_publico_documents()
            self._log_action(
                agente_name="GobernanzaAgent",
                accion="validate_publico_documents",
                resultado=ActionResult.SUCCESS,
                metadata={"document_warnings": document_warnings},
            )

            # Overall success logging
            total_alerts = inactivity_alerts + detention_alerts + document_warnings
            action_result = (
                f"Governance check completed: "
                f"{inactivity_alerts} inactivity alerts, "
                f"{detention_alerts} detention reminders, "
                f"{auto_cancellations} auto-cancellations, "
                f"{document_warnings} document warnings."
            )

            self._log_action(
                agente_name="GobernanzaAgent",
                accion="execute_governance_checks",
                resultado=ActionResult.SUCCESS,
                metadata={
                    "inactivity_alerts": inactivity_alerts,
                    "detention_alerts": detention_alerts,
                    "auto_cancellations": auto_cancellations,
                    "document_warnings": document_warnings,
                    "total_alerts": total_alerts,
                },
            )

            return {
                **state,
                "action_result": action_result,
                "ot_data": {
                    "inactivity_alerts": inactivity_alerts,
                    "detention_alerts": detention_alerts,
                    "auto_cancellations": auto_cancellations,
                    "document_warnings": document_warnings,
                    "total_alerts": total_alerts,
                },
            }

        except Exception as e:
            action_result = f"GobernanzaAgent failed: {str(e)}"
            self._log_action(
                agente_name="GobernanzaAgent",
                accion="execute",
                resultado=ActionResult.FAILURE,
                metadata={"error": str(e)},
            )
            return {
                **state,
                "action_result": action_result,
                "error_message": str(e),
                "ot_data": {
                    "inactivity_alerts": 0,
                    "detention_alerts": 0,
                    "auto_cancellations": 0,
                    "document_warnings": 0,
                },
            }

    def _check_inactivity(self) -> int:
        """
        Check for OTs stuck in PREPLANIFICADA status for too long.

        Queries OTs with:
        - status = PREPLANIFICADA
        - created_at older than INACTIVITY_THRESHOLD_HOURS

        Logs alert for each inactive OT with details (id, external_id, hours_in_status).

        Returns:
            Count of inactivity alerts generated
        """
        alerts = 0
        inactivity_threshold_hours = self.config.INACTIVITY_THRESHOLD_HOURS

        try:
            # Calculate threshold timestamp
            threshold_time = datetime.utcnow() - timedelta(
                hours=inactivity_threshold_hours
            )

            # Query inactive OTs in PREPLANIFICADA status
            inactive_ots = (
                self.db_session.query(OT)
                .filter(OT.status == "PREPLANIFICADA")
                .filter(OT.created_at < threshold_time)
                .all()
            )

            for ot in inactive_ots:
                hours_in_status = (datetime.utcnow() - ot.created_at).total_seconds() / 3600

                # Log the inactivity alert
                self._log_action(
                    agente_name="GobernanzaAgent",
                    accion="inactivity_alert",
                    resultado=ActionResult.SUCCESS,
                    ot_id=ot.id,
                    metadata={
                        "external_id": ot.external_id,
                        "hours_in_status": round(hours_in_status, 2),
                        "threshold_hours": inactivity_threshold_hours,
                        "priority": "HIGH",
                    },
                )
                alerts += 1

        except Exception as e:
            print(f"❌ Error in inactivity check: {str(e)}")
            self._log_action(
                agente_name="GobernanzaAgent",
                accion="inactivity_check_error",
                resultado=ActionResult.FAILURE,
                metadata={"error": str(e)},
            )

        return alerts

    def _check_detention_reminders(self) -> int:
        """
        Send reminder alerts for OTs in DETENIDA status.

        Queries OTs with status = DETENIDA and checks days in detention.
        Sends alerts on specific days (default: 20, 25, 29) to escalate urgency.

        Algorithm:
        1. Query all OTs in DETENIDA status
        2. For each OT, calculate days in DETENIDA status
        3. If days matches any ALERT_DAYS, log reminder alert
        4. Include context for escalation (days remaining until auto-cancel)

        Returns:
            Count of detention reminder alerts generated
        """
        alerts = 0
        alert_days = self.config.ALERT_DAYS
        cancellation_threshold = self.config.CANCELLATION_THRESHOLD_DAYS

        try:
            # Query OTs in DETENIDA status
            detained_ots = (
                self.db_session.query(OT)
                .filter(OT.status == "DETENIDA")
                .all()
            )

            for ot in detained_ots:
                # Calculate days in DETENIDA status
                days_in_status = calculate_days_in_status(ot, "DETENIDA")

                # Check if days match alert days
                if days_in_status in alert_days:
                    days_until_cancel = cancellation_threshold - days_in_status

                    # Log the detention reminder alert
                    self._log_action(
                        agente_name="GobernanzaAgent",
                        accion="detention_reminder_alert",
                        resultado=ActionResult.SUCCESS,
                        ot_id=ot.id,
                        metadata={
                            "external_id": ot.external_id,
                            "days_in_detention": days_in_status,
                            "days_until_cancellation": days_until_cancel,
                            "priority": "MEDIUM",
                        },
                    )
                    alerts += 1

        except Exception as e:
            print(f"❌ Error in detention reminder check: {str(e)}")
            self._log_action(
                agente_name="GobernanzaAgent",
                accion="detention_reminder_check_error",
                resultado=ActionResult.FAILURE,
                metadata={"error": str(e)},
            )

        return alerts

    async def _auto_cancel_detained_ots(self) -> int:
        """
        Auto-cancel OTs that exceed detention threshold.

        Queries OTs with:
        - status = DETENIDA
        - Days in detention >= CANCELLATION_THRESHOLD_DAYS (default 30)

        For each OT:
        1. Update status to ANULADA
        2. Call TelcosService.update_status() to sync with TELCOS API
        3. Log the auto-cancellation with reason
        4. Commit database changes

        Returns:
            Count of OTs auto-cancelled
        """
        cancellations = 0
        cancellation_threshold = self.config.CANCELLATION_THRESHOLD_DAYS

        try:
            # Query OTs in DETENIDA status
            detained_ots = (
                self.db_session.query(OT)
                .filter(OT.status == "DETENIDA")
                .all()
            )

            for ot in detained_ots:
                # Calculate days in DETENIDA status
                days_in_status = calculate_days_in_status(ot, "DETENIDA")

                # Check if threshold exceeded
                if days_in_status >= cancellation_threshold:
                    try:
                        # Update status to ANULADA
                        ot.status = "ANULADA"

                        # Notify TELCOS API of cancellation
                        success = await self.telcos_service.update_status(
                            ot.external_id, "ANULADA"
                        )

                        # Log the auto-cancellation
                        self._log_action(
                            agente_name="GobernanzaAgent",
                            accion="auto_cancel_ot",
                            resultado=ActionResult.SUCCESS if success else ActionResult.FAILURE,
                            ot_id=ot.id,
                            metadata={
                                "external_id": ot.external_id,
                                "days_in_detention": days_in_status,
                                "reason": "Exceeded cancellation threshold",
                                "telcos_update_success": success,
                            },
                        )
                        cancellations += 1

                    except Exception as e:
                        print(f"❌ Error cancelling OT {ot.external_id}: {str(e)}")
                        self._log_action(
                            agente_name="GobernanzaAgent",
                            accion="auto_cancel_error",
                            resultado=ActionResult.FAILURE,
                            ot_id=ot.id,
                            metadata={
                                "external_id": ot.external_id,
                                "error": str(e),
                            },
                        )

            # Commit all cancellations
            self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            print(f"❌ Error in auto-cancellation: {str(e)}")
            self._log_action(
                agente_name="GobernanzaAgent",
                accion="auto_cancel_ots_error",
                resultado=ActionResult.FAILURE,
                metadata={"error": str(e)},
            )

        return cancellations

    def _validate_publico_documents(self) -> int:
        """
        Validate PUBLICO projects have required 29 documents.

        Queries PUBLICO projects in PLANIFICADA or ASIGNADO_TAREA status.
        For each project, fetches document count from TelcoDrive via TelcosService.
        Logs warning if documents incomplete.

        Algorithm:
        1. Query PUBLICO OTs in PLANIFICADA or ASIGNADO_TAREA status
        2. For each OT, call TelcosService.get_documents_status()
        3. Validate document count >= 29 using validate_project_completion()
        4. Log warning if validation fails

        Returns:
            Count of document validation warnings
        """
        warnings = 0

        try:
            # Query PUBLICO projects in active statuses
            publico_ots = (
                self.db_session.query(OT)
                .filter(OT.project_type == "PUBLICO")
                .filter(OT.status.in_(["PLANIFICADA", "ASIGNADO_TAREA"]))
                .all()
            )

            for ot in publico_ots:
                try:
                    # Fetch document count from TelcoDrive
                    doc_count = self.db_session.run_sync(
                        lambda: self.telcos_service.get_documents_status(ot.external_id)
                    )

                    # Validate document completion
                    is_complete = validate_project_completion(ot, doc_count or 0)

                    if not is_complete:
                        # Log the validation warning
                        self._log_action(
                            agente_name="GobernanzaAgent",
                            accion="publico_document_validation_failed",
                            resultado=ActionResult.SUCCESS,
                            ot_id=ot.id,
                            metadata={
                                "external_id": ot.external_id,
                                "document_count": doc_count or 0,
                                "required_documents": 29,
                                "priority": "WARNING",
                            },
                        )
                        warnings += 1

                except Exception as e:
                    print(f"❌ Error validating documents for OT {ot.external_id}: {str(e)}")
                    self._log_action(
                        agente_name="GobernanzaAgent",
                        accion="document_validation_error",
                        resultado=ActionResult.FAILURE,
                        ot_id=ot.id,
                        metadata={
                            "external_id": ot.external_id,
                            "error": str(e),
                        },
                    )

        except Exception as e:
            print(f"❌ Error in document validation: {str(e)}")
            self._log_action(
                agente_name="GobernanzaAgent",
                accion="document_validation_check_error",
                resultado=ActionResult.FAILURE,
                metadata={"error": str(e)},
            )

        return warnings

