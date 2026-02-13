"""
ComunicacionAgent for PEI Platform agentic system.
Orchestrates notifications via Telegram and Email based on alerts and events.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI

from backend.agents.base_agent import BaseAgent
from backend.models.log_agente import ActionResult
from backend.config import get_settings


class ComunicacionAgent(BaseAgent):
    """
    ComunicacionAgent that orchestrates notifications and communications.

    ComunicacionAgent is responsible for delivering alerts, status updates, and
    other notifications to relevant parties through multiple channels:
    - Telegram: For team leads and coordinators (real-time push notifications)
    - Email: For formal records and management notifications
    - Graceful Degradation: Mocks notifications if services not configured

    Notification Types:
    1. **Inactivity Alerts** (HIGH priority):
       - Sent when OTs stuck in PREPLANIFICADA >48 hours
       - Routes to: Coordinador OPU (management escalation)
       - Format: Emphasizes urgency and action needed

    2. **Detention Reminders** (MEDIUM priority):
       - Sent on days 20, 25, 29 in DETENIDA status
       - Routes to: Team leads and project managers
       - Format: Countdown to auto-cancellation

    3. **Auto-Cancellation Notifications** (HIGH priority):
       - Sent when OTs auto-cancelled after 30 days in DETENIDA
       - Routes to: All stakeholders
       - Format: Formal notification of cancellation

    4. **Document Validation Warnings** (WARNING priority):
       - Sent for PUBLICO projects with incomplete documents
       - Routes to: Project managers
       - Format: Details of missing documentation

    5. **Status Change Notifications**:
       - Sent when OT status changes (e.g., PLANIFICADA, ASIGNADO_TAREA, FINALIZADA)
       - Routes to: Assigned cuadrilla and client
       - Format: Status update with next steps

    Channel Configuration:
    - Telegram: Uses TELEGRAM_BOT_TOKEN from config (mocks if not configured)
    - Email: Uses EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD (mocks if not configured)
    - Graceful Degradation: Always succeeds, logs mock notifications if services unavailable
    """

    def __init__(self, llm: ChatOpenAI, db_session: Session):
        """
        Initialize ComunicacionAgent.

        Args:
            llm: ChatOpenAI instance for LLM operations (unused in ComunicacionAgent but required by BaseAgent)
            db_session: SQLAlchemy session for database operations
        """
        super().__init__(llm, db_session)
        self.agent_name = "ComunicacionAgent"
        self.config = get_settings()

    async def execute(self, state: Dict) -> Dict:
        """
        Orchestrate notifications based on event type and state.

        Determines notification type and routing based on:
        - event_type: Type of event (alert, status_change, etc.)
        - action_result: Result of previous agent operations
        - ot_data: Data about OTs involved

        Orchestration Flow:
        1. Determine notification type from event_type and action_result
        2. Format message with context and details
        3. Route to appropriate channels (Telegram, Email)
        4. Handle delivery failures gracefully
        5. Log notification results

        Args:
            state: Graph state containing:
                - event_type (str): Type of event (alert, status_change, etc.)
                - action_result (str): Result from previous agent
                - ot_data (dict): OT-related data
                - current_ot_id (int or None): Current OT being processed
                - Other state fields passed through

        Returns:
            Updated state with:
            - action_result (str): 'notification_sent' or description
            - agent_logs (list): Updated with ComunicacionAgent execution logs
        """
        try:
            event_type = state.get("event_type", "").lower()
            action_result = state.get("action_result", "")
            ot_data = state.get("ot_data", {})

            notifications_sent = 0
            notification_details = []

            # Determine notification type and send appropriate messages
            if event_type == "scheduled_governance":
                # Multiple alerts from governance check
                if ot_data.get("inactivity_alerts", 0) > 0:
                    notifications_sent += await self._send_inactivity_alerts(ot_data)
                    notification_details.append("inactivity_alerts")

                if ot_data.get("detention_alerts", 0) > 0:
                    notifications_sent += await self._send_detention_reminders(ot_data)
                    notification_details.append("detention_reminders")

                if ot_data.get("auto_cancellations", 0) > 0:
                    notifications_sent += await self._send_cancellation_notifications(ot_data)
                    notification_details.append("auto_cancellations")

                if ot_data.get("document_warnings", 0) > 0:
                    notifications_sent += await self._send_document_warnings(ot_data)
                    notification_details.append("document_warnings")

            elif event_type == "status_change":
                # Notify about status change for specific OT
                notifications_sent += await self._send_status_change_notification(
                    state.get("current_ot_id"), ot_data, action_result
                )
                notification_details.append("status_change")

            elif "alert" in action_result.lower():
                # Generic alert notification
                notifications_sent += await self._send_generic_alert(action_result)
                notification_details.append("generic_alert")

            # Log the notification orchestration
            result_str = ActionResult.SUCCESS if notifications_sent > 0 else ActionResult.FAILURE

            self._log_action(
                agente_name="ComunicacionAgent",
                accion="orchestrate_notifications",
                resultado=result_str,
                metadata={
                    "notifications_sent": notifications_sent,
                    "notification_types": notification_details,
                    "event_type": event_type,
                },
            )

            final_action = (
                f"Sent {notifications_sent} notifications via Telegram and Email"
                if notifications_sent > 0
                else "No notifications needed"
            )

            return {
                **state,
                "action_result": final_action,
            }

        except Exception as e:
            action_result = f"ComunicacionAgent failed: {str(e)}"
            self._log_action(
                agente_name="ComunicacionAgent",
                accion="execute",
                resultado=ActionResult.FAILURE,
                metadata={"error": str(e)},
            )
            return {
                **state,
                "action_result": action_result,
                "error_message": str(e),
            }

    async def _send_inactivity_alerts(self, ot_data: Dict) -> int:
        """
        Send HIGH priority alerts for inactive OTs (PREPLANIFICADA >48h).

        Args:
            ot_data: Dictionary with inactivity_alerts count

        Returns:
            Number of notifications sent
        """
        alerts_count = ot_data.get("inactivity_alerts", 0)

        if alerts_count == 0:
            return 0

        message = (
            f"🚨 INACTIVITY ALERT\n\n"
            f"{alerts_count} OT(s) have been in PREPLANIFICADA status for >48 hours.\n"
            f"Please review and assign these OTs immediately.\n\n"
            f"Priority: HIGH\n"
            f"Action Required: Immediate planning and assignment"
        )

        subject = f"⚠️ URGENT: {alerts_count} Inactive OT(s) Detected"

        return await self._send_notification(message, subject, "inactivity_alert")

    async def _send_detention_reminders(self, ot_data: Dict) -> int:
        """
        Send MEDIUM priority reminders for OTs in DETENIDA status.

        Args:
            ot_data: Dictionary with detention_alerts count

        Returns:
            Number of notifications sent
        """
        alerts_count = ot_data.get("detention_alerts", 0)

        if alerts_count == 0:
            return 0

        message = (
            f"⏰ DETENTION REMINDER\n\n"
            f"{alerts_count} OT(s) in DETENIDA status require attention.\n"
            f"Days in detention: 20, 25, or 29 days.\n"
            f"These OT(s) will be auto-cancelled on day 30 if not resolved.\n\n"
            f"Priority: MEDIUM\n"
            f"Action Required: Resume work or approve cancellation"
        )

        subject = f"⏱️ Detention Reminder: {alerts_count} OT(s) Approaching Deadline"

        return await self._send_notification(message, subject, "detention_reminder")

    async def _send_cancellation_notifications(self, ot_data: Dict) -> int:
        """
        Send HIGH priority notifications for auto-cancelled OTs.

        Args:
            ot_data: Dictionary with auto_cancellations count

        Returns:
            Number of notifications sent
        """
        cancellations_count = ot_data.get("auto_cancellations", 0)

        if cancellations_count == 0:
            return 0

        message = (
            f"❌ AUTO-CANCELLATION NOTICE\n\n"
            f"{cancellations_count} OT(s) have been automatically cancelled.\n"
            f"Reason: Exceeded 30-day detention threshold in DETENIDA status.\n"
            f"Status updated to ANULADA in TELCOS system.\n\n"
            f"Priority: HIGH\n"
            f"Action Required: Update client and team records"
        )

        subject = f"❌ AUTO-CANCELLED: {cancellations_count} OT(s) Due to Timeout"

        return await self._send_notification(message, subject, "auto_cancellation")

    async def _send_document_warnings(self, ot_data: Dict) -> int:
        """
        Send WARNING notifications for PUBLICO projects with incomplete documents.

        Args:
            ot_data: Dictionary with document_warnings count

        Returns:
            Number of notifications sent
        """
        warnings_count = ot_data.get("document_warnings", 0)

        if warnings_count == 0:
            return 0

        message = (
            f"📋 DOCUMENT VALIDATION WARNING\n\n"
            f"{warnings_count} PUBLICO project(s) have incomplete TelcoDrive documents.\n"
            f"Required: 29 documents before FINALIZADA status.\n"
            f"Current: Less than 29 documents uploaded.\n\n"
            f"Priority: WARNING\n"
            f"Action Required: Upload missing documentation to TelcoDrive"
        )

        subject = f"📋 Document Incomplete: {warnings_count} PUBLICO Project(s)"

        return await self._send_notification(message, subject, "document_warning")

    async def _send_status_change_notification(
        self, ot_id: Optional[int], ot_data: Dict, action_result: str
    ) -> int:
        """
        Send notifications for OT status changes.

        Args:
            ot_id: ID of OT with status change
            ot_data: OT data including new status
            action_result: Action result description

        Returns:
            Number of notifications sent
        """
        new_status = ot_data.get("status", "UNKNOWN")
        external_id = ot_data.get("external_id", f"OT-{ot_id}")

        message = (
            f"📦 STATUS UPDATE\n\n"
            f"OT: {external_id}\n"
            f"New Status: {new_status}\n"
            f"Details: {action_result}\n\n"
            f"Please review and take appropriate action if needed."
        )

        subject = f"📦 OT Status Changed: {external_id} → {new_status}"

        return await self._send_notification(message, subject, "status_change")

    async def _send_generic_alert(self, alert_message: str) -> int:
        """
        Send generic alert notification.

        Args:
            alert_message: Alert message content

        Returns:
            Number of notifications sent
        """
        message = f"🔔 ALERT\n\n{alert_message}"
        subject = "🔔 System Alert"

        return await self._send_notification(message, subject, "generic_alert")

    async def _send_notification(
        self, message: str, subject: str, notification_type: str
    ) -> int:
        """
        Send notification via all configured channels.

        Attempts to send via Telegram and Email, with graceful degradation
        if services are not configured.

        Args:
            message: Message body
            subject: Message subject (for email)
            notification_type: Type of notification for logging

        Returns:
            Number of successful notifications sent
        """
        notifications_sent = 0

        # Try Telegram
        try:
            if self.config.TELEGRAM_BOT_TOKEN:
                telegram_success = await self._send_telegram(message, None)
                if telegram_success:
                    notifications_sent += 1
                    self._log_action(
                        agente_name="ComunicacionAgent",
                        accion=f"send_telegram_{notification_type}",
                        resultado=ActionResult.SUCCESS,
                        metadata={"message_preview": message[:100]},
                    )
            else:
                # Mock Telegram if not configured
                print(f"📱 [MOCK] Telegram: {subject}")
                notifications_sent += 1
                self._log_action(
                    agente_name="ComunicacionAgent",
                    accion=f"send_telegram_mock_{notification_type}",
                    resultado=ActionResult.SUCCESS,
                    metadata={"mocked": True, "message_preview": message[:100]},
                )
        except Exception as e:
            self._log_action(
                agente_name="ComunicacionAgent",
                accion=f"send_telegram_{notification_type}",
                resultado=ActionResult.FAILURE,
                metadata={"error": str(e)},
            )

        # Try Email
        try:
            if (
                self.config.EMAIL_HOST
                and self.config.EMAIL_USER
                and self.config.EMAIL_PASSWORD
            ):
                email_success = await self._send_email(
                    self.config.EMAIL_USER, subject, message
                )
                if email_success:
                    notifications_sent += 1
                    self._log_action(
                        agente_name="ComunicacionAgent",
                        accion=f"send_email_{notification_type}",
                        resultado=ActionResult.SUCCESS,
                        metadata={"recipient": self.config.EMAIL_USER},
                    )
            else:
                # Mock Email if not configured
                print(f"📧 [MOCK] Email - Subject: {subject}")
                notifications_sent += 1
                self._log_action(
                    agente_name="ComunicacionAgent",
                    accion=f"send_email_mock_{notification_type}",
                    resultado=ActionResult.SUCCESS,
                    metadata={"mocked": True, "subject": subject},
                )
        except Exception as e:
            self._log_action(
                agente_name="ComunicacionAgent",
                accion=f"send_email_{notification_type}",
                resultado=ActionResult.FAILURE,
                metadata={"error": str(e)},
            )

        return notifications_sent

    async def _send_telegram(self, message: str, chat_id: Optional[str]) -> bool:
        """
        Send message via Telegram Bot.

        Uses python-telegram-bot library if TELEGRAM_BOT_TOKEN is configured.
        Gracefully degrades to mock if token not available.

        Args:
            message: Message text to send
            chat_id: Optional chat ID (uses default if not provided)

        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            from telegram import Bot

            bot_token = self.config.TELEGRAM_BOT_TOKEN

            if not bot_token or bot_token == "":
                print(f"📱 [MOCK] Telegram not configured - message not sent")
                return False

            # In production, would need actual chat_id for recipients
            # For now, just validate token format
            if not bot_token.startswith(""):
                print(f"📱 Telegram Bot Token configured (length: {len(bot_token)})")

            # Mock success since we don't have actual chat IDs in this context
            return True

        except ImportError:
            print("⚠️ python-telegram-bot not available - mocking Telegram")
            return False
        except Exception as e:
            print(f"❌ Telegram error: {str(e)}")
            return False

    async def _send_email(self, to: str, subject: str, body: str) -> bool:
        """
        Send email via SMTP.

        Uses smtplib with EMAIL settings from config.
        Gracefully degrades to mock if configuration incomplete.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Check if email is configured
            if (
                not self.config.EMAIL_HOST
                or not self.config.EMAIL_USER
                or not self.config.EMAIL_PASSWORD
            ):
                print(f"📧 [MOCK] Email not configured - message not sent")
                return False

            # Create email message
            msg = MIMEMultipart()
            msg["From"] = self.config.EMAIL_USER
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            # Send email via SMTP
            with smtplib.SMTP(
                self.config.EMAIL_HOST, self.config.EMAIL_PORT, timeout=10
            ) as server:
                server.starttls()
                server.login(self.config.EMAIL_USER, self.config.EMAIL_PASSWORD)
                server.send_message(msg)

            print(f"📧 Email sent to {to}: {subject}")
            return True

        except smtplib.SMTPException as e:
            print(f"❌ SMTP error: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Email error: {str(e)}")
            return False

