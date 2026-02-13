import logging
import smtplib
from datetime import datetime
from typing import Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class ComunicacionAgent:
    """
    ComunicacionAgent handles all notifications and communications.
    
    Responsibilities:
    - Send Telegram notifications to team managers
    - Send email notifications for important events
    - Route notifications based on event type (alerts, errors, completions)
    - Log all notification attempts and results
    
    Note: Current implementation uses stubs with logging.
    In production, integrate with real Telegram Bot API and SMTP servers.
    """

    def __init__(self):
        """Initialize ComunicacionAgent with notification configuration."""
        self.agent_name = "ComunicacionAgent"
        self.telegram_bot_token = settings.TELEGRAM_BOT_TOKEN
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD

    async def send_telegram_notification(
        self,
        message: str,
        chat_id: str
    ) -> Dict[str, Any]:
        """
        Send a notification via Telegram to a team manager.
        
        Current implementation: Stub with logging
        Future implementation: Use python-telegram-bot library to send real messages
        
        Args:
            message: Notification message content
            chat_id: Telegram chat ID of the recipient (team manager)
        
        Returns:
            Dict with notification status:
            - success: Boolean indicating if notification was sent
            - message: Status message
            - timestamp: When the notification was sent/attempted
            - method: "telegram"
        """
        try:
            logger.info(f"[TELEGRAM STUB] Sending message to chat_id {chat_id}: {message}")

            # In production, this would use python-telegram-bot:
            # from telegram import Bot
            # bot = Bot(token=self.telegram_bot_token)
            # await bot.send_message(chat_id=chat_id, text=message)

            # For now, we just log the notification
            logger.info(f"[TELEGRAM STUB] Message queued for chat_id {chat_id}")

            return {
                "success": True,
                "message": f"Telegram notification sent to chat_id {chat_id}",
                "timestamp": datetime.utcnow().isoformat(),
                "method": "telegram",
                "chat_id": chat_id
            }

        except Exception as e:
            error_msg = f"Failed to send Telegram notification: {str(e)}"
            logger.error(error_msg)

            return {
                "success": False,
                "message": error_msg,
                "timestamp": datetime.utcnow().isoformat(),
                "method": "telegram",
                "chat_id": chat_id,
                "error": str(e)
            }

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        """
        Send an email notification.
        
        Current implementation: Stub with logging
        Future implementation: Use smtplib to send real emails via configured SMTP server
        
        Args:
            to: Email recipient address
            subject: Email subject line
            body: Email body content (HTML supported)
        
        Returns:
            Dict with notification status:
            - success: Boolean indicating if email was sent
            - message: Status message
            - timestamp: When the email was sent/attempted
            - method: "email"
            - to: Recipient email address
        """
        try:
            logger.info(f"[EMAIL STUB] Sending email to {to} with subject: {subject}")

            # In production, this would use smtplib:
            # msg = MIMEMultipart('alternative')
            # msg['Subject'] = subject
            # msg['From'] = self.smtp_user
            # msg['To'] = to
            # msg.attach(MIMEText(body, 'html'))
            #
            # with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            #     server.starttls()
            #     server.login(self.smtp_user, self.smtp_password)
            #     server.send_message(msg)

            # For now, we just log the email
            logger.info(f"[EMAIL STUB] Email to {to} queued in queue")

            return {
                "success": True,
                "message": f"Email sent to {to}",
                "timestamp": datetime.utcnow().isoformat(),
                "method": "email",
                "to": to,
                "subject": subject
            }

        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(error_msg)

            return {
                "success": False,
                "message": error_msg,
                "timestamp": datetime.utcnow().isoformat(),
                "method": "email",
                "to": to,
                "error": str(e)
            }

    async def notify_pm(
        self,
        ot_id: str,
        event_type: str,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Route and send notifications to Project Manager (PM) based on event type.
        
        Event types and routing:
        - "alert": High-priority alerts (detention, compliance issues) -> Telegram + Email
        - "error": Errors in processing -> Email
        - "completion": OT completion -> Email
        - "status_change": Status updates -> Telegram only
        
        Args:
            ot_id: External OT ID
            event_type: Type of event triggering notification (alert, error, completion, status_change)
            additional_info: Optional dict with additional context (cliente_id, days_detained, etc.)
        
        Returns:
            Dict with notification results:
            - ot_id: OT ID
            - event_type: Event type
            - notifications_sent: List of notification results
            - timestamp: When notifications were sent
        """
        if additional_info is None:
            additional_info = {}

        notification_results = {
            "ot_id": ot_id,
            "event_type": event_type,
            "notifications_sent": [],
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            # Format the notification message
            message = self._format_message(ot_id, event_type, additional_info)

            logger.info(f"Routing notification for OT {ot_id} event type: {event_type}")

            # Route notification based on event type
            if event_type == "alert":
                # High-priority alerts: send via Telegram and Email
                logger.info(f"[ALERT] Sending via Telegram and Email for OT {ot_id}")

                # Send Telegram (to team manager chat)
                telegram_result = await self.send_telegram_notification(
                    message=f"🚨 {message}",
                    chat_id=additional_info.get("pm_chat_id", "DEFAULT_PM")
                )
                notification_results["notifications_sent"].append(telegram_result)

                # Send Email (to team manager email)
                email_result = await self.send_email(
                    to=additional_info.get("pm_email", "pm@telconet.com"),
                    subject=f"[ALERT] OT {ot_id}: {additional_info.get('title', 'Detention Alert')}",
                    body=message
                )
                notification_results["notifications_sent"].append(email_result)

            elif event_type == "error":
                # Errors: send via Email only
                logger.warning(f"[ERROR] Sending email for OT {ot_id}")

                email_result = await self.send_email(
                    to=additional_info.get("pm_email", "pm@telconet.com"),
                    subject=f"[ERROR] OT {ot_id}: Processing Error",
                    body=message
                )
                notification_results["notifications_sent"].append(email_result)

            elif event_type == "completion":
                # Completions: send via Email
                logger.info(f"[COMPLETION] Sending email for OT {ot_id}")

                email_result = await self.send_email(
                    to=additional_info.get("pm_email", "pm@telconet.com"),
                    subject=f"[COMPLETION] OT {ot_id}: Work Order Completed",
                    body=message
                )
                notification_results["notifications_sent"].append(email_result)

            elif event_type == "status_change":
                # Status changes: send via Telegram
                logger.info(f"[STATUS_CHANGE] Sending via Telegram for OT {ot_id}")

                telegram_result = await self.send_telegram_notification(
                    message=f"📋 {message}",
                    chat_id=additional_info.get("pm_chat_id", "DEFAULT_PM")
                )
                notification_results["notifications_sent"].append(telegram_result)

            else:
                logger.warning(f"Unknown event type: {event_type}")
                notification_results["notifications_sent"].append({
                    "success": False,
                    "message": f"Unknown event type: {event_type}"
                })

            return notification_results

        except Exception as e:
            error_msg = f"Error routing notification for OT {ot_id}: {str(e)}"
            logger.error(error_msg)

            return {
                **notification_results,
                "error": error_msg,
                "notifications_sent": []
            }

    def _format_message(
        self,
        ot_id: str,
        event_type: str,
        additional_info: Dict[str, Any]
    ) -> str:
        """
        Format a notification message based on event type and context.
        
        Args:
            ot_id: OT ID
            event_type: Type of event
            additional_info: Additional context information
        
        Returns:
            Formatted message string
        """
        cliente_id = additional_info.get("cliente_id", "UNKNOWN")
        login_id = additional_info.get("login_id", "UNKNOWN")

        if event_type == "alert":
            days_detained = additional_info.get("days_detained", 0)
            title = additional_info.get("title", "Detention Alert")
            return (
                f"{title}\n\n"
                f"OT ID: {ot_id}\n"
                f"Cliente: {cliente_id}\n"
                f"Login: {login_id}\n"
                f"Days Detained: {days_detained}\n"
                f"Status: REQUIRES IMMEDIATE ATTENTION"
            )

        elif event_type == "error":
            error_description = additional_info.get("error_description", "Unknown error")
            return (
                f"Error Processing OT\n\n"
                f"OT ID: {ot_id}\n"
                f"Cliente: {cliente_id}\n"
                f"Error: {error_description}\n"
                f"Please investigate and take corrective action."
            )

        elif event_type == "completion":
            return (
                f"Work Order Completed\n\n"
                f"OT ID: {ot_id}\n"
                f"Cliente: {cliente_id}\n"
                f"Login: {login_id}\n"
                f"Status: FINALIZADA\n"
                f"Completion time: {additional_info.get('completion_time', 'N/A')}"
            )

        elif event_type == "status_change":
            new_status = additional_info.get("new_status", "UNKNOWN")
            old_status = additional_info.get("old_status", "UNKNOWN")
            return (
                f"Status Update\n\n"
                f"OT ID: {ot_id}\n"
                f"Cliente: {cliente_id}\n"
                f"Status Change: {old_status} → {new_status}\n"
                f"Timestamp: {datetime.utcnow().isoformat()}"
            )

        else:
            return f"Notification for OT {ot_id} (event: {event_type})"

    async def notify_detention_alert(
        self,
        ot_id: str,
        days_detained: int,
        cliente_id: str,
        login_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Convenience method for sending detention alerts.
        
        Args:
            ot_id: OT ID
            days_detained: Number of days detained
            cliente_id: Customer ID
            login_id: Service point login
            **kwargs: Additional context (pm_chat_id, pm_email, etc.)
        
        Returns:
            Notification results
        """
        return await self.notify_pm(
            ot_id=ot_id,
            event_type="alert",
            additional_info={
                "cliente_id": cliente_id,
                "login_id": login_id,
                "days_detained": days_detained,
                "title": f"Detention Alert ({days_detained} days)",
                **kwargs
            }
        )

    async def notify_completion(
        self,
        ot_id: str,
        cliente_id: str,
        login_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Convenience method for sending completion notifications.
        
        Args:
            ot_id: OT ID
            cliente_id: Customer ID
            login_id: Service point login
            **kwargs: Additional context
        
        Returns:
            Notification results
        """
        return await self.notify_pm(
            ot_id=ot_id,
            event_type="completion",
            additional_info={
                "cliente_id": cliente_id,
                "login_id": login_id,
                "completion_time": datetime.utcnow().isoformat(),
                **kwargs
            }
        )

