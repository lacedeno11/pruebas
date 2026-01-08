# Policy Validation Copilot

**LangGraph-based Agentic Architecture for Automated Decision Support**

## Overview

The Policy Validation Copilot is an intelligent, automated system that validates service requests against insurance policies using a LangGraph-based agentic architecture. The system minimizes human intervention by leveraging machine learning, guardrails, and evidence-based decision making while maintaining complete audit trails and compliance.

## Key Features

- **Agentic LangGraph Architecture**: Orchestrated workflow with intelligent agents for policy retrieval, rules evaluation, and decision making
- **ML-Powered Intelligence**: Classification, anomaly detection, and ETA prediction services
- **Comprehensive Guardrails**: OWASP LLM Top 10 controls, RBAC/ABAC authorization, PII masking, and anti-hallucination measures
- **Evidence-Based Decisions**: RAG-powered policy retrieval with verifiable citations and coverage scoring
- **HITL Gates**: Human-in-the-loop intervention only for low/medium confidence, high risk, anomalies, or conflicts
- **Complete Audit Trail**: Immutable evidence packages with versioning, checksums, and decision traceability

## Architecture

The system implements 14 use cases (UC-OP-01 to UC-OP-14) covering the complete end-to-end workflow:

### Core LangGraph Workflow
```
CRM → LG_Ingest → Guardrails → LG_Route → ML Services → LG_RAG → LG_Check → LG_Decide → LG_Close
```

### Key Components

- **Case Ingest Node**: Payload validation, normalization, and deduplication
- **Policy Retrieval Agent**: RAG-based evidence extraction with coverage scoring
- **Rules & Checklist Builder**: Deterministic rule execution and checklist construction
- **Decision Orchestrator**: Confidence/risk calculation and threshold-based routing
- **Insurer Connector**: External consultation automation
- **Audited Closure**: Evidence packaging and decision finalization

### ML Services

- **Classification Service**: Request type prediction and intelligent routing
- **Anomaly Detection**: Pattern analysis and risk assessment
- **ETA Prediction**: SLA management and expectation setting

## Project Structure

```
src/policy_validation_copilot/
├── models/           # Pydantic data models
├── langgraph/        # LangGraph state and workflow
├── ml/               # ML service clients and contracts
├── guardrails/       # Security and governance controls
├── agents/           # LangGraph agents
├── nodes/            # LangGraph nodes
├── integrations/     # External system integrations
└── api/              # FastAPI REST endpoints

tests/
├── unit/             # Unit tests
└── integration/      # Integration tests

config/               # Configuration files
docs/                 # Documentation
```

## Business Rules

- **RB-01**: No APROBADO without verifiable evidence (≥1 citation/table with exact reference)
- **RB-02**: Allowlist sources only - versioned/approved documents; no unverified text
- **RB-03**: Active/approved exceptions prevail within their scope
- **RB-04**: Auto-closure thresholds: confidence_high + risk_low + coverage_ok + no critical guardrails
- **RB-05**: Version tracking mandatory for policies/rules/models in every decision

## State Schema

The system maintains comprehensive state including:
- **case**: IDs, service details, dates, attachments, SLA, state, queue
- **evidence_pack**: Items with doc_id/version/checksum/pointer/excerpt + coverage_score
- **checklist**: Outcomes + evidence_ref; missing_fields; rule_ids_applied
- **ml**: Outputs + model_versions (classify/anomaly/eta)
- **decision**: Status + confidence/risk + next_actions + thresholds_version
- **guardrails**: Decision + flags + redactions
- **hitl**: Required + questions/responses + approvals
- **audit**: Node_execution_log + timestamps + export_logs

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL (for RDBMS)
- Vector database (ChromaDB)
- Object storage (S3-compatible)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd policy-validation-copilot

# Install dependencies
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install
```

### Configuration

1. Copy configuration template:
   ```bash
   cp config/settings.example.yaml config/settings.yaml
   ```

2. Update configuration with your environment settings

3. Set environment variables:
   ```bash
   export DATABASE_URL="postgresql://user:pass@localhost/policy_db"
   export VECTOR_DB_PATH="./chroma_db"
   export OBJECT_STORAGE_URL="s3://your-bucket"
   ```

### Running the System

```bash
# Start the API server
uvicorn policy_validation_copilot.api.main:app --reload

# Run the LangGraph workflow
python -m policy_validation_copilot.cli workflow start

# Monitor system health
python -m policy_validation_copilot.cli health check
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m e2e
```

### Code Quality

```bash
# Format code
black src tests
isort src tests

# Lint code
flake8 src tests
mypy src

# Run all quality checks
pre-commit run --all-files
```

## Use Cases

The system implements 14 comprehensive use cases:

- **UC-OP-01**: End-to-end service validation (system-led)
- **UC-OP-02**: Policy ingestion and versioning
- **UC-OP-03**: Exception management with HITL approval
- **UC-OP-04**: Audit and evidence reconstruction
- **UC-OP-05**: Automated case ingestion from CRM
- **UC-OP-06**: Policy retrieval with RAG
- **UC-OP-07**: Rules and checklist builder
- **UC-OP-08**: Decision orchestration with thresholds
- **UC-OP-09**: External insurer consultation
- **UC-OP-10**: Guardrails and governance enforcement
- **UC-OP-11**: ML classification and routing
- **UC-OP-12**: ML anomaly detection
- **UC-OP-13**: ML ETA prediction
- **UC-OP-14**: Continuous learning loop

## Security & Compliance

- OWASP LLM Top 10 controls implementation
- RBAC/ABAC authorization framework
- PII masking and data redaction
- Source allowlist validation
- Injection/jailbreak detection
- Evidence anchoring validation
- Comprehensive security event logging

## Monitoring & Observability

- Prometheus metrics collection
- Structured logging with correlation IDs
- Health check endpoints
- Performance monitoring
- Audit trail export capabilities
- ML model drift detection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions, issues, or contributions, please refer to:
- Documentation: [docs/](docs/)
- Issue Tracker: GitHub Issues
- Architecture Diagrams: [docs/architecture/](docs/architecture/)
- API Documentation: Available at `/docs` when running the server
