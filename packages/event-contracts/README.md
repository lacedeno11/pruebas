# Event Contracts Package

Standard event envelope schema and RabbitMQ helpers for the DERCAS-ONCO-XAI platform.

## Features

- Standard event envelope schema
- RabbitMQ publish/consume helpers
- Event type definitions
- JSON schemas for validation
- Event serialization/deserialization
- Dead letter queue handling
- Event deduplication utilities

## Event Envelope Schema

```json
{
  "eventId": "evt_...",
  "eventType": "inference.completed",
  "timestamp": "ISO-8601",
  "correlationId": "corr_...",
  "producer": "inference-service",
  "caseId": "case_...",
  "payload": {}
}
```

## Event Types

### Case Events
- `case.created`
- `case.updated`

### Image Events
- `image.uploaded`
- `image.deleted`

### Job Events
- `job.created`
- `job.progress`
- `job.completed`
- `job.failed`

### Inference Events
- `inference.completed`
- `inference.failed`

### EHR Events
- `ehr.ingested`
- `ehr.extracted`
- `ehr.mapped`

### Graph Events
- `graph.built`
- `graph.failed`

### Ontology Events
- `ontology.proposal.created`
- `ontology.published`
- `ontology.rollbacked`

### Audit Events
- `audit.event.created`

## Usage

```python
from packages.event_contracts import EventEnvelope, EventPublisher, EventConsumer

# Publishing events
publisher = EventPublisher(rabbitmq_url)
event = EventEnvelope(
    event_type="case.created",
    producer="case-service",
    case_id="case_123",
    payload={"patient_id": "patient_456"}
)
await publisher.publish(event)

# Consuming events
consumer = EventConsumer(rabbitmq_url)
await consumer.subscribe("case.created", handle_case_created)
```
