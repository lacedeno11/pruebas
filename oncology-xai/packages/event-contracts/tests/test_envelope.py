"""Tests for event envelope."""

from event_contracts import EventEnvelope, create_event, EventType


def test_create_event():
    """Test creating an event."""
    event = create_event(
        event_type=EventType.CASE_CREATED,
        payload={"case_id": "case_123", "patient_id": "patient_456"},
        producer="case-service",
        case_id="case_123",
    )

    assert event["eventType"] == "case.created"
    assert event["producer"] == "case-service"
    assert event["caseId"] == "case_123"
    assert event["payload"]["case_id"] == "case_123"
    assert event["eventId"].startswith("evt_")
    assert event["correlationId"].startswith("corr_")


def test_event_envelope_create():
    """Test EventEnvelope.create class method."""
    envelope = EventEnvelope.create(
        event_type="test.event",
        payload={"key": "value"},
        producer="test-service",
        correlation_id="corr_custom",
    )

    assert envelope.event_type == "test.event"
    assert envelope.producer == "test-service"
    assert envelope.correlation_id == "corr_custom"
    assert envelope.payload == {"key": "value"}


def test_event_envelope_serialization():
    """Test event envelope JSON serialization."""
    envelope = EventEnvelope.create(
        event_type="inference.completed",
        payload={"result_id": "res_123"},
        producer="inference-service",
        case_id="case_001",
    )

    data = envelope.model_dump(by_alias=True, mode="json")

    assert "eventId" in data
    assert "eventType" in data
    assert "correlationId" in data
    assert "caseId" in data
    assert data["caseId"] == "case_001"
