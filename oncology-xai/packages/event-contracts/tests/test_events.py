"""Tests for event contracts."""
import pytest
from uuid import uuid4
from datetime import datetime
from event_contracts import EventType, EventEnvelope, create_event


class TestEventType:
    def test_all_event_types_defined(self):
        expected_types = [
            "CASE_CREATED",
            "CASE_UPDATED",
            "IMAGE_UPLOADED",
            "INFERENCE_STARTED",
            "INFERENCE_COMPLETED",
            "INFERENCE_FAILED",
            "EHR_INGESTED",
            "ENTITIES_EXTRACTED",
            "ONTOLOGY_MAPPED",
            "GRAPH_UPDATED",
            "EXPLANATION_GENERATED",
            "AUDIT_EVENT",
        ]
        for event_type in expected_types:
            assert hasattr(EventType, event_type)

    def test_event_type_values(self):
        assert EventType.CASE_CREATED.value == "case.created"
        assert EventType.IMAGE_UPLOADED.value == "image.uploaded"
        assert EventType.INFERENCE_COMPLETED.value == "inference.completed"


class TestEventEnvelope:
    def test_envelope_creation(self):
        envelope = EventEnvelope(
            event_id=str(uuid4()),
            event_type=EventType.CASE_CREATED,
            timestamp=datetime.utcnow().isoformat(),
            source="test-service",
            payload={"case_id": str(uuid4())},
        )
        assert envelope.event_type == EventType.CASE_CREATED
        assert envelope.source == "test-service"

    def test_envelope_with_correlation_id(self):
        envelope = EventEnvelope(
            event_id=str(uuid4()),
            event_type=EventType.CASE_CREATED,
            timestamp=datetime.utcnow().isoformat(),
            source="test-service",
            payload={},
            correlation_id="corr-123",
        )
        assert envelope.correlation_id == "corr-123"

    def test_envelope_with_case_id(self):
        case_id = str(uuid4())
        envelope = EventEnvelope(
            event_id=str(uuid4()),
            event_type=EventType.CASE_CREATED,
            timestamp=datetime.utcnow().isoformat(),
            source="test-service",
            payload={},
            case_id=case_id,
        )
        assert envelope.case_id == case_id


class TestCreateEvent:
    def test_create_event_function(self):
        payload = {"test": "data"}
        envelope = create_event(
            event_type=EventType.CASE_CREATED,
            source="test-service",
            payload=payload,
        )

        assert envelope.event_type == EventType.CASE_CREATED
        assert envelope.source == "test-service"
        assert envelope.payload == payload
        assert envelope.event_id is not None
        assert envelope.timestamp is not None

    def test_create_event_with_options(self):
        case_id = str(uuid4())
        correlation_id = "test-corr"

        envelope = create_event(
            event_type=EventType.IMAGE_UPLOADED,
            source="image-service",
            payload={"image_id": str(uuid4())},
            case_id=case_id,
            correlation_id=correlation_id,
        )

        assert envelope.case_id == case_id
        assert envelope.correlation_id == correlation_id
