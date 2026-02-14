"""
Comunicacion Agent for PEI Platform - Notification Orchestration.

The ComunicacionAgent is responsible for orchestrating all notifications sent
to stakeholders. It routes notifications through appropriate channels (Telegram
for technical teams, Email for management) based on notification type and priority.

Notification Types:
- 'alert': Operational alerts to technical teams (Telegram)
- 'status_change': Status changes to project managers (Email)
- 'geo_error': Geographic errors to PM with details (Email)
- 'governance_alert': Governance violations (Email + Telegram based on priority)

This agent is typically called after other agents complete their work to
communicate results to relevant stakeholders.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base_agent import BaseAgent
from src.agents.state import PEIState
from src.models import OT
from src.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class ComunicacionAgent(BaseAgent):
    """
    Communication Agent for notification orchestration and delivery.

    This agent handles all outbound notifications to stakeholders:
    - Technical teams via Telegram for operational alerts
    - Project managers via Email for status changes
    - Management via Email/Telegram for governance violations

    Notifications are formatted with relevant OT details and timestamps
    for clear communication and audit trail.
    """

    def __init__(self, db: AsyncSession, llm=None):
        """Initialize the ComunicacionAgent."""
        super().__init__(db, llm, agent_name="ComunicacionAgent")
        self.notification_service = NotificationService()

    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for Comunicacion Agent.

        Returns:
            str: System prompt text
        """
        return """You are the Comunicacion (Communication) Agent for the PEI system.
Your responsibility is to:
1. Format clear and professional notifications for stakeholders
2. Route notifications to appropriate channels (Telegram, Email)
3. Include relevant OT details, status, and timestamps
4. Ensure all communications are logged for audit trail
5. Handle different notification types appropriately

Message formatting rules:
- Include OT external_id and relevant status in all messages
- Use timestamps for time-sensitive operations
- Keep messages concise but informative
- For technical teams: Use Telegram with alerts focus
- For PMs: Use Email with full details and context
- For governance: Use high priority and follow-up escalation

Always ensure proper channel routing and message clarity."""

    async def process(self, state: PEIState) -> PEIState:
        """
        Orchestrate notifications based on state metadata.

        Args:
            state (PEIState): Current workflow state with notification metadata

        Returns:
            PEIState: Updated state with notification results
        """
        try:
            # Validate state
            if not await self.validate_state(state):
                return await self.handle_error(state, "Invalid state for ComunicacionAgent")

            logger.info("ComunicacionAgent: Starting notification orchestration")

            # Get notification type from metadata
            notification_type = state.get("metadata", {}).get("notification_type", "status_change")
            current_ot_id = state.get("current_ot_id")

            notifications_sent = 0
            errors = []

            # Route based on notification type
            if notification_type == "alert":
                notifications_sent += await self._send_alert_notification(state, current_ot_id, errors)

            elif notification_type == "status_change":
                notifications_sent += await self._send_status_change_notification(state, current_ot_id, errors)

            elif notification_type == "geo_error":
                notifications_sent += await self._send_geo_error_notification(state, current_ot_id, errors)

            elif notification_type == "governance_alert":
                notifications_sent += await self._send_governance_alert(state, current_ot_id, errors)

            else:
                logger.warning(f"ComunicacionAgent: Unknown notification type: {notification_type}")

            # Log communication action
            accion = f"Notifications orchestrated - Type: {notification_type}, Sent: {notifications_sent}"
            await self.log_action(
                ot_id=current_ot_id,
                accion=accion,
                resultado="SUCCESS" if notifications_sent > 0 else "WARNING",
                metadata={
                    "notification_type": notification_type,
                    "notifications_sent": notifications_sent,
                    "errors": errors if errors else None,
                },
            )

            # Update state
            state["agent_messages"].append({
                "agent": "ComunicacionAgent",
                "content": f"Sent {notifications_sent} notifications ({notification_type})",
                "timestamp": datetime.utcnow().isoformat(),
            })

            state["action_result"] = {
                "success": notifications_sent > 0,
                "message": f"Sent {notifications_sent} notifications",
                "data": {
                    "notifications_sent": notifications_sent,
                    "notification_type": notification_type,
                    "errors": errors if errors else None,
                },
            }

            logger.info(
                f"ComunicacionAgent: Completed notification orchestration - "
                f"{notifications_sent} sent, {len(errors)} errors"
            )

            return state

        except Exception as e:
            logger.error(f"ComunicacionAgent error: {str(e)}", exc_info=True)
            return await self.handle_error(state, f"ComunicacionAgent error: {str(e)}")

    async def _send_alert_notification(
        self, state: PEIState, ot_id: Optional[int], errors: list
    ) -> int:
        """
        Send operational alert to technical teams via Telegram.

        Args:
            state (PEIState): Current state
            ot_id (Optional[int]): OT ID if applicable
            errors (list): Error list to append to

        Returns:
            int: Number of notifications sent
        """
        try:
            # Get OT details if available
            ot_details = ""
            if ot_id:
                result = await self.db.execute(select(OT).where(OT.id == ot_id))
                ot = result.scalars().first()
                if ot:
                    ot_details = f" (OT: {ot.external_id})"

            # Format alert message
            alert_msg = await self._format_alert_message(state, ot_id)

            # Send via Telegram to technical teams
            await self.notification_service.send_telegram(
                message=alert_msg,
                chat_id="technical_team_chat_id",  # Would be configured in settings
                priority="HIGH",
            )

            logger.info(f"ComunicacionAgent: Sent alert notification{ot_details}")
            return 1

        except Exception as e:
            error_msg = f"Failed to send alert notification: {str(e)}"
            logger.error(f"ComunicacionAgent: {error_msg}")
            errors.append(error_msg)
            return 0

    async def _send_status_change_notification(
        self, state: PEIState, ot_id: Optional[int], errors: list
    ) -> int:
        """
        Send status change notification to project managers via Email.

        Args:
            state (PEIState): Current state
            ot_id (Optional[int]): OT ID if applicable
            errors (list): Error list to append to

        Returns:
            int: Number of notifications sent
        """
        try:
            # Get OT details
            if not ot_id:
                logger.warning("ComunicacionAgent: No OT ID for status change notification")
                return 0

            result = await self.db.execute(select(OT).where(OT.id == ot_id))
            ot = result.scalars().first()

            if not ot:
                logger.warning(f"ComunicacionAgent: OT {ot_id} not found")
                return 0

            # Format email
            subject, body = await self._format_status_change_email(ot, state)

            # Send email to PM
            await self.notification_service.send_email(
                to=ot.cliente_id + "@example.com",  # Would use actual email from system
                subject=subject,
                body=body,
                priority="NORMAL",
            )

            logger.info(f"ComunicacionAgent: Sent status change email for OT {ot.external_id}")
            return 1

        except Exception as e:
            error_msg = f"Failed to send status change notification: {str(e)}"
            logger.error(f"ComunicacionAgent: {error_msg}")
            errors.append(error_msg)
            return 0

    async def _send_geo_error_notification(
        self, state: PEIState, ot_id: Optional[int], errors: list
    ) -> int:
        """
        Send geographic error notification to PM with detailed error information.

        Args:
            state (PEIState): Current state
            ot_id (Optional[int]): OT ID if applicable
            errors (list): Error list to append to

        Returns:
            int: Number of notifications sent
        """
        try:
            # Get OT details
            if not ot_id:
                logger.warning("ComunicacionAgent: No OT ID for geo error notification")
                return 0

            result = await self.db.execute(select(OT).where(OT.id == ot_id))
            ot = result.scalars().first()

            if not ot:
                logger.warning(f"ComunicacionAgent: OT {ot_id} not found")
                return 0

            # Format geo error notification
            subject, body = await self._format_geo_error_notification(ot)

            # Send email to PM
            await self.notification_service.send_email(
                to=ot.cliente_id + "@example.com",
                subject=subject,
                body=body,
                priority="HIGH",
            )

            logger.info(f"ComunicacionAgent: Sent geo error notification for OT {ot.external_id}")
            return 1

        except Exception as e:
            error_msg = f"Failed to send geo error notification: {str(e)}"
            logger.error(f"ComunicacionAgent: {error_msg}")
            errors.append(error_msg)
            return 0

    async def _send_governance_alert(
        self, state: PEIState, ot_id: Optional[int], errors: list
    ) -> int:
        """
        Send governance alert via Email and/or Telegram based on priority.

        Args:
            state (PEIState): Current state
            ot_id (Optional[int]): OT ID if applicable
            errors (list): Error list to append to

        Returns:
            int: Number of notifications sent
        """
        try:
            # Get alert details from metadata
            alert_data = state.get("metadata", {})
            alert_type = alert_data.get("alert_type", "governance_violation")
            priority = alert_data.get("alert_priority", "NORMAL")

            # Get OT details if available
            ot = None
            ot_details = ""
            if ot_id:
                result = await self.db.execute(select(OT).where(OT.id == ot_id))
                ot = result.scalars().first()
                if ot:
                    ot_details = f" (OT: {ot.external_id})"

            # Format governance alert message
            alert_msg = f"[{alert_type.upper()}] {alert_data.get('alert_message', 'Governance alert')}{ot_details}"
            timestamp = datetime.utcnow().isoformat()

            notifications_sent = 0

            # Send Email for all governance alerts
            try:
                await self.notification_service.send_email(
                    to="coordinator@telconet.ec",
                    subject=f"Governance Alert: {alert_type}",
                    body=f"{alert_msg}\n\nTimestamp: {timestamp}",
                    priority=priority,
                )
                notifications_sent += 1
                logger.info(f"ComunicacionAgent: Sent governance email alert{ot_details}")
            except Exception as e:
                error_msg = f"Failed to send governance email: {str(e)}"
                logger.warning(f"ComunicacionAgent: {error_msg}")
                errors.append(error_msg)

            # Send Telegram for high-priority governance alerts
            if priority in ["HIGH", "CRITICAL"]:
                try:
                    await self.notification_service.send_telegram(
                        message=f"🚨 GOVERNANCE ALERT: {alert_msg}",
                        chat_id="coordinator_chat_id",
                        priority=priority,
                    )
                    notifications_sent += 1
                    logger.info(f"ComunicacionAgent: Sent governance Telegram alert{ot_details}")
                except Exception as e:
                    error_msg = f"Failed to send governance Telegram: {str(e)}"
                    logger.warning(f"ComunicacionAgent: {error_msg}")
                    errors.append(error_msg)

            return notifications_sent

        except Exception as e:
            error_msg = f"Failed to send governance alert: {str(e)}"
            logger.error(f"ComunicacionAgent: {error_msg}")
            errors.append(error_msg)
            return 0

    async def _format_alert_message(self, state: PEIState, ot_id: Optional[int]) -> str:
        """
        Format operational alert message for technical teams.

        Args:
            state (PEIState): Current state
            ot_id (Optional[int]): OT ID if applicable

        Returns:
            str: Formatted alert message
        """
        try:
            alert_data = state.get("metadata", {})
            message = alert_data.get("alert_message", "Operational alert")

            if ot_id:
                result = await self.db.execute(select(OT).where(OT.id == ot_id))
                ot = result.scalars().first()
                if ot:
                    message = f"🔔 OT {ot.external_id}: {message}"

            return message

        except Exception as e:
            logger.error(f"ComunicacionAgent: Error formatting alert message: {str(e)}")
            return "Operational alert"

    async def _format_status_change_email(self, ot: OT, state: PEIState) -> tuple[str, str]:
        """
        Format status change email for project manager.

        Args:
            ot (OT): OT being reported
            state (PEIState): Current state

        Returns:
            tuple[str, str]: (subject, body)
        """
        try:
            subject = f"OT {ot.external_id} Status Changed: {ot.status.value}"

            status_msg = state.get("action_result", {}).get("message", "Status updated")
            cuadrilla_info = ""
            if ot.cuadrilla_id:
                cuadrilla_info = f"\nAssigned Cuadrilla: {ot.cuadrilla_id}"

            body = f"""
Dear Project Manager,

Work Order {ot.external_id} status has been updated.

Current Status: {ot.status.value}
Project Type: {ot.project_type.value}
Cliente: {ot.cliente_id}
{cuadrilla_info}

Message: {status_msg}

Updated: {datetime.utcnow().isoformat()}

Best regards,
PEI Agent Platform
"""
            return subject, body

        except Exception as e:
            logger.error(f"ComunicacionAgent: Error formatting status email: {str(e)}")
            return "OT Status Update", "Status update notification"

    async def _format_geo_error_notification(self, ot: OT) -> tuple[str, str]:
        """
        Format geographic error notification with detailed information.

        Args:
            ot (OT): OT with geographic error

        Returns:
            tuple[str, str]: (subject, body)
        """
        try:
            subject = f"Geographic Error Alert: OT {ot.external_id} - Manual Validation Required"

            coords_info = "Not available" if not ot.lat or not ot.long else f"({ot.lat}, {ot.long})"

            body = f"""
Dear Project Manager,

Geographic validation failed for work order {ot.external_id}.

ERROR_GEO DETAILS:
=================

OT External ID: {ot.external_id}
Cliente: {ot.cliente_id}
Login: {ot.login_id}
Project Type: {ot.project_type.value}

Coordinates: {coords_info}
Status: {ot.status.value}

ACTION REQUIRED:
================
This order has been flagged for manual geographic validation.
Please review and correct the coordinates in the system before assignment.

Contact the technical team if assistance is needed.

Created: {ot.created_at.isoformat() if ot.created_at else 'Unknown'}
Reported: {datetime.utcnow().isoformat()}

Best regards,
PEI Agent Platform - Geographic Validation System
"""
            return subject, body

        except Exception as e:
            logger.error(f"ComunicacionAgent: Error formatting geo error notification: {str(e)}")
            return "Geographic Error Alert", "Geographic error notification"

