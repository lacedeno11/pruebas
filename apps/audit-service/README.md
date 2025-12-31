# Audit Service

Comprehensive audit trail service with RabbitMQ event consumption and query APIs.

## Features

- RabbitMQ event consumption for comprehensive audit trail
- Database model for audit_events with correlation tracking
- Query APIs with filtering by caseId, userId, event type, and time ranges
- PHI redaction in logs
- Event deduplication by eventId/correlationId
- Efficient indexing for audit queries
- Audit event standardization
- Optional SIEM export capabilities

## Endpoints

- `GET /api/v1/audit/events` - Query audit events with filters
- `GET /api/v1/audit/events/{eventId}` - Get specific audit event

## Development

```bash
cd apps/audit-service
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload --port 8007
```
