"""Event envelope definition."""

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field


T = TypeVar("T")


class EventEnvelope(BaseModel, Generic[T]):
    """Standard event envelope following spec.

    {
      "eventId": "evt_...",
      "eventType": "inference.completed",
      "timestamp": "ISO-8601",
      "correlationId": "corr_...",
      "producer": "inference-service",
      "caseId": "case_...",
      "payload": {}
    }
    """

    event_id: str = Field(..., alias="eventId")
    event_type: str = Field(..., alias="eventType")
    timestamp: datetime
    correlation_id: str = Field(..., alias="correlationId")
    producer: str
    case_id: str | None = Field(None, alias="caseId")
    payload: T

    class Config:
        populate_by_name = True

    @classmethod
    def create(
        cls,
        event_type: str,
        payload: T,
        producer: str,
        case_id: str | None = None,
        correlation_id: str | None = None,
    ) -> "EventEnvelope[T]":
        """Create a new event envelope."""
        return cls(
            eventId=f"evt_{uuid4().hex[:16]}",
            eventType=event_type,
            timestamp=datetime.now(timezone.utc),
            correlationId=correlation_id or f"corr_{uuid4().hex[:16]}",
            producer=producer,
            caseId=case_id,
            payload=payload,
        )


def create_event(
    event_type: str,
    payload: dict[str, Any],
    producer: str,
    case_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Create an event envelope as a dictionary."""
    envelope = EventEnvelope[dict].create(
        event_type=event_type,
        payload=payload,
        producer=producer,
        case_id=case_id,
        correlation_id=correlation_id,
    )
    return envelope.model_dump(by_alias=True, mode="json")
