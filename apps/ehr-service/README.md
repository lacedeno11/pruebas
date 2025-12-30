# EHR Service

FastAPI service for Electronic Health Record processing in DERCAS-ONCO-XAI V1 platform.

## Responsibilities

- EHR document ingestion and versioning
- Entity extraction using mock LLM
- Ontology mapping to NCIt/MONDO/SO with evidence tracking
- EHRToOntologyGraph LangGraph workflow implementation
- Conflict detection and ambiguity resolution

## LangGraph Workflow: EHRToOntologyGraph

NormalizeEHR → ExtractEntities → LookupCandidates → Disambiguate → BuildEvidencePack → PersistEntitiesMappings → Finalize

## Endpoints

- `POST /api/v1/cases/{caseId}/ehr:ingest` - Ingest EHR document
- `GET /api/v1/cases/{caseId}/ehr/versions` - List EHR versions
- `GET /api/v1/ehr/{ehrId}` - Get EHR document
- `POST /api/v1/ehr/{ehrId}:extract-and-map` - Extract entities and map to ontologies
- `GET /api/v1/ehr/{ehrId}/entities` - Get extracted entities
- `GET /api/v1/ehr/{ehrId}/mappings` - Get ontology mappings

## Development

```bash
cd apps/ehr-service
python -m uvicorn main:app --reload --port 8004
```
