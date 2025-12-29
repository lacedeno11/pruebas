# DERCAS-ONCO-XAI Architecture Document

## System Overview

DERCAS-ONCO-XAI is an explainable AI platform for oncology pathology, specifically designed for lung adenocarcinoma analysis. The system combines computer vision, natural language processing, and knowledge graphs to provide interpretable clinical decision support.

## Design Principles

1. **Explainability First**: Every prediction includes XAI artifacts (heatmaps, attention maps)
2. **Clinical Safety**: Guardrails prevent definitive diagnostic language
3. **Audit Trail**: All actions are logged for compliance
4. **Loose Coupling**: Event-driven architecture for service independence
5. **Ontology-Driven**: Biomedical ontologies provide semantic grounding

## Technology Stack

### Backend
- **Language**: Python 3.11
- **Framework**: FastAPI with Pydantic v2
- **Database**: PostgreSQL 16 + SQLAlchemy 2.0
- **Migrations**: Alembic
- **Task Queue**: Celery + Redis
- **Message Broker**: RabbitMQ
- **Object Storage**: MinIO (S3-compatible)
- **Triple Store**: Apache Jena Fuseki
- **Auth**: Keycloak (OIDC)
- **AI Workflows**: LangGraph

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: TailwindCSS
- **Graph Visualization**: vis-network

### Observability
- **Tracing**: OpenTelemetry + Jaeger
- **Metrics**: Prometheus
- **Logging**: Structured JSON

## Service Architecture

### API Gateway (Port 8000)
- JWT token validation against Keycloak
- Role-based access control (RBAC)
- Request routing to downstream services
- Correlation ID propagation

### Case Service (Port 8001)
- Patient demographic management
- Case lifecycle (created → processing → completed/failed)
- Event publishing on state changes

### Image Service (Port 8002)
- File upload validation (PNG, BIFF formats)
- Checksum calculation
- Storage in MinIO
- Signed URL generation for viewing

### Inference Service (Port 8003)
- Async job scheduling via Celery
- Pattern segmentation (5 types)
- Mutation prediction (EGFR, KRAS, TP53)
- XAI artifact generation (GradCAM)

### EHR Service (Port 8004)
- Clinical text normalization
- Entity extraction (LLM-based NER)
- Ontology candidate lookup
- Disambiguation and confidence scoring
- Explanation generation with guardrails

### Graph Service (Port 8005)
- SPARQL query execution
- Triple management
- Case subgraph assembly
- Visualization data formatting

### Ontology Admin Service (Port 8006)
- Ontology version management
- LangGraph workflow for updates
- Human-in-the-loop approval
- Reasoner consistency checks

### Audit Service (Port 8007)
- RabbitMQ event consumer
- Persistent audit log storage
- Query interface for compliance

## Data Flow

### Image Analysis Flow
```
1. User uploads image via WebApp
2. API Gateway validates JWT, routes to Image Service
3. Image Service stores in MinIO, publishes IMAGE_UPLOADED event
4. Inference Service creates job, starts Celery task
5. Worker runs LangGraph ImageAnalysisGraph:
   - Load image from MinIO
   - Run pattern model (mock/Triton)
   - Run mutation model (mock/Triton)
   - Generate GradCAM heatmap
   - Check policy compliance
   - Persist results
6. INFERENCE_COMPLETED event published
7. Audit Service logs all events
```

### EHR Processing Flow
```
1. User pastes clinical text in EHR Panel
2. API Gateway routes to EHR Service
3. EHR Service runs EHRToOntologyGraph:
   - Normalize text
   - Extract entities via LLM
   - Query Fuseki for ontology candidates
   - Disambiguate with context
   - Build evidence pack
4. Entities and mappings persisted
5. ExplanationComposerGraph generates report:
   - Gather all evidence
   - Detect conflicting findings
   - Draft explanation
   - Validate against guardrails
   - Publish if compliant
```

## Event-Driven Architecture

### Event Types
- `case.created`, `case.updated`
- `image.uploaded`
- `inference.started`, `inference.completed`, `inference.failed`
- `ehr.ingested`, `entities.extracted`, `ontology.mapped`
- `graph.updated`
- `explanation.generated`
- `audit.event`

### Event Envelope
```json
{
  "event_id": "uuid",
  "event_type": "inference.completed",
  "timestamp": "2024-01-01T00:00:00Z",
  "source": "inference-service",
  "correlation_id": "uuid",
  "case_id": "uuid",
  "payload": { ... }
}
```

## LangGraph Workflows

### State Machine Pattern
Each workflow follows a consistent pattern:
1. **State Definition**: TypedDict with all workflow data
2. **Node Functions**: Async functions that modify state
3. **Conditional Edges**: Branching based on state
4. **Error Handling**: Catch exceptions, set error state

### Example: ImageAnalysisGraph
```python
graph = StateGraph(ImageAnalysisState)
graph.add_node("validate", validate_input)
graph.add_node("load", load_image)
graph.add_node("pattern", run_pattern_model)
graph.add_node("mutation", run_mutation_model)
graph.add_node("xai", generate_xai)
graph.add_node("policy", policy_check)
graph.add_node("persist", persist_results)
graph.add_node("finalize", finalize)

graph.add_edge(START, "validate")
graph.add_conditional_edges("validate", check_error, {"error": "finalize", "ok": "load"})
graph.add_edge("load", "pattern")
graph.add_edge("pattern", "mutation")
graph.add_edge("mutation", "xai")
graph.add_edge("xai", "policy")
graph.add_edge("policy", "persist")
graph.add_edge("persist", "finalize")
graph.add_edge("finalize", END)
```

## Clinical Guardrails

### Prohibited Patterns
- "definitive diagnosis"
- "confirmed [disease]"
- "patient has [disease]"
- "definitely", "certainly", "undoubtedly"

### Required Sections
- Summary
- Disclaimer
- Clinical correlation recommendation

### Validation Flow
```python
def validate_explanation(text: str) -> GuardrailResult:
    result = GuardrailResult(passed=True, violations=[], warnings=[])

    # Check prohibited phrases
    for pattern in PROHIBITED_PATTERNS:
        if pattern.search(text):
            result.passed = False
            result.violations.append(f"Prohibited phrase: {pattern.pattern}")

    # Check required sections
    if "disclaimer" not in text.lower():
        result.passed = False
        result.violations.append("Missing disclaimer section")

    return result
```

## Security Model

### Authentication
- Keycloak OIDC provider
- JWT tokens with RS256 signing
- Token refresh via refresh_token

### Authorization
- Role-based access control (RBAC)
- Roles: clinician, admin, auditor
- Permission checks in API Gateway

### Data Protection
- TLS for all external communication
- Encryption at rest for MinIO
- Audit logging for all data access

## Deployment Considerations

### Container Requirements
| Service | CPU | Memory | Notes |
|---------|-----|--------|-------|
| API Gateway | 0.5 | 512MB | Stateless |
| Case Service | 0.5 | 512MB | DB connection pool |
| Image Service | 0.5 | 1GB | File handling |
| Inference Service | 2 | 4GB | ML models |
| EHR Service | 1 | 2GB | LLM calls |
| Graph Service | 0.5 | 1GB | SPARQL queries |
| Audit Service | 0.25 | 256MB | Event consumer |

### Scaling Strategy
- Horizontal scaling for stateless services
- Read replicas for PostgreSQL
- Redis cluster for high availability
- RabbitMQ clustering for message durability

## Future Considerations

### Phase 2 Enhancements
- Real ML model integration (Triton Inference Server)
- FHIR R4 integration for EHR
- Multi-cancer type support
- Federated learning for privacy

### Technical Debt
- Add comprehensive integration tests
- Implement circuit breakers
- Add request rate limiting
- Enhance observability dashboards
