# DERCAS-ONCO-XAI: Explainable AI Oncology Platform

A comprehensive explainable AI platform for oncology (lung cancer) that integrates histopathological image analysis, EHR processing, ontological knowledge graphs, and clinical decision support with full audit trails and compliance features.

## 🎯 System Overview

DERCAS-ONCO-XAI provides:

- **Image Analysis**: Upload and process histopathological images (.png, .biff) with ML-powered pattern segmentation for 5 histological patterns (lepidic, acinar, papillary, micropapillary, solid)
- **Genetic Mutation Prediction**: AI-assisted prediction for key mutations (EGFR, KRAS, TP53) with explainable AI artifacts
- **EHR Integration**: Text processing with entity extraction and mapping to medical ontologies (NCIt/MONDO/SO)
- **Knowledge Graphs**: Integrated ontological visualization with case-specific subgraphs and provenance tracking
- **Admin Tools**: Deep search ontology updates using LangGraph workflows with diff analysis and reasoner validation
- **Audit & Compliance**: End-to-end audit trails with clinical guardrails preventing definitive diagnosis language

## 🏗️ Architecture

### Microservices Architecture

```
apps/
├── api-gateway/          # JWT validation, RBAC, request routing
├── case-service/         # Patient and case management
├── image-service/        # Image upload, storage, and viewer URLs
├── inference-service/    # ML inference with LangGraph workflows
├── ehr-service/          # EHR processing and ontology mapping
├── graph-service/        # Triple store and knowledge graph management
├── ontology-admin-service/ # Ontology updates with LangGraph
├── audit-service/        # Comprehensive audit and compliance
└── webapp/              # React frontend with 4 main panels
```

### Shared Packages

```
packages/
├── common/              # Pydantic models, auth utils, error schemas
├── event-contracts/     # Event envelope and RabbitMQ helpers
└── langgraph-workflows/ # Base GraphState and common tools
```

### Infrastructure

```
infra/
├── docker-compose.yml   # PostgreSQL, RabbitMQ, Redis, MinIO, Keycloak, Fuseki, Jaeger, Prometheus
├── keycloak/           # Realm configuration
├── fuseki/             # Triple store configuration
└── prometheus/         # Monitoring configuration
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.12+
- Node.js 18+
- Make

### 1. Clone and Setup

```bash
git clone <repository-url>
cd dercas-onco-xai
```

### 2. Environment Configuration

```bash
# Copy environment template
make env-example

# Edit .env with your configuration
nano .env
```

### 3. Quick Start (Recommended)

```bash
# Start infrastructure and install dependencies
make quickstart
```

This will:
- Start all infrastructure services (PostgreSQL, RabbitMQ, Redis, MinIO, Keycloak, Fuseki, Jaeger, Prometheus)
- Install Python dependencies for all services
- Install Node.js dependencies for the webapp

### 4. Manual Setup (Alternative)

```bash
# Start infrastructure
make up

# Install dependencies
make install-deps

# Check service health
make health
```

## 🔧 Development

### Available Commands

```bash
# Infrastructure Management
make up              # Start all services
make down            # Stop all services
make logs            # View logs
make restart         # Restart services
make clean           # Clean up containers and volumes

# Development
make install-deps    # Install all dependencies
make build          # Build all services
make test           # Run all tests
make lint           # Run linting
make fmt            # Format code

# Health Checks
make health         # Check service health
```

### Service URLs (Default)

- **API Gateway**: http://localhost:8000
- **Webapp**: http://localhost:3000
- **Keycloak Admin**: http://localhost:8080/auth/admin (admin/admin)
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **Fuseki**: http://localhost:3030
- **Jaeger UI**: http://localhost:16686
- **Prometheus**: http://localhost:9090

## 📊 Technology Stack

### Backend Services
- **Python 3.12** with FastAPI and Pydantic v2
- **PostgreSQL 16** with SQLAlchemy 2.0 and Alembic
- **RabbitMQ + Celery** (Redis backend) for async jobs
- **MinIO** S3-compatible object storage
- **Apache Jena Fuseki** triple store for SPARQL
- **Keycloak** OIDC authentication with JWT validation

### AI/ML Components
- **LangGraph** for AI agent workflows
- **LangChain** for LLM integration
- **Mock ML Models** (ready for Triton/TorchServe integration)
- **Explainable AI** artifacts generation

### Frontend
- **React 18** with Vite
- **TypeScript**
- **Tailwind CSS**
- **vis-network** for graph visualization
- **Keycloak JS** for authentication

### Observability
- **OpenTelemetry** distributed tracing
- **Jaeger** trace visualization
- **Prometheus** metrics collection
- **Structured logging** with correlation IDs

## 🔐 Security & Compliance

### Authentication & Authorization
- **OIDC/JWT** authentication via Keycloak
- **RBAC** with roles: clinician, admin, auditor
- **ABAC** for fine-grained access control
- **Correlation ID** tracking across all services

### Clinical Guardrails
- **No definitive diagnosis** language in AI outputs
- **Mandatory disclaimers** and limitations
- **Model version tracking** for reproducibility
- **Confidence thresholds** with HITL policies

### Audit & Compliance
- **End-to-end audit trails** for all actions
- **PHI redaction** in logs
- **Immutable event storage**
- **Compliance reporting** by case/time/user

## 🧬 Clinical Workflows

### 1. Image Analysis Workflow
```
Upload Image → Validate → ML Inference → Generate XAI → 
Policy Check → Audit → Results (Patterns + Mutations)
```

### 2. EHR Processing Workflow
```
Ingest EHR → Normalize → Extract Entities → 
Map to Ontologies → Detect Conflicts → Persist
```

### 3. Knowledge Graph Workflow
```
Fetch Case Findings → Query Subgraph → 
Annotate Provenance → Generate Layout → Snapshot
```

### 4. Explanation Generation Workflow
```
Gather Evidence → Detect Conflicts → Draft Explanation → 
Validate Guardrails → Publish Report
```

### 5. Ontology Update Workflow
```
Source Discovery → Fetch → Validate → Parse → 
Compute Diff → LLM Suggestions → Reasoner Check → 
Impact Analysis → HITL Approval → Publish/Rollback
```

## 📋 End-to-End Acceptance Criteria

The platform supports the following complete workflow:

1. ✅ **Create patient and case**
2. ✅ **Upload PNG image**
3. ✅ **Process image** → get overlays + scores for 5 patterns + 3 mutations
4. ✅ **Ingest EHR** → extract entities → map to ontologies
5. ✅ **Rebuild graph** → visualize nodes/edges with provenance
6. ✅ **Generate explanation** → HTML report with guardrails
7. ✅ **Admin publishes ontology update** → audited event
8. ✅ **Auditor queries timeline** by caseId

## 🔬 Data Models

### Core Entities
- **Patient**: Demographics and identifiers
- **Case**: Clinical cases with status tracking
- **Image**: Histopathological images with metadata
- **ResultBundle**: ML inference results with XAI artifacts
- **EHRDocument**: Versioned EHR text with entities
- **CaseGraph**: Knowledge graph snapshots
- **ExplanationReport**: Unified clinical reports

### Supported Patterns
- **Histological**: lepidic, acinar, papillary, micropapillary, solid
- **Genetic Mutations**: EGFR, KRAS, TP53

### Ontologies
- **NCIt**: National Cancer Institute Thesaurus
- **MONDO**: Monarch Disease Ontology
- **SO**: Sequence Ontology

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific service tests
cd apps/case-service && python -m pytest

# Run with coverage
cd apps/case-service && python -m pytest --cov
```

## 📚 Documentation

- **Architecture**: `docs/architecture.md` - C4 model and event flows
- **Runbook**: `docs/runbook.md` - Operations and troubleshooting
- **OpenAPI**: `docs/openapi/` - API specifications
- **Environment**: `.env.example` - Configuration reference

## 🐛 Troubleshooting

### Common Issues

1. **Services not starting**: Check `make health` and `make logs`
2. **Database connection**: Ensure PostgreSQL is running and credentials are correct
3. **Authentication issues**: Verify Keycloak realm configuration
4. **Storage issues**: Check MinIO credentials and bucket configuration

### Debug Commands

```bash
# Check service health
make health

# View logs
make logs

# Restart specific service
docker-compose -f infra/docker-compose.yml restart postgres

# Clean restart
make clean && make up
```

## 🤝 Contributing

1. Follow the established code style (ruff, black, mypy)
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure all services pass health checks

## 📄 License

[Add your license information here]

## 🆘 Support

For issues and questions:
- Check the troubleshooting section
- Review logs with `make logs`
- Consult `docs/runbook.md` for operational guidance

---

**DERCAS-ONCO-XAI** - Advancing oncology through explainable AI and comprehensive clinical decision support.
