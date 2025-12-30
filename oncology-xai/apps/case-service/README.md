# Case Service

Patient and case management service for the DERCAS-ONCO-XAI V1 platform.

## Overview

The Case Service provides comprehensive patient and case management functionality for the oncology platform. It handles:

- **Patient Management**: CRUD operations for patient records with demographics and medical information
- **Case Management**: Clinical case lifecycle management with status tracking and metadata
- **Event Emission**: Real-time event publishing for case and patient lifecycle events
- **Database Persistence**: SQLAlchemy 2.0 with PostgreSQL and Alembic migrations
- **Comprehensive Testing**: Unit tests, integration tests, and API testing

## Features

### Patient Management
- Create, read, update, and delete patient records
- Support for external patient IDs and medical record numbers
- Patient demographics with age calculation
- Soft delete functionality
- Comprehensive validation and error handling

### Case Management
- Clinical case creation and management
- Case status tracking (draft, active, completed, archived)
- Priority levels (low, normal, high, urgent)
- Processing status tracking for AI workflows
- Tag-based categorization
- Flexible metadata storage
- Case-to-patient relationships

### Event-Driven Architecture
- Real-time event emission for all lifecycle changes
- RabbitMQ integration for reliable message delivery
- Event types: `patient.created`, `patient.updated`, `case.created`, `case.updated`, `case.status_changed`, `case.processing_status_changed`
- Correlation ID tracking for distributed tracing

### Database Features
- SQLAlchemy 2.0 with async support
- PostgreSQL with JSONB for flexible metadata
- Alembic migrations for schema management
- Comprehensive indexing for performance
- Audit fields (created_at, updated_at, created_by, updated_by)
- Soft delete support

## API Endpoints

### Patient Endpoints
- `POST /api/v1/patients` - Create a new patient
- `GET /api/v1/patients` - List patients with pagination and filtering
- `GET /api/v1/patients/{patient_id}` - Get patient by ID
- `PUT /api/v1/patients/{patient_id}` - Update patient
- `DELETE /api/v1/patients/{patient_id}` - Delete patient (soft delete)
- `GET /api/v1/patients/{patient_id}/cases` - List cases for a patient

### Case Endpoints
- `POST /api/v1/cases` - Create a new case
- `GET /api/v1/cases` - List cases with pagination and filtering
- `GET /api/v1/cases/{case_id}` - Get case by ID
- `PATCH /api/v1/cases/{case_id}` - Update case
- `DELETE /api/v1/cases/{case_id}` - Delete case (soft delete)
- `GET /api/v1/cases/statistics/summary` - Get case statistics

### Health and Utility Endpoints
- `GET /healthz` - Health check
- `GET /api/v1/info` - Service information
- `POST /api/v1/seed` - Seed development data (debug mode only)

## Configuration

The service is configured via environment variables:

```bash
# Application settings
DEBUG=false
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8001

# Database
DATABASE_URL=postgresql+asyncpg://oncology_user:oncology_pass@localhost:5432/oncology_xai
DATABASE_ECHO=false
DATABASE_POOL_SIZE=10

# RabbitMQ for events
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_EXCHANGE=oncology-xai
RABBITMQ_ROUTING_KEY_PREFIX=case

# Security
SECRET_KEY=your-secret-key

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Observability
JAEGER_ENDPOINT=http://localhost:14268/api/traces
PROMETHEUS_ENABLED=true
LOG_LEVEL=INFO

# Pagination
DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100
```

## Database Schema

### Patients Table
- `id` (UUID) - Primary key
- `external_id` (String) - External patient ID (unique)
- `first_name` (String) - Patient first name
- `last_name` (String) - Patient last name
- `date_of_birth` (DateTime) - Patient date of birth
- `gender` (String) - Patient gender (M/F/O/U)
- `medical_record_number` (String) - Medical record number (unique)
- `metadata` (JSONB) - Additional patient metadata
- Audit fields: `created_at`, `updated_at`, `created_by`, `updated_by`
- `is_active` (Boolean) - Soft delete flag

### Cases Table
- `id` (UUID) - Primary key
- `patient_id` (UUID) - Foreign key to patients
- `external_id` (String) - External case ID
- `title` (String) - Case title
- `description` (Text) - Case description
- `status` (String) - Case status (draft, active, completed, archived)
- `priority` (String) - Case priority (low, normal, high, urgent)
- `diagnosis` (Text) - Clinical diagnosis
- `clinical_notes` (Text) - Clinical notes
- `case_date` (DateTime) - Case date
- `admission_date` (DateTime) - Admission date
- `discharge_date` (DateTime) - Discharge date
- `tags` (JSONB) - Case tags array
- `metadata` (JSONB) - Additional case metadata
- Processing fields: `processing_status`, `processing_progress`, `processing_error`
- Data flags: `has_images`, `has_ehr_data`, `has_inference_results`, `has_graph_data`
- Audit fields: `created_at`, `updated_at`, `created_by`, `updated_by`
- `is_active` (Boolean) - Soft delete flag

## Development

### Running Locally

```bash
# Install dependencies
pip install -e .

# Set up database
alembic upgrade head

# Run the service
uvicorn src.case_service.main:app --reload --host 0.0.0.0 --port 8001

# Or use the Makefile from project root
make case-service-dev
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/case_service

# Run specific test file
pytest tests/test_models.py

# Run integration tests
pytest tests/test_api.py -m integration
```

### Seed Data

The service includes comprehensive seed data for development:

```bash
# Seed data is automatically loaded in development mode
# Or manually trigger via API (debug mode only)
curl -X POST http://localhost:8001/api/v1/seed \
  -H "Authorization: Bearer <token>"
```

Seed data includes:
- 8 sample patients with realistic demographics
- 8 sample cases covering various lung cancer scenarios
- Different case statuses and priorities
- Realistic clinical metadata and tags

## Docker

```bash
# Build image
docker build -t oncology-xai-case-service .

# Run container
docker run -p 8001:8001 --env-file .env oncology-xai-case-service

# Or use docker-compose from project root
docker-compose up case-service
```

## API Documentation

When running in debug mode, API documentation is available at:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`
- OpenAPI JSON: `http://localhost:8001/openapi.json`

## Event Schema

### Patient Events

**patient.created / patient.updated**
```json
{
  "event_id": "01234567-89ab-cdef-0123-456789abcdef",
  "event_type": "patient.created",
  "timestamp": "2024-01-01T12:00:00Z",
  "correlation_id": "01234567-89ab-cdef-0123-456789abcdef",
  "producer": "case-service",
  "case_id": null,
  "payload": {
    "patient_id": "01234567-89ab-cdef-0123-456789abcdef",
    "full_name": "John Smith",
    "medical_record_number": "MRN001234",
    "created_by": "user123"
  }
}
```

### Case Events

**case.created / case.updated**
```json
{
  "event_id": "01234567-89ab-cdef-0123-456789abcdef",
  "event_type": "case.created",
  "timestamp": "2024-01-01T12:00:00Z",
  "correlation_id": "01234567-89ab-cdef-0123-456789abcdef",
  "producer": "case-service",
  "case_id": "01234567-89ab-cdef-0123-456789abcdef",
  "payload": {
    "case_id": "01234567-89ab-cdef-0123-456789abcdef",
    "patient_id": "01234567-89ab-cdef-0123-456789abcdef",
    "title": "Suspected Lung Adenocarcinoma",
    "status": "active",
    "processing_status": "pending",
    "created_by": "user123"
  }
}
```

**case.status_changed**
```json
{
  "event_id": "01234567-89ab-cdef-0123-456789abcdef",
  "event_type": "case.status_changed",
  "timestamp": "2024-01-01T12:00:00Z",
  "correlation_id": "01234567-89ab-cdef-0123-456789abcdef",
  "producer": "case-service",
  "case_id": "01234567-89ab-cdef-0123-456789abcdef",
  "payload": {
    "case_id": "01234567-89ab-cdef-0123-456789abcdef",
    "patient_id": "01234567-89ab-cdef-0123-456789abcdef",
    "title": "Suspected Lung Adenocarcinoma",
    "old_status": "draft",
    "new_status": "active",
    "processing_status": "pending",
    "updated_by": "user123"
  }
}
```

## Error Handling

The service provides comprehensive error handling with structured responses:

```json
{
  "error": "Validation failed",
  "message": "Patient with MRN 'MRN001234' already exists",
  "correlation_id": "01234567-89ab-cdef-0123-456789abcdef"
}
```

Common error scenarios:
- `400 Bad Request` - Invalid input data
- `404 Not Found` - Resource not found
- `409 Conflict` - Duplicate external ID or MRN
- `422 Unprocessable Entity` - Validation errors
- `500 Internal Server Error` - Unexpected errors

## Monitoring

### Health Checks
- `/healthz` - Basic health check for load balancers
- Database connectivity verification
- Service startup time tracking

### Logging
Structured JSON logging with correlation IDs:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "info",
  "message": "Patient created successfully",
  "patient_id": "01234567-89ab-cdef-0123-456789abcdef",
  "user_id": "user123",
  "correlation_id": "01234567-89ab-cdef-0123-456789abcdef"
}
```

### Metrics
- Request count and duration
- Database query performance
- Event emission success/failure rates
- Error rates by endpoint

## Security

### Authentication
- JWT token validation via shared auth utilities
- User context extraction from tokens
- Role-based access control integration

### Data Protection
- Soft delete for data retention
- Audit trails for all changes
- Input validation and sanitization
- SQL injection prevention via SQLAlchemy

### Privacy
- No sensitive medical data in logs
- Correlation ID tracking without PII
- Configurable data retention policies

## Performance

### Database Optimization
- Comprehensive indexing strategy
- Connection pooling with configurable limits
- Async database operations
- Query optimization with SQLAlchemy 2.0

### Caching Strategy
- No caching at service level (handled by API Gateway)
- Database query optimization
- Efficient pagination with offset/limit

### Scalability
- Stateless service design
- Horizontal scaling support
- Event-driven architecture for loose coupling
- Async processing for non-blocking operations

## Troubleshooting

### Common Issues

1. **Database connection errors**
   - Check DATABASE_URL configuration
   - Verify PostgreSQL is running
   - Check network connectivity

2. **Migration failures**
   - Ensure database user has proper permissions
   - Check for conflicting schema changes
   - Review migration logs

3. **Event publishing failures**
   - Verify RabbitMQ connectivity
   - Check exchange and routing key configuration
   - Review RabbitMQ logs

4. **Validation errors**
   - Check input data format
   - Verify required fields are provided
   - Review API documentation for constraints

### Debug Mode
Enable debug mode for development:

```bash
DEBUG=true
```

This enables:
- Detailed error messages
- API documentation endpoints
- Seed data endpoint
- SQL query logging (if DATABASE_ECHO=true)

## Contributing

### Code Style
- Follow PEP 8 guidelines
- Use type hints throughout
- Write comprehensive docstrings
- Maintain test coverage above 90%

### Testing Requirements
- Unit tests for all models and CRUD operations
- Integration tests for API endpoints
- Event emission testing
- Database migration testing

### Pull Request Process
1. Create feature branch from main
2. Implement changes with tests
3. Run full test suite
4. Update documentation if needed
5. Submit pull request with description
