# Graph Service

Triple store integration and case-specific subgraph generation service with Apache Jena Fuseki.

## Features

- Apache Jena Fuseki integration for RDF/SPARQL operations
- Named graph management (graph:case:{caseId})
- Case-specific subgraph generation
- GraphAssemblerGraph LangGraph workflow
- SPARQL queries for case data fusion
- Provenance tracking using PROV-O
- Graph snapshot generation for visualization
- Support for inferred vs asserted relationships

## Endpoints

- `GET /api/v1/cases/{caseId}/graph` - Get case graph with filters
- `POST /api/v1/cases/{caseId}/graph:rebuild` - Rebuild case graph
- `GET /api/v1/graphs/{graphSnapshotId}` - Get graph snapshot

## LangGraph Workflow

```
FetchCaseFindings → QuerySubgraph → FuseAnnotateProvenance → 
BuildLayout → PersistSnapshot → Finalize
```

## Development

```bash
cd apps/graph-service
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload --port 8005
```
