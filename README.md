# Policy Validation Copilot

**Agentic LangGraph Implementation for Policy Validation with ML + Guardrails**

A comprehensive policy validation system using LangGraph for agentic workflows, ML services for intelligent routing and decision making, and guardrails for security and governance.

## Overview

The Policy Validation Copilot is an advanced system that automates policy validation processes using:

- **LangGraph**: Agentic workflow orchestration with 7 main nodes/agents
- **ML Services**: Classification, anomaly detection, and ETA prediction
- **Guardrails**: OWASP LLM Top 10, RBAC/ABAC, PII masking, and security controls
- **Evidence-based Validation**: RAG-powered policy retrieval with audit trails
- **HITL Integration**: Human-in-the-loop for low confidence cases

## Architecture

### Core Components

1. **LangGraph Workflow** (`src/policy_copilot/workflow/`)
   - Policy Validation Workflow orchestrating all nodes and agents
   - State management and transitions
   - Conditional routing and error handling

2. **Agents** (`src/policy_copilot/agents/`)
   - Policy Retrieval Agent (RAG + Evidence Pack)
   - Rules & Checklist Builder Agent (Policy-as-code)
   - Decision Orchestrator Agent (Confidence/Risk calculation)
   - Insurer Connector Agent (External queries)

3. **Nodes** (`src/policy_copilot/nodes/`)
   - Case Ingest Node (Validation/Normalization)
   - Intelligent Routing Node (ML-enhanced routing)
   - Audited Closure Node (Decision finalization)

4. **ML Services** (`src/policy_copilot/ml_services/`)
   - Classification Service (UC-OP-11)
   - Anomaly Detection Service (UC-OP-12)
   - ETA Prediction Service (UC-OP-13)

5. **Guardrails** (`src/policy_copilot/guardrails/`)
   - Security enforcement (UC-OP-10)
   - RBAC/ABAC controls
   - PII masking and injection detection

## Use Cases

The system implements 14 use cases (UC-OP-01 through UC-OP-14):

- **UC-OP-01**: End-to-end policy validation (main workflow)
- **UC-OP-02**: Policy ingestion and versioning
- **UC-OP-03**: Exception management
- **UC-OP-04**: Audit and evidence management
- **UC-OP-05**: Case ingestion from CRM/Ticketing
- **UC-OP-06**: Policy retrieval with RAG
- **UC-OP-07**: Rules and checklist building
- **UC-OP-08**: Decision orchestration
- **UC-OP-09**: External insurer queries
- **UC-OP-10**: Guardrails and governance
- **UC-OP-11**: ML classification and routing
- **UC-OP-12**: ML anomaly detection
- **UC-OP-13**: ML ETA prediction
- **UC-OP-14**: Continuous learning loop

## Quick Start

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- PostgreSQL 15+
- Redis 7+

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd policy-copilot
```

2. Copy environment configuration:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start services with Docker Compose:
```bash
docker-compose up -d
```

4. Install dependencies:
```bash
pip install -r requirements.txt
pip install -e .
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the application:
```bash
uvicorn policy_copilot.main:app --reload
```

### Development Setup

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Set up pre-commit hooks:
```bash
pre-commit install
```

3. Run tests:
```bash
pytest
```

## Configuration

The system uses environment variables for configuration. See `.env.example` for all available options.

Key configuration areas:
- Database and Redis connections
- ML service endpoints
- Security and authentication
- External integrations (CRM, object storage)
- Monitoring and observability

## API Documentation

Once running, access the interactive API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Monitoring

Access monitoring dashboards:
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Jaeger: http://localhost:16686

## Project Structure

```
src/policy_copilot/
├── __init__.py
├── agents/              # LangGraph agents
├── nodes/               # LangGraph nodes
├── workflow/            # Workflow orchestration
├── ml_services/         # ML service interfaces
├── guardrails/          # Security and governance
├── database/            # Data persistence layer
├── integrations/        # External service integrations
└── config/              # Configuration management

tests/                   # Test suite
docs/                    # Documentation
scripts/                 # Utility scripts
config/                  # Configuration files
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.
