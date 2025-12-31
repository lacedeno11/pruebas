# DERCAS-ONCO-XAI V1 - System Architecture

## Overview

DERCAS-ONCO-XAI V1 is a microservices-based explainable AI platform for lung cancer oncology that integrates histopathological image analysis, EHR processing, ontology mapping, and clinical decision support.

## Architecture Principles

- **Microservices**: Loosely coupled services with clear boundaries
- **Event-Driven**: Asynchronous communication via RabbitMQ
- **Domain-Driven Design**: Services organized around clinical domains
- **Clinical Safety**: Mandatory guardrails and audit trails
- **Explainability**: Transparent AI decisions with provenance
- **Scalability**: Horizontal scaling with container orchestration

## System Context (C4 Level 1)

```
┌─────────────────────────────────────────────────────────────┐
│                    DERCAS-ONCO-XAI V1                      │
│                                                             │
│  Explainable AI Platform for Lung Cancer Oncology         │
│                                                             │
│  • Histopathological Image Analysis                        │
│  • EHR Processing & Ontology Mapping                       │
│  • Knowledge Graph Generation                              │
│  • Clinical Decision Support                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Oncologists │    │   Pathologists  │    │ System Admins   │
│             │    │                 │    │                 │
│ • View cases│    │ • Analyze images│    │ • Manage system │
│ • Review AI │    │ • Validate AI   │    │ • Update ontol. │
│ • Generate  │    │ • Clinical QA   │    │ • Monitor audit │
│   reports   │    │                 │    │                 │
└─────────────┘    └─────────────────┘    └─────────────────┘
```

## Container Diagram (C4 Level 2)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DERCAS-ONCO-XAI V1                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────────────────────────────────────────┐    │
│  │   WebApp    │    │                API Gateway                      │    │
│  │ React+Vite  │◄──►│ FastAPI + JWT + RBAC + Rate Limiting           │    │
│  └─────────────┘    └─────────────────┬───────────────────────────────┘    │
│                                       │                                     │
│  ┌─────────────────────────────────────┼─────────────────────────────────┐  │
│  │                    Microservices    │                                 │  │
│  │                                     ▼                                 │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │Case Service │  │Image Service│  │Inference Svc│  │ EHR Service │  │  │
│  │  │             │  │             │  │             │  │             │  │  │
│  │  │• Patients   │  │• Upload     │  │• ML Models  │  │• Ingestion  │  │  │
│  │  │• Cases      │  │• Storage    │  │• LangGraph  │  │• Extraction │  │  │
│  │  │• Events     │  │• Validation │  │• XAI        │  │• Mapping    │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  │                                                                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │Graph Service│  │Ontology Adm │  │Audit Service│  │             │  │  │
│  │  │             │  │             │  │             │  │             │  │  │
│  │  │• SPARQL     │  │• Deep Search│  │• Events     │  │             │  │  │
│  │  │• Subgraphs  │  │• Diff/Merge │  │• Compliance │  │             │  │  │
│  │  │• Provenance │  │• Validation │  │• Queries    │  │             │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        Infrastructure                               │  │
│  │                                                                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │  │
│  │  │ PostgreSQL  │  │  RabbitMQ   │  │    Redis    │  │   MinIO     │ │  │
│  │  │             │  │             │  │             │  │             │ │  │
│  │  │• Relational │  │• Events     │  │• Cache      │  │• Objects    │ │  │
│  │  │• ACID       │  │• Jobs       │  │• Sessions   │  │• Images     │ │  │
│  │  │• Migrations │  │• Queues     │  │• Celery     │  │• Artifacts  │ │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │  │
│  │                                                                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │  │
│  │  │  Keycloak   │  │   Fuseki    │  │   Jaeger    │  │ Prometheus  │ │  │
│  │  │             │  │             │  │             │  │             │ │  │
│  │  │• OIDC       │  │• RDF Store  │  │• Tracing    │  │• Metrics    │ │  │
│  │  │• JWT        │  │• SPARQL     │  │• Monitoring │  │• Alerting   │ │  │
│  │  │• RBAC       │  │• Ontologies │  │• Debugging  │  │• Dashboards │ │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Diagram (C4 Level 3) - Inference Service

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Inference Service                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      FastAPI Application                           │   │
│  │                                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │   Process   │  │    Jobs     │  │   Results   │  │ Artifacts   │ │   │
│  │  │  Endpoint   │  │  Endpoint   │  │  Endpoint   │  │  Endpoint   │ │   │
│  │  │             │  │             │  │             │  │             │ │   │
│  │  │POST :process│  │GET /jobs/   │  │GET /results/│  │GET /artifacts│ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    ImageAnalysisGraph (LangGraph)                  │   │
│  │                                                                     │   │
│  │  ValidateInput → LoadImage → RunPatternModel → RunMutationModel    │   │
│  │       ↓              ↓              ↓               ↓              │   │
│  │  GenerateXAI → AssembleResultBundle → PolicyCheck → PersistAudit   │   │
│  │       ↓              ↓              ↓               ↓              │   │
│  │                    Finalize                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Celery Workers                              │   │
│  │                                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │   Pattern   │  │  Mutation   │  │     XAI     │  │   Policy    │ │   │
│  │  │   Models    │  │   Models    │  │  Generator  │  │   Engine    │ │   │
│  │  │             │  │             │  │             │  │             │ │   │
│  │  │• Lepidic    │  │• EGFR       │  │• GradCAM    │  │• Thresholds │ │   │
│  │  │• Acinar     │  │• KRAS       │  │• Saliency   │  │• Guardrails │ │   │
│  │  │• Papillary  │  │• TP53       │  │• Overlays   │  │• HITL       │ │   │
│  │  │• Micropap.  │  │             │  │• Heatmaps   │  │• Conflicts  │ │   │
│  │  │• Solid      │  │             │  │             │  │             │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Data Access Layer                             │   │
│  │                                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │   Models    │  │ Repositories│  │   Events    │  │   Storage   │ │   │
│  │  │             │  │             │  │             │  │             │ │   │
│  │  │• MLJobs     │  │• JobRepo    │  │• Publisher  │  │• MinIO      │ │   │
│  │  │• Results    │  │• ResultRepo │  │• Consumer   │  │• Artifacts  │ │   │
│  │  │• Patterns   │  │• ArtifactRepo│  │• Envelope   │  │• Overlays   │ │   │
│  │  │• Genetics   │  │             │  │             │  │• Heatmaps   │ │   │
│  │  │• XAI        │  │             │  │             │  │             │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Event Flow Diagram

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    User     │    │   WebApp    │    │API Gateway  │    │Case Service │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │                  │
       │ Create Case      │                  │                  │
       ├─────────────────►│                  │                  │
       │                  │ POST /cases      │                  │
       │                  ├─────────────────►│                  │
       │                  │                  │ POST /patients   │
       │                  │                  ├─────────────────►│
       │                  │                  │                  │
       │                  │                  │ case.created     │
       │                  │                  │◄─────────────────┤
       │                  │ 201 Created      │                  │
       │                  │◄─────────────────┤                  │
       │ Case Created     │                  │                  │
       │◄─────────────────┤                  │                  │
       │                  │                  │                  │

┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    User     │    │   WebApp    │    │Image Service│    │Inference Svc│
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │                  │
       │ Upload Image     │                  │                  │
       ├─────────────────►│                  │                  │
       │                  │ POST :upload     │                  │
       │                  ├─────────────────►│                  │
       │                  │                  │                  │
       │                  │                  │ image.uploaded   │
       │                  │                  ├─────────────────►│
       │                  │ Image Uploaded   │                  │
       │                  │◄─────────────────┤                  │
       │ Upload Success   │                  │                  │
       │◄─────────────────┤                  │                  │
       │                  │                  │                  │
       │ Process Image    │                  │                  │
       ├─────────────────►│                  │                  │
       │                  │ POST :process    │                  │
       │                  ├─────────────────────────────────────►│
       │                  │                  │                  │
       │                  │                  │ job.created      │
       │                  │◄─────────────────────────────────────┤
       │                  │                  │                  │
       │                  │                  │ job.progress     │
       │                  │◄─────────────────────────────────────┤
       │                  │                  │                  │
       │                  │                  │ inference.completed
       │                  │◄─────────────────────────────────────┤
       │ Results Ready    │                  │                  │
       │◄─────────────────┤                  │                  │
```

## Data Flow Architecture

### Image Processing Pipeline

```
Image Upload → Validation → Storage → Queue → ML Processing → XAI → Results
     │              │          │        │         │           │       │
     ▼              ▼          ▼        ▼         ▼           ▼       ▼
┌─────────┐ ┌─────────────┐ ┌──────┐ ┌──────┐ ┌─────────┐ ┌──────┐ ┌──────┐
│Format   │ │Magic Bytes  │ │MinIO │ │Celery│ │Pattern  │ │Grad  │ │Result│
│Check    │ │Validation   │ │S3    │ │Queue │ │Models   │ │CAM   │ │Bundle│
│(.png/   │ │Checksum     │ │      │ │      │ │Mutation │ │Overlay│ │      │
│.biff)   │ │Size Limits  │ │      │ │      │ │Models   │ │Heat  │ │      │
│         │ │             │ │      │ │      │ │         │ │Maps  │ │      │
└─────────┘ └─────────────┘ └──────┘ └──────┘ └─────────┘ └──────┘ └──────┘
```

### EHR Processing Pipeline

```
EHR Text → Normalization → Entity Extraction → Ontology Mapping → Conflict Detection
    │            │               │                    │                 │
    ▼            ▼               ▼                    ▼                 ▼
┌─────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ ┌─────────────┐
│Text     │ │Section      │ │NLP/LLM      │ │SPARQL Lookup    │ │Image vs EHR │
│Ingestion│ │Detection    │ │Named Entity │ │NCIt/MONDO/SO    │ │Comparison   │
│Version  │ │Cleaning     │ │Recognition  │ │Candidate Match  │ │Confidence   │
│Control  │ │Tokenization │ │Confidence   │ │Disambiguation   │ │Thresholds   │
│         │ │             │ │Spans        │ │Evidence Pack    │ │HITL Trigger │
└─────────┘ └─────────────┘ └─────────────┘ └─────────────────┘ └─────────────┘
```

### Knowledge Graph Assembly

```
Case Findings → SPARQL Queries → Graph Fusion → Provenance → Visualization
      │              │              │             │             │
      ▼              ▼              ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ ┌─────────────┐
│Image Results│ │Subgraph     │ │Ontology     │ │PROV-O    │ │Nodes/Edges  │
│EHR Entities │ │Extraction   │ │Alignment    │ │Tracking  │ │Layout Model │
│Mappings     │ │Named Graphs │ │Equivalence  │ │Source    │ │Interactive  │
│Conflicts    │ │Reasoning    │ │Inference    │ │Evidence  │ │Filtering    │
│             │ │             │ │             │ │Metadata  │ │             │
└─────────────┘ └─────────────┘ └─────────────┘ └──────────┘ └─────────────┘
```

## Security Architecture

### Authentication & Authorization Flow

```
User → WebApp → Keycloak → JWT Token → API Gateway → Service
 │       │         │          │           │            │
 │       │         │          │           │            │
 ▼       ▼         ▼          ▼           ▼            ▼
┌────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────┐
│PKCE│ │OIDC    │ │Realm   │ │RS256   │ │JWKS      │ │RBAC    │
│Flow│ │Login   │ │Roles   │ │Signing │ │Verify    │ │Check   │
│    │ │        │ │Claims  │ │        │ │          │ │        │
└────┘ └────────┘ └────────┘ └────────┘ └──────────┘ └────────┘
```

### Data Protection

- **Encryption at Rest**: Database encryption, MinIO encryption
- **Encryption in Transit**: TLS 1.3 for all communications
- **PHI Redaction**: Automatic redaction in logs and audit trails
- **Access Control**: Role-based access with case-level permissions
- **Audit Trail**: Immutable audit logs with correlation tracking

## Deployment Architecture

### Local Development

```
Docker Compose
├── Infrastructure Services
│   ├── PostgreSQL 16
│   ├── RabbitMQ + Management UI
│   ├── Redis
│   ├── MinIO + Console
│   ├── Keycloak + Admin Console
│   ├── Apache Jena Fuseki
│   ├── Jaeger
│   └── Prometheus
├── Application Services
│   ├── API Gateway (Port 8080)
│   ├── Case Service (Port 8001)
│   ├── Image Service (Port 8002)
│   ├── Inference Service (Port 8003)
│   ├── EHR Service (Port 8004)
│   ├── Graph Service (Port 8005)
│   ├── Ontology Admin Service (Port 8006)
│   └── Audit Service (Port 8007)
└── Frontend
    └── React WebApp (Port 3000)
```

### Production Considerations

- **Container Orchestration**: Kubernetes with Helm charts
- **Load Balancing**: NGINX Ingress with SSL termination
- **Database**: PostgreSQL cluster with read replicas
- **Message Broker**: RabbitMQ cluster with high availability
- **Object Storage**: S3-compatible storage with CDN
- **Monitoring**: Prometheus + Grafana + AlertManager
- **Logging**: ELK Stack or similar centralized logging
- **Backup**: Automated backups with point-in-time recovery

## Quality Attributes

### Performance
- **Response Time**: < 200ms for API calls, < 30s for ML inference
- **Throughput**: 100 concurrent users, 1000 images/hour processing
- **Scalability**: Horizontal scaling of stateless services

### Reliability
- **Availability**: 99.9% uptime for clinical operations
- **Fault Tolerance**: Circuit breakers, retries, graceful degradation
- **Data Integrity**: ACID transactions, checksums, versioning

### Security
- **Authentication**: Multi-factor authentication support
- **Authorization**: Fine-grained RBAC with audit trails
- **Data Protection**: Encryption, PHI redaction, secure communication

### Maintainability
- **Modularity**: Clear service boundaries and interfaces
- **Testability**: Comprehensive test coverage (unit, integration, e2e)
- **Observability**: Distributed tracing, metrics, structured logging

### Clinical Compliance
- **Guardrails**: No deterministic diagnoses, mandatory limitations
- **Traceability**: Complete audit trail with correlation IDs
- **Reproducibility**: Version tracking for models and ontologies
- **Validation**: Clinical review workflows for AI outputs

## Technology Decisions

### Backend Framework: FastAPI
- **Rationale**: High performance, automatic OpenAPI, type safety
- **Alternatives**: Django REST, Flask
- **Trade-offs**: Learning curve vs. productivity and performance

### Database: PostgreSQL 16
- **Rationale**: ACID compliance, JSON support, mature ecosystem
- **Alternatives**: MySQL, MongoDB
- **Trade-offs**: Relational constraints vs. flexibility

### Message Broker: RabbitMQ
- **Rationale**: Reliable delivery, routing flexibility, management UI
- **Alternatives**: Apache Kafka, Redis Pub/Sub
- **Trade-offs**: Complexity vs. reliability and features

### Object Storage: MinIO
- **Rationale**: S3 compatibility, self-hosted, high performance
- **Alternatives**: AWS S3, Azure Blob Storage
- **Trade-offs**: Operational overhead vs. cost and control

### Authentication: Keycloak
- **Rationale**: Open source, OIDC/SAML support, enterprise features
- **Alternatives**: Auth0, AWS Cognito, custom solution
- **Trade-offs**: Setup complexity vs. feature richness and cost

### AI Orchestration: LangGraph
- **Rationale**: Workflow management, state tracking, debugging
- **Alternatives**: Apache Airflow, Prefect, custom orchestration
- **Trade-offs**: AI-specific features vs. general workflow tools

## Future Considerations

### Scalability Enhancements
- **Microservice Decomposition**: Further service splitting as needed
- **Caching Strategy**: Redis caching for frequently accessed data
- **Database Sharding**: Horizontal partitioning for large datasets
- **CDN Integration**: Global content delivery for images and reports

### Advanced AI Features
- **Model Versioning**: A/B testing and gradual rollouts
- **Federated Learning**: Multi-institutional model training
- **Real-time Inference**: Streaming ML pipelines
- **Advanced XAI**: Counterfactual explanations, feature attribution

### Integration Capabilities
- **FHIR Integration**: Standard healthcare data exchange
- **DICOM Support**: Medical imaging standards
- **HL7 Messaging**: Healthcare communication protocols
- **External Ontologies**: Automated ontology synchronization

### Compliance & Governance
- **HIPAA Compliance**: Enhanced PHI protection measures
- **FDA Validation**: Medical device software lifecycle processes
- **Clinical Trials**: Research data management capabilities
- **International Standards**: ISO 13485, IEC 62304 compliance
