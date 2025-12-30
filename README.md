# DERCAS-ONCO-XAI V1: Explainable AI Oncology Platform

A comprehensive explainable AI platform for lung cancer histopathology analysis, integrating image processing, EHR analysis, and ontology management.

## Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd oncology-xai

# Start infrastructure and services
make up

# View logs
make logs

# Run tests
make test

# Stop everything
make down
```

## Architecture Overview

This platform consists of:

- **Image Processing**: Upload and analyze histopathological images (.png/.biff)
- **Pattern Detection**: ML models for 5 patterns (lepidic, acinar, papillary, micropapillary, solid)
- **Genetic Analysis**: Mutation prediction (EGFR, KRAS, TP53)
- **EHR Integration**: Text processing and ontology mapping (NCIt/MONDO/SO)
- **Knowledge Graphs**: Case-specific ontological representations
- **Admin Tools**: Ontology updates via LLM deep search
- **Audit System**: Complete traceability and compliance

## Services

- **API Gateway**: Authentication, routing, rate limiting
- **Case Service**: Patient and case management
- **Image Service**: Image upload, storage, and viewing
- **Inference Service**: ML processing with LangGraph workflows
- **EHR Service**: Document ingestion and entity extraction
- **Graph Service**: RDF triple store and SPARQL queries
- **Ontology Admin**: Deep search and ontology management
- **Audit Service**: Event tracking and compliance
- **WebApp**: React frontend with 5 main panels

## Technology Stack

- **Backend**: Python 3.12+ FastAPI + Pydantic v2
- **Database**: PostgreSQL 16 + SQLAlchemy 2.0
- **Jobs**: RabbitMQ + Celery + Redis
- **Storage**: MinIO (S3 compatible)
- **Triple Store**: Apache Jena Fuseki
- **Auth**: Keycloak (OIDC)
- **AI Workflows**: LangGraph
- **Frontend**: React + Vite
- **Observability**: OpenTelemetry + Jaeger + Prometheus

## Development

See [docs/runbook.md](docs/runbook.md) for detailed setup and operation instructions.

## Clinical Compliance

This platform implements strict clinical guardrails:
- Never emits deterministic diagnoses
- Always includes confidence scores and limitations
- Maintains complete audit trails
- Supports Human-in-the-Loop (HITL) workflows
