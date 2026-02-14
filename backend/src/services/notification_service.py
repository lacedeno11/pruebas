"""
Notification Service for PEI Platform.

This module handles sending notifications to technical teams via Telegram and to PMs/Clients
via Email. It includes retry logic, error handling, and integration with agent logs for
tracking communication history.
"""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Optional

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Types of notifications that can be sent."""

    ALERT = "alert"
    STATUS_CHANGE = "status_change"
    GEO_ERROR = "geo_error"
    GOVERNANCE_ALERT = "governance_alert"
    DETENTION_WARNING = "detention_warning"
    DOCUMENT_MISSING = "document_missing"


class Priority(str, Enum):
    """Priority levels for notifications."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NotificationResult:
    """Result of a notification attempt."""

    def __init__(
        self,
        success: bool,
        channel: str,
        message: str,
        timestamp: datetime = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.channel = channel
        self.message = message
        self.timestamp = timestamp or datetime.utcnow()
        self.error = error

    def to_dict(self) -> dict:
        """Convert result to dictionary for logging."""
        return {
            "success": self.success,
            "channel": self.channel,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
        }


class NotificationService:
    """
    Service for sending notifications via multiple channels.

    Supports:
    - Telegram: For operational alerts to technical teams
    - Email: For status changes and documentation issues to PMs/Clients
    """

    # Telegram API endpoint
    TELEGRAM_API_URL = "https://api.telegram.org"

    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1.0  # seconds
    RETRY_BACKOFF = 2.0  # exponential backoff multiplier

    def __init__(self):
        """Initialize the notification service."""
        self.settings = settings
        self.http_client = None

    async def __aenter__(self):
        """Context manager entry."""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.http_client:
            await self.http_client.aclose()

    async def send_telegram(
        self,
        message: str,
        chat_id: str,
        priority: str = "NORMAL",
    ) -> NotificationResult:
        """
        Send a message via Telegram to technical teams.

        Args:
            message (str): Message text to send
            chat_id (str): Telegram chat ID (individual or group)
            priority (str): Priority level (LOW, NORMAL, HIGH, CRITICAL)

        Returns:
            NotificationResult: Result of the send attempt
        """
        if settings.is_mock_mode:
            logger.info(
                f"[MOCK] Telegram message to {chat_id}: {message[:50]}... (Priority: {priority})"
            )
            return NotificationResult(
                success=True,
                channel="telegram",
                message=message,
            )

        if not settings.telegram_bot_token:
            logger.warning("Telegram bot token not configured, skipping Telegram notification")
            return NotificationResult(
                success=False,
                channel="telegram",
                message=message,
                error="Telegram bot token not configured",
            )

        # Add priority indicator to message
        priority_emoji = {
            "LOW": "ℹ️",
            "NORMAL": "📬",
            "HIGH": "⚠️",
            "CRITICAL": "🚨",
        }.get(priority, "📬")

        full_message = f"{priority_emoji} [{priority}] {message}"

        # Retry logic with exponential backoff
        delay = self.INITIAL_RETRY_DELAY
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                if not self.http_client:
                    self.http_client = httpx.AsyncClient(timeout=30.0)

                url = f"{self.TELEGRAM_API_URL}/bot{settings.telegram_bot_token}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": full_message,
                    "parse_mode": "HTML",
                }

                response = await self.http_client.post(url, json=payload)

                if response.status_code == 200:
                    logger.info(f"Telegram message sent successfully to {chat_id}")
                    return NotificationResult(
                        success=True,
                        channel="telegram",
                        message=message,
                    )
                else:
                    last_error = f"HTTP {response.status_code}: {response.text}"

            except asyncio.TimeoutError:
                last_error = "Request timeout"
            except httpx.RequestError as e:
                last_error = f"Request error: {str(e)}"
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"

            # Retry logic
            if attempt < self.MAX_RETRIES - 1:
                logger.warning(
                    f"Telegram send attempt {attempt + 1} failed: {last_error}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
                delay *= self.RETRY_BACKOFF
            else:
                logger.error(f"Telegram send failed after {self.MAX_RETRIES} attempts: {last_error}")

        return NotificationResult(
            success=False,
            channel="telegram",
            message=message,
            error=last_error or "Unknown error",
        )

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        priority: str = "NORMAL",
        html: bool = False,
    ) -> NotificationResult:
        """
        Send an email notification to a PM or client.

        Args:
            to (str): Recipient email address
            subject (str): Email subject
            body (str): Email body (plain text or HTML)
            priority (str): Priority level (affects X-Priority header)
            html (bool): Whether body is HTML (default: False)

        Returns:
            NotificationResult: Result of the send attempt
        """
        if settings.is_mock_mode:
            logger.info(f"[MOCK] Email to {to}: Subject='{subject}' (Priority: {priority})")
            return NotificationResult(
                success=True,
                channel="email",
                message=f"Email to {to}",
            )

        if not settings.smtp_host or not settings.smtp_port:
            logger.warning("SMTP not configured, skipping email notification")
            return NotificationResult(
                success=False,
                channel="email",
                message=f"Email to {to}",
                error="SMTP not configured",
            )

        try:
            # Import aiosmtplib for async SMTP operations
            try:
                import aiosmtplib
            except ImportError:
                logger.warning("aiosmtplib not installed, cannot send email")
                return NotificationResult(
                    success=False,
                    channel="email",
                    message=f"Email to {to}",
                    error="aiosmtplib not installed",
                )

            # Build email headers
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.smtp_user or "noreply@pei.telconet.ec"
            msg["To"] = to

            # Set priority header
            priority_map = {"LOW": "5", "NORMAL": "3", "HIGH": "2", "CRITICAL": "1"}
            msg["X-Priority"] = priority_map.get(priority, "3")

            # Attach body
            msg.attach(MIMEText(body, "html" if html else "plain"))

            # Retry logic
            delay = self.INITIAL_RETRY_DELAY
            last_error = None

            for attempt in range(self.MAX_RETRIES):
                try:
                    async with aiosmtplib.SMTP(
                        hostname=settings.smtp_host,
                        port=settings.smtp_port,
                        timeout=30,
                    ) as smtp:
                        # Start TLS if not on port 25
                        if settings.smtp_port != 25:
                            await smtp.starttls()

                        # Login if credentials provided
                        if settings.smtp_user and settings.smtp_password:
                            await smtp.login(settings.smtp_user, settings.smtp_password)

                        # Send email
                        await smtp.send_message(msg)

                    logger.info(f"Email sent successfully to {to}")
                    return NotificationResult(
                        success=True,
                        channel="email",
                        message=f"Email to {to}",
                    )

                except asyncio.TimeoutError:
                    last_error = "SMTP timeout"
                except Exception as e:
                    last_error = f"SMTP error: {str(e)}"

                # Retry logic
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(
                        f"Email send attempt {attempt + 1} failed: {last_error}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= self.RETRY_BACKOFF

        except Exception as e:
            logger.error(f"Email send failed: {str(e)}")
            return NotificationResult(
                success=False,
                channel="email",
                message=f"Email to {to}",
                error=str(e),
            )

        return NotificationResult(
            success=False,
            channel="email",
            message=f"Email to {to}",
            error=last_error or "Unknown error",
        )

    async def send_alert(
        self,
        alert_type: str,
        ot_id: Optional[int],
        recipients: list,
        message: str,
        priority: str = "NORMAL",
    ) -> dict:
        """
        Send an alert through appropriate channels based on alert type.

        Routes alerts to different channels:
        - ALERT: Telegram to technical teams
        - STATUS_CHANGE: Email to PM
        - GEO_ERROR: Email to PM with details
        - GOVERNANCE_ALERT: Email + Telegram based on priority
        - DETENTION_WARNING: Telegram to coordinators
        - DOCUMENT_MISSING: Email to PM

        Args:
            alert_type (str): Type of alert (see NotificationType)
            ot_id (Optional[int]): OT ID if applicable
            recipients (list): List of recipient identifiers (chat IDs or emails)
            message (str): Alert message
            priority (str): Priority level

        Returns:
            dict: Summary of notification results
        """
        results = {
            "alert_type": alert_type,
            "ot_id": ot_id,
            "timestamp": datetime.utcnow().isoformat(),
            "results": [],
        }

        if alert_type == NotificationType.ALERT:
            # Operational alerts go to Telegram
            for recipient in recipients:
                result = await self.send_telegram(message, recipient, priority)
                results["results"].append(result.to_dict())

        elif alert_type == NotificationType.STATUS_CHANGE:
            # Status changes go via Email
            for recipient in recipients:
                formatted_message = self._format_status_change_email(message, ot_id)
                result = await self.send_email(
                    recipient,
                    f"OT #{ot_id} Status Change",
                    formatted_message,
                    priority,
                    html=True,
                )
                results["results"].append(result.to_dict())

        elif alert_type == NotificationType.GEO_ERROR:
            # Geographic errors go via Email with details
            for recipient in recipients:
                formatted_message = self._format_geo_error_notification(message, ot_id)
                result = await self.send_email(
                    recipient,
                    f"GEO ERROR: OT #{ot_id} Missing Coordinates",
                    formatted_message,
                    "HIGH",
                    html=True,
                )
                results["results"].append(result.to_dict())

        elif alert_type == NotificationType.GOVERNANCE_ALERT:
            # Governance alerts may use both channels
            for recipient in recipients:
                if priority == "CRITICAL":
                    # Critical alerts via both channels
                    telegram_result = await self.send_telegram(message, recipient, priority)
                    results["results"].append({"channel": "telegram", **telegram_result.to_dict()})
                else:
                    # Normal governance via email
                    result = await self.send_email(
                        recipient,
                        "Governance Alert",
                        self._format_governance_email(message),
                        priority,
                        html=True,
                    )
                    results["results"].append(result.to_dict())

        elif alert_type == NotificationType.DETENTION_WARNING:
            # Detention warnings to coordinators via Telegram
            for recipient in recipients:
                result = await self.send_telegram(message, recipient, priority)
                results["results"].append(result.to_dict())

        elif alert_type == NotificationType.DOCUMENT_MISSING:
            # Missing documents alert to PM via Email
            for recipient in recipients:
                formatted_message = self._format_document_missing_email(message, ot_id)
                result = await self.send_email(
                    recipient,
                    f"Missing Documents: OT #{ot_id}",
                    formatted_message,
                    "HIGH",
                    html=True,
                )
                results["results"].append(result.to_dict())

        return results

    def _format_alert_message(self, base_message: str, ot_id: Optional[int] = None) -> str:
        """Format alert message with OT details."""
        if ot_id:
            return f"🔔 Alert OT #{ot_id}: {base_message}"
        return f"🔔 {base_message}"

    def _format_status_change_email(self, message: str, ot_id: Optional[int]) -> str:
        """Format status change notification as HTML email."""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>OT Status Change Notification</h2>
                <p>OT ID: <strong>#{ot_id}</strong></p>
                <p>{message}</p>
                <p style="color: #666; font-size: 12px;">
                    This is an automated notification from PEI Platform.
                </p>
            </body>
        </html>
        """

    def _format_geo_error_notification(self, message: str, ot_id: Optional[int]) -> str:
        """Format geo error notification as HTML email."""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color: #d32f2f;">Geographic Error - Manual Intervention Required</h2>
                <p>OT ID: <strong>#{ot_id}</strong></p>
                <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 12px;">
                    <p><strong>Issue:</strong> {message}</p>
                    <p><strong>Action Required:</strong> Please verify and update the geographic coordinates for this OT.</p>
                </div>
                <p style="color: #666; font-size: 12px;">
                    Geographic coordinates are critical for the Planificación Agent's proximity calculations.
                </p>
            </body>
        </html>
        """

    def _format_governance_email(self, message: str) -> str:
        """Format governance alert as HTML email."""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>Governance Alert</h2>
                <div style="background-color: #f0f4f8; border-left: 4px solid #1976d2; padding: 12px;">
                    <p>{message}</p>
                </div>
                <p style="color: #666; font-size: 12px;">
                    This is a governance-related notification. Please review and take appropriate action.
                </p>
            </body>
        </html>
        """

    def _format_document_missing_email(self, message: str, ot_id: Optional[int]) -> str:
        """Format document missing notification as HTML email."""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color: #d32f2f;">Missing Required Documents</h2>
                <p>OT ID: <strong>#{ot_id}</strong></p>
                <div style="background-color: #ffebee; border-left: 4px solid #d32f2f; padding: 12px;">
                    <p>{message}</p>
                    <p><strong>Required:</strong> PUBLICO projects require 29 documents in TelcoDrive before completion.</p>
                </div>
                <p style="color: #666; font-size: 12px;">
                    Please upload the required documents and verify in TelcoDrive.
                </p>
            </body>
        </html>
        """


# Convenience function for getting a notification service instance
async def get_notification_service() -> NotificationService:
    """
    Get a notification service instance.

    Usage:
        async with await get_notification_service() as notifier:
            await notifier.send_telegram("Hello", "123456")

    Returns:
        NotificationService: Configured notification service instance
    """
    service = NotificationService()
    await service.__aenter__()
    return service

