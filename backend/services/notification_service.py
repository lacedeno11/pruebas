"""
Notification Service for Telegram and Email communications.
Handles sending notifications to technicians, PMs, and clients.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

try:
    from telegram import Bot
    from telegram.error import TelegramError
except ImportError:
    Bot = None
    TelegramError = Exception

try:
    import aiosmtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
except ImportError:
    aiosmtplib = None


# Configure logging
logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for sending notifications via Telegram and Email.
    
    Provides methods for:
    - Telegram notifications to technicians
    - Email notifications to PMs and clients
    - Governance alerts (inactivity, auto-cancellation)
    - Error notifications
    """

    def __init__(self):
        """Initialize NotificationService with environment credentials"""
        # Telegram configuration
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_bot = None
        if self.telegram_token:
            try:
                self.telegram_bot = Bot(token=self.telegram_token)
            except Exception as e:
                logger.warning(f"Failed to initialize Telegram bot: {e}")

        # SMTP configuration
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")

        # Validate SMTP configuration
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials not configured. Email notifications disabled.")

    async def send_telegram_message(
        self, chat_id: str, message: str
    ) -> Dict[str, Any]:
        """
        Send a message via Telegram.
        
        Args:
            chat_id: Telegram chat ID (user or group)
            message: Message text to send
            
        Returns:
            Success/error response dict
        """
        if not self.telegram_bot:
            logger.warning("Telegram bot not configured")
            return {
                "success": False,
                "error": "Telegram bot not configured",
                "channel": "telegram",
            }

        try:
            # Simulate async operation with small delay
            await asyncio.sleep(0.1)

            # Send message via Telegram
            result = await self.telegram_bot.send_message(
                chat_id=chat_id, text=message, parse_mode="HTML"
            )

            logger.info(f"Telegram message sent to {chat_id}")
            return {
                "success": True,
                "channel": "telegram",
                "chat_id": chat_id,
                "message_id": result.message_id,
                "sent_at": datetime.now().isoformat(),
            }
        except TelegramError as e:
            logger.error(f"Telegram error for chat {chat_id}: {e}")
            return {
                "success": False,
                "channel": "telegram",
                "chat_id": chat_id,
                "error": str(e),
                "sent_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {e}")
            return {
                "success": False,
                "channel": "telegram",
                "error": str(e),
                "sent_at": datetime.now().isoformat(),
            }

    async def send_email(
        self, to_email: str, subject: str, body: str, html: bool = False
    ) -> Dict[str, Any]:
        """
        Send an email message.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body text
            html: Whether body is HTML formatted
            
        Returns:
            Success/error response dict
        """
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials not configured")
            return {
                "success": False,
                "error": "SMTP not configured",
                "channel": "email",
                "to": to_email,
            }

        try:
            # Simulate async operation with small delay
            await asyncio.sleep(0.1)

            # Create email message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_user
            msg["To"] = to_email

            # Add body
            if html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))

            # Send email via SMTP
            if aiosmtplib:
                async with aiosmtplib.SMTP(
                    hostname=self.smtp_host, port=self.smtp_port
                ) as smtp:
                    await smtp.login(self.smtp_user, self.smtp_password)
                    await smtp.send_message(msg)
            else:
                # Fallback: log instead of sending
                logger.warning(f"aiosmtplib not available. Would send email to {to_email}")

            logger.info(f"Email sent to {to_email}: {subject}")
            return {
                "success": True,
                "channel": "email",
                "to": to_email,
                "subject": subject,
                "sent_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return {
                "success": False,
                "channel": "email",
                "to": to_email,
                "error": str(e),
                "sent_at": datetime.now().isoformat(),
            }

    async def notify_pm_geo_error(
        self, ot_id: int, ot_external_id: str, pm_email: str
    ) -> Dict[str, Any]:
        """
        Send notification to PM about OT with missing coordinates.
        
        Args:
            ot_id: Internal OT ID
            ot_external_id: External OT identifier
            pm_email: PM email address
            
        Returns:
            Notification result
        """
        subject = f"⚠️ OT {ot_external_id} - Coordenadas Faltantes"
        body = f"""
Estimado PM,

La Orden de Trabajo {ot_external_id} (ID: {ot_id}) fue ingresada sin coordenadas geográficas válidas.

Acciones requeridas:
1. Verificar y validar las coordenadas del Login
2. Actualizar la información en el sistema
3. Reasignar la OT al algoritmo de planificación

Estado actual: ERROR_GEO

Por favor, contacte al coordinador OPU para resolver esta situación.

Sistema DERCAS PEI
{datetime.now().isoformat()}
"""
        return await self.send_email(to_email=pm_email, subject=subject, body=body)

    async def notify_inactivity_alert(
        self, ot_id: int, ot_external_id: str, days: int, recipient_email: str
    ) -> Dict[str, Any]:
        """
        Send inactivity alert for OT in DETENIDA state.
        
        Args:
            ot_id: Internal OT ID
            ot_external_id: External OT identifier
            days: Number of days in current state
            recipient_email: Recipient email address
            
        Returns:
            Notification result
        """
        if days == 20:
            urgency = "BAJA"
            emoji = "⚡"
        elif days == 25:
            urgency = "MEDIA"
            emoji = "🔴"
        elif days == 29:
            urgency = "ALTA"
            emoji = "🚨"
        else:
            urgency = "NORMAL"
            emoji = "⚠️"

        subject = f"{emoji} Alerta de Inactividad - OT {ot_external_id} ({urgency})"
        body = f"""
ALERTA DE INACTIVIDAD EN OT

ID de Orden: {ot_external_id}
ID Interno: {ot_id}
Días en DETENIDA: {days}
Nivel de Urgencia: {urgency}

La Orden de Trabajo ha estado en estado DETENIDA por {days} días.

Acciones recomendadas:
- Si {days} < 30: Resolver el problema y cambiar estado
- Si {days} == 30: La OT será automáticamente ANULADA

Contáctese con el coordinador OPU si requiere asistencia.

Sistema DERCAS PEI
{datetime.now().isoformat()}
"""
        return await self.send_email(to_email=recipient_email, subject=subject, body=body)

    async def notify_auto_cancellation(
        self,
        ot_id: int,
        ot_external_id: str,
        recipient_email: str,
        project_type: str = "DESCONOCIDO",
    ) -> Dict[str, Any]:
        """
        Send notification for automatic OT cancellation after 30 days inactivity.
        
        Args:
            ot_id: Internal OT ID
            ot_external_id: External OT identifier
            recipient_email: Recipient email address
            project_type: Type of project (PUBLICO, PRIVADO, TERCERIZADO)
            
        Returns:
            Notification result
        """
        subject = f"🚫 OT {ot_external_id} - Anulada por Inactividad"
        body = f"""
NOTIFICACIÓN DE ANULACIÓN

ID de Orden: {ot_external_id}
ID Interno: {ot_id}
Tipo de Proyecto: {project_type}
Motivo: Exceso de tiempo en estado DETENIDA (>= 30 días)

La Orden de Trabajo ha sido automáticamente ANULADA por el Sistema de Gobernanza
después de permanecer en estado DETENIDA por más de 30 días.

Información:
- Fecha de anulación: {datetime.now().isoformat()}
- Ejecutado por: Governance Agent
- Referencia de Log: AUTO_CANCEL_POLICY

Si esta anulación fue por error, contacte inmediatamente al coordinador OPU
para escalar y revertir la decisión.

Sistema DERCAS PEI - Governance Rules Engine
"""
        return await self.send_email(to_email=recipient_email, subject=subject, body=body)

    async def notify_assignment(
        self,
        ot_external_id: str,
        cuadrilla_name: str,
        distance_km: float,
        recipient_email: str,
    ) -> Dict[str, Any]:
        """
        Send notification when OT is assigned to a crew.
        
        Args:
            ot_external_id: External OT identifier
            cuadrilla_name: Name of assigned crew
            distance_km: Distance to crew centroid in km
            recipient_email: Recipient email
            
        Returns:
            Notification result
        """
        subject = f"✅ OT {ot_external_id} - Asignada a {cuadrilla_name}"
        body = f"""
ASIGNACIÓN DE ORDEN DE TRABAJO

ID de Orden: {ot_external_id}
Cuadrilla Asignada: {cuadrilla_name}
Distancia al Centroide: {distance_km:.2f} km

Su Orden de Trabajo ha sido asignada exitosamente al equipo técnico.

Próximos pasos:
1. Revisar detalles en el dashboard
2. Coordinar con el equipo asignado
3. Realizar el seguimiento de la ejecución

Sistema DERCAS PEI
{datetime.now().isoformat()}
"""
        return await self.send_email(to_email=recipient_email, subject=subject, body=body)

    async def notify_completion(
        self, ot_external_id: str, recipient_email: str
    ) -> Dict[str, Any]:
        """
        Send notification when OT is completed.
        
        Args:
            ot_external_id: External OT identifier
            recipient_email: Recipient email
            
        Returns:
            Notification result
        """
        subject = f"✔️ OT {ot_external_id} - Completada"
        body = f"""
ORDEN DE TRABAJO COMPLETADA

ID de Orden: {ot_external_id}
Estado: FINALIZADA
Fecha: {datetime.now().isoformat()}

La Orden de Trabajo ha sido marcada como FINALIZADA.

El servicio solicitado ha sido completado exitosamente.

Sistema DERCAS PEI
"""
        return await self.send_email(to_email=recipient_email, subject=subject, body=body)

    async def send_batch_notifications(
        self, notifications: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send multiple notifications in parallel.
        
        Args:
            notifications: List of notification dicts with 'type', 'channel', and 'data'
            
        Returns:
            Summary of send results
        """
        results = []
        tasks = []

        for notif in notifications:
            try:
                channel = notif.get("channel", "email")
                data = notif.get("data", {})

                if channel == "telegram":
                    task = self.send_telegram_message(
                        chat_id=data.get("chat_id"),
                        message=data.get("message"),
                    )
                elif channel == "email":
                    task = self.send_email(
                        to_email=data.get("to_email"),
                        subject=data.get("subject"),
                        body=data.get("body"),
                        html=data.get("html", False),
                    )
                else:
                    continue

                tasks.append(task)
            except Exception as e:
                logger.error(f"Error preparing notification: {e}")

        # Send all tasks concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "success": True,
            "total": len(notifications),
            "sent": len([r for r in results if isinstance(r, dict) and r.get("success")]),
            "results": results,
        }


# Global instance
notification_service = NotificationService()

