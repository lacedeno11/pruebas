# Case Service

FastAPI service for patient and case management in DERCAS-ONCO-XAI V1 platform.

## Responsibilities

- CRUD operations for patients and cases
- Case status management (CREATED, READY, PROCESSING, REVIEW_REQUIRED, CLOSED)
- Event emission for case.created/case.updated
- SQLAlchemy 2.0 models and Alembic migrations

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
python -m uvicorn main:app --reload --port 8001
```
