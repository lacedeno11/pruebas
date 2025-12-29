# DERCAS-ONCO-XAI V1

**Explainable AI System for Oncology Pathology (Lung Cancer)**

A comprehensive microservices-based platform for analyzing histopathological images, extracting clinical entities from EHR data, mapping to biomedical ontologies, and generating explainable AI reports with clinical guardrails.

## Features

- **Image Analysis**: Upload and analyze histopathological images (.png, .biff) for 5 adenocarcinoma patterns (lepidic, acinar, papillary, micropapillary, solid) and 3 mutation predictions (EGFR, KRAS, TP53)
- **EHR Processing**: Entity extraction and normalization from clinical text with LLM-powered NER
- **Ontology Mapping**: Automatic mapping to NCIt, MONDO, SO, HGNC, and RxNorm ontologies
- **Knowledge Graph**: SPARQL-queryable triple store with provenance tracking
- **XAI Artifacts**: GradCAM heatmaps and attention maps for model interpretability
- **Clinical Guardrails**: Automated validation preventing definitive diagnostic language
- **Audit Trail**: Complete event logging for compliance and reproducibility

## Quick Start

### Prerequisites
- Docker & Docker Compose v2.20+
- Python 3.11+
- Node.js 20+ (for webapp)

### Running Locally

```bash
# Navigate to infrastructure directory
cd infra

# Start all services
docker compose up -d

# Wait for services to be ready (~60s for Keycloak)
docker compose logs -f keycloak

# Access the application
open http://localhost:3000
```

### Default Credentials

| Service | URL | Username | Password |
|---------|-----|----------|----------|
| WebApp | http://localhost:3000 | clinician | clinician123 |
| Keycloak Admin | http://localhost:8080 | admin | admin |
| MinIO Console | http://localhost:9001 | minioadmin | minioadmin |
| Fuseki SPARQL | http://localhost:3030 | admin | fuseki_secret |
| RabbitMQ | http://localhost:15672 | guest | guest |
| Jaeger UI | http://localhost:16686 | - | - |
| Prometheus | http://localhost:9090 | - | - |

### Development

```bash
# Run Python tests
cd packages/common && pytest tests/ -v
cd apps/case-service && pytest tests/ -v

# Run frontend tests
cd apps/webapp && npm test

# Lint Python code
ruff check packages apps

# Lint frontend
cd apps/webapp && npm run lint

# Stop all services
cd infra && docker compose down
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation.

## Project Structure

```
oncology-xai/
├── apps/
│   ├── api-gateway/         # JWT validation, routing, RBAC
│   ├── case-service/        # Patients and cases CRUD
│   ├── image-service/       # Image upload, storage, viewer URLs
│   ├── inference-service/   # ML inference jobs, XAI artifacts
│   ├── ehr-service/         # EHR ingestion, entity extraction, mapping
│   ├── graph-service/       # Triple store, case subgraphs
│   ├── ontology-admin-service/ # Ontology updates, diff, publish
│   ├── audit-service/       # Event auditing and queries
│   └── webapp/              # React frontend
├── packages/
│   ├── common/              # Shared Pydantic models, auth utils
│   ├── event-contracts/     # Event envelope, JSON schemas
│   └── langgraph-workflows/ # Reusable LangGraph workflows
├── infra/
│   ├── docker-compose.yml   # All infrastructure services
│   ├── keycloak/            # Realm configuration
│   ├── fuseki/              # SPARQL endpoint config
│   └── prometheus/          # Metrics configuration
└── docs/
    ├── openapi/             # OpenAPI specs per service
    ├── architecture.md      # C4 diagrams and design
    └── runbook.md           # Operations guide
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| api-gateway | 8000 | API Gateway with JWT validation |
| case-service | 8001 | Patient and case management |
| image-service | 8002 | Image upload and storage |
| inference-service | 8003 | ML inference and XAI |
| ehr-service | 8004 | EHR processing and mapping |
| graph-service | 8005 | Ontology graph management |
| ontology-admin-service | 8006 | Ontology administration |
| audit-service | 8007 | Audit event storage |
| webapp | 3000 | React frontend |

## License

Proprietary - All rights reserved
