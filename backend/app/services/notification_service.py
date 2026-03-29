"""
NotificationService: Handles multi-channel notifications for DERCAS system events.

This service provides notification capabilities through:

Telegram Notifications:
    For immediate alerts to field technicians via Telegram Bot API.
    Used for ERROR_GEO, detention warnings, and route updates.

Email Notifications:
    For formal communications to PMs, clients, and coordinators via SMTP.
    Used for inactivity alerts, completion confirmations, and reports.

Notification Types:
    - ERROR_GEO: Immediate telegram to PM + email backup
    - Inactivity Alert: Email to Coordinador OPU (high priority)
    - Detention Warning: Email to PM with action required
    - Route Update: Telegram to technician with daily assignments
    - Planning Complete: Email to PM with summary

All notifications include error handling and logging without blocking main flow.
"""

import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class NotificationChannel:
    """Available notification channels."""
    TELEGRAM = "telegram"
    EMAIL = "email"
    SMS = "sms"  # Future enhancement


class NotificationPriority:
    """Notification priority levels."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NotificationService:
    """
    Service for sending multi-channel notifications.
    
    Manages:
    - Telegram Bot API notifications to field teams
    - SMTP email notifications to stakeholders
    - Error handling with graceful degradation
    - Async/concurrent notification delivery
    
    Configuration is loaded from app.core.config.settings:
    - TELEGRAM_BOT_TOKEN: Telegram Bot API token
    - SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD: Email credentials
    """

    def __init__(self, settings: Any):
        """
        Initialize NotificationService with configuration.
        
        Args:
            settings: Configuration object from app.core.config.settings
        """
        self.settings = settings
        self.telegram_token = settings.TELEGRAM_BOT_TOKEN
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD

    async def send_telegram_notification(
        self,
        chat_id: str,
        message: str,
        parse_mode: str = "HTML",
    ) -> Dict[str, Any]:
        """
        Send notification via Telegram Bot API.
        
        Uses Telegram Bot API to send messages to field technicians.
        Includes error handling for network failures.
        
        Args:
            chat_id: Telegram chat ID (user or group)
            message: Message text (supports HTML formatting)
            parse_mode: Message format ('HTML', 'Markdown', or 'plain')
            
        Returns:
            Dict with 'success' (bool), 'message_id' (if successful), 'error' (if failed)
        """
        if not self.telegram_token:
            logger.warning("Telegram token not configured, skipping notification")
            return {
                "success": False,
                "error": "Telegram token not configured",
                "channel": "telegram",
            }

        try:
            # Telegram Bot API endpoint
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    json={
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": parse_mode,
                    },
                )

            # Check response status
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"Telegram notification sent to {chat_id}: "
                    f"message_id={result.get('result', {}).get('message_id')}"
                )
                return {
                    "success": True,
                    "message_id": result.get("result", {}).get("message_id"),
                    "channel": "telegram",
                }
            else:
                logger.error(
                    f"Telegram API error: {response.status_code} - {response.text}"
                )
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "channel": "telegram",
                }

        except Exception as e:
            logger.error(
                f"Error sending Telegram notification to {chat_id}: {str(e)}"
            )
            return {
                "success": False,
                "error": str(e),
                "channel": "telegram",
            }

    async def send_email_notification(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send notification via SMTP email.
        
        Sends HTML/plain text emails to stakeholders via configured SMTP server.
        Uses async execution to avoid blocking main thread.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Plain text body
            html_body: HTML body (optional, preferred if provided)
            
        Returns:
            Dict with 'success' (bool), 'message' (if successful), 'error' (if failed)
        """
        if not (self.smtp_host and self.smtp_user):
            logger.warning("SMTP not configured, skipping email notification")
            return {
                "success": False,
                "error": "SMTP not configured",
                "channel": "email",
            }

        try:
            # Create email message
            msg = MIMEText(html_body or body, "html" if html_body else "plain")
            msg["Subject"] = subject
            msg["From"] = self.smtp_user
            msg["To"] = to_email

            # Send email in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._send_smtp, to_email, msg.as_string()
            )

            logger.info(f"Email notification sent to {to_email}: {subject}")
            return {
                "success": True,
                "message": f"Email sent to {to_email}",
                "channel": "email",
            }

        except Exception as e:
            logger.error(
                f"Error sending email to {to_email}: {str(e)}"
            )
            return {
                "success": False,
                "error": str(e),
                "channel": "email",
            }

    def _send_smtp(self, to_email: str, message: str) -> None:
        """
        Synchronous SMTP send (runs in thread pool).
        
        Args:
            to_email: Recipient email address
            message: Complete email message (including headers)
        """
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                # Enable TLS encryption
                server.starttls()
                # Authenticate
                server.login(self.smtp_user, self.smtp_password)
                # Send message
                server.sendmail(self.smtp_user, to_email, message)

        except Exception as e:
            logger.error(f"SMTP error sending to {to_email}: {str(e)}")
            raise

    async def notify_pm_error_geo(
        self,
        ot_id: int,
        ot_external_id: str,
        details: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Notify PM about OT with missing geographic coordinates (ERROR_GEO).
        
        Sends immediate Telegram alert + email notification to PM.
        
        Args:
            ot_id: OT database ID
            ot_external_id: OT external identifier
            details: Additional context (cliente_id, login, etc.)
            
        Returns:
            List of notification results from each channel
        """
        results = []

        # Telegram message to PM (immediate)
        telegram_message = (
            f"<b>🚨 ERROR GEO ALERT</b>\n\n"
            f"OT: <b>{ot_external_id}</b>\n"
            f"Problema: Falta de coordenadas geográficas\n"
            f"Cliente: {details.get('cliente_id', 'N/A')}\n"
            f"Login: {details.get('login', 'N/A')}\n\n"
            f"<i>La OT no puede ser planificada hasta que se proporcionen coordenadas.</i>"
        )

        # Email message to PM (formal)
        email_subject = f"[DERCAS] ERROR GEO - OT {ot_external_id} requiere coordenadas"
        email_body = (
            f"Estimado PM,\n\n"
            f"Se ha detectado un error geográfico en la siguiente orden de trabajo:\n\n"
            f"OT: {ot_external_id}\n"
            f"Cliente: {details.get('cliente_id', 'N/A')}\n"
            f"Login: {details.get('login', 'N/A')}\n\n"
            f"Esta OT no tiene coordenadas geográficas (lat/long) y no puede ser "
            f"planificada automáticamente.\n\n"
            f"Por favor, actualice los datos de ubicación en el sistema TELCOS "
            f"y sincronice nuevamente.\n\n"
            f"Estado: ERROR_GEO\n"
            f"Acción requerida: Actualizar coordenadas\n\n"
            f"Saludos,\nDERCAS PEI System"
        )

        # Get PM chat ID from settings or use placeholder
        pm_chat_id = details.get("pm_chat_id")
        if pm_chat_id:
            tg_result = await self.send_telegram_notification(
                pm_chat_id, telegram_message
            )
            results.append(tg_result)

        # Send email (always)
        pm_email = details.get("pm_email")
        if pm_email:
            email_result = await self.send_email_notification(
                pm_email, email_subject, email_body
            )
            results.append(email_result)

        return results

    async def notify_coordinador_inactivity(
        self,
        ot_ids: List[int],
        ot_external_ids: List[str],
        age_hours: List[int],
    ) -> List[Dict[str, Any]]:
        """
        Notify Coordinador OPU about inactive OTs (>48h in PREPLANIFICADA).
        
        Sends high-priority email to Coordinador OPU.
        
        Args:
            ot_ids: List of OT database IDs
            ot_external_ids: List of OT external IDs
            age_hours: List of ages (hours) for each OT
            
        Returns:
            List of notification results
        """
        results = []

        if not ot_external_ids:
            logger.warning("No OTs provided for inactivity notification")
            return results

        # Build OT list for email
        ot_list_html = "<ul>"
        for ext_id, hours in zip(ot_external_ids, age_hours):
            ot_list_html += f"<li>{ext_id}: {hours}h en PREPLANIFICADA</li>"
        ot_list_html += "</ul>"

        # Email to Coordinador OPU
        email_subject = (
            f"[DERCAS] ALERTA DE INACTIVIDAD - {len(ot_external_ids)} OTs "
            f"requieren atención"
        )
        email_html = (
            f"<h2>🔴 ALERTA DE INACTIVIDAD - DERCAS PEI</h2>\n\n"
            f"<p>Las siguientes órdenes de trabajo han estado en estado "
            f"<b>PREPLANIFICADA</b> por más de <b>48 horas</b>:</p>\n\n"
            f"{ot_list_html}\n\n"
            f"<p><b>Acción requerida:</b> Revisar y actualizar estas OTs de inmediato.</p>\n\n"
            f"<p>Saludos,<br>DERCAS PEI System</p>"
        )

        # Send to coordinador
        coordinador_email = self.settings.COORDINADOR_EMAIL
        if coordinador_email:
            email_result = await self.send_email_notification(
                coordinador_email,
                email_subject,
                email_html,
                html_body=email_html,
            )
            results.append(email_result)
        else:
            logger.warning("COORDINADOR_EMAIL not configured")

        return results

    async def notify_detention_warning(
        self,
        ot_external_id: str,
        days_detained: int,
        days_until_cancel: int,
        pm_email: str,
    ) -> List[Dict[str, Any]]:
        """
        Notify PM about OT approaching auto-cancellation (day 20/25/29).
        
        Args:
            ot_external_id: OT external ID
            days_detained: Days in DETENIDA status
            days_until_cancel: Days remaining before auto-cancellation
            pm_email: PM email address
            
        Returns:
            List of notification results
        """
        results = []

        email_subject = (
            f"[DERCAS] AVISO DE DETENCIÓN - OT {ot_external_id} "
            f"({days_until_cancel} días para anulación)"
        )

        email_html = (
            f"<h2>⚠️ AVISO DE DETENCIÓN - DERCAS PEI</h2>\n\n"
            f"<p>La siguiente orden de trabajo ha estado en estado "
            f"<b>DETENIDA</b> por <b>{days_detained} días</b>:</p>\n\n"
            f"<p><b>OT:</b> {ot_external_id}</p>\n"
            f"<p><b>Días restantes:</b> {days_until_cancel} días</p>\n\n"
            f"<p style='color: red;'><b>⚠️ IMPORTANTE:</b> Esta OT será "
            f"<b>anulada automáticamente</b> en {days_until_cancel} días "
            f"si no se resuelve.</p>\n\n"
            f"<p><b>Acciones recomendadas:</b></p>\n"
            f"<ul>\n"
            f"<li>Resolver el motivo de detención</li>\n"
            f"<li>Reanudar la planificación</li>\n"
            f"<li>Contactar a soporte si requiere asistencia</li>\n"
            f"</ul>\n\n"
            f"<p>Saludos,<br>DERCAS PEI System</p>"
        )

        if pm_email:
            email_result = await self.send_email_notification(
                pm_email,
                email_subject,
                email_html,
                html_body=email_html,
            )
            results.append(email_result)

        return results

    async def notify_crew_route_update(
        self,
        crew_name: str,
        crew_chat_id: str,
        route_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Notify crew about daily route assignments via Telegram.
        
        Sends summary of assigned OTs for the day.
        
        Args:
            crew_name: Crew name
            crew_chat_id: Telegram chat ID for crew group
            route_details: Dict with 'ot_count', 'ots', 'total_distance_km', 'estimated_time'
            
        Returns:
            Notification result dict
        """
        ot_count = route_details.get("ot_count", 0)
        total_distance = route_details.get("total_distance_km", 0)
        estimated_time = route_details.get("estimated_time", "N/A")

        # Build OT list
        ot_list = ""
        ots = route_details.get("ots", [])
        for i, ot in enumerate(ots[:5], 1):  # Show first 5
            ot_list += f"{i}. {ot.get('external_id')} - {ot.get('login')}\n"

        if len(ots) > 5:
            ot_list += f"... y {len(ots) - 5} más\n"

        telegram_message = (
            f"<b>📋 RUTA DEL DÍA - {crew_name}</b>\n\n"
            f"<b>📦 Total OTs:</b> {ot_count}\n"
            f"<b>🗺️ Distancia:</b> {total_distance:.1f} km\n"
            f"<b>⏱️ Tiempo estimado:</b> {estimated_time}\n\n"
            f"<b>Asignaciones:</b>\n{ot_list}\n"
            f"Consulta la plataforma DERCAS para detalles completos."
        )

        return await self.send_telegram_notification(
            crew_chat_id, telegram_message
        )

    async def notify_planning_complete(
        self,
        assigned_count: int,
        warning_count: int,
        pm_email: str,
    ) -> List[Dict[str, Any]]:
        """
        Notify PM about completed planning cycle.
        
        Args:
            assigned_count: Number of OTs assigned
            warning_count: Number of warnings/issues
            pm_email: PM email address
            
        Returns:
            List of notification results
        """
        results = []

        email_subject = (
            f"[DERCAS] Planificación Completada - "
            f"{assigned_count} OTs asignadas"
        )

        warning_html = ""
        if warning_count > 0:
            warning_html = (
                f"<p style='color: orange;'><b>⚠️ Advertencias:</b> "
                f"{warning_count} OTs requieren atención manual</p>"
            )

        email_html = (
            f"<h2>✅ PLANIFICACIÓN COMPLETADA - DERCAS PEI</h2>\n\n"
            f"<p>El ciclo de planificación automática ha completado "
            f"exitosamente.</p>\n\n"
            f"<p><b>Resultados:</b></p>\n"
            f"<ul>\n"
            f"<li><b>OTs Asignadas:</b> {assigned_count}</li>\n"
            f"<li><b>Advertencias:</b> {warning_count}</li>\n"
            f"</ul>\n\n"
            f"{warning_html}\n"
            f"<p>Ingrese a la plataforma DERCAS para revisar los detalles "
            f"de las asignaciones.</p>\n\n"
            f"<p>Saludos,<br>DERCAS PEI System</p>"
        )

        if pm_email:
            email_result = await self.send_email_notification(
                pm_email,
                email_subject,
                email_html,
                html_body=email_html,
            )
            results.append(email_result)

        return results

    async def send_batch_notifications(
        self,
        notifications: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Send multiple notifications concurrently.
        
        Uses asyncio.gather for concurrent delivery without blocking.
        
        Args:
            notifications: List of notification dicts with 'type', 'data'
            
        Returns:
            List of results for each notification
        """
        tasks = []

        for notification in notifications:
            notification_type = notification.get("type")
            data = notification.get("data", {})

            if notification_type == "telegram":
                task = self.send_telegram_notification(
                    data.get("chat_id"),
                    data.get("message"),
                )
            elif notification_type == "email":
                task = self.send_email_notification(
                    data.get("to_email"),
                    data.get("subject"),
                    data.get("body"),
                    data.get("html_body"),
                )
            else:
                logger.warning(f"Unknown notification type: {notification_type}")
                continue

            tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error dicts
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "error": str(result),
                })
            else:
                processed_results.append(result)

        return processed_results

