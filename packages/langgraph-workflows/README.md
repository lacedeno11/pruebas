# LangGraph Workflows Package

Base GraphState class and common workflow utilities for the DERCAS-ONCO-XAI platform.

## Features

- Base GraphState class with common fields
- Common workflow utilities and tools
- Shared LangGraph node implementations
- Workflow execution helpers
- State management utilities
- Error handling for workflows

## Base GraphState

```python
from packages.langgraph_workflows import BaseGraphState

class MyWorkflowState(BaseGraphState):
    # Add workflow-specific fields
    custom_field: str = None
```

## Common Fields

### Identity and Correlation
- `correlation_id`: Trace end-to-end requests
- `user_id`: User performing the action
- `roles`: User roles for authorization
- `permissions`: Effective permissions

### Clinical Context
- `patient_id`: Patient identifier
- `case_id`: Case identifier

### Inputs
- `image_id`: Image identifier
- `image_uri`: Image storage URI
- `ehr_id`: EHR document identifier
- `ehr_text`: EHR text content
- `ontology_versions`: Active ontology versions

### Execution
- `job_id`: Async job identifier
- `status`: Current workflow status
- `progress`: Execution progress (0.0-1.0)
- `errors`: List of errors encountered
- `metrics`: Performance metrics

### Outputs
- `pattern_outputs`: Pattern detection results
- `genetic_outputs`: Genetic mutation results
- `xai_artifacts`: Explainability artifacts
- `ehr_entities`: Extracted entities
- `ehr_mappings`: Ontology mappings
- `graph_snapshot_id`: Graph snapshot identifier
- `explanation_report_id`: Generated report identifier

### Policies
- `thresholds`: Confidence thresholds
- `hitl_policy`: Human-in-the-loop policy
- `guardrails_policy`: Clinical guardrails policy

## Workflow Tools

### Common Tools
- `llm_client`: LLM integration (mock/OpenAI/Anthropic)
- `model_client`: ML model client (mock/Triton)
- `storage_client`: Object storage client (MinIO S3)
- `sparql_client`: Triple store client (Fuseki)
- `reasoner_client`: Ontology reasoner client
- `audit_logger`: Audit event logger
- `policy_engine`: Policy validation engine

## Usage

```python
from packages.langgraph_workflows import BaseGraphState, WorkflowBuilder

# Define workflow state
class ImageAnalysisState(BaseGraphState):
    image_data: bytes = None
    pattern_results: List[PatternResult] = []

# Build workflow
workflow = WorkflowBuilder() \
    .add_node("validate_input", validate_input_node) \
    .add_node("load_image", load_image_node) \
    .add_node("run_patterns", run_pattern_model_node) \
    .add_edge("validate_input", "load_image") \
    .add_edge("load_image", "run_patterns") \
    .build()

# Execute workflow
result = await workflow.execute(ImageAnalysisState(
    correlation_id="corr_123",
    case_id="case_456",
    image_id="img_789"
))
```
