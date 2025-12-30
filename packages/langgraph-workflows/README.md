# LangGraph Workflows Package

Reusable LangGraph workflows and components for DERCAS-ONCO-XAI V1 platform.

## Contents

### Base GraphState
- Common state structure for all workflows
- Identity and correlation tracking
- Clinical context management
- Input/output standardization

### Common Tools Interfaces
- LLM client abstraction (mock, OpenAI, Anthropic)
- Model client interface (mock, Triton)
- Storage client (MinIO S3)
- SPARQL client (Fuseki)
- Reasoner client (stub, owlrl/rdfLib)

### Workflow Templates
- Base workflow patterns
- Error handling and retry logic
- HITL (Human-in-the-Loop) integration points
- Clinical guardrails enforcement

### Implemented Workflows
1. **ImageAnalysisGraph** (inference-service)
   - ValidateInput → LoadImage → RunPatternModel → RunMutationModel → GenerateXAI → AssembleResultBundle → PolicyCheck → PersistAndAudit → Finalize

2. **EHRToOntologyGraph** (ehr-service)
   - NormalizeEHR → ExtractEntities → LookupCandidates → Disambiguate → BuildEvidencePack → PersistEntitiesMappings → Finalize

3. **GraphAssemblerGraph** (graph-service)
   - FetchCaseFindings → QuerySubgraph → FuseAnnotateProvenance → BuildLayout → PersistSnapshot → Finalize

4. **ExplanationComposerGraph** (ehr-service)
   - GatherEvidence → DetectConflicts → DraftExplanation → ValidateClaimsGuardrails → PublishReport → Finalize

5. **OntologyUpdateWorkflow** (ontology-admin-service)
   - SourceDiscovery → FetchOntology → ValidateIntegrity → ParseRDF → ComputeDiff → LLMMappingSuggestions → ReasonerCheck → ImpactAnalysis → CreateProposal → HITLApproval → PublishOrRollback

## Usage

```python
from packages.langgraph_workflows import BaseGraphState, BaseTool
from packages.langgraph_workflows.image_analysis import ImageAnalysisGraph
from packages.langgraph_workflows.tools import LLMClient, StorageClient

# Initialize workflow
workflow = ImageAnalysisGraph()
state = BaseGraphState(
    correlation_id="corr_123",
    case_id="case_456",
    image_id="img_789"
)

# Execute workflow
result = await workflow.execute(state)
```

## Clinical Compliance

All workflows implement:
- Clinical guardrails (no definitive diagnoses)
- Confidence thresholds and HITL triggers
- Complete audit trails
- Version tracking for reproducibility
