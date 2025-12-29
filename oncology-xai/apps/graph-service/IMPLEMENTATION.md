# Graph Service Implementation Summary

## Overview
Complete Graph Service implementation for the Oncology XAI system at `/home/user/pruebas/oncology-xai/apps/graph-service`.

## Features Implemented

### Core Functionality
- FastAPI REST API running on port 8005
- Celery with Redis for async graph building
- Integration with GraphAssembler LangGraph workflow
- SPARQLClient for Fuseki triple store interaction
- PostgreSQL database for graph snapshot storage
- Mock data generation for visualization

### API Endpoints
1. **GET /api/v1/cases/{caseId}/graph** - Get latest case graph with optional depth and includeInferred params
2. **POST /api/v1/cases/{caseId}/graph:rebuild** - Trigger async graph rebuild
3. **GET /api/v1/graphs/{graphSnapshotId}** - Get specific graph snapshot by ID
4. **GET /api/v1/tasks/{taskId}/status** - Check Celery task status

## File Structure

```
/home/user/pruebas/oncology-xai/apps/graph-service/
├── Dockerfile                          # FastAPI service container
├── Dockerfile.worker                   # Celery worker container
├── README.md                           # Service documentation
├── IMPLEMENTATION.md                   # This file
├── docker-compose.example.yml          # Docker compose configuration
├── pyproject.toml                      # Python dependencies
├── alembic.ini                         # Alembic configuration
├── .dockerignore                       # Docker ignore file
│
├── alembic/
│   ├── env.py                          # Alembic environment
│   └── versions/
│       └── 001_initial.py              # Initial migration (case_graph_snapshots table)
│
└── src/
    └── graph_service/
        ├── __init__.py
        ├── main.py                     # FastAPI application entry point
        ├── config.py                   # Service configuration
        ├── database.py                 # SQLAlchemy setup
        │
        ├── models/
        │   ├── __init__.py
        │   └── graph_snapshot.py       # CaseGraphSnapshot model
        │
        ├── services/
        │   ├── __init__.py
        │   └── graph_service.py        # Business logic for graph operations
        │
        ├── routes/
        │   ├── __init__.py
        │   └── graphs.py               # API route handlers
        │
        └── tasks/
            ├── __init__.py
            ├── celery_app.py           # Celery configuration
            └── graph_tasks.py          # Async graph rebuild task
```

## Database Model: CaseGraphSnapshot

### Schema
```python
graph_snapshot_id: UUID (PK)
case_id: UUID (indexed)
nodes: JSONB                            # Array of graph nodes
edges: JSONB                            # Array of graph edges
layout: JSONB                           # Node positions for visualization
depth: Integer                          # Graph traversal depth (1-5)
include_inferred: Boolean               # Include inferred relationships
metadata: JSONB                         # Provenance, stats, etc.
task_id: String(255)                    # Celery task ID if async
created_at: Timestamp
updated_at: Timestamp
```

### Indexes
- `ix_case_graph_snapshots_case_id` on `case_id`
- `ix_case_graph_snapshots_case_depth_inferred` on `(case_id, depth, include_inferred)`

## Integration Points

### LangGraph Workflow
The service integrates with the `GraphAssemblerGraph` workflow from `langgraph-workflows` package:

1. **FetchCaseFindings** - Fetches findings (currently mocked)
2. **QuerySubgraph** - Queries ontology subgraph from Fuseki
3. **FuseAnnotateProvenance** - Merges graphs and adds provenance metadata
4. **BuildLayout** - Calculates node positions using force-directed layout
5. **PersistSnapshot** - Saves complete graph to database
6. **Finalize** - Completes workflow execution

### Mock Data Generated
The workflow currently generates mock nodes and edges:

**Nodes:**
- Case node (type: Case)
- Diagnosis node (type: Diagnosis, from NCIt ontology)
- Pattern nodes (type: Pattern, e.g., Lepidic, Acinar)
- Mutation nodes (type: Mutation, e.g., EGFR)

**Edges:**
- Asserted relationships (from direct findings)
- Inferred relationships (from ontology reasoning)

### SPARQL Integration
Uses `SPARQLClient` from `oncology-common` to query the Fuseki triple store:
- Fuseki URL: configurable via `FUSEKI_URL` env var
- Dataset: configurable via `FUSEKI_DATASET` env var

## Configuration

### Environment Variables
```bash
POSTGRES_DSN=postgresql+asyncpg://oncology:oncology_secret@postgres:5432/oncology_xai
REDIS_URL=redis://redis:6379/0
FUSEKI_URL=http://fuseki:3030
FUSEKI_DATASET=oncology
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318  # Optional
```

### Dependencies
- fastapi>=0.104.0
- uvicorn[standard]>=0.24.0
- sqlalchemy[asyncio]>=2.0.0
- asyncpg>=0.29.0
- alembic>=1.12.0
- pydantic>=2.5.0
- pydantic-settings>=2.1.0
- celery[redis]>=5.3.0
- redis>=5.0.0
- oncology-common (shared utilities)
- oncology-event-contracts (event schemas)
- oncology-langgraph-workflows (LangGraph workflows)

## Running the Service

### 1. Run Migrations
```bash
cd /home/user/pruebas/oncology-xai/apps/graph-service
alembic upgrade head
```

### 2. Start FastAPI Server
```bash
uvicorn graph_service.main:app --host 0.0.0.0 --port 8005
```

### 3. Start Celery Worker
```bash
celery -A graph_service.tasks.celery_app worker --loglevel=info
```

### 4. Using Docker
```bash
# Build and run API service
docker build -t graph-service -f Dockerfile ../..
docker run -p 8005:8005 graph-service

# Build and run Celery worker
docker build -t graph-worker -f Dockerfile.worker ../..
docker run graph-worker
```

## API Usage Examples

### Get Latest Graph for Case
```bash
curl -X GET "http://localhost:8005/api/v1/cases/{caseId}/graph?depth=2&includeInferred=true"
```

Response:
```json
{
  "graph_snapshot_id": "uuid",
  "case_id": "uuid",
  "nodes": [
    {
      "id": "case_uuid",
      "label": "Case UUID",
      "type": "Case",
      "iri": "urn:oncology:case:uuid",
      "source": "internal",
      "properties": {...}
    },
    ...
  ],
  "edges": [
    {
      "source": "case_uuid",
      "target": "ncit_c3512",
      "label": "hasDiagnosis",
      "type": "asserted"
    },
    ...
  ],
  "layout": {
    "case_uuid": {"x": 300, "y": 300},
    ...
  },
  "depth": 2,
  "include_inferred": true,
  "metadata": {
    "provenance": [...],
    "node_count": 5,
    "edge_count": 6
  },
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Rebuild Graph Asynchronously
```bash
curl -X POST "http://localhost:8005/api/v1/cases/{caseId}/graph:rebuild?depth=2&includeInferred=true"
```

Response:
```json
{
  "task_id": "celery-task-uuid",
  "case_id": "uuid",
  "status": "pending",
  "message": "Graph rebuild started for case uuid"
}
```

### Check Task Status
```bash
curl -X GET "http://localhost:8005/api/v1/tasks/{taskId}/status"
```

Response:
```json
{
  "task_id": "celery-task-uuid",
  "status": "success",
  "result": {
    "graph_snapshot_id": "uuid",
    "case_id": "uuid",
    "status": "completed",
    "node_count": 5,
    "edge_count": 6
  }
}
```

### Get Specific Snapshot
```bash
curl -X GET "http://localhost:8005/api/v1/graphs/{graphSnapshotId}"
```

## Testing

### Health Check
```bash
curl http://localhost:8005/healthz
```

Expected response:
```json
{
  "status": "healthy",
  "service": "graph-service",
  "version": "0.1.0"
}
```

## Code Statistics
- Total Python files: 11
- Total lines of code: ~595 lines
- Test coverage: N/A (tests not yet implemented)

## Next Steps

1. **Integration Testing** - Add tests for graph assembly workflow
2. **Real Data Integration** - Replace mocks with actual EHR/Inference service calls
3. **Advanced Graph Algorithms** - Add centrality, clustering, path finding
4. **Graph Filtering** - Allow filtering by node/edge types
5. **Graph Diff** - Compare snapshots to show changes
6. **Export Formats** - Add GraphML, Cytoscape, Neo4j export
7. **Performance** - Add caching and optimize SPARQL queries
8. **Monitoring** - Add metrics for graph build time, size, etc.

## Notes
- All findings fetch is currently mocked (see `graph_assembler.py:fetch_case_findings`)
- Layout algorithm is simple circular layout (can be enhanced with force-directed or hierarchical)
- SPARQL queries are mocked in the workflow (real queries would go to Fuseki)
- Task timeout is set to 30 minutes (configurable in `celery_app.py`)
