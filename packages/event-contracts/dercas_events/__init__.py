"""
DERCAS-ONCO-XAI Event Contracts

Event envelope schema and RabbitMQ publish/consume helpers for event-driven architecture.
"""

__version__ = "0.1.0"

from .envelope import *
from .publisher import *
from .consumer import *
from .events import *

__all__ = [
    # Envelope
    "EventEnvelope",
    "EventMetadata",
    "validate_event_envelope",
    
    # Publisher
    "EventPublisher",
    "publish_event",
    "init_event_publisher",
    
    # Consumer
    "EventConsumer",
    "EventHandler",
    "consume_events",
    "register_event_handler",
    
    # Events
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
