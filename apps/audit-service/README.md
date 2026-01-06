# Audit Service

FastAPI service for audit trail and compliance tracking in DERCAS-ONCO-XAI V1 platform.

## Responsibilities

- RabbitMQ event consumption from all services
- Audit event persistence in PostgreSQL
- Query APIs with filtering capabilities
- Event ingestion with idempotency and correlation tracking
- Complete audit trails for compliance

## Endpoints

- `GET /api/v1/audit/events` - Query audit events with filters
- `GET /api/v1/audit/events/{eventId}` - Get specific audit event

## Query Parameters

- `caseId` - Filter by case ID
- `type` - Filter by event type
- `from` - Start date filter
- `to` - End date filter

## Development

```bash
cd apps/audit-service
python -m uvicorn main:app --reload --port 8007
```
