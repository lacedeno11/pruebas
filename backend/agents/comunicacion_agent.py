"""
ComunicacionAgent - Notification and communication orchestration agent.
Formats and sends notifications via Telegram and Email channels.
"""

import logging
from typing import Any, Dict, Optional

from backend.config import Settings
from backend.utils.logging_helper import log_agent_action

logger = logging.getLogger(__name__)


# Predefined message templates for common scenarios
MESSAGE_TEMPLATES = {
    "OT_ASSIGNED": {
        "telegram": "✅ OT {ot_external_id} asignada a tu cuadrilla. Coordenadas: {lat}, {long}",
        "email": "<h2>Asignación de Orden de Trabajo</h2><p>Se ha asignado la OT {ot_external_id} a tu cuadrilla. Por favor revisa los detalles en la plataforma.</p>",
    },
    "OT_DELAYED": {
        "telegram": "⏰ OT {ot_external_id} en demora. Estado: {status}. Tiempo en estado: {days} días.",
        "email": "<h2>Orden de Trabajo en Demora</h2><p>La OT {ot_external_id} ha estado en estado {status} por {days} días.</p>",
    },
    "OT_CANCELLED": {
        "telegram": "❌ OT {ot_external_id} ha sido cancelada después de {days} días en DETENIDA.",
        "email": "<h2>Cancelación de Orden de Trabajo</h2><p>La OT {ot_external_id} ha sido cancelada debido a inactividad prolongada ({days} días).</p>",
    },
    "ALERT_INACTIVITY": {
        "telegram": "⚠️ ALERTA: OT {ot_external_id} lleva {days} días en DETENIDA. Acción requerida.",
        "email": "<h2>Alerta de Inactividad</h2><p>La OT {ot_external_id} ha estado inactiva por {days} días. Se requiere acción inmediata.</p>",
    },
}


class ComunicacionAgent:
    """
    ComunicacionAgent - Orchestrates notifications and communications.
    
    Responsibilities:
    1. Format messages appropriately for each channel
    2. Send notifications via Telegram and Email
    3. Use predefined message templates for consistency
    4. Log all notification attempts
    5. Handle failures gracefully
    """

    def __init__(
        self,
        llm: Optional[object] = None,
        settings: Optional[Settings] = None,
    ):
        """
        Initialize ComunicacionAgent.

        Args:
            llm: OpenAI LLM instance (for message formatting)
            settings: Application settings (for channel configuration)
        """
        self.llm = llm
        self.settings = settings

    async def send_notification(
        self,
        recipient_type: str,
        message: str,
        channel: str,
        recipient_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send notification via specified channel.
        
        Args:
            recipient_type: "crew", "customer", "pm" (project manager)
            message: Message content
            channel: "telegram" or "email"
            recipient_id: Optional recipient identifier
            
        Returns:
            Dict with {success: bool, channel: str, recipient_type: str, message_id: str}
        """
        logger.info(
            f"ComunicacionAgent: Sending {channel} notification to {recipient_type}"
        )
        
        try:
            # Format message for channel
            formatted_message = await self.format_message_for_channel(message, channel)
            
            # Send via appropriate channel
            if channel == "telegram":
                success = await self.send_telegram_notification(
                    recipient_type, formatted_message
                )
            elif channel == "email":
                success = await self.send_email_notification(
                    recipient_type, formatted_message
                )
            else:
                logger.error(f"ComunicacionAgent: Unknown channel {channel}")
                return {
                    "success": False,
                    "channel": channel,
                    "recipient_type": recipient_type,
                    "error": f"Unknown channel: {channel}",
                }

            return {
                "success": success,
                "channel": channel,
                "recipient_type": recipient_type,
                "message_id": recipient_id or "unknown",
            }

        except Exception as e:
            logger.error(
                f"ComunicacionAgent: Error sending {channel} notification: {str(e)}"
            )
            return {
                "success": False,
                "channel": channel,
                "recipient_type": recipient_type,
                "error": str(e),
            }

    async def format_message_for_channel(
        self, message: str, channel: str
    ) -> str:
        """
        Format message appropriately for channel.
        
        Telegram: Concise, emoji, short sentences
        Email: Formal, HTML-formatted, detailed
        
        Args:
            message: Original message
            channel: Target channel ("telegram" or "email")
            
        Returns:
            Formatted message
        """
        logger.debug(f"ComunicacionAgent: Formatting message for {channel}")
        
        try:
            # TODO: Implement LLM-based formatting via ChatOpenAI
            # For now, use simple formatting rules
            
            if channel == "telegram":
                # Concise format for Telegram
                formatted = message[:280]  # Telegram limit
                if len(message) > 280:
                    formatted += "..."
                return formatted
            
            elif channel == "email":
                # HTML format for Email
                return f"""
                <html>
                    <body>
                        <p>{message}</p>
                        <hr>
                        <p><small>Este mensaje fue generado automáticamente por el Sistema PEI.</small></p>
                    </body>
                </html>
                """
            
            return message

        except Exception as e:
            logger.error(f"ComunicacionAgent: Error formatting message: {str(e)}")
            return message

    def get_message_template(
        self, template_name: str, channel: str, **kwargs
    ) -> str:
        """
        Get and format predefined message template.
        
        Args:
            template_name: Template name (OT_ASSIGNED, OT_DELAYED, etc.)
            channel: "telegram" or "email"
            **kwargs: Variables to substitute in template
            
        Returns:
            Formatted template message
        """
        try:
            if template_name not in MESSAGE_TEMPLATES:
                logger.warning(f"ComunicacionAgent: Unknown template {template_name}")
                return f"Notification: {template_name}"
            
            template = MESSAGE_TEMPLATES[template_name].get(channel, "")
            
            if not template:
                logger.warning(
                    f"ComunicacionAgent: No template for {template_name} on {channel}"
                )
                return f"Notification: {template_name}"
            
            # Substitute variables in template
            try:
                message = template.format(**kwargs)
                return message
            except KeyError as e:
                logger.error(
                    f"ComunicacionAgent: Missing template variable {e} for {template_name}"
                )
                return template

        except Exception as e:
            logger.error(f"ComunicacionAgent: Error getting template: {str(e)}")
            return f"Notification: {template_name}"

    # Helper methods
    async def send_telegram_notification(
        self, recipient_type: str, message: str
    ) -> bool:
        """Send Telegram notification."""
        logger.info(
            f"ComunicacionAgent: Telegram notification to {recipient_type}: {message[:50]}..."
        )
        # TODO: Implement python-telegram-bot integration
        # For now, log and return success
        return True

    async def send_email_notification(
        self, recipient_type: str, message: str
    ) -> bool:
        """Send Email notification."""
        logger.info(
            f"ComunicacionAgent: Email notification to {recipient_type}: {message[:50]}..."
        )
        # TODO: Implement smtplib email integration
        # For now, log and return success
        return True

