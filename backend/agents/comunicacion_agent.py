"""Communication Agent for notifications and messaging"""

import logging
import asyncio
from typing import List, Dict, Optional
from datetime import datetime

from backend.services.notification_service import NotificationService
from backend.database.models import LogAgente
from backend.agents.graph import PEIState
from backend.utils.constants import OT_STATUS, PROJECT_TYPES

logger = logging.getLogger(__name__)


class ComunicacionAgent:
    """
    Communication Agent for routing and sending notifications.

    This agent manages all notification workflows including:
    1. Direct notification requests from state
    2. Batch notification sending with rate limiting
    3. Status change notifications with dynamic recipient routing
    4. Template-based message formatting
    5. Comprehensive audit logging of all sent notifications
    """

    def __init__(self, notification_service: NotificationService):
        """
        Initialize ComunicacionAgent with notification service.

        Args:
            notification_service: Service for sending emails and telegrams
        """
        self.notification_service = notification_service

        logger.info("ComunicacionAgent initialized")

    async def execute(self, state: PEIState) -> PEIState:
        """
        Execute notification routing and sending.

        Extracts notification requests from state and routes to appropriate
        notification methods based on channel (EMAIL or TELEGRAM).

        Args:
            state: Current PEI state with notification requests

        Returns:
            Updated state with notification send results

        Raises:
            Exception: If notification service errors occur (wrapped and logged)
        """
        try:
            logger.info("ComunicacionAgent: Starting notification routing")

            # Extract notification requests from state
            notifications = state.get("notifications", [])

            if not notifications:
                logger.info("ComunicacionAgent: No notifications to send")
                state["agent_logs"].append(
                    {
                        "agent": "communication",
                        "action": "send_notifications",
                        "result": "success",
                        "notifications_sent": 0,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                return state

            logger.info(f"ComunicacionAgent: Processing {len(notifications)} notifications")

            # Send batch notifications
            result = await self.send_batch_notifications(notifications)

            # Update state with results
            state["validation_result"] = {
                "notifications_sent": result["sent"],
                "notifications_failed": result["failed"],
            }

            # Add to agent logs
            state["agent_logs"].append(
                {
                    "agent": "communication",
                    "action": "send_notifications",
                    "result": "success",
                    "notifications_sent": result["sent"],
                    "notifications_failed": result["failed"],
                    "timestamp": datetime.now().isoformat(),
                }
            )

            logger.info(
                f"ComunicacionAgent: Notifications sent - "
                f"Sent: {result['sent']}, Failed: {result['failed']}"
            )

            return state

        except Exception as e:
            logger.error(f"ComunicacionAgent: Fatal error during notification routing: {str(e)}")

            # Set error state
            state["error"] = f"Communication agent error: {str(e)}"

            # Add error to agent logs
            state["agent_logs"].append(
                {
                    "agent": "communication",
                    "action": "send_notifications",
                    "result": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )

            return state

    async def send_batch_notifications(
        self, notifications: List[Dict]
    ) -> Dict[str, int]:
        """
        Send batch of notifications with rate limiting.

        Processes multiple notifications with configurable delays between
        sends to avoid overwhelming the notification services.

        Args:
            notifications: List of notification dictionaries with:
                - recipient: Email or chat ID
                - channel: "EMAIL" or "TELEGRAM"
                - message: Message content
                - subject: Subject (for email)
                - priority: "LOW", "NORMAL", "HIGH", "URGENT"

        Returns:
            Dictionary with:
            - sent: Number of successfully sent notifications
            - failed: Number of failed notifications
            - details: List of send operation details
        """
        try:
            logger.info(f"ComunicacionAgent: Starting batch notification send")

            result = {
                "sent": 0,
                "failed": 0,
                "details": [],
            }

            # Rate limiting delays by priority
            rate_limits = {
                "URGENT": 0.1,  # 100ms
                "HIGH": 0.5,  # 500ms
                "NORMAL": 1.0,  # 1s
                "LOW": 2.0,  # 2s
            }

            # Group notifications by channel
            email_notifications = [n for n in notifications if n.get("channel") == "EMAIL"]
            telegram_notifications = [
                n for n in notifications if n.get("channel") == "TELEGRAM"
            ]

            # Send email notifications
            for notification in email_notifications:
                try:
                    await self.notification_service.send_email(
                        recipient=notification.get("recipient"),
                        subject=notification.get("subject", "PEI Platform Notification"),
                        body=notification.get("message", ""),
                        html=notification.get("html", True),
                    )

                    result["sent"] += 1
                    result["details"].append(
                        {
                            "recipient": notification.get("recipient"),
                            "channel": "EMAIL",
                            "status": "sent",
                        }
                    )

                    logger.info(
                        f"ComunicacionAgent: Email sent to {notification.get('recipient')}"
                    )

                    # Apply rate limiting
                    priority = notification.get("priority", "NORMAL")
                    delay = rate_limits.get(priority, 1.0)
                    await asyncio.sleep(delay)

                except Exception as email_error:
                    result["failed"] += 1
                    result["details"].append(
                        {
                            "recipient": notification.get("recipient"),
                            "channel": "EMAIL",
                            "status": "failed",
                            "error": str(email_error),
                        }
                    )

                    logger.error(
                        f"ComunicacionAgent: Failed to send email to "
                        f"{notification.get('recipient')}: {str(email_error)}"
                    )

            # Send telegram notifications
            for notification in telegram_notifications:
                try:
                    await self.notification_service.send_telegram(
                        chat_id=notification.get("recipient"),
                        message=notification.get("message", ""),
                    )

                    result["sent"] += 1
                    result["details"].append(
                        {
                            "recipient": notification.get("recipient"),
                            "channel": "TELEGRAM",
                            "status": "sent",
                        }
                    )

                    logger.info(
                        f"ComunicacionAgent: Telegram sent to {notification.get('recipient')}"
                    )

                    # Apply rate limiting
                    priority = notification.get("priority", "NORMAL")
                    delay = rate_limits.get(priority, 1.0)
                    await asyncio.sleep(delay)

                except Exception as telegram_error:
                    result["failed"] += 1
                    result["details"].append(
                        {
                            "recipient": notification.get("recipient"),
                            "channel": "TELEGRAM",
                            "status": "failed",
                            "error": str(telegram_error),
                        }
                    )

                    logger.error(
                        f"ComunicacionAgent: Failed to send telegram to "
                        f"{notification.get('recipient')}: {str(telegram_error)}"
                    )

            logger.info(
                f"ComunicacionAgent: Batch send complete - "
                f"Sent: {result['sent']}, Failed: {result['failed']}"
            )

            return result

        except Exception as e:
            logger.error(f"ComunicacionAgent: Error in batch notification send: {str(e)}")
            return {
                "sent": 0,
                "failed": len(notifications),
                "details": [{"error": str(e)}],
            }

    async def send_ot_update_notification(
        self, ot_id: int, ot_external_id: str, previous_status: str, new_status: str,
        project_type: str = None, db_session=None
    ) -> dict:
        """
        Send notification for OT status change.

        Determines recipients based on project type and status transition,
        formats message using templates, and sends via appropriate channels.

        Args:
            ot_id: OT database ID
            ot_external_id: External OT ID from API
            previous_status: Previous OT status
            new_status: New OT status
            project_type: OT project type (PUBLICO, PRIVADO, TERCERIZADO)
            db_session: SQLAlchemy database session for logging

        Returns:
            Dictionary with send results and details
        """
        try:
            logger.info(
                f"ComunicacionAgent: Sending OT update notification - "
                f"OT {ot_external_id}: {previous_status} → {new_status}"
            )

            result = {
                "notifications_sent": 0,
                "notifications_failed": 0,
                "details": [],
            }

            # Determine recipients based on status transition
            recipients = self._get_notification_recipients(
                new_status, project_type or PROJECT_TYPES["PRIVADO"]
            )

            logger.info(f"ComunicacionAgent: Recipients for {new_status}: {recipients}")

            # Format notification message
            message_data = {
                "ot_id": ot_external_id,
                "previous_status": previous_status,
                "new_status": new_status,
                "timestamp": datetime.now().isoformat(),
            }

            # Send to each recipient
            for recipient_info in recipients:
                try:
                    recipient = recipient_info["recipient"]
                    channel = recipient_info["channel"]
                    recipient_type = recipient_info["type"]

                    # Format message based on recipient type
                    message = self._format_status_change_message(
                        recipient_type, message_data
                    )

                    # Send notification
                    if channel == "EMAIL":
                        subject = f"Actualización OT: {ot_external_id} → {new_status}"

                        await self.notification_service.send_email(
                            recipient=recipient,
                            subject=subject,
                            body=message,
                            html=True,
                        )

                    elif channel == "TELEGRAM":
                        await self.notification_service.send_telegram(
                            chat_id=recipient,
                            message=message,
                        )

                    result["notifications_sent"] += 1
                    result["details"].append(
                        {
                            "recipient": recipient_type,
                            "channel": channel,
                            "status": "sent",
                        }
                    )

                    logger.info(
                        f"ComunicacionAgent: {channel} notification sent to {recipient_type}"
                    )

                except Exception as send_error:
                    result["notifications_failed"] += 1
                    result["details"].append(
                        {
                            "recipient": recipient_type,
                            "channel": channel,
                            "status": "failed",
                            "error": str(send_error),
                        }
                    )

                    logger.error(
                        f"ComunicacionAgent: Failed to send {channel} to {recipient_type}: "
                        f"{str(send_error)}"
                    )

            # Create log entry if db_session provided
            if db_session:
                try:
                    log_entry = LogAgente(
                        ot_id=ot_id,
                        agente_name="ComunicacionAgent",
                        accion="send_status_notification",
                        resultado="SUCCESS" if result["notifications_sent"] > 0 else "ERROR",
                        raw_llm_response=None,
                        metadata={
                            "external_id": ot_external_id,
                            "previous_status": previous_status,
                            "new_status": new_status,
                            "notifications_sent": result["notifications_sent"],
                            "notifications_failed": result["notifications_failed"],
                        },
                    )

                    db_session.add(log_entry)
                    db_session.commit()

                    logger.info(f"ComunicacionAgent: Log entry created for OT {ot_id}")

                except Exception as log_error:
                    logger.error(
                        f"ComunicacionAgent: Failed to create log entry: {str(log_error)}"
                    )

            logger.info(
                f"ComunicacionAgent: OT notification complete - "
                f"Sent: {result['notifications_sent']}, Failed: {result['notifications_failed']}"
            )

            return result

        except Exception as e:
            logger.error(
                f"ComunicacionAgent: Error in send_ot_update_notification: {str(e)}"
            )
            return {
                "notifications_sent": 0,
                "notifications_failed": 1,
                "details": [{"error": str(e)}],
            }

    def _get_notification_recipients(
        self, new_status: str, project_type: str
    ) -> List[Dict]:
        """
        Determine notification recipients based on status and project type.

        Args:
            new_status: New OT status
            project_type: OT project type

        Returns:
            List of recipient dicts with: recipient, channel, type
        """
        recipients = []

        # PM always gets notifications for critical status changes
        if new_status in [OT_STATUS["DETENIDA"], OT_STATUS["ANULADA"], OT_STATUS["FINALIZADA"]]:
            recipients.append(
                {
                    "recipient": "pm@telconet.ec",
                    "channel": "EMAIL",
                    "type": "PM",
                }
            )

        # Cliente gets notification for FINALIZADA
        if new_status == OT_STATUS["FINALIZADA"]:
            recipients.append(
                {
                    "recipient": "cliente@telconet.ec",
                    "channel": "EMAIL",
                    "type": "Cliente",
                }
            )

        # Técnico gets notification for ASIGNADO_TAREA
        if new_status == OT_STATUS["ASIGNADO_TAREA"]:
            recipients.append(
                {
                    "recipient": "tecnico@telconet.ec",
                    "channel": "EMAIL",
                    "type": "Técnico",
                }
            )

        # Coordinador OPU gets important notifications via Telegram
        if new_status in [OT_STATUS["ANULADA"], OT_STATUS["FINALIZADA"]]:
            try:
                from backend.config.settings import settings

                if settings.TELEGRAM_COORDINADOR_CHAT_ID:
                    recipients.append(
                        {
                            "recipient": str(settings.TELEGRAM_COORDINADOR_CHAT_ID),
                            "channel": "TELEGRAM",
                            "type": "Coordinador OPU",
                        }
                    )
            except Exception as config_error:
                logger.warning(
                    f"ComunicacionAgent: Could not load Telegram config: {str(config_error)}"
                )

        return recipients

    def _format_status_change_message(self, recipient_type: str, message_data: dict) -> str:
        """
        Format OT status change message based on recipient type.

        Args:
            recipient_type: Type of recipient (PM, Cliente, Técnico, etc.)
            message_data: Dictionary with ot_id, previous_status, new_status, timestamp

        Returns:
            Formatted message string in Spanish
        """
        ot_id = message_data.get("ot_id", "UNKNOWN")
        previous = message_data.get("previous_status", "DESCONOCIDO")
        new = message_data.get("new_status", "DESCONOCIDO")
        timestamp = message_data.get("timestamp", "")

        # Status translations to Spanish
        status_map = {
            "PREPLANIFICADA": "Preplanificada",
            "PLANIFICADA": "Planificada",
            "ASIGNADO_TAREA": "Asignada",
            "DETENIDA": "Detenida",
            "ANULADA": "Anulada",
            "FINALIZADA": "Finalizada",
        }

        previous_es = status_map.get(previous, previous)
        new_es = status_map.get(new, new)

        # Format based on recipient
        if recipient_type == "PM":
            return (
                f"Actualización de OT\n\n"
                f"OT: {ot_id}\n"
                f"Estado anterior: {previous_es}\n"
                f"Estado nuevo: {new_es}\n"
                f"Timestamp: {timestamp}\n\n"
                f"Por favor revise los detalles en el sistema PEI."
            )

        elif recipient_type == "Cliente":
            return (
                f"Su Orden de Trabajo ha sido finalizada\n\n"
                f"OT: {ot_id}\n"
                f"Estado: {new_es}\n"
                f"Fecha: {timestamp}\n\n"
                f"Gracias por utilizar nuestros servicios."
            )

        elif recipient_type == "Técnico":
            return (
                f"Nueva Orden de Trabajo Asignada\n\n"
                f"OT: {ot_id}\n"
                f"Estado: {new_es}\n"
                f"Timestamp: {timestamp}\n\n"
                f"Por favor inicie el trabajo según las instrucciones."
            )

        elif recipient_type == "Coordinador OPU":
            return (
                f"⚠️ Actualización OT: {ot_id}\n"
                f"{previous_es} → {new_es}"
            )

        else:
            return (
                f"Actualización de OT\n"
                f"OT: {ot_id}\n"
                f"Estado: {previous_es} → {new_es}"
            )

    async def get_communication_stats(self) -> dict:
        """
        Get statistics about communication activity.

        Returns:
            Dictionary with communication statistics
        """
        try:
            logger.info("ComunicacionAgent: Calculating communication statistics")

            # This would require database queries in a full implementation
            # For now, return placeholder structure

            return {
                "total_notifications_sent": 0,
                "notifications_by_channel": {
                    "EMAIL": 0,
                    "TELEGRAM": 0,
                },
                "notifications_by_type": {
                    "STATUS_CHANGE": 0,
                    "ALERT": 0,
                    "REMINDER": 0,
                },
                "failed_notifications": 0,
            }

        except Exception as e:
            logger.error(f"ComunicacionAgent: Error in get_communication_stats: {str(e)}")
            return {"error": str(e)}

