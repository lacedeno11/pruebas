# Event Contracts Package

Event schemas and messaging utilities for DERCAS-ONCO-XAI V1 platform.

## Contents

### Event Envelope Schema
- Standardized event envelope format
- Event type definitions and validation
- Correlation ID and tracing support

### Event Types
- `case.created` - New case created
- `case.updated` - Case status or metadata updated
- `image.uploaded` - New image uploaded
- `image.deleted` - Image removed
- `job.created` - Async job started
- `job.progress` - Job progress update
- `job.completed` - Job finished successfully
- `job.failed` - Job failed with error
- `inference.completed` - ML inference completed
- `inference.failed` - ML inference failed
- `ehr.ingested` - EHR document ingested
- `ehr.extracted` - Entities extracted from EHR
- `ehr.mapped` - Entities mapped to ontologies
- `graph.built` - Knowledge graph constructed
- `graph.failed` - Graph construction failed
- `ontology.proposal.created` - New ontology update proposal
- `ontology.published` - Ontology version published
- `ontology.rollbacked` - Ontology version rolled back
- `audit.event.created` - Audit event recorded

### RabbitMQ Helpers
- Event publishing utilities
- Event consumption patterns
- Dead letter queue handling
- Retry mechanisms

### JSON Schemas
- Event payload validation
- Schema versioning support
- Backward compatibility checks

## Usage

```python
from packages.event_contracts import EventEnvelope, EventType
from packages.event_contracts.publishers import publish_event
from packages.event_contracts.consumers import consume_events

# Publishing an event
await publish_event(
    event_type=EventType.CASE_CREATED,
    payload={"caseId": "case_123", "patientId": "patient_456"},
    correlation_id="corr_789"
)

# Consuming events
async for event in consume_events(EventType.CASE_CREATED):
    # Process event
    pass
```
