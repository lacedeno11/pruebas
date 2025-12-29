# Audit Service - Quick Start Guide

## Quick Setup (Local Development)

### 1. Install Dependencies
```bash
./run.sh install
# or
make install
```

### 2. Setup Environment
```bash
# Start PostgreSQL and RabbitMQ
./run.sh setup

# Or manually with docker-compose
docker-compose up -d postgres rabbitmq
```

### 3. Run Migrations
```bash
./run.sh migrate
# or
make migrate
```

### 4. Start the Service
```bash
./run.sh dev
# or
make dev
```

The service will be available at:
- API: http://localhost:8007
- API Docs: http://localhost:8007/docs
- RabbitMQ Management: http://localhost:15672 (guest/guest)

## Quick Start with Docker

```bash
# Build and run everything
./run.sh docker
# or
make docker-up
```

## API Examples

### List All Audit Events
```bash
curl http://localhost:8007/api/v1/audit/events
```

### Filter by Case ID
```bash
curl "http://localhost:8007/api/v1/audit/events?case_id=case-123"
```

### Filter by Date Range
```bash
curl "http://localhost:8007/api/v1/audit/events?from=2025-01-01T00:00:00Z&to=2025-01-31T23:59:59Z"
```

### Filter with Pagination
```bash
curl "http://localhost:8007/api/v1/audit/events?page=1&page_size=20&user_id=user-456"
```

### Get Specific Event
```bash
curl http://localhost:8007/api/v1/audit/events/{event_id}
```

## Publishing Events to RabbitMQ

### Using Python (aio-pika)
```python
import asyncio
import json
from aio_pika import connect, Message, ExchangeType

async def publish_audit_event():
    # Connect to RabbitMQ
    connection = await connect("amqp://guest:guest@localhost:5672/")
    channel = await connection.channel()

    # Declare exchange
    exchange = await channel.declare_exchange(
        "oncology.events",
        ExchangeType.TOPIC,
        durable=True
    )

    # Create event data
    event = {
        "entity_type": "case",
        "entity_id": "case-123",
        "action": "created",
        "status": "success",
        "user_id": "user-456",
        "case_id": "case-123",
        "correlation_id": "req-789",
        "details_json": {
            "patient_name": "John Doe",
            "diagnosis": "Lung Cancer"
        },
        "source_service": "case-service",
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0..."
    }

    # Publish message
    message = Message(
        body=json.dumps(event).encode(),
        content_type="application/json"
    )

    await exchange.publish(message, routing_key="case.created")
    print("Event published!")

    await connection.close()

asyncio.run(publish_audit_event())
```

### Using Python (pika - sync)
```python
import pika
import json

# Connect to RabbitMQ
connection = pika.BlockingConnection(
    pika.ConnectionParameters('localhost')
)
channel = connection.channel()

# Declare exchange
channel.exchange_declare(
    exchange='oncology.events',
    exchange_type='topic',
    durable=True
)

# Create event data
event = {
    "entity_type": "analysis",
    "entity_id": "analysis-456",
    "action": "completed",
    "status": "success",
    "user_id": "user-789",
    "case_id": "case-123",
    "details_json": {
        "model": "xai-model-v1",
        "confidence": 0.95
    }
}

# Publish message
channel.basic_publish(
    exchange='oncology.events',
    routing_key='analysis.completed',
    body=json.dumps(event)
)

print("Event published!")
connection.close()
```

### Using curl (RabbitMQ Management API)
```bash
curl -i -u guest:guest -H "content-type:application/json" \
  -X POST http://localhost:15672/api/exchanges/%2F/oncology.events/publish \
  -d '{
    "properties": {},
    "routing_key": "test.event",
    "payload": "{\"entity_type\":\"test\",\"action\":\"test\",\"status\":\"success\"}",
    "payload_encoding": "string"
  }'
```

## Event Schema

All events should include these fields:

### Required Fields
- `entity_type` (string): Type of entity (e.g., "case", "analysis", "report")
- `action` (string): Action performed (e.g., "created", "updated", "deleted")
- `status` (string): Status of the action (e.g., "success", "failure", "pending")

### Optional but Recommended Fields
- `entity_id` (string): Identifier of the entity
- `user_id` (string): User who performed the action
- `case_id` (string): Associated case ID
- `correlation_id` (string): For tracking related events
- `details_json` (object): Additional event details
- `source_service` (string): Service that generated the event
- `ip_address` (string): Client IP address
- `user_agent` (string): Client user agent
- `metadata` (object): Additional metadata

### Example Event Types

**Case Created:**
```json
{
  "entity_type": "case",
  "entity_id": "case-123",
  "action": "created",
  "status": "success",
  "user_id": "user-456",
  "case_id": "case-123",
  "source_service": "case-service"
}
```

**Analysis Started:**
```json
{
  "entity_type": "analysis",
  "entity_id": "analysis-789",
  "action": "started",
  "status": "pending",
  "user_id": "user-456",
  "case_id": "case-123",
  "correlation_id": "req-abc",
  "source_service": "xai-service"
}
```

**Report Generated:**
```json
{
  "entity_type": "report",
  "entity_id": "report-321",
  "action": "generated",
  "status": "success",
  "user_id": "user-456",
  "case_id": "case-123",
  "details_json": {
    "format": "pdf",
    "pages": 12
  },
  "source_service": "report-service"
}
```

## Testing

### Run All Tests
```bash
./run.sh test
# or
make test
```

### Run Specific Test
```bash
poetry run pytest tests/test_api.py::test_health_check -v
```

## Development Commands

```bash
# Format code
./run.sh format

# Run linters
./run.sh lint

# Clean cache files
./run.sh clean

# Create new migration
make migrate-create name="add_new_field"
```

## Monitoring

### Check Service Health
```bash
curl http://localhost:8007/health
```

### View Logs
```bash
# If running with Docker Compose
docker-compose logs -f audit-service

# If running locally
# Logs will be in stdout
```

### RabbitMQ Management UI
- URL: http://localhost:15672
- Username: guest
- Password: guest

Check:
- Exchanges: `oncology.events` should be present
- Queues: `audit.events` should be present
- Bindings: Queue should be bound to exchange

## Troubleshooting

### Service won't start
1. Check PostgreSQL is running: `docker-compose ps postgres`
2. Check RabbitMQ is running: `docker-compose ps rabbitmq`
3. Check migrations are up to date: `make migrate`

### No events showing up
1. Check RabbitMQ queue has messages: Visit http://localhost:15672
2. Check service logs for errors
3. Verify event format matches schema
4. Confirm exchange and routing key are correct

### Database connection errors
1. Verify PostgreSQL is accessible
2. Check DATABASE_URL in .env
3. Ensure migrations have run

## Production Deployment

1. Set environment variables in .env
2. Use strong database credentials
3. Configure RabbitMQ authentication
4. Set LOG_LEVEL=INFO or WARN
5. Set DEBUG=false
6. Use a reverse proxy (nginx) for SSL termination
7. Monitor logs and metrics
8. Set up database backups
9. Configure RabbitMQ clustering for high availability

## Support

For issues or questions, refer to the main README.md or contact the development team.
