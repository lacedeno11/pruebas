# DERCAS-ONCO-XAI V1 Architecture

## Overview

DERCAS-ONCO-XAI V1 is an explainable AI platform for lung cancer histopathology analysis. The platform integrates image processing, EHR analysis, and ontology management in a microservices architecture.

## System Architecture

### High-Level Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WebApp        │    │  API Gateway    │    │  Keycloak       │
│  (React/Vite)   │◄──►│  (FastAPI)      │◄──►│  (Auth)         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
        ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
        │ Case Service │ │Image Service│ │EHR Service │
        │ (Patients/   │ │(Upload/     │ │(Ingest/    │
        │  Cases)      │ │ Storage)    │ │ Extract)   │
        └──────────────┘ └─────────────┘ └────────────┘
                │               │               │
        ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
        │Inference     │ │Graph Service│ │Ontology    │
        │Service       │ │(RDF/SPARQL) │ │Admin       │
        │(ML/XAI)      │ │             │ │Service     │
        └──────────────┘ └─────────────┘ └────────────┘
                │               │               │
                └───────────────┼───────────────┘
                                │
                        ┌───────▼──────┐
                        │Audit Service │
                        │(Events/      │
                        │ Compliance)  │
                        └──────────────┘
```

### Infrastructure Components

- **PostgreSQL 16**: Primary database for all services
- **RabbitMQ**: Event messaging and job queues
- **Redis**: Celery backend and caching
- **MinIO**: S3-compatible object storage
- **Apache Jena Fuseki**: RDF triple store for ontologies
- **Keycloak**: OIDC authentication and authorization
- **Jaeger**: Distributed tracing
- **Prometheus**: Metrics collection

## Service Responsibilities

### API Gateway
- JWT validation and RBAC routing
- Request proxying to internal services
- Rate limiting and request size limits
- Correlation-ID propagation

### Case Service
- Patient and case management
- Case status workflow
- Event emission for case lifecycle

### Image Service
- Histopathological image upload and storage
- File validation and checksum verification
- Signed URL generation for viewing

### Inference Service
- ML model inference for pattern detection
- Genetic mutation prediction
- XAI artifact generation
- LangGraph workflow: ImageAnalysisGraph

### EHR Service
- Electronic health record ingestion
- Entity extraction and ontology mapping
- LangGraph workflow: EHRToOntologyGraph

### Graph Service
- RDF triple store management
- Case-specific knowledge graphs
- LangGraph workflow: GraphAssemblerGraph

### Ontology Admin Service
- Ontology version management
- Deep search and update workflows
- LangGraph workflow: OntologyUpdateWorkflow

### Audit Service
- Event consumption and persistence
- Compliance and traceability queries

## Data Flow

### Image Processing Workflow
1. User uploads image via WebApp
2. Image Service validates and stores in MinIO
3. User triggers processing via Inference Service
4. ImageAnalysisGraph workflow executes:
   - Pattern detection (5 patterns)
   - Mutation prediction (3 mutations)
   - XAI artifact generation
5. Results stored and events emitted
6. Audit Service records all activities

### EHR Processing Workflow
1. User ingests EHR document via WebApp
2. EHR Service stores and versions document
3. User triggers extraction via EHR Service
4. EHRToOntologyGraph workflow executes:
   - Entity extraction
   - Ontology mapping to NCIt/MONDO/SO
   - Evidence pack generation
5. Results stored and events emitted

### Knowledge Graph Construction
1. Graph Service consumes inference and EHR events
2. GraphAssemblerGraph workflow executes:
   - Fetches case findings
   - Queries relevant ontology subgraphs
   - Fuses and annotates with provenance
   - Generates layout for visualization
3. Graph snapshot created and stored

## Event-Driven Architecture

### Event Types
- `case.created`, `case.updated`
- `image.uploaded`, `image.deleted`
- `job.created`, `job.progress`, `job.completed`, `job.failed`
- `inference.completed`, `inference.failed`
- `ehr.ingested`, `ehr.extracted`, `ehr.mapped`
- `graph.built`, `graph.failed`
- `ontology.proposal.created`, `ontology.published`
- `audit.event.created`

### Event Envelope
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

## Security Architecture

### Authentication
- Keycloak OIDC with PKCE flow
- JWT tokens with role-based claims
- Service-to-service authentication

### Authorization
- RBAC roles: clinician, admin, auditor
- ABAC for patient data access
- Resource-level permissions

### Data Protection
- PHI redaction in logs
- Encrypted storage for sensitive data
- Audit trails for all access

## Clinical Compliance

### Guardrails
- No deterministic diagnosis language
- Confidence scores and thresholds
- Model version tracking
- Limitations and disclaimers required

### HITL (Human-in-the-Loop)
- Low confidence score triggers
- Conflict detection between sources
- Manual review workflows
- Approval gates for critical decisions

### Audit Requirements
- Complete traceability with correlation IDs
- Immutable audit logs
- Model and ontology version tracking
- Compliance reporting capabilities

## Deployment Architecture

### Development
- Docker Compose for local development
- Hot reloading for all services
- Mock implementations for external dependencies

### Production (Future)
- Kubernetes deployment
- Horizontal pod autoscaling
- External secret management
- Production-grade databases and message brokers

## Technology Decisions

### Backend
- **FastAPI**: Modern, fast, OpenAPI-native
- **Pydantic v2**: Type safety and validation
- **SQLAlchemy 2.0**: Modern ORM with async support
- **LangGraph**: AI workflow orchestration

### Frontend
- **React + Vite**: Modern, fast development
- **TypeScript**: Type safety
- **Material-UI**: Consistent design system

### Infrastructure
- **PostgreSQL**: ACID compliance for clinical data
- **RabbitMQ**: Reliable message delivery
- **MinIO**: S3-compatible, self-hosted storage
- **Fuseki**: Standards-compliant RDF store

This architecture ensures scalability, maintainability, and clinical compliance while providing a foundation for explainable AI in oncology.
