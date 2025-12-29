# EHR Service

The EHR Service is responsible for ingesting, processing, and mapping clinical EHR text to ontologies in the Oncology XAI system.

## Features

- **EHR Ingestion**: Store clinical EHR text with versioning support
- **Entity Extraction**: Extract clinical entities (diagnoses, mutations, patterns, stages) using LLM
- **Ontology Mapping**: Map extracted entities to standard ontologies (NCIt, MONDO, SO)
- **Async Processing**: Celery-based async processing for heavy workflows
- **LangGraph Integration**: Uses EHRToOntologyGraph and ExplanationComposerGraph workflows
- **Mock LLM Support**: Supports mock LLM for development/testing

## Architecture

```
┌─────────────┐
│  FastAPI    │ Port 8004
│  REST API   │
└─────────────┘
      │
      ├─ POST /api/v1/cases/{caseId}/ehr:ingest
      ├─ GET  /api/v1/cases/{caseId}/ehr/versions
      ├─ GET  /api/v1/ehr/{ehrId}
      ├─ POST /api/v1/ehr/{ehrId}:extract-and-map
      ├─ GET  /api/v1/ehr/{ehrId}/entities
      ├─ GET  /api/v1/ehr/{ehrId}/mappings
      └─ POST /api/v1/cases/{caseId}:generate-explanation
      │
      ├─────────────┐
      │   Celery    │ Async Tasks
      │   Workers   │
      └─────────────┘
            │
            ├─ extract_and_map_task
            └─ generate_explanation_task
            │
      ├─────────────┐
      │  LangGraph  │ Workflows
      │  Workflows  │
      └─────────────┘
            │
            ├─ EHRToOntologyGraph
            └─ ExplanationComposerGraph
```

## Database Models

### ehr_documents
- `ehr_id` (UUID, PK)
- `case_id` (UUID, FK to cases)
- `version` (int)
- `raw_text` (text)
- `normalized_text` (text, nullable)
- `status` (enum: INGESTED, PROCESSING, ENTITIES_EXTRACTED, MAPPED, FAILED)
- `processing_metadata` (JSONB)
- `task_id` (string, nullable)
- `created_by` (string, nullable)
- `created_at` (timestamp)
- `updated_at` (timestamp, nullable)

### ehr_entities
- `entity_id` (UUID, PK)
- `ehr_id` (UUID, FK to ehr_documents)
- `entity_type` (string: DIAGNOSIS, MUTATION, PATTERN, STAGE)
- `text` (string)
- `start_position` (int, nullable)
- `end_position` (int, nullable)
- `confidence` (float)
- `section` (string, nullable)
- `metadata` (JSONB)
- `created_at` (timestamp)

### ehr_mappings
- `mapping_id` (UUID, PK)
- `ehr_id` (UUID, FK to ehr_documents)
- `entity_id` (UUID, FK to ehr_entities)
- `ontology` (string: NCIt, MONDO, SO, etc.)
- `iri` (string)
- `label` (string)
- `confidence` (float)
- `mapping_method` (string: automatic, manual, etc.)
- `evidence` (JSONB)
- `created_at` (timestamp)

## API Endpoints

### POST /api/v1/cases/{caseId}/ehr:ingest
Ingest EHR text for a case.

**Request:**
```json
{
  "ehr_text": "Patient presents with lung adenocarcinoma..."
}
```

**Response:**
```json
{
  "ehr_id": "uuid",
  "case_id": "uuid",
  "version": 1,
  "status": "INGESTED",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### GET /api/v1/cases/{caseId}/ehr/versions
List all EHR versions for a case.

**Response:**
```json
{
  "data": [
    {
      "ehr_id": "uuid",
      "version": 1,
      "status": "MAPPED",
      "created_at": "2024-01-01T00:00:00Z",
      "entity_count": 5,
      "mapping_count": 8
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "has_more": false
}
```

### GET /api/v1/ehr/{ehrId}
Get EHR document by ID.

**Response:**
```json
{
  "ehr_id": "uuid",
  "case_id": "uuid",
  "version": 1,
  "raw_text": "...",
  "normalized_text": "...",
  "status": "MAPPED",
  "processing_metadata": {},
  "created_by": "user@example.com",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:05:00Z"
}
```

### POST /api/v1/ehr/{ehrId}:extract-and-map
Extract entities and map to ontologies (async).

**Response:**
```json
{
  "ehr_id": "uuid",
  "task_id": "celery-task-id",
  "status": "processing",
  "message": "Entity extraction and mapping started"
}
```

### GET /api/v1/ehr/{ehrId}/entities
Get extracted entities.

**Query Parameters:**
- `entity_type` (optional): Filter by entity type

**Response:**
```json
[
  {
    "entity_id": "uuid",
    "entity_type": "DIAGNOSIS",
    "text": "adenocarcinoma",
    "start_position": 42,
    "end_position": 56,
    "confidence": 0.95,
    "section": "diagnosis",
    "metadata": {}
  }
]
```

### GET /api/v1/ehr/{ehrId}/mappings
Get ontology mappings.

**Query Parameters:**
- `ontology` (optional): Filter by ontology

**Response:**
```json
[
  {
    "mapping_id": "uuid",
    "entity_id": "uuid",
    "ontology": "NCIt",
    "iri": "http://purl.obolibrary.org/obo/NCIT_C3512",
    "label": "Lung Adenocarcinoma",
    "confidence": 0.90,
    "mapping_method": "lexical_match",
    "evidence": {}
  }
]
```

### POST /api/v1/cases/{caseId}:generate-explanation
Generate clinical explanation (async).

**Request:**
```json
{
  "context": {
    "outputs": {},
    "policies": {}
  }
}
```

**Response:**
```json
{
  "case_id": "uuid",
  "task_id": "celery-task-id",
  "status": "processing",
  "message": "Explanation generation started"
}
```

## Development

### Run the service:
```bash
uvicorn ehr_service.main:app --host 0.0.0.0 --port 8004 --reload
```

### Run Celery worker:
```bash
celery -A ehr_service.celery_app worker --loglevel=info
```

### Run migrations:
```bash
alembic upgrade head
```

### Run tests:
```bash
pytest
```

## Environment Variables

- `POSTGRES_DSN`: PostgreSQL connection string
- `REDIS_URL`: Redis URL for Celery
- `CELERY_BROKER_URL`: Celery broker URL
- `CELERY_RESULT_BACKEND`: Celery result backend URL
- `RABBITMQ_URL`: RabbitMQ URL for events
- `LLM_PROVIDER`: LLM provider (mock, openai, anthropic)
- `OPENAI_API_KEY`: OpenAI API key (if using OpenAI)
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OpenTelemetry endpoint (optional)
- `LOG_LEVEL`: Logging level (default: INFO)

## Dependencies

- FastAPI
- SQLAlchemy (async)
- Celery
- Redis
- PostgreSQL
- LangGraph
- oncology-common
- oncology-event-contracts
- oncology-langgraph-workflows
