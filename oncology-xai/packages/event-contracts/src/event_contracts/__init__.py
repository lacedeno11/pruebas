"""Event contracts for Oncology XAI."""

from event_contracts.envelope import EventEnvelope, create_event
from event_contracts.types import (
    EventType,
    CaseCreatedPayload,
    CaseUpdatedPayload,
    ImageUploadedPayload,
    ImageDeletedPayload,
    JobCreatedPayload,
    JobProgressPayload,
    JobCompletedPayload,
    JobFailedPayload,
    InferenceCompletedPayload,
    EHRIngestedPayload,
    EHRExtractedPayload,
    EHRMappedPayload,
    GraphBuiltPayload,
    OntologyPublishedPayload,
)

__version__ = "0.1.0"

__all__ = [
    "EventEnvelope",
    "create_event",
    "EventType",
    "CaseCreatedPayload",
    "CaseUpdatedPayload",
    "ImageUploadedPayload",
    "ImageDeletedPayload",
    "JobCreatedPayload",
    "JobProgressPayload",
    "JobCompletedPayload",
    "JobFailedPayload",
    "InferenceCompletedPayload",
    "EHRIngestedPayload",
    "EHRExtractedPayload",
    "EHRMappedPayload",
    "GraphBuiltPayload",
    "OntologyPublishedPayload",
]
