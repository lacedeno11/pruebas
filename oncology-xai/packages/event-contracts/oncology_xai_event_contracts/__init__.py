# DERCAS-ONCO-XAI V1 - Event Contracts Package
# Event envelope schema and RabbitMQ publish/consume helpers

"""
Event contracts package for DERCAS-ONCO-XAI V1 platform.

This package contains:
- Event envelope schema (eventId, eventType, timestamp, correlationId, producer, caseId, payload)
- RabbitMQ publish/consume helpers
- JSON schemas for event validation
"""

__version__ = "1.0.0"

from .envelope import EventEnvelope, EventType
from .publisher import EventPublisher
from .consumer import EventConsumer
from .schemas import (
    CaseCreatedEvent,
    CaseUpdatedEvent,
    ImageUploadedEvent,
    ImageDeletedEvent,
    JobCreatedEvent,
    JobProgressEvent,
    JobCompletedEvent,
    JobFailedEvent,
    InferenceCompletedEvent,
    InferenceFailedEvent,
    EHRIngestedEvent,
    EHRExtractedEvent,
    EHRMappedEvent,
    GraphBuiltEvent,
    GraphFailedEvent,
    OntologyProposalCreatedEvent,
    OntologyPublishedEvent,
    OntologyRollbackedEvent,
    AuditEventCreatedEvent,
)

__all__ = [
    # Core
    "EventEnvelope",
    "EventType",
    "EventPublisher",
    "EventConsumer",
    # Event schemas
    "CaseCreatedEvent",
    "CaseUpdatedEvent",
    "ImageUploadedEvent",
    "ImageDeletedEvent",
    "JobCreatedEvent",
    "JobProgressEvent",
    "JobCompletedEvent",
    "JobFailedEvent",
    "InferenceCompletedEvent",
    "InferenceFailedEvent",
    "EHRIngestedEvent",
    "EHRExtractedEvent",
    "EHRMappedEvent",
    "GraphBuiltEvent",
    "GraphFailedEvent",
    "OntologyProposalCreatedEvent",
    "OntologyPublishedEvent",
    "OntologyRollbackedEvent",
    "AuditEventCreatedEvent",
]
