"""
Gobernanza Agent for PEI Platform - Governance Rules and Validation.

The GobernanzaAgent is responsible for enforcing business rules and governance
constraints across the system. It validates transitions, monitors detention times,
checks document requirements, and triggers alerts for rule violations.

Responsibilities:
1. Validate OT status transitions against business rules
2. Monitor OTs in DETENIDA status and trigger alerts at days 20, 25, 29
3. Auto-cancel OTs at day 30 of detention
4. Alert on PREPLANIFICADA OTs >48 hours without assignment
5. Validate PUBLICO projects have 29 documents before FINALIZADA
6. Enforce capacity constraints during planning

Implements UC-PEI-08: Auto-cancellation by Inactivity
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.agents.base_agent import BaseAgent
from src.agents.state import PEIState
from src.models import OT, OTStatus, ProjectType
from src.services.api_factory import get_api_service
from src.services.notification_service import NotificationService
from src.utils.business_rules import (
    can_transition_to_finalizada,
    should_trigger_preplanificada_alert,
    calculate_detention_alert_day,
)

logger = logging.getLogger(__name__)


class GobernanzaAgent(BaseAgent):
    """
    Governance Agent for enforcing business rules and validating transitions.

    This agent ensures that all OT transitions comply with business rules and
    that governance constraints are maintained throughout the OT lifecycle.

    Key Rules:
    - DETENIDA OTs: Auto-cancel at day 30, alert at days 20, 25, 29
    - PREPLANIFICADA OTs: Alert if >48 hours without assignment
    - PUBLICO projects: Must have 29 TelcoDrive documents before FINALIZADA
    - Capacity constraints: No cuadrilla exceeds max_daily_capacity
    """

    def __init__(self, db: AsyncSession, llm=None):
        """Initialize the GobernanzaAgent."""
        super().__init__(db, llm, agent_name="GobernanzaAgent")
        self.api_service = get_api_service()
        self.notification_service = NotificationService()

    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for Gobernanza Agent.

        Returns:
            str: System prompt text
        """
        return """You are the Gobernanza (Governance) Agent for the PEI system.
Your responsibility is to:
1. Enforce business rules and constraints
2. Validate all OT status transitions
3. Monitor detention times and auto-cancel overdue OTs
4. Check that PUBLICO projects have required documentation
5. Alert on violations that require human intervention
6. Maintain data integrity across the system

Key rules:
- OTs in DETENIDA status >30 days must be auto-cancelled
- OTs in PREPLANIFICADA >48 hours trigger alerts
- PUBLICO projects require 29 TelcoDrive documents before completion
- All status transitions must follow the defined state machine
- Cuadrillas cannot exceed their daily capacity

Log all governance decisions and alerts with clear reasoning."""

    async def process(self, state: PEIState) -> PEIState:
        """
        Execute governance checks and validations.

        Args:
            state (PEIState): Current workflow state

        Returns:
            PEIState: Updated state with governance results
        """
        try:
            # Validate state
            if not await self.validate_state(state):
                return await self.handle_error(state, "Invalid state for GobernanzaAgent")

            logger.info("GobernanzaAgent: Starting governance checks")

            now = datetime.utcnow()
            alerts_triggered = 0
            cancellations = 0
            validations_passed = 0

            # Check DETENIDA OTs for detention timeouts
            detenida_result = await self.db.execute(
                select(OT).where(OT.status == OTStatus.DETENIDA)
            )
            detenida_ots = detenida_result.scalars().all()

            for ot in detenida_ots:
                if ot.assigned_at is None:
                    continue

                days_detained = (now - ot.assigned_at).days

                # Auto-cancel at day 30
                if days_detained >= 30:
                    try:
                        ot.status = OTStatus.ANULADA
                        self.db.add(ot)
                        await self.db.flush()

                        accion = "Anulada por Governance Agent - Motivo: Exceso de tiempo en estado DETENIDA"
                        await self.log_action(
                            ot_id=ot.id,
                            accion=accion,
                            resultado="SUCCESS",
                            metadata={
                                "days_detained": days_detained,
                                "reason": "Exceeded 30-day detention limit",
                            },
                        )

                        cancellations += 1
                        logger.info(
                            f"GobernanzaAgent: Auto-cancelled OT {ot.external_id} "
                            f"after {days_detained} days in DETENIDA"
                        )

                    except Exception as e:
                        logger.error(
                            f"GobernanzaAgent: Error auto-cancelling OT {ot.external_id}: {str(e)}"
                        )
                        continue

                # Alert at days 20, 25, 29
                elif days_detained in [20, 25, 29]:
                    try:
                        alert_msg = (
                            f"OT {ot.external_id} has been in DETENIDA status for {days_detained} days. "
                            f"It will be auto-cancelled at day 30 if not resolved."
                        )
                        await self.notification_service.send_alert(
                            alert_type="detention",
                            ot_id=ot.id,
                            recipients=["coordinator@telconet.ec"],
                            message=alert_msg,
                        )

                        alerts_triggered += 1
                        logger.info(
                            f"GobernanzaAgent: Triggered detention alert for OT {ot.external_id} "
                            f"at day {days_detained}"
                        )

                    except Exception as e:
                        logger.warning(
                            f"GobernanzaAgent: Failed to send detention alert: {str(e)}"
                        )
                        continue

            # Check PREPLANIFICADA OTs for >48 hours without assignment
            preplanificada_result = await self.db.execute(
                select(OT).where(OT.status == OTStatus.PREPLANIFICADA)
            )
            preplanificada_ots = preplanificada_result.scalars().all()

            for ot in preplanificada_ots:
                if should_trigger_preplanificada_alert(ot):
                    try:
                        hours_waiting = (now - ot.created_at).total_seconds() / 3600
                        alert_msg = (
                            f"OT {ot.external_id} has been in PREPLANIFICADA status for {hours_waiting:.1f} hours. "
                            f"Please review and assign to a cuadrilla."
                        )
                        await self.notification_service.send_alert(
                            alert_type="preplanificada",
                            ot_id=ot.id,
                            recipients=["coordinator@telconet.ec"],
                            message=alert_msg,
                        )

                        alerts_triggered += 1
                        logger.info(
                            f"GobernanzaAgent: Triggered preplanificada alert for OT {ot.external_id} "
                            f"after {hours_waiting:.1f} hours"
                        )

                    except Exception as e:
                        logger.warning(
                            f"GobernanzaAgent: Failed to send preplanificada alert: {str(e)}"
                        )
                        continue

            # Commit changes
            try:
                await self.db.commit()
            except Exception as e:
                await self.db.rollback()
                logger.error(f"GobernanzaAgent: Error committing changes: {str(e)}")

            # Log governance check completion
            await self.log_action(
                accion=f"Governance check complete - {alerts_triggered} alerts, {cancellations} cancellations",
                resultado="SUCCESS",
                metadata={
                    "alerts_triggered": alerts_triggered,
                    "cancellations": cancellations,
                    "ots_checked": len(detenida_ots) + len(preplanificada_ots),
                },
            )

            # Update state
            state["agent_messages"].append({
                "agent": "GobernanzaAgent",
                "content": f"Governance check: {alerts_triggered} alerts, {cancellations} auto-cancellations",
                "timestamp": datetime.utcnow().isoformat(),
            })

            state["action_result"] = {
                "success": True,
                "message": f"Governance check complete",
                "data": {
                    "alerts_triggered": alerts_triggered,
                    "cancellations": cancellations,
                },
            }

            logger.info(
                f"GobernanzaAgent: Completed governance checks - "
                f"{alerts_triggered} alerts, {cancellations} cancellations"
            )

            return state

        except Exception as e:
            logger.error(f"GobernanzaAgent error: {str(e)}", exc_info=True)
            return await self.handle_error(state, f"GobernanzaAgent error: {str(e)}")

    async def validate_transition(
        self, ot_id: int, new_status: str, reason: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validate an OT status transition against business rules.

        Args:
            ot_id (int): OT ID to validate
            new_status (str): Target status
            reason (str, optional): Reason for transition (required for DETENIDA)

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            # Get OT
            result = await self.db.execute(select(OT).where(OT.id == ot_id))
            ot = result.scalars().first()

            if not ot:
                return False, f"OT {ot_id} not found"

            # Validate status value
            try:
                target_status = OTStatus[new_status]
            except KeyError:
                return False, f"Invalid status: {new_status}"

            # Check if transition is allowed
            if not ot.can_transition_to(target_status):
                return (
                    False,
                    f"Cannot transition from {ot.status.value} to {new_status}",
                )

            # Special validation for DETENIDA
            if target_status == OTStatus.DETENIDA:
                if not reason:
                    return False, "Detention reason is required"
                if len(reason) < 10:
                    return False, "Detention reason must be at least 10 characters"

            # Special validation for FINALIZADA
            if target_status == OTStatus.FINALIZADA:
                if ot.project_type == ProjectType.PUBLICO:
                    # Check document count
                    doc_result = await self.api_service.get_telcodrive_documents(
                        ot.external_id
                    )
                    if doc_result.get("success"):
                        doc_count = doc_result.get("document_count", 0)
                        if doc_count < 29:
                            return (
                                False,
                                f"PUBLICO project requires 29 documents ({doc_count}/29 present)",
                            )
                    else:
                        return False, "Could not verify document count"

            logger.info(
                f"GobernanzaAgent: Transition validated for OT {ot_id}: "
                f"{ot.status.value} → {new_status}"
            )
            return True, ""

        except Exception as e:
            logger.error(f"GobernanzaAgent: Error validating transition: {str(e)}")
            return False, f"Validation error: {str(e)}"

    async def check_capacity_constraint(
        self, cuadrilla_id: int, ot_count: int = 1
    ) -> Tuple[bool, str]:
        """
        Check if a cuadrilla has capacity for additional OTs.

        Args:
            cuadrilla_id (int): Cuadrilla ID to check
            ot_count (int): Number of OTs to assign

        Returns:
            Tuple[bool, str]: (has_capacity, message)
        """
        try:
            from src.models import Cuadrilla

            result = await self.db.execute(
                select(Cuadrilla).where(Cuadrilla.id == cuadrilla_id)
            )
            cuadrilla = result.scalars().first()

            if not cuadrilla:
                return False, f"Cuadrilla {cuadrilla_id} not found"

            available_capacity = (
                cuadrilla.max_daily_capacity - cuadrilla.current_load
            )
            if available_capacity < ot_count:
                return (
                    False,
                    f"Cuadrilla {cuadrilla.name} does not have capacity "
                    f"({available_capacity}/{ot_count} available)",
                )

            return True, ""

        except Exception as e:
            logger.error(f"GobernanzaAgent: Error checking capacity: {str(e)}")
            return False, f"Capacity check error: {str(e)}"

