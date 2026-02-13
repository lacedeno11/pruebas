"""
GobernanzaAgent - Governance and compliance agent.
Monitors inactivity, enforces business rules, sends escalation alerts, auto-cancels OTs.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import OrdenTrabajo
from backend.services import TelcosClient
from backend.utils.logging_helper import log_agent_action

logger = logging.getLogger(__name__)


class GobernanzaAgent:
    """
    GobernanzaAgent - Implements governance and compliance monitoring.
    
    Responsibilities:
    1. Monitor OT inactivity in DETENIDA status
    2. Send escalation alerts at days 20, 25, 29
    3. Auto-cancel OTs after 30 days in DETENIDA
    4. Check PREPLANIFICADA 48-hour timeout
    5. Validate stop reasons via LLM
    6. Sync cancellations with TELCOS system
    7. Log all governance actions
    """

    def __init__(
        self,
        llm: Optional[object] = None,
        db_session: Optional[AsyncSession] = None,
        telcos_client: Optional[TelcosClient] = None,
    ):
        """
        Initialize GobernanzaAgent.

        Args:
            llm: OpenAI LLM instance (for reason validation)
            db_session: AsyncSession for database operations
            telcos_client: TelcosClient instance (for syncing cancellations)
        """
        self.llm = llm
        self.db_session = db_session
        self.telcos_client = telcos_client

    async def check_inactive_ots(self) -> Dict[str, Any]:
        """
        Check for inactive OTs in DETENIDA status.
        
        Process:
        1. Query all OTs in DETENIDA status
        2. Calculate days since detenida_at
        3. Send alerts at days 20, 25, 29
        4. Auto-cancel at day 30+
        5. Log all governance actions
        
        Returns:
            Dictionary with inactivity check results
        """
        logger.info("GobernanzaAgent: Starting inactivity check")
        
        try:
            if not self.db_session:
                logger.error("GobernanzaAgent: Database session not initialized")
                return {
                    "status": "error",
                    "detenida_alerts": 0,
                    "day_20_alerts": 0,
                    "day_25_alerts": 0,
                    "day_29_alerts": 0,
                    "auto_cancelled": 0,
                    "summary": "Failed: Database session not configured",
                }

            # TODO: Query OTs in DETENIDA status
            detenida_ots = []
            
            day_20_alerts = 0
            day_25_alerts = 0
            day_29_alerts = 0
            auto_cancelled = 0

            now = datetime.utcnow()

            for ot in detenida_ots:
                if not ot.detenida_at:
                    continue

                days_detenida = (now - ot.detenida_at).days

                # Day 20 alert
                if days_detenida == 20:
                    await self.send_alert(ot.id, "INACTIVITY", f"OT {ot.external_id} in DETENIDA for 20 days")
                    day_20_alerts += 1
                
                # Day 25 alert
                elif days_detenida == 25:
                    await self.send_alert(ot.id, "INACTIVITY", f"OT {ot.external_id} in DETENIDA for 25 days")
                    day_25_alerts += 1
                
                # Day 29 alert
                elif days_detenida == 29:
                    await self.send_alert(ot.id, "INACTIVITY", f"OT {ot.external_id} in DETENIDA for 29 days")
                    day_29_alerts += 1
                
                # Day 30+ auto-cancel
                elif days_detenida >= 30:
                    await self.auto_cancel_ot(ot.id)
                    auto_cancelled += 1

            summary = (
                f"Inactivity check: {day_20_alerts} 20-day, {day_25_alerts} 25-day, "
                f"{day_29_alerts} 29-day alerts, {auto_cancelled} auto-cancelled"
            )

            if self.db_session:
                await log_agent_action(
                    self.db_session,
                    agente_name="GobernanzaAgent",
                    ot_id=None,
                    accion="check_inactive_ots",
                    resultado=summary,
                    raw_llm_response={
                        "day_20_alerts": day_20_alerts,
                        "day_25_alerts": day_25_alerts,
                        "day_29_alerts": day_29_alerts,
                        "auto_cancelled": auto_cancelled,
                    },
                )

            return {
                "status": "success",
                "detenida_alerts": day_20_alerts + day_25_alerts + day_29_alerts,
                "day_20_alerts": day_20_alerts,
                "day_25_alerts": day_25_alerts,
                "day_29_alerts": day_29_alerts,
                "auto_cancelled": auto_cancelled,
                "summary": summary,
            }

        except Exception as e:
            logger.error(f"GobernanzaAgent: Error checking inactivity: {str(e)}")
            return {
                "status": "error",
                "detenida_alerts": 0,
                "day_20_alerts": 0,
                "day_25_alerts": 0,
                "day_29_alerts": 0,
                "auto_cancelled": 0,
                "summary": f"Inactivity check failed: {str(e)}",
            }

    async def check_preplanificada_timeout(self) -> Dict[str, Any]:
        """
        Check for PREPLANIFICADA OTs exceeding 48-hour timeout.
        
        Returns:
            Dictionary with timeout check results
        """
        logger.info("GobernanzaAgent: Starting PREPLANIFICADA timeout check")
        
        try:
            if not self.db_session:
                return {
                    "status": "error",
                    "preplanificada_count": 0,
                    "over_48h_count": 0,
                    "alerts_sent": 0,
                    "summary": "Failed: Database session not configured",
                }

            # TODO: Query OTs in PREPLANIFICADA status
            preplanificada_ots = []
            
            alerts_sent = 0
            now = datetime.utcnow()
            timeout_hours = 48

            for ot in preplanificada_ots:
                hours_preplanificada = (now - ot.created_at).total_seconds() / 3600

                if hours_preplanificada > timeout_hours:
                    await self.send_alert(
                        ot.id,
                        "TIMEOUT",
                        f"OT {ot.external_id} in PREPLANIFICADA for {int(hours_preplanificada)} hours"
                    )
                    alerts_sent += 1

            summary = (
                f"PREPLANIFICADA timeout: {len(preplanificada_ots)} total, "
                f"{alerts_sent} over 48 hours, {alerts_sent} alerts sent"
            )

            if self.db_session:
                await log_agent_action(
                    self.db_session,
                    agente_name="GobernanzaAgent",
                    ot_id=None,
                    accion="check_preplanificada_timeout",
                    resultado=summary,
                    raw_llm_response={
                        "total_preplanificada": len(preplanificada_ots),
                        "over_48h_count": alerts_sent,
                    },
                )

            return {
                "status": "success",
                "preplanificada_count": len(preplanificada_ots),
                "over_48h_count": alerts_sent,
                "alerts_sent": alerts_sent,
                "summary": summary,
            }

        except Exception as e:
            logger.error(f"GobernanzaAgent: Error checking timeout: {str(e)}")
            return {
                "status": "error",
                "preplanificada_count": 0,
                "over_48h_count": 0,
                "alerts_sent": 0,
                "summary": f"Timeout check failed: {str(e)}",
            }

    async def validate_stop_reason(self, reason: str) -> Dict[str, Any]:
        """
        Validate stop reason using LLM.
        
        Args:
            reason: Stop reason text to validate
            
        Returns:
            Dictionary with validation result
        """
        logger.info(f"GobernanzaAgent: Validating stop reason: {reason[:50]}...")
        
        try:
            # TODO: Implement LLM-based validation
            # For now, simple heuristic validation
            
            min_length = 10
            
            if len(reason.strip()) < min_length:
                return {
                    "valid": False,
                    "message": f"Reason too short. Minimum {min_length} characters required.",
                    "suggested_alternatives": [
                        "Weather conditions preventing installation",
                        "Equipment failure during work",
                        "Customer not available at location",
                        "Site access denied",
                        "Material shortage",
                    ]
                }

            return {
                "valid": True,
                "message": "Reason accepted",
                "suggested_alternatives": []
            }

        except Exception as e:
            logger.error(f"GobernanzaAgent: Error validating reason: {str(e)}")
            return {
                "valid": False,
                "message": f"Validation error: {str(e)}",
                "suggested_alternatives": []
            }

    # Helper methods
    async def send_alert(self, ot_id: UUID, alert_type: str, message: str) -> bool:
        """Send governance alert."""
        logger.info(f"GobernanzaAgent: Alert - {alert_type}: {message}")
        # TODO: Implement notification sending via notification_tools
        return True

    async def auto_cancel_ot(self, ot_id: UUID) -> bool:
        """Auto-cancel OT after 30 days in DETENIDA status."""
        logger.info(f"GobernanzaAgent: Auto-cancelling OT {ot_id}")
        try:
            if not self.db_session:
                return False

            # TODO: Update OT status to ANULADA
            # TODO: Call telcos_client.update_ot_status() to sync
            
            return True

        except Exception as e:
            logger.error(f"GobernanzaAgent: Error auto-cancelling OT: {str(e)}")
            return False

