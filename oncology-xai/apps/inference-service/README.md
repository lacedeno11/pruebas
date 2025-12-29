# Inference Service

The Inference Service is a core component of the Oncology XAI system, responsible for running machine learning inference jobs on medical images using LangGraph workflows.

## Features

- **FastAPI REST API** - High-performance async API running on port 8003
- **Celery Integration** - Asynchronous job processing with Redis backend
- **LangGraph Workflows** - ImageAnalysisGraph workflow for advanced image analysis
- **Database Models** - Comprehensive models for jobs, results, patterns, genetic markers, and XAI artifacts
- **Event Publishing** - RabbitMQ integration for job completion events
- **Database Migrations** - Alembic for schema management

## Architecture

```
inference-service/
├── src/inference_service/
│   ├── models/           # Database models
│   ├── routes/           # API routes
│   ├── services/         # Business logic
│   ├── tasks/            # Celery tasks
│   ├── config.py         # Configuration
│   ├── database.py       # Database setup
│   └── main.py           # FastAPI application
├── alembic/              # Database migrations
├── Dockerfile            # Container image
└── docker-compose.yml    # Local development stack
```

## API Endpoints

### Inference Operations

- `POST /api/v1/images/{imageId}/process` - Start inference job for an image
- `GET /api/v1/jobs/{jobId}` - Get job status and details
- `GET /api/v1/images/{imageId}/results/latest` - Get latest results for an image
- `GET /api/v1/results/{resultBundleId}` - Get complete result bundle
- `GET /api/v1/results/{resultBundleId}/artifacts` - Get XAI artifacts

### Health & Info

- `GET /health` - Health check endpoint
- `GET /` - Service information
- `GET /docs` - OpenAPI documentation
- `GET /redoc` - ReDoc documentation

## Database Models

### MLJob
Tracks inference job lifecycle and status.

### ResultBundle
Contains all inference outputs for a single job.

### PatternResult
Morphological and architectural patterns detected in images.

### GeneticResult
Genetic markers and their clinical significance.

### XAIArtifact
Explainable AI artifacts (heatmaps, feature importance, etc.)

## Quick Start

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec inference-api alembic upgrade head

# View logs
docker-compose logs -f inference-api

# Stop services
docker-compose down
```

### Local Development

```bash
# Install dependencies
pip install -e .

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start API server
uvicorn inference_service.main:app --host 0.0.0.0 --port 8003 --reload

# Start Celery worker (in another terminal)
celery -A inference_service.celery_app worker --loglevel=info --queues=inference

# Start Celery Flower (optional, for monitoring)
celery -A inference_service.celery_app flower --port=5555
```

## Configuration

Configuration is managed through environment variables:

```bash
# Application
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

# Database
DATABASE_URL=postgresql://user:pass@host:5432/inference_db

# Redis & Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_EXCHANGE=oncology_xai
RABBITMQ_ROUTING_KEY=inference.completed

# External Services
IMAGE_SERVICE_URL=http://localhost:8001
```

## LangGraph Integration

The service integrates with ImageAnalysisGraph workflow from the langgraph_workflows package:

```python
from inference_service.tasks.inference_task import run_langgraph_workflow

# Run workflow
results = run_langgraph_workflow(image_id)
```

The workflow returns:
- Overall confidence scores
- Pattern detection results
- Genetic marker analysis
- XAI artifacts (heatmaps, feature importance, GradCAM)

## Job Lifecycle

1. **PENDING** - Job created, waiting for processing
2. **PROCESSING** - Celery worker running inference
3. **COMPLETED** - Results saved, event emitted
4. **FAILED** - Error occurred, details logged
5. **CANCELLED** - Job cancelled by user

## Event Publishing

On job completion, events are published to RabbitMQ:

```json
{
  "event_type": "inference.completed",
  "job_id": "uuid",
  "image_id": "uuid",
  "result_bundle_id": "uuid",
  "timestamp": "2025-01-01T00:00:00Z"
}
```

## Monitoring

- **API Docs**: http://localhost:8003/docs
- **Celery Flower**: http://localhost:5555
- **RabbitMQ Management**: http://localhost:15672

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=inference_service --cov-report=html

# Lint
ruff check .
black --check .

# Type checking
mypy .
```

## Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one revision
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

## Troubleshooting

### Database Connection Issues
- Verify DATABASE_URL is correct
- Check PostgreSQL is running
- Ensure migrations are applied

### Celery Worker Not Processing
- Check CELERY_BROKER_URL is correct
- Verify Redis is running
- Check worker logs for errors

### RabbitMQ Connection Issues
- Verify RABBITMQ_URL is correct
- Check RabbitMQ is running
- Ensure exchange exists

## Production Deployment

For production deployment:

1. Set `DEBUG=false`
2. Use production-grade PostgreSQL
3. Configure proper Redis persistence
4. Set up RabbitMQ cluster
5. Use environment-specific secrets
6. Enable HTTPS/TLS
7. Configure CORS appropriately
8. Set up monitoring and alerts
9. Scale Celery workers as needed
10. Implement rate limiting

## License

Copyright 2025 Oncology XAI System
