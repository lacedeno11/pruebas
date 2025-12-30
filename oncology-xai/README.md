# DERCAS-ONCO-XAI V1: Explainable AI Oncology Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2.0-61DAFB.svg)](https://reactjs.org)

## 🎯 Overview

DERCAS-ONCO-XAI V1 is a comprehensive Explainable AI platform for oncology, specifically designed for lung cancer analysis. The platform integrates:

- **Histopathological Image Processing**: Upload and analysis of .png and .biff images
- **ML Pattern Recognition**: Segmentation and explanation of 5 lung cancer patterns (lepidic, acinar, papillary, micropapillary, solid)
- **Genetic Mutation Prediction**: AI-assisted prediction of EGFR, KRAS, TP53 mutations
- **EHR Integration**: Text processing with entity extraction and ontology mapping
- **Knowledge Graph Visualization**: Integrated ontological graphs (NCIt/MONDO/SO) with provenance
- **Admin Interface**: Ontology management with LLM-powered deep search capabilities
- **End-to-End Auditing**: Complete traceability and explainable reporting with clinical guardrails

## 🏗️ Architecture

### Microservices Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React Web    │    │   API Gateway    │    │  Keycloak Auth  │
│     App         │◄──►│   (FastAPI)      │◄──►│     (OIDC)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
        ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
        │ Case Service │ │Image Service│ │EHR Service │
        │ (Patients/   │ │(Upload/     │ │(NLP/Entity │
        │  Cases)      │ │ Viewer)     │ │ Extraction)│
        └──────────────┘ └─────────────┘ └────────────┘
                │               │               │
        ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
        │Inference     │ │Graph Service│ │Ontology    │
        │Service       │ │(Triple Store│ │Admin       │
        │(ML+XAI)      │ │ +Snapshots) │ │Service     │
        └──────────────┘ └─────────────┘ └────────────┘
                │               │               │
                └───────────────┼───────────────┘
                                │
                        ┌───────▼──────┐
                        │Audit Service │
                        │(Events+Trace)│
                        └──────────────┘
```

### Technology Stack

**Backend Services**
- **Language**: Python 3.12
- **Framework**: FastAPI + Pydantic v2
- **Database**: PostgreSQL 16 with SQLAlchemy 2.0 + Alembic
- **Message Broker**: RabbitMQ + Celery (Redis backend)
- **Object Storage**: MinIO (S3 compatible)
- **Triple Store**: Apache Jena Fuseki (SPARQL)
- **Authentication**: Keycloak (OIDC) + JWT validation
- **AI Workflows**: LangGraph for complex AI pipelines

**Infrastructure & Observability**
- **Containerization**: Docker + Docker Compose
- **Tracing**: OpenTelemetry + Jaeger
- **Metrics**: Prometheus
- **Code Quality**: ruff + black + mypy + pytest

**Frontend**
- **Framework**: React 18 + Vite
- **Authentication**: Keycloak OIDC integration
- **Visualization**: vis-network for graph rendering

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Node.js 18+ (for frontend development)
- Git

### 1. Clone and Setup

```bash
git clone <repository-url>
cd oncology-xai

# Copy environment configuration
cp .env.example .env

# Edit .env with your specific configuration
nano .env
```

### 2. Start the Platform

```bash
# Start all infrastructure services
make up

# Wait for services to be ready (30-60 seconds)
make health

# Run database migrations
make db-migrate
```

### 3. Access the Platform

- **Web Application**: http://localhost:3000
- **API Gateway**: http://localhost:8080
- **API Documentation**: http://localhost:8080/docs

### 4. Development Setup

```bash
# Complete development environment setup
make dev-setup

# Install dependencies for all services
make install

# Run tests
make test

# Code formatting and linting
make fmt
make lint
```

## 📁 Repository Structure

```
oncology-xai/
├── apps/                           # Microservices
│   ├── api-gateway/               # FastAPI gateway with JWT validation
│   ├── case-service/              # Patient and case management
│   ├── image-service/             # Image upload and viewer URLs
│   ├── inference-service/         # ML inference + XAI (LangGraph)
│   ├── ehr-service/               # EHR processing + entity extraction
│   ├── graph-service/             # Triple store + graph snapshots
│   ├── ontology-admin-service/    # Ontology management (LangGraph)
│   ├── audit-service/             # Event auditing and traceability
│   └── webapp/                    # React frontend application
├── packages/                      # Shared libraries
│   ├── common/                    # Auth utils, models, error schemas
│   ├── event-contracts/           # Event envelope and RabbitMQ helpers
│   └── langgraph-workflows/       # Reusable LangGraph components
├── infra/                         # Infrastructure configuration
│   ├── docker-compose.yml         # All services orchestration
│   ├── keycloak/                  # Authentication realm configuration
│   ├── fuseki/                    # Triple store configuration
│   ├── prometheus/                # Metrics configuration
│   └── grafana/                   # Dashboards (optional)
├── docs/                          # Documentation
│   ├── openapi/                   # Generated API specifications
│   ├── architecture.md            # System architecture documentation
│   └── runbook.md                 # Operations and troubleshooting
├── tests/                         # Integration and E2E tests
├── Makefile                       # Development and operations commands
├── .env.example                   # Environment variables template
└── README.md                      # This file
```

## 🔧 Configuration

### Environment Variables

Key configuration variables (see `.env.example` for complete list):

```bash
# Database
POSTGRES_DSN=postgresql://user:pass@localhost:5432/oncology_xai

# Message Broker
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
REDIS_URL=redis://localhost:6379/0

# Object Storage
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=oncology-xai

# Authentication
KEYCLOAK_URL=http://localhost:8081
KEYCLOAK_REALM=oncology-xai
JWKS_URL=http://localhost:8081/realms/oncology-xai/protocol/openid-connect/certs

# Triple Store
FUSEKI_URL=http://localhost:3030

# AI/ML Configuration
LLM_PROVIDER=mock  # mock|openai|anthropic
MODEL_BACKEND=mock  # mock|triton
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
make test

# Run tests for specific service
make test-service SERVICE=case-service

# Run integration tests
make test-integration

# Run with coverage
make test-coverage
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: Database and external service integration
- **Contract Tests**: API specification validation
- **End-to-End Tests**: Complete workflow testing

## 🔍 Monitoring & Observability

### Available Dashboards

```bash
# Open monitoring interfaces
make monitor
```

- **Jaeger Tracing**: http://localhost:16686
- **Prometheus Metrics**: http://localhost:9090
- **Grafana Dashboards**: http://localhost:3000 (if configured)
- **MinIO Console**: http://localhost:9001
- **RabbitMQ Management**: http://localhost:15672

### Health Checks

```bash
# Check all service health
make health

# View service status
make status

# View logs
make logs

# View logs for specific service
make logs-service SERVICE=api-gateway
```

## 🔒 Security

### Authentication & Authorization

- **OIDC Integration**: Keycloak-based authentication
- **Role-Based Access Control**: Clinician, Admin, Auditor roles
- **JWT Validation**: All API endpoints protected
- **Audit Trail**: Complete action traceability

### Clinical Guardrails

- **No Definitive Diagnosis**: AI outputs include disclaimers
- **Score Transparency**: All predictions include confidence scores
- **Version Tracking**: Model and ontology versions recorded
- **Conflict Detection**: EHR vs Image prediction conflicts flagged

### Security Scanning

```bash
# Run security scans
make security-scan

# Check production readiness
make prod-check
```

## 🏥 Clinical Workflows

### 1. Image Analysis Workflow
1. Upload histopathological image (.png/.biff)
2. Process with ML models for pattern detection
3. Generate XAI overlays and heatmaps
4. Review results with confidence scores

### 2. EHR Processing Workflow
1. Ingest EHR text documents
2. Extract clinical entities with NLP
3. Map entities to ontologies (NCIt/MONDO/SO)
4. Detect conflicts with image analysis

### 3. Knowledge Graph Integration
1. Build case-specific subgraphs
2. Integrate findings from multiple sources
3. Visualize with provenance tracking
4. Generate explainable reports

### 4. Ontology Management
1. Discover new ontology versions
2. Compute diffs and impact analysis
3. Validate with reasoner checks
4. Approve and publish updates

## 🛠️ Development

### Adding New Services

1. Create service directory in `apps/`
2. Implement FastAPI application
3. Add database models and migrations
4. Implement event publishing/consuming
5. Add comprehensive tests
6. Update docker-compose.yml
7. Document API endpoints

### Code Quality Standards

- **Linting**: ruff for fast Python linting
- **Formatting**: black for consistent code style
- **Type Checking**: mypy for static type analysis
- **Testing**: pytest with comprehensive coverage
- **Documentation**: OpenAPI automatic generation

### Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📚 API Documentation

### Service Endpoints

- **API Gateway**: http://localhost:8080/docs
- **Case Service**: http://localhost:8001/docs
- **Image Service**: http://localhost:8002/docs
- **Inference Service**: http://localhost:8003/docs
- **EHR Service**: http://localhost:8004/docs
- **Graph Service**: http://localhost:8005/docs
- **Ontology Admin**: http://localhost:8006/docs
- **Audit Service**: http://localhost:8007/docs

### Key API Patterns

```bash
# Authentication
GET /auth/me

# Patient Management
POST /api/v1/patients
GET /api/v1/patients/{patientId}

# Case Management
POST /api/v1/cases
GET /api/v1/cases/{caseId}

# Image Processing
POST /api/v1/cases/{caseId}/images:upload
POST /api/v1/images/{imageId}:process

# EHR Processing
POST /api/v1/cases/{caseId}/ehr:ingest
POST /api/v1/ehr/{ehrId}:extract-and-map

# Graph Visualization
GET /api/v1/cases/{caseId}/graph
POST /api/v1/cases/{caseId}/graph:rebuild

# Explanation Generation
POST /api/v1/cases/{caseId}:generate-explanation
```

## 🚨 Troubleshooting

### Common Issues

**Services not starting**
```bash
# Check Docker resources
docker system df
docker system prune

# Restart with clean state
make clean
make up
```

**Database connection issues**
```bash
# Check PostgreSQL logs
make logs-service SERVICE=postgres

# Reset database
make db-reset
```

**Authentication problems**
```bash
# Check Keycloak configuration
make logs-service SERVICE=keycloak

# Verify realm import
curl http://localhost:8081/realms/oncology-xai
```

### Performance Optimization

- **Database**: Ensure proper indexing for audit queries
- **Object Storage**: Configure appropriate bucket policies
- **Message Broker**: Monitor queue depths
- **Triple Store**: Optimize SPARQL queries

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

For support and questions:

- **Documentation**: Check `docs/` directory
- **Issues**: Create GitHub issue with detailed description
- **Operations**: See `docs/runbook.md` for operational procedures

## 🔮 Roadmap

- [ ] Advanced ML model integration (Triton Inference Server)
- [ ] Real-time collaboration features
- [ ] Advanced visualization components
- [ ] Mobile application support
- [ ] Integration with hospital EHR systems
- [ ] Advanced analytics and reporting
- [ ] Multi-language support

---

**⚠️ Clinical Disclaimer**: This platform is designed for research and educational purposes. All AI predictions should be validated by qualified medical professionals. The system includes built-in guardrails to prevent definitive diagnostic claims.
