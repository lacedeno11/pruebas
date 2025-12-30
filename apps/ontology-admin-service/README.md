# Ontology Admin Service

FastAPI service for ontology management and deep search in DERCAS-ONCO-XAI V1 platform.

## Responsibilities

- Ontology updates via LLM deep search (online/offline)
- Diff computation and reasoner validation
- OntologyUpdateWorkflow LangGraph implementation
- Whitelist validation and impact analysis
- Proposal management and approval workflows

## LangGraph Workflow: OntologyUpdateWorkflow

SourceDiscovery → FetchOntology → ValidateIntegrity → ParseRDF → ComputeDiff → LLMMappingSuggestions → ReasonerCheck → ImpactAnalysis → CreateProposal → HITLApproval → PublishOrRollback

## Endpoints

- `GET /api/v1/admin/ontologies` - List ontology versions
- `POST /api/v1/admin/ontologies:update-proposal` - Create update proposal
- `GET /api/v1/admin/ontologies/proposals/{proposalId}` - Get proposal details
- `POST /api/v1/admin/ontologies/proposals/{proposalId}:run-validation` - Run validation
- `POST /api/v1/admin/ontologies/proposals/{proposalId}:approve-and-publish` - Approve and publish
- `POST /api/v1/admin/ontologies/proposals/{proposalId}:rollback` - Rollback changes

## Development

```bash
cd apps/ontology-admin-service
python -m uvicorn main:app --reload --port 8006
```
