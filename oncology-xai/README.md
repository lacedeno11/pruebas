# DERCAS-ONCO-XAI V1

Explainable AI Application for Oncology (Lung Cancer) with:
- Histopathological image processing and visualization (.png, .biff)
- ML-based pattern segmentation (lepidic, acinar, papillary, micropapillary, solid)
- Mutation prediction (EGFR, KRAS, TP53)
- EHR text panel with entity extraction and ontology mapping (NCIt/MONDO/SO)
- Integrated ontology graph visualization with provenance
- Admin module for ontology updates via LangGraph
- End-to-end audit and explainable reports with clinical guardrails

## Quickstart

### Prerequisites
- Docker & Docker Compose v2+
- Python 3.12+
- Node.js 20+ (for webapp)
- Make

### Setup

1. Clone and configure environment:
```bash
cp .env.example .env
# Edit .env with your settings (defaults work for local development)
```

2. Start infrastructure:
```bash
make up
```

3. Wait for services to be healthy:
```bash
make logs
```

4. Access services:
- API Gateway: http://localhost:8000
- Webapp: http://localhost:3000
- Keycloak Admin: http://localhost:8080 (admin/admin)
- MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
- Fuseki SPARQL: http://localhost:3030
- Jaeger UI: http://localhost:16686
- Prometheus: http://localhost:9090
- RabbitMQ Management: http://localhost:15672 (guest/guest)

### Development

```bash
# Run all tests
make test

# Lint and format
make lint
make fmt

# Stop all services
make down
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
