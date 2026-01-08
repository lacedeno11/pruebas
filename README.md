# DERCAS 01 Policy Validation Copilot

A comprehensive LangGraph-based agentic system for insurance policy validation with machine learning, guardrails, and human-in-the-loop capabilities.

## 🎯 Overview

DERCAS 01 is an advanced policy validation copilot that automates insurance policy validation processes using:

- **LangGraph Agentic Architecture**: Orchestrated workflow with intelligent agents
- **Machine Learning Integration**: Classification, anomaly detection, and ETA prediction
- **Comprehensive Guardrails**: OWASP LLM Top 10 compliance, RBAC, PII masking
- **Human-in-the-Loop (HITL)**: Escalation for low confidence, high risk, or anomalous cases
- **Complete Audit Trail**: Full traceability and evidence tracking
- **Policy-as-Code**: Deterministic rule evaluation and exception management

## 🏗️ Architecture

The system implements a complete end-to-end workflow:

1. **Case Ingest** → Validation, normalization, deduplication
2. **Intelligent Routing** → ML-powered classification and risk assessment
3. **Policy Retrieval (RAG)** → Evidence pack construction with exact references
4. **Rules & Checklist Builder** → Deterministic policy-as-code evaluation
5. **Decision Orchestrator** → Threshold-based auto-close vs HITL escalation
6. **External Connector** → Insurance company queries when needed
7. **Audited Closure** → Final decision with complete evidence trail

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- ChromaDB (for vector storage)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/dercas/dercas01.git
   cd dercas01
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e .
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Set up database**
   ```bash
   # Create PostgreSQL database
   createdb dercas01_db
   
   # Run migrations
   alembic upgrade head
   ```

6. **Start services**
   ```bash
   # Start Redis
   redis-server
   
   # Start ChromaDB (in separate terminal)
   chroma run --host localhost --port 8001
   
   # Start the API server
   uvicorn dercas01.api.main:app --reload
   ```

### Docker Setup (Alternative)

```bash
# Start all services with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
```

## 📋 Use Cases

The system implements 14 comprehensive use cases:

### Core Workflow
- **UC-OP-01**: End-to-end policy validation (system-led)
- **UC-OP-05**: Automatic case ingestion from CRM/ticketing
- **UC-OP-06**: Policy retrieval with RAG and evidence pack construction
- **UC-OP-07**: Rules and checklist builder (deterministic)
- **UC-OP-08**: Decision orchestrator with configurable thresholds

### Policy & Exception Management
- **UC-OP-02**: Policy ingestion, versioning, QA, and drift detection
- **UC-OP-03**: Exception management with approval workflows

### Audit & Governance
- **UC-OP-04**: Complete audit and evidence tracking
- **UC-OP-10**: Guardrails and governance enforcement

### ML Services
- **UC-OP-11**: Classification and intelligent routing
- **UC-OP-12**: Anomaly detection
- **UC-OP-13**: ETA prediction

### External Integration & Learning
- **UC-OP-09**: External insurance company connector
- **UC-OP-14**: Continuous learning and model improvement

## 🔧 Configuration

### Key Configuration Areas

- **Database**: PostgreSQL connection and pool settings
- **Vector Store**: ChromaDB configuration for RAG
- **ML Services**: Model endpoints and versioning
- **Guardrails**: Security thresholds and PII settings
- **Decision Thresholds**: Confidence, risk, and coverage limits
- **External APIs**: CRM, insurance company integrations

See `.env.example` for complete configuration options.

## 🛡️ Security & Compliance

### Guardrails Implementation
- **OWASP LLM Top 10** compliance
- **RBAC/ABAC** role-based access control
- **PII Detection & Masking** for sensitive data
- **Source Allowlisting** for document verification
- **Anti-hallucination** checks with evidence anchoring
- **Injection Detection** for prompt security

### Business Rules
- **RB-01**: No approval without verifiable evidence
- **RB-02**: Only allowlisted, versioned documents
- **RB-03**: Active exceptions prevail in scope
- **RB-04**: Configurable auto-close thresholds
- **RB-05**: Complete version tracking

## 📊 Monitoring & Observability

- **Health Checks**: System component monitoring
- **Metrics**: Performance and business KPIs
- **Logging**: Structured logging with audit trails
- **Alerting**: Anomaly and threshold-based alerts
- **Dashboards**: Real-time system status

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test types
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/e2e/          # End-to-end tests

# Run with coverage
pytest --cov=src/dercas01 --cov-report=html
```

## 📚 API Documentation

Once the server is running, access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔄 Development Workflow

### Code Quality
```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/
mypy src/

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## 🏢 Production Deployment

### Environment Setup
1. Configure production environment variables
2. Set up SSL/TLS certificates
3. Configure monitoring and alerting
4. Set up backup and disaster recovery

### Scaling Considerations
- **Horizontal scaling**: Multiple API instances behind load balancer
- **Database**: Read replicas and connection pooling
- **Vector Store**: ChromaDB clustering
- **Task Queue**: Celery workers for background processing

## 📖 Documentation

- **Architecture**: Detailed system design and component interactions
- **API Reference**: Complete endpoint documentation
- **Use Cases**: Detailed workflow specifications
- **Configuration**: Environment and deployment guides

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: GitHub Issues for bug reports and feature requests
- **Documentation**: Comprehensive guides and API reference
- **Community**: Discussion forums and chat channels

## 🔗 Related Projects

- **LangGraph**: Graph-based workflow orchestration
- **LangChain**: LLM application framework
- **ChromaDB**: Vector database for embeddings
- **FastAPI**: Modern Python web framework
