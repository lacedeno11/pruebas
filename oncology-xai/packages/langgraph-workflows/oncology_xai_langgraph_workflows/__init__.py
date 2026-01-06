# DERCAS-ONCO-XAI V1 - LangGraph Workflows Package
# Base GraphState and common workflow utilities

"""
LangGraph workflows package for DERCAS-ONCO-XAI V1 platform.

This package contains:
- Base GraphState with common fields (identity, context, inputs, exec, outputs, policies)
- Common workflow utilities and tools
- Reusable LangGraph components for AI workflows
- Tool interfaces for LLM, model, storage, SPARQL, and reasoner clients
"""

__version__ = "1.0.0"

from .state import (
    BaseGraphState,
    IdentityContext,
    ClinicalContext,
    InputContext,
    ExecutionContext,
    OutputContext,
    PolicyContext,
)
from .tools import (
    BaseTool,
    LLMClient,
    ModelClient,
    StorageClient,
    SPARQLClient,
    ReasonerClient,
    MockLLMClient,
    MockModelClient,
)
from .workflows import (
    BaseWorkflow,
    WorkflowNode,
    WorkflowEdge,
    ConditionalEdge,
    create_workflow_graph,
)
from .utils import (
    generate_correlation_id,
    create_job_context,
    validate_clinical_guardrails,
    format_workflow_error,
)

__all__ = [
    # State
    "BaseGraphState",
    "IdentityContext",
    "ClinicalContext",
    "InputContext",
    "ExecutionContext",
    "OutputContext",
    "PolicyContext",
    # Tools
    "BaseTool",
    "LLMClient",
    "ModelClient",
    "StorageClient",
    "SPARQLClient",
    "ReasonerClient",
    "MockLLMClient",
    "MockModelClient",
    # Workflows
    "BaseWorkflow",
    "WorkflowNode",
    "WorkflowEdge",
    "ConditionalEdge",
    "create_workflow_graph",
    # Utils
    "generate_correlation_id",
    "create_job_context",
    "validate_clinical_guardrails",
    "format_workflow_error",
]
