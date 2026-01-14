# Policy Validation Copilot

**Agentic LangGraph Architecture for Automated Decision Support**

A comprehensive system for automated policy validation using LangGraph agents, ML services, and governance controls.

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd policy-copilot
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Or install locally**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

## 🏗️ Architecture

The Policy Validation Copilot implements a sophisticated agentic architecture using LangGraph for workflow orchestration:

### Core Components

- **LangGraph Agents**: Case Ingest, Policy Retrieval (RAG), Rules & Checklist Builder, Decision Orchestrator, Insurer Connector
- **ML Services**: Classification/Routing, Anomaly Detection, ETA Prediction
- **Guardrails**: OWASP LLM Top 10 controls, RBAC/ABAC, PII masking, anti-hallucination
- **Data Layer**: RDBMS, Vector DB, Object Storage, Feature Store
- **HITL Gates**: Human-in-the-loop for low confidence, high risk, or anomalous cases

### Workflow (UC-OP-01)

```
CRM → Case Ingest → Guardrails → Intelligent Routing → ML Services → 
Policy Retrieval (RAG) → Rules & Checklist Builder → Decision Orchestrator → 
[Auto-close OR HITL Gate] → Audited Closure
```

## 📋 Use Cases

- **UC-OP-01**: Main E2E Policy Validation (LangGraph orchestrated)
- **UC-OP-05**: Case Ingestion from CRM with deduplication/idempotency
- **UC-OP-06**: Policy Retrieval Agent (RAG) with Evidence Pack construction
- **UC-OP-07**: Rules & Checklist Builder with policy-as-code engine
- **UC-OP-08**: Decision Orchestrator with threshold-based routing
- **UC-OP-10**: Guardrails Enforcement with OWASP LLM Top 10 controls
- **UC-OP-11-13**: ML Services (Classification, Anomaly Detection, ETA Prediction)

## 🛠️ Development

### Project Structure

```
src/policy_copilot/
├── agents/          # LangGraph agents
├── ml/              # ML services
├── data/            # Database layer
├── guardrails/      # Security controls
├── models/          # Data models
├── workflow/        # LangGraph orchestration
├── hitl/            # Human-in-the-loop interfaces
├── audit/           # Audit and evidence system
├── api/             # REST API layer
└── utils/           # Utilities
```

### Running Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# End-to-end tests
pytest tests/e2e/

# All tests with coverage
pytest --cov=src/policy_copilot
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint
flake8 src/ tests/
mypy src/

# Pre-commit hooks
pre-commit run --all-files
```

## 🔧 Configuration

Key configuration areas:

- **Database**: PostgreSQL for transactional data
- **Vector DB**: ChromaDB for policy document embeddings
- **Object Storage**: MinIO/S3 for document storage
- **ML Services**: MLflow for model registry
- **Monitoring**: Prometheus + Grafana
- **Message Queue**: RabbitMQ for HITL workflows

See `.env.example` for all configuration options.

## 📊 Monitoring

- **Health Checks**: `/health` endpoint
- **Metrics**: Prometheus metrics at `/metrics`
- **Logs**: Structured logging with correlation IDs
- **Tracing**: OpenTelemetry integration (optional)

## 🔒 Security

- **OWASP LLM Top 10**: Comprehensive controls implemented
- **RBAC/ABAC**: Role-based and attribute-based access control
- **PII Masking**: Automatic detection and redaction
- **Evidence Anchoring**: Anti-hallucination measures
- **Audit Trail**: Complete decision traceability

## 📚 Documentation

- [Architecture Guide](docs/architecture.md)
- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Configuration Reference](docs/configuration.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run quality checks
6. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/policy-copilot/policy-copilot/issues)
- **Documentation**: [Read the Docs](https://policy-copilot.readthedocs.io)
- **Discussions**: [GitHub Discussions](https://github.com/policy-copilot/policy-copilot/discussions)
