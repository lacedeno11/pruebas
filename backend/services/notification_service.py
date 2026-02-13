"""Notification Service for email and Telegram communications"""

import asyncio
import logging
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib
from telegram import Bot
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications via email and Telegram"""

    def __init__(self):
        """Initialize the notification service"""
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.email_from = settings.EMAIL_FROM
        self.telegram_token = settings.TELEGRAM_BOT_TOKEN
        self.telegram_bot = Bot(token=self.telegram_token)

    async def send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        html: bool = True,
    ) -> bool:
        """
        Send email notification.

        Args:
            recipient: Email address to send to
            subject: Email subject
            body: Email body content
            html: Whether body is HTML formatted

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Sending email to {recipient} with subject: {subject}")

            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.email_from
            message["To"] = recipient

            # Attach body
            mime_type = "html" if html else "plain"
            message.attach(MIMEText(body, mime_type))

            # Send via SMTP
            async with aiosmtplib.SMTP(
                hostname=self.smtp_host, port=self.smtp_port
            ) as smtp:
                await smtp.login(self.smtp_user, self.smtp_password)
                await smtp.sendmail(
                    self.email_from,
                    recipient,
                    message.as_string(),
                )

            logger.info(f"Email sent successfully to {recipient}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {str(e)}")
            return False

    async def send_telegram(
        self,
        chat_id: str,
        message: str,
    ) -> bool:
        """
        Send Telegram notification.

        Args:
            chat_id: Telegram chat ID
            message: Message to send

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(
                f"Sending Telegram message to chat {chat_id}"
            )

            await self.telegram_bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML",
            )

            logger.info(
                f"Telegram message sent successfully to chat {chat_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to send Telegram message to {chat_id}: {str(e)}"
            )
            return False

    def get_alert_template(
        self,
        alert_type: str,
        ot_id: str,
    ) -> dict:
        """
        Get email template for alert type.

        Args:
            alert_type: Type of alert (WARNING_20, WARNING_25, FINAL_WARNING, AUTO_CANCELLED, INACTIVITY_48H)
            ot_id: OT ID for the alert

        Returns:
            Dictionary with 'subject' and 'body' keys
        """
        templates = {
            "WARNING_20": {
                "subject": f"⚠️ Alerta: OT {ot_id} detenida 20 días",
                "body": self._get_html_template_20(ot_id),
            },
            "WARNING_25": {
                "subject": f"⚠️ Alerta Urgente: OT {ot_id} detenida 25 días",
                "body": self._get_html_template_25(ot_id),
            },
            "FINAL_WARNING": {
                "subject": f"🔴 Alerta Final: OT {ot_id} detenida 29 días",
                "body": self._get_html_template_final(ot_id),
            },
            "AUTO_CANCELLED": {
                "subject": f"❌ OT {ot_id} anulada automáticamente",
                "body": self._get_html_template_cancelled(ot_id),
            },
            "INACTIVITY_48H": {
                "subject": f"🔔 Acción Requerida: OT {ot_id} sin planificar",
                "body": self._get_html_template_inactivity_48h(ot_id),
            },
        }

        return templates.get(
            alert_type,
            {
                "subject": f"Notificación: OT {ot_id}",
                "body": f"<p>Notificación de sistema para OT {ot_id}</p>",
            },
        )

    def _get_html_template_20(self, ot_id: str) -> str:
        """Get HTML template for WARNING_20 alert"""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="border: 2px solid #FFA500; padding: 20px; border-radius: 5px; background-color: #fff8f0;">
                    <h2 style="color: #FFA500;">⚠️ Alerta: OT Detenida 20 Días</h2>
                    <p>La orden de trabajo <strong>{ot_id}</strong> ha permanecido en estado DETENIDA durante <strong>20 días</strong>.</p>
                    <p style="background-color: #fff3cd; padding: 10px; border-left: 4px solid #FFA500; margin: 15px 0;">
                        <strong>Acción requerida:</strong> Por favor reactivar o finalizar esta OT.
                    </p>
                    <p><strong>Próximas alertas:</strong></p>
                    <ul>
                        <li>Día 25: Segunda alerta urgente</li>
                        <li>Día 29: Alerta final - Se anulará al día 30</li>
                    </ul>
                    <p style="color: #666; font-size: 12px; margin-top: 20px;">
                        Sistema PEI - Gestión de Órdenes de Trabajo
                    </p>
                </div>
            </body>
        </html>
        """

    def _get_html_template_25(self, ot_id: str) -> str:
        """Get HTML template for WARNING_25 alert"""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="border: 2px solid #FF6B6B; padding: 20px; border-radius: 5px; background-color: #ffe0e0;">
                    <h2 style="color: #FF6B6B;">⚠️ Alerta Urgente: OT Detenida 25 Días</h2>
                    <p>La orden de trabajo <strong>{ot_id}</strong> ha permanecido en estado DETENIDA durante <strong>25 días</strong>.</p>
                    <p style="background-color: #ffebee; padding: 10px; border-left: 4px solid #FF6B6B; margin: 15px 0;">
                        <strong>⏰ Tiempo restante:</strong> 5 días antes de anulación automática
                    </p>
                    <p><strong>Acciones inmediatas necesarias:</strong></p>
                    <ul>
                        <li>Reactivar la OT con un motivo válido</li>
                        <li>O finalizar la OT si ya está completada</li>
                        <li>O anularla manualmente si no es viable</li>
                    </ul>
                    <p style="color: #666; font-size: 12px; margin-top: 20px;">
                        Sistema PEI - Gestión de Órdenes de Trabajo
                    </p>
                </div>
            </body>
        </html>
        """

    def _get_html_template_final(self, ot_id: str) -> str:
        """Get HTML template for FINAL_WARNING alert"""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="border: 2px solid #DC143C; padding: 20px; border-radius: 5px; background-color: #ffe0e0;">
                    <h2 style="color: #DC143C;">🔴 Alerta Final: OT Detenida 29 Días</h2>
                    <p>La orden de trabajo <strong>{ot_id}</strong> ha permanecido en estado DETENIDA durante <strong>29 días</strong>.</p>
                    <p style="background-color: #ffcccc; padding: 15px; border-left: 4px solid #DC143C; margin: 15px 0; font-weight: bold;">
                        ⏰ ÚLTIMA OPORTUNIDAD: La OT será anulada automáticamente MAÑANA si no se toma acción.
                    </p>
                    <p><strong>Acciones requeridas AHORA:</strong></p>
                    <ul>
                        <li>Reactivar la OT urgentemente</li>
                        <li>O finalizar la OT</li>
                        <li>O anularla manualmente</li>
                    </ul>
                    <p style="color: #666; font-size: 12px; margin-top: 20px;">
                        Sistema PEI - Gestión de Órdenes de Trabajo
                    </p>
                </div>
            </body>
        </html>
        """

    def _get_html_template_cancelled(self, ot_id: str) -> str:
        """Get HTML template for AUTO_CANCELLED notification"""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="border: 2px solid #DC143C; padding: 20px; border-radius: 5px; background-color: #ffe0e0;">
                    <h2 style="color: #DC143C;">❌ OT Anulada Automáticamente</h2>
                    <p>La orden de trabajo <strong>{ot_id}</strong> ha sido <strong>anulada automáticamente</strong> por el sistema.</p>
                    <p style="background-color: #ffcccc; padding: 10px; border-left: 4px solid #DC143C; margin: 15px 0;">
                        <strong>Motivo:</strong> Ha permanecido en estado DETENIDA por más de 30 días.
                    </p>
                    <p><strong>Próximas acciones:</strong></p>
                    <ul>
                        <li>Revisar el estado de la OT en el sistema</li>
                        <li>Si es necesario reactivar, contactar al administrador</li>
                        <li>Crear una nueva OT si se requieren trabajos adicionales</li>
                    </ul>
                    <p style="color: #666; font-size: 12px; margin-top: 20px;">
                        Sistema PEI - Gestión de Órdenes de Trabajo
                    </p>
                </div>
            </body>
        </html>
        """

    def _get_html_template_inactivity_48h(self, ot_id: str) -> str:
        """Get HTML template for INACTIVITY_48H alert"""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="border: 2px solid #4169E1; padding: 20px; border-radius: 5px; background-color: #e6f2ff;">
                    <h2 style="color: #4169E1;">🔔 Acción Requerida: OT Sin Planificar</h2>
                    <p>La orden de trabajo <strong>{ot_id}</strong> ha estado en estado PREPLANIFICADA durante <strong>más de 48 horas</strong>.</p>
                    <p style="background-color: #cce5ff; padding: 10px; border-left: 4px solid #4169E1; margin: 15px 0;">
                        <strong>Acción requerida:</strong> Por favor planificar o asignar esta OT a una cuadrilla.
                    </p>
                    <p><strong>Pasos sugeridos:</strong></p>
                    <ul>
                        <li>Revisar los detalles de la OT</li>
                        <li>Asignar a una cuadrilla disponible</li>
                        <li>O indicar el motivo del retraso en la planificación</li>
                    </ul>
                    <p style="color: #666; font-size: 12px; margin-top: 20px;">
                        Sistema PEI - Gestión de Órdenes de Trabajo
                    </p>
                </div>
            </body>
        </html>
        """

    async def send_batch_notifications(
        self,
        notifications: list,
    ) -> dict:
        """
        Send multiple notifications with rate limiting.

        Args:
            notifications: List of notification dicts with keys:
                - type: 'email' or 'telegram'
                - recipient/chat_id: recipient address
                - subject: (for email) subject line
                - body: message content

        Returns:
            Dictionary with success/failed counts
        """
        logger.info(f"Sending batch of {len(notifications)} notifications")

        results = {
            "total": len(notifications),
            "successful": 0,
            "failed": 0,
        }

        for notification in notifications:
            try:
                if notification.get("type") == "email":
                    success = await self.send_email(
                        recipient=notification.get("recipient"),
                        subject=notification.get("subject"),
                        body=notification.get("body"),
                    )
                elif notification.get("type") == "telegram":
                    success = await self.send_telegram(
                        chat_id=notification.get("chat_id"),
                        message=notification.get("body"),
                    )
                else:
                    success = False

                if success:
                    results["successful"] += 1
                else:
                    results["failed"] += 1

                # Rate limiting: small delay between notifications
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(
                    f"Error sending notification: {str(e)}"
                )
                results["failed"] += 1

        logger.info(
            f"Batch notification complete: "
            f"{results['successful']} successful, {results['failed']} failed"
        )
        return results

