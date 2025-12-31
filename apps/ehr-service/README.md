# EHR Service

EHR document ingestion, entity extraction, and ontology mapping service with LangGraph workflows.

## Features

- EHR document ingestion (versioned)
- Entity extraction using mock LLM/NLP
- Ontology mapping to NCIt/MONDO/SO concepts
- EHRToOntologyGraph LangGraph workflow
- Evidence tracking (text spans, confidence scores)
- Conflict detection with image results
- HITL triggers for ambiguous mappings

## Endpoints

- `POST /api/v1/cases/{caseId}/ehr:ingest` - Ingest EHR document
- `GET /api/v1/cases/{caseId}/ehr/versions` - List EHR versions
- `GET /api/v1/ehr/{ehrId}` - Get EHR document
- `POST /api/v1/ehr/{ehrId}:extract-and-map` - Extract entities and map to ontologies
- `GET /api/v1/ehr/{ehrId}/entities` - Get extracted entities
- `GET /api/v1/ehr/{ehrId}/mappings` - Get ontology mappings

## LangGraph Workflow

```
NormalizeEHR → ExtractEntities → LookupCandidates → Disambiguate → 
BuildEvidencePack → PersistEntitiesMappings → Finalize
```

## Development

```bash
cd apps/ehr-service
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload --port 8004
```
