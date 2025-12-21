"""
CRM/Ticketing Service.

Handles integration with external CRM and ticketing systems.
Based on UC-OP-05 Case Ingest.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from policy_validation_copilot.models.case import (
    Case,
    CaseState,
    CasePriority,
    Attachment,
)

logger = logging.getLogger(__name__)


class CRMServiceError(Exception):
    """Error in CRM operations."""

    pass


class CRMService:
    """
    CRM/Ticketing service client.

    Handles case creation, updates, and synchronization.
    """

    def __init__(
        self,
        crm_api_url: Optional[str] = None,
        default_sla_minutes: int = 240,
    ):
        self.crm_api_url = crm_api_url
        self.default_sla_minutes = default_sla_minutes
        # In production, would maintain HTTP client for CRM API
        self._case_cache: dict[str, Case] = {}

    async def create_case_from_ticket(
        self,
        ticket_payload: dict,
        channel: str = "CRM",
    ) -> Case:
        """
        Create a case from CRM/ticket payload.

        UC-OP-05: Normalizes fields and applies idempotency.
        """
        # Extract and normalize fields
        ticket_id = ticket_payload.get("ticket_id") or ticket_payload.get("id")
        if not ticket_id:
            raise CRMServiceError("Missing ticket_id in payload")

        # Idempotency check
        existing = await self._check_idempotency(ticket_id, ticket_payload)
        if existing:
            logger.info(f"Idempotent case found for ticket {ticket_id}")
            return existing

        # Generate case ID
        case_id = f"CASE-{uuid4().hex[:8].upper()}"

        # Normalize priority
        priority = self._normalize_priority(ticket_payload.get("priority"))

        # Calculate SLA
        sla_target = self._calculate_sla(priority)

        # Build case
        case = Case(
            case_id=case_id,
            crm_ticket_id=ticket_id,
            customer_id=ticket_payload.get("customer_id", "UNKNOWN"),
            contract_id=ticket_payload.get("contract_id"),
            insurer_id=ticket_payload.get("insurer_id", "UNKNOWN"),
            plan_id=ticket_payload.get("plan_id", "UNKNOWN"),
            service_code=ticket_payload.get("service_code"),
            service_description=ticket_payload.get("service_description")
            or ticket_payload.get("description"),
            service_date=self._parse_date(ticket_payload.get("service_date")),
            provider_id=ticket_payload.get("provider_id"),
            priority=priority,
            sla_target=sla_target,
            state=CaseState.CREATED,
            channel=channel,
            created_by="SYSTEM",
            normalization_log={
                "original_priority": ticket_payload.get("priority"),
                "normalized_priority": priority.value,
                "sla_calculated": sla_target.isoformat() if sla_target else None,
            },
        )

        # Cache for idempotency
        self._case_cache[self._idempotency_key(ticket_id, ticket_payload)] = case

        logger.info(f"Created case {case_id} from ticket {ticket_id}")
        return case

    async def _check_idempotency(
        self,
        ticket_id: str,
        payload: dict,
    ) -> Optional[Case]:
        """Check if case already exists for this ticket."""
        key = self._idempotency_key(ticket_id, payload)
        return self._case_cache.get(key)

    def _idempotency_key(self, ticket_id: str, payload: dict) -> str:
        """Generate idempotency key from ticket and payload hash."""
        import hashlib
        import json

        payload_str = json.dumps(payload, sort_keys=True, default=str)
        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:16]
        return f"{ticket_id}:{payload_hash}"

    def _normalize_priority(self, raw_priority: Optional[str]) -> CasePriority:
        """Normalize priority from various CRM formats."""
        if not raw_priority:
            return CasePriority.NORMAL

        raw = raw_priority.upper().strip()
        priority_map = {
            "P1": CasePriority.URGENT,
            "P2": CasePriority.HIGH,
            "P3": CasePriority.NORMAL,
            "P4": CasePriority.LOW,
            "CRITICAL": CasePriority.URGENT,
            "URGENT": CasePriority.URGENT,
            "HIGH": CasePriority.HIGH,
            "MEDIUM": CasePriority.NORMAL,
            "NORMAL": CasePriority.NORMAL,
            "LOW": CasePriority.LOW,
        }
        return priority_map.get(raw, CasePriority.NORMAL)

    def _calculate_sla(self, priority: CasePriority) -> datetime:
        """Calculate SLA deadline based on priority."""
        multipliers = {
            CasePriority.URGENT: 0.25,
            CasePriority.HIGH: 0.5,
            CasePriority.NORMAL: 1.0,
            CasePriority.LOW: 2.0,
        }
        minutes = int(self.default_sla_minutes * multipliers[priority])
        return datetime.utcnow() + timedelta(minutes=minutes)

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime."""
        if not date_str:
            return None

        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%d/%m/%Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    async def update_case_status(
        self,
        case_id: str,
        status: str,
        notes: Optional[str] = None,
    ) -> bool:
        """Update case status in CRM."""
        # In production, would call CRM API
        logger.info(f"Updating case {case_id} status to {status}")
        return True

    async def add_case_note(
        self,
        case_id: str,
        note: str,
        note_type: str = "SYSTEM",
    ) -> bool:
        """Add a note to the case in CRM."""
        logger.info(f"Adding note to case {case_id}: {note[:50]}...")
        return True

    async def get_case_history(
        self,
        customer_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """Get historical cases for a customer."""
        # In production, would query CRM
        return []
