# Audit Service

The Audit Service is a critical component of the Oncology XAI system that tracks and stores all system events for compliance, debugging, and analytics purposes.

## Features

- **Event Consumption**: Listens to RabbitMQ events from the `oncology.events` exchange
- **Comprehensive Tracking**: Stores detailed audit trail with timestamps, user info, and event details
- **Efficient Querying**: Optimized database indexes for fast event retrieval
- **Flexible Filtering**: Filter events by case ID, user ID, type, action, status, and date range
- **Pagination Support**: Handle large result sets with configurable page sizes
- **RESTful API**: Clean API endpoints for querying audit events

## Architecture

- **Framework**: FastAPI (async/await)
- **Database**: PostgreSQL with SQLAlchemy (async)
- **Message Queue**: RabbitMQ (aio-pika)
- **Migrations**: Alembic

## API Endpoints

### Health Check
- `GET /health` - Service health status

### Audit Events
- `GET /api/v1/audit/events` - List audit events with filters
  - Query parameters: `case_id`, `user_id`, `entity_type`, `action`, `status`, `from`, `to`, `correlation_id`, `page`, `page_size`
- `GET /api/v1/audit/events/{eventId}` - Get specific event details

## Database Schema

### audit_events Table

| Column | Type | Description |
|--------|------|-------------|
| event_id | UUID | Primary key (auto-generated) |
| timestamp | TIMESTAMP | Event timestamp (auto-generated) |
| user_id | VARCHAR(255) | User who triggered the event |
| case_id | VARCHAR(255) | Associated case ID |
| entity_type | VARCHAR(100) | Type of entity (e.g., "case", "analysis") |
| entity_id | VARCHAR(255) | Entity identifier |
| action | VARCHAR(100) | Action performed (e.g., "created", "updated") |
| status | VARCHAR(50) | Event status (e.g., "success", "failure") |
| details_json | JSONB | Additional event details |
| correlation_id | VARCHAR(255) | For tracking related events |
| source_service | VARCHAR(100) | Service that generated the event |
| ip_address | VARCHAR(45) | Client IP address |
| user_agent | TEXT | Client user agent |
| metadata | JSONB | Additional metadata |

**Indexes:**
- Single column: `timestamp`, `user_id`, `case_id`, `entity_type`, `action`, `status`, `correlation_id`
- Composite: `(case_id, timestamp)`, `(user_id, timestamp)`, `(entity_type, action)`
- Descending: `timestamp DESC` for recent events

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- RabbitMQ 3.12+

### Installation

1. Install dependencies:
```bash
poetry install
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run database migrations:
```bash
alembic upgrade head
```

4. Start the service:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8007
```

## Docker

Build and run with Docker:

```bash
docker build -t audit-service .
docker run -p 8007:8007 --env-file .env audit-service
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `DATABASE_URL`: PostgreSQL connection string
- `RABBITMQ_URL`: RabbitMQ connection string
- `RABBITMQ_EXCHANGE`: Exchange name for events (default: "oncology.events")
- `PORT`: Service port (default: 8007)

## RabbitMQ Integration

The service automatically:
1. Connects to RabbitMQ on startup
2. Declares the `oncology.events` exchange (topic type)
3. Creates and binds the `audit.events` queue
4. Consumes messages with routing key `#` (all events)
5. Stores events in the database

### Event Message Format

Events should be published as JSON with the following structure:

```json
{
  "entity_type": "case",
  "entity_id": "case-123",
  "action": "created",
  "status": "success",
  "user_id": "user-456",
  "case_id": "case-123",
  "correlation_id": "req-789",
  "details_json": {
    "field": "value"
  },
  "source_service": "case-service",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "metadata": {}
}
```

## Development

### Run tests
```bash
pytest
```

### Code formatting
```bash
black app/
ruff check app/
```

### Type checking
```bash
mypy app/
```

## Monitoring

The service logs all events in JSON format for easy parsing and monitoring. Key log events:
- RabbitMQ connection status
- Event processing (success/failure)
- Database operations
- API requests

## Security

- No authentication required (handled by API Gateway RBAC)
- Read-only API endpoints
- Audit events are immutable (no update/delete operations)
- Correlation IDs for request tracing

## Performance

- Async/await for high concurrency
- Database connection pooling
- Optimized indexes for common queries
- Configurable RabbitMQ prefetch count
- Pagination to handle large datasets

## License

Copyright 2025 Oncology XAI Team
