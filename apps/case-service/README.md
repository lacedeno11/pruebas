# Case Service

Patient and case management service with SQLAlchemy 2.0 models and event emission.

## Features

- CRUD operations for patients and cases
- Case status management (CREATED, READY, PROCESSING, REVIEW_REQUIRED, CLOSED)
- Event emission (case.created, case.updated) via RabbitMQ
- Alembic database migrations
- Comprehensive validation and testing

## Endpoints

- `POST /api/v1/patients` - Create patient
- `GET /api/v1/patients` - List patients with query
- `GET /api/v1/patients/{patientId}` - Get patient details
- `POST /api/v1/cases` - Create case
- `GET /api/v1/cases` - List cases by patient
- `GET /api/v1/cases/{caseId}` - Get case details
- `PATCH /api/v1/cases/{caseId}` - Update case

## Development

```bash
cd apps/case-service
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload --port 8001
```
