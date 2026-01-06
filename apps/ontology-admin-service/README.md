# Ontology Admin Service

Ontology management service with LangGraph workflows for automated discovery and updates.

## Features

- OntologyUpdateWorkflow LangGraph for automated ontology discovery
- Database models for ontology_versions and ontology_update_proposals
- RDFLib integration for parsing/diffing
- Basic reasoner validation (owlrl)
- Whitelist-based source validation
- Offline mode for manual OWL/RDF uploads
- Impact analysis for breaking changes

## Endpoints

- `GET /api/v1/admin/ontologies` - List ontology versions
- `POST /api/v1/admin/ontologies:update-proposal` - Create update proposal
- `GET /api/v1/admin/ontologies/proposals/{proposalId}` - Get proposal details
- `POST /api/v1/admin/ontologies/proposals/{proposalId}:run-validation` - Run validation
- `POST /api/v1/admin/ontologies/proposals/{proposalId}:approve-and-publish` - Approve and publish
- `POST /api/v1/admin/ontologies/proposals/{proposalId}:rollback` - Rollback changes

## LangGraph Workflow

```
SourceDiscovery → FetchOntology → ValidateIntegrity → ParseRDF → 
ComputeDiff → LLMMappingSuggestions → ReasonerCheck → ImpactAnalysis → 
CreateProposal → HITLApproval → PublishOrRollback
```

## Development

```bash
cd apps/ontology-admin-service
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload --port 8006
```
