# DERCAS-ONCO-XAI V1 - Explainable AI Oncology Platform

A comprehensive explainable AI platform for lung cancer oncology that integrates histopathological image analysis, EHR processing, ontology mapping, and clinical decision support.

## 🎯 Overview

DERCAS-ONCO-XAI V1 is a microservices-based platform that provides:

- **Image Analysis**: Upload and process histopathological images (.png/.biff) to detect 5 patterns (lepidic, acinar, papillary, micropapillary, solid)
- **Genetic Mutation Prediction**: AI-assisted prediction of EGFR, KRAS, TP53 mutations with explainability
- **EHR Integration**: Text processing with entity extraction and ontology mapping (NCIt/MONDO/SO)
- **Knowledge Graphs**: Case-specific ontological graphs with provenance tracking
- **Admin Interface**: Deep search ontology updates using LangGraph workflows
- **Audit & Compliance**: End-to-end traceability with clinical guardrails

## 🏗️ Architecture

### Monorepo Structure

```
oncology-xai/
├── apps/                           # Microservices
│   ├── api-gateway/               # FastAPI gateway with JWT validation
│   ├── case-service/              # Patient/case management
│   ├── image-service/             # Image upload/storage (MinIO)
│   ├── inference-service/         # ML processing with LangGraph
│   ├── ehr-service/               # EHR ingestion & ontology mapping
│   ├── graph-service/             # Triple store & SPARQL queries
│   ├── ontology-admin-service/    # Ontology updates via LLM deep search
│   ├── audit-service/             # Event auditing & compliance
│   └── webapp/                    # React + Vite frontend
├── packages/                      # Shared libraries
│   ├── common/                    # Auth utils, models, middleware
│   ├── event-contracts/           # RabbitMQ event schemas
│   └── langgraph-workflows/       # AI workflow definitions
├── infra/                         # Infrastructure
│   ├── docker-compose.yml         # Local development stack
│   ├── keycloak/                  # OIDC realm configuration
│   ├── fuseki/                    # SPARQL endpoint setup
│   └── prometheus/                # Monitoring configuration
└── docs/                          # Documentation
    ├── architecture.md            # System design & C4 diagrams
    ├── runbook.md                 # Operations guide
    └── openapi/                   # API specifications
```

### Tech Stack

- **Backend**: Python 3.12, FastAPI, Pydantic v2
- **Database**: PostgreSQL 16 (SQLAlchemy 2.0 + Alembic)
- **Message Broker**: RabbitMQ + Celery (Redis backend)
- **Object Storage**: MinIO (S3-compatible)
- **Triple Store**: Apache Jena Fuseki (SPARQL)
- **Authentication**: Keycloak (OIDC) + JWT validation
- **Observability**: OpenTelemetry + Jaeger + Prometheus
- **Frontend**: React + Vite
- **AI Workflows**: LangGraph for orchestration
- **Code Quality**: ruff + black + mypy + pytest

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Node.js 18+ (for webapp)
- Make

### 1. Clone and Setup

```bash
git clone <repository-url>
cd oncology-xai
cp .env.example .env
make dev-setup
```

### 2. Start Infrastructure

```bash
# Start all infrastructure services
make up

# Check service health
make health

# View logs
make logs
```

### 3. Access Services

- **API Gateway**: http://localhost:8080
- **Keycloak Admin**: http://localhost:8081/admin (admin/admin)
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **Fuseki**: http://localhost:3030
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686
- **WebApp**: http://localhost:3000

### 4. Development Workflow

```bash
# Install dependencies
make install-deps

# Run tests
make test

# Code formatting
make fmt

# Linting
make lint

# Build services
make build
```

## 🔧 Environment Configuration

Copy `.env.example` to `.env` and configure:

### Database
- `POSTGRES_DSN`: PostgreSQL connection string
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password

### Message Broker
- `RABBITMQ_URL`: RabbitMQ connection URL
- `REDIS_URL`: Redis connection URL

### Object Storage
- `S3_ENDPOINT`: MinIO endpoint URL
- `S3_ACCESS_KEY`: MinIO access key
- `S3_SECRET_KEY`: MinIO secret key
- `S3_BUCKET`: Default bucket name

### Authentication
- `KEYCLOAK_URL`: Keycloak server URL
- `KEYCLOAK_REALM`: Realm name
- `JWKS_URL`: JWT verification endpoint

### AI & ML
- `LLM_PROVIDER`: mock|openai|anthropic
- `OPENAI_API_KEY`: OpenAI API key (if using)
- `ANTHROPIC_API_KEY`: Anthropic API key (if using)
- `MODEL_BACKEND`: mock|triton
- `TRITON_URL`: Triton inference server URL

### Observability
- `JAEGER_ENDPOINT`: Jaeger collector endpoint
- `PROMETHEUS_ENDPOINT`: Prometheus server URL

## 🧬 Clinical Domain

### Histological Patterns (5)
- **Lepidic**: Growth along alveolar walls
- **Acinar**: Glandular structures
- **Papillary**: Finger-like projections
- **Micropapillary**: Small papillary clusters
- **Solid**: Sheets of cells

### Genetic Mutations (3)
- **EGFR**: Epidermal Growth Factor Receptor
- **KRAS**: Kirsten RAS oncogene
- **TP53**: Tumor Protein 53

### Ontologies
- **NCIt**: National Cancer Institute Thesaurus
- **MONDO**: Monarch Disease Ontology
- **SO**: Sequence Ontology

## 🔒 Clinical Guardrails

The platform implements mandatory clinical safety measures:

- ❌ **No deterministic diagnoses** - All outputs are assistive/suggestive
- ✅ **Score transparency** - Always show confidence scores and thresholds
- ✅ **Version tracking** - Model versions, ontology versions, and timestamps
- ✅ **Limitations disclosure** - Mandatory limitations section in reports
- ✅ **Conflict detection** - Automatic detection of EHR vs image conflicts
- ✅ **HITL triggers** - Human-in-the-loop for low confidence or conflicts

## 🔄 LangGraph Workflows

### 1. ImageAnalysisGraph (Inference Service)
```
ValidateInput → LoadImage → RunPatternModel → RunMutationModel → 
GenerateXAI → AssembleResultBundle → PolicyCheck → PersistAndAudit → Finalize
```

### 2. EHRToOntologyGraph (EHR Service)
```
NormalizeEHR → ExtractEntities → LookupCandidates → Disambiguate → 
BuildEvidencePack → PersistEntitiesMappings → Finalize
```

### 3. GraphAssemblerGraph (Graph Service)
```
FetchCaseFindings → QuerySubgraph → FuseAnnotateProvenance → 
BuildLayout → PersistSnapshot → Finalize
```

### 4. ExplanationComposerGraph (EHR Service)
```
GatherEvidence → DetectConflicts → DraftExplanation → 
ValidateClaimsGuardrails → PublishReport → Finalize
```

### 5. OntologyUpdateWorkflow (Ontology Admin Service)
```
SourceDiscovery → FetchOntology → ValidateIntegrity → ParseRDF → 
ComputeDiff → LLMMappingSuggestions → ReasonerCheck → ImpactAnalysis → 
CreateProposal → HITLApproval → PublishOrRollback
```

## 📊 Event-Driven Architecture

### Standard Event Envelope
```json
{
  "eventId": "evt_...",
  "eventType": "inference.completed",
  "timestamp": "ISO-8601",
  "correlationId": "corr_...",
  "producer": "inference-service",
  "caseId": "case_...",
  "payload": {}
}
```

### Key Event Types
- `case.created`, `case.updated`
- `image.uploaded`, `image.deleted`
- `job.created`, `job.progress`, `job.completed`, `job.failed`
- `inference.completed`, `inference.failed`
- `ehr.ingested`, `ehr.extracted`, `ehr.mapped`
- `graph.built`, `graph.failed`
- `ontology.proposal.created`, `ontology.published`, `ontology.rollbacked`
- `audit.event.created`

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific service tests
cd apps/case-service && python -m pytest tests/ -v

# Run with coverage
cd apps/case-service && python -m pytest tests/ --cov=src --cov-report=html
```

## 📚 API Documentation

Each service exposes OpenAPI documentation:

- **API Gateway**: http://localhost:8080/docs
- **Case Service**: http://localhost:8001/docs
- **Image Service**: http://localhost:8002/docs
- **Inference Service**: http://localhost:8003/docs
- **EHR Service**: http://localhost:8004/docs
- **Graph Service**: http://localhost:8005/docs
- **Ontology Admin**: http://localhost:8006/docs
- **Audit Service**: http://localhost:8007/docs

## 🔍 Monitoring & Observability

- **Metrics**: Prometheus + Grafana dashboards
- **Tracing**: Jaeger distributed tracing
- **Logs**: Structured logging with correlation IDs
- **Health Checks**: `/healthz` endpoints on all services
- **Audit Trail**: Complete event tracking for compliance

## 🚨 Troubleshooting

### Common Issues

1. **Services not starting**: Check Docker resources and port conflicts
2. **Database connection errors**: Verify PostgreSQL is running and credentials
3. **Authentication failures**: Check Keycloak realm configuration
4. **ML model errors**: Ensure mock models are properly initialized

### Debug Commands

```bash
# Check service status
make health

# View service logs
docker-compose -f infra/docker-compose.yml logs <service-name>

# Restart specific service
docker-compose -f infra/docker-compose.yml restart <service-name>

# Clean and restart
make clean && make up
```

## 🤝 Contributing

1. Follow the established code style (black + ruff)
2. Write comprehensive tests
3. Update documentation
4. Ensure clinical guardrails are maintained
5. Add audit logging for new features

## 📄 License

[Add your license information here]

## 🆘 Support

For technical support or questions:
- Check the [runbook](docs/runbook.md) for operational procedures
- Review [architecture documentation](docs/architecture.md)
- Open an issue for bugs or feature requests

---

**⚠️ Clinical Disclaimer**: This platform is for research and development purposes. All AI predictions are assistive only and require clinical validation. Never use for direct patient diagnosis without proper medical oversight.
