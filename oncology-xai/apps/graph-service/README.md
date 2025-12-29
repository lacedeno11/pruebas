# Graph Service

Graph assembly and management service for the Oncology XAI system. This service builds knowledge graphs for cases by integrating findings from various sources (EHR, imaging, inference) with ontology data.

## Features

- **FastAPI REST API** running on port 8005
- **Celery + Redis** for asynchronous graph building
- **LangGraph Integration** using GraphAssembler workflow
- **SPARQL Client** for querying Fuseki triple store
- **PostgreSQL** for storing graph snapshots
- **Mock Data Generation** for visualization

## Architecture

The service uses a multi-stage graph assembly process:

1. **Fetch Case Findings** - Retrieves findings from EHR and Inference services (currently mocked)
2. **Query Subgraph** - Queries relevant ontology subgraph from Fuseki
3. **Fuse & Annotate** - Merges graphs and adds provenance
4. **Build Layout** - Calculates node positions for visualization
5. **Persist Snapshot** - Saves complete graph to database

## API Endpoints

### Get Case Graph
```
GET /api/v1/cases/{caseId}/graph?depth=2&includeInferred=true
```
Returns the latest graph snapshot for a case with specified parameters.

### Rebuild Case Graph
```
POST /api/v1/cases/{caseId}/graph:rebuild?depth=2&includeInferred=true
```
Triggers asynchronous graph rebuild. Returns task ID.

### Get Graph Snapshot
```
GET /api/v1/graphs/{graphSnapshotId}
```
Returns a specific graph snapshot by ID.

### Get Task Status
```
GET /api/v1/tasks/{taskId}/status
```
Checks status of a graph rebuild task.

## Database Model

### CaseGraphSnapshot
- `graph_snapshot_id` (UUID, PK)
- `case_id` (UUID, indexed)
- `nodes` (JSONB) - Array of graph nodes
- `edges` (JSONB) - Array of graph edges
- `layout` (JSONB) - Node positions for visualization
- `depth` (Integer) - Graph traversal depth
- `include_inferred` (Boolean) - Whether inferred edges included
- `metadata` (JSONB) - Provenance, stats, etc.
- `task_id` (String) - Celery task ID if async
- `created_at` (Timestamp)
- `updated_at` (Timestamp)

## Running the Service

### API Server
```bash
uvicorn graph_service.main:app --host 0.0.0.0 --port 8005
```

### Celery Worker
```bash
celery -A graph_service.tasks.celery_app worker --loglevel=info
```

### Database Migrations
```bash
alembic upgrade head
```

## Configuration

Environment variables:
- `POSTGRES_DSN` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `FUSEKI_URL` - Fuseki SPARQL endpoint
- `FUSEKI_DATASET` - Fuseki dataset name
- `OTEL_EXPORTER_OTLP_ENDPOINT` - OpenTelemetry endpoint (optional)

## Development

Install dependencies:
```bash
pip install -e .
pip install -e .[dev]
```

Run tests:
```bash
pytest
```

## Mock Data

The service currently generates mock nodes and edges:
- **Case Node** - Represents the case
- **Diagnosis Node** - From ontology (e.g., Lung Adenocarcinoma)
- **Pattern Nodes** - From image analysis (e.g., Lepidic, Acinar)
- **Mutation Nodes** - From genomic analysis (e.g., EGFR)

Edges represent relationships:
- **Asserted** - Direct findings from analysis
- **Inferred** - Derived from ontology reasoning

## Future Enhancements

- Real integration with EHR and Inference services
- Advanced graph algorithms (centrality, clustering)
- Interactive graph filtering and exploration
- Graph diff/comparison between snapshots
- Export to standard formats (GraphML, Cytoscape)
