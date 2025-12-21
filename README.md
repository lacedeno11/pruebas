# Policy Validation Copilot

**DERCAS 01 - Cabina Aseguradoras Policy Validation Copilot (TO-BE)**

A LangGraph-based agentic system for automated insurance policy validation with ML integration and Human-in-the-Loop (HITL) gates.

## Overview

This system implements an intelligent policy validation workflow that:

- **Automates** routine policy validation decisions with high confidence
- **Escalates** complex cases to human reviewers (HITL) based on configurable thresholds
- **Ensures** compliance through guardrails (OWASP LLM Top 10, RBAC, PII masking)
- **Provides** complete audit trails for all decisions

## Architecture

```
┌─────────────────┐     ┌─────────────────────────────────────────────┐
│  CRM/Ticketing  │────▶│           LangGraph Workflow                │
└─────────────────┘     │                                             │
                        │  ┌─────────┐  ┌─────────┐  ┌─────────────┐ │
                        │  │  Case   │─▶│Intelligent│─▶│   Policy    │ │
                        │  │ Ingest  │  │ Routing  │  │  Retrieval  │ │
                        │  └─────────┘  └─────────┘  └─────────────┘ │
                        │       │            │              │         │
                        │       ▼            ▼              ▼         │
                        │  ┌─────────┐  ┌─────────┐  ┌─────────────┐ │
                        │  │  Rules  │◀─│   ML    │  │  Guardrails │ │
                        │  │Checklist│  │Services │  │   Service   │ │
                        │  └─────────┘  └─────────┘  └─────────────┘ │
                        │       │                          │         │
                        │       ▼                          │         │
                        │  ┌─────────────────┐            │         │
                        │  │    Decision     │◀───────────┘         │
                        │  │  Orchestrator   │                       │
                        │  └─────────────────┘                       │
                        │       │                                    │
                        │       ▼                                    │
                        │  ┌─────────┐  ┌─────────────┐             │
                        │  │  HITL   │─▶│   Audited   │             │
                        │  │  Gate   │  │   Closure   │             │
                        │  └─────────┘  └─────────────┘             │
                        └─────────────────────────────────────────────┘
```

## Features

### Use Cases Implemented

| UC | Name | Description |
|----|------|-------------|
| UC-OP-01 | Validar Servicio Adicional | End-to-end service validation workflow |
| UC-OP-04 | Auditoría y Evidencia | Complete audit trail with evidence |
| UC-OP-05 | Ingesta Automática | Case ingestion from CRM/tickets |
| UC-OP-06 | Policy Retrieval (RAG) | Evidence pack construction |
| UC-OP-07 | Rules & Checklist | Deterministic rule evaluation |
| UC-OP-08 | Decision Orchestrator | Threshold-based decision making |
| UC-OP-09 | Insurer Connector | External insurer consultation |
| UC-OP-10 | Guardrails | Security and compliance controls |
| UC-OP-11 | ML Classification | Request type and routing |
| UC-OP-12 | ML Anomaly | Anomaly detection |
| UC-OP-13 | ML ETA | Resolution time prediction |

### Key Components

- **LangGraph Workflow**: Orchestrates the validation pipeline with conditional routing
- **ML Services**: Classification, anomaly detection, and ETA prediction with fallbacks
- **Guardrails**: PII masking, source validation, anti-hallucination checks
- **HITL Gates**: Human review for low-confidence or high-risk cases
- **Audit Trail**: Complete traceability of all decisions

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd policy-validation-copilot

# Install dependencies
pip install -e ".[dev]"

# Or with ML dependencies
pip install -e ".[dev,ml]"
```

## Usage

### Start the API Server

```bash
# Using the CLI
policy-copilot

# Or directly with uvicorn
uvicorn policy_validation_copilot.api.main:app --reload
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/validate` | Submit case for validation |
| GET | `/api/v1/cases/{case_id}` | Get case status |
| GET | `/api/v1/cases/{case_id}/hitl` | Get HITL request |
| POST | `/api/v1/cases/{case_id}/hitl` | Submit HITL response |
| GET | `/api/v1/cases/{case_id}/audit` | Get audit trail |
| GET | `/api/v1/workflow/diagram` | Get workflow diagram |

### Example: Validate a Case

```python
import httpx

response = httpx.post(
    "http://localhost:8000/api/v1/validate",
    json={
        "customer_id": "CUST-001",
        "insurer_id": "INS-001",
        "plan_id": "PLAN-BASIC",
        "service_code": "SVC-DENTAL-001",
        "service_description": "Dental cleaning service",
        "priority": "NORMAL",
    },
)

result = response.json()
print(f"Case ID: {result['case_id']}")
print(f"Status: {result['status']}")
print(f"Decision: {result['decision_status']}")
```

### Programmatic Usage

```python
from policy_validation_copilot.models.case import Case, CasePriority
from policy_validation_copilot.agents.workflow import run_validation

# Create a case
case = Case(
    case_id="CASE-001",
    customer_id="CUST-001",
    insurer_id="INS-001",
    plan_id="PLAN-001",
    service_code="SVC-001",
    priority=CasePriority.NORMAL,
)

# Run validation
final_state = await run_validation(case)

# Check result
if final_state.decision:
    print(f"Decision: {final_state.decision.status}")
    print(f"Confidence: {final_state.decision.confidence_score}")
```

## Configuration

Configuration is managed through environment variables:

```bash
# Thresholds
POLICY_COPILOT_THRESHOLDS__CONFIDENCE_HIGH=0.85
POLICY_COPILOT_THRESHOLDS__RISK_LOW=0.30

# ML Services
POLICY_COPILOT_ML__CLASSIFY_ENDPOINT=http://ml-service:8001/classify
POLICY_COPILOT_ML__FALLBACK_ENABLED=true

# Guardrails
POLICY_COPILOT_GUARDRAILS__PII_MASKING_ENABLED=true
POLICY_COPILOT_GUARDRAILS__ALLOWLIST_SOURCES_ONLY=true
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=policy_validation_copilot

# Run specific test file
pytest tests/test_models.py
```

## Project Structure

```
src/policy_validation_copilot/
├── __init__.py
├── models/           # Pydantic data models (Anexo A state schema)
│   ├── case.py       # Case entity
│   ├── evidence.py   # Evidence pack
│   ├── checklist.py  # Rule evaluation
│   ├── decision.py   # Decision output
│   ├── ml.py         # ML contracts (Anexo B)
│   ├── guardrails.py # Guardrail results
│   ├── hitl.py       # HITL requests/responses
│   ├── audit.py      # Audit trail
│   └── state.py      # LangGraph state
├── nodes/            # LangGraph nodes
│   ├── case_ingest.py
│   ├── intelligent_routing.py
│   ├── policy_retrieval.py
│   ├── rules_checklist.py
│   ├── decision_orchestrator.py
│   ├── insurer_connector.py
│   ├── hitl_gate.py
│   └── audited_closure.py
├── agents/           # LangGraph workflow
│   └── workflow.py
├── services/         # External integrations
│   ├── ml_service.py
│   ├── kb_service.py
│   ├── storage_service.py
│   └── crm_service.py
├── guardrails/       # Security controls
│   ├── service.py
│   ├── pii_detector.py
│   ├── source_validator.py
│   └── hallucination_checker.py
├── api/              # FastAPI endpoints
│   └── main.py
└── utils/            # Utilities
    └── logging.py
```

## Business Rules

| Rule | Description |
|------|-------------|
| RB-01 | No APROBADO without verifiable evidence |
| RB-02 | Allowlist of sources only |
| RB-03 | Approved exceptions prevail in scope |
| RB-04 | Configurable thresholds for auto-close vs HITL |
| RB-05 | Version tracking for all decisions |

## License

MIT License
