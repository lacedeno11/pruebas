# Ontology Admin Service

Ontology administration and versioning service for the Oncology XAI system.

## Features

- **Ontology Version Management**: Track and manage multiple versions of medical ontologies (NCIt, MONDO, SO)
- **Update Proposals**: Create and track ontology update proposals with approval workflow
- **Reasoner Validation**: Automatic consistency checking using OWL-RL reasoner
- **LangGraph Integration**: Uses OntologyUpdateWorkflow for automated processing
- **Diff Computation**: Automatically compute changes between ontology versions
- **Impact Analysis**: Analyze the impact of ontology updates on the system
- **Approval Workflow**: Human-in-the-loop approval for critical changes
- **Rollback Support**: Rollback to previous ontology versions
- **Event Publishing**: Publishes events to RabbitMQ for system-wide notification
- **Async Processing**: Uses Celery with Redis for background task processing

## Architecture

### Models

- `OntologyVersion`: Represents a published ontology version
- `OntologyUpdateProposal`: Represents an update proposal with approval workflow

### Proposal Status Flow

```
DRAFT → VALIDATING → VALIDATED/REQUIRES_FIX → PENDING_APPROVAL → APPROVED → PUBLISHED
```

Rollback flow:
```
ROLLBACK_REQUESTED → ROLLED_BACK
```

### API Endpoints

#### GET /api/v1/admin/ontologies
List all active ontology versions.

#### POST /api/v1/admin/ontologies:update-proposal
Create a new ontology update proposal.

**Request:**
```json
{
  "ontologySources": ["NCIt", "MONDO"],
  "mode": "online",  // or "offline"
  "uploadedFiles": {},  // For offline mode
  "createdBy": "admin@example.com"
}
```

#### GET /api/v1/admin/ontologies/proposals/{proposalId}
Get details of a specific proposal.

#### POST /api/v1/admin/ontologies/proposals/{proposalId}:run-validation
Run reasoner validation on a proposal.

#### POST /api/v1/admin/ontologies/proposals/{proposalId}:approve-and-publish
Approve and publish a proposal.

**Request:**
```json
{
  "approvedBy": "admin@example.com",
  "approvalNotes": "Approved after review"
}
```

#### POST /api/v1/admin/ontologies/proposals/{proposalId}:rollback
Rollback to a previous version.

**Request:**
```json
{
  "toVersionId": "uuid-of-version",  // Optional, uses previous version if not specified
  "createdBy": "admin@example.com"
}
```

## Configuration

Environment variables:

- `POSTGRES_DSN`: PostgreSQL connection string
- `RABBITMQ_URL`: RabbitMQ connection URL
- `REDIS_URL`: Redis connection URL
- `REASONER_BACKEND`: Reasoner backend to use (`mock` or `owlrl`)
- `ALLOWED_ONTOLOGY_SOURCES`: Whitelisted ontology sources (default: NCIt, MONDO, SO)

## Running the Service

### Development

```bash
# Install dependencies
pip install -e .

# Run database migrations
alembic upgrade head

# Start the service
uvicorn ontology_admin_service.main:app --reload --port 8006

# Start Celery worker
celery -A ontology_admin_service.tasks.celery_app worker --loglevel=info
```

### Docker

```bash
docker build -t oncology-ontology-admin-service .
docker run -p 8006:8006 oncology-ontology-admin-service
```

## Integration with LangGraph

The service integrates with the `OntologyUpdateWorkflow` LangGraph workflow:

1. When a proposal is created in `online` mode, the workflow is automatically triggered
2. The workflow performs:
   - Source discovery and validation
   - Ontology fetching
   - Integrity validation
   - RDF parsing
   - Diff computation
   - LLM mapping suggestions
   - Reasoner consistency check
   - Impact analysis
   - Proposal creation
3. Results are stored in the proposal for review
4. Admins can approve and publish the proposal

## Events Published

The service publishes the following events to RabbitMQ:

- `ontology.proposal.created`: When a new proposal is created
- `ontology.proposal.validated`: When validation completes
- `ontology.published`: When an ontology version is published
- `ontology.rolled_back`: When an ontology is rolled back

## Security

- Whitelisted ontology sources prevent unauthorized ontology imports
- Human approval required for publishing changes
- Content hash verification ensures data integrity
- Audit trail for all changes (created_by, approved_by, timestamps)

## License

Proprietary - Oncology XAI System
