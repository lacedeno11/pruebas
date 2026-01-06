# Graph Service

FastAPI service for RDF triple store and knowledge graph management in DERCAS-ONCO-XAI V1 platform.

## Responsibilities

- Apache Jena Fuseki integration for RDF triple store
- Case-specific named graphs (graph:case:{caseId})
- SPARQL query handling and optimization
- GraphAssemblerGraph LangGraph workflow implementation
- Provenance tracking and layout generation for graph visualization

## LangGraph Workflow: GraphAssemblerGraph

FetchCaseFindings → QuerySubgraph → FuseAnnotateProvenance → BuildLayout → PersistSnapshot → Finalize

## Endpoints

- `GET /api/v1/cases/{caseId}/graph` - Get case knowledge graph
- `POST /api/v1/cases/{caseId}/graph:rebuild` - Rebuild case graph
- `GET /api/v1/graphs/{graphSnapshotId}` - Get graph snapshot

## Development

```bash
cd apps/graph-service
python -m uvicorn main:app --reload --port 8005
```
