"""
Policy Validation Copilot: Agentic LangGraph Architecture for Automated Decision Support

This package implements a comprehensive policy validation system using LangGraph for
agentic workflow orchestration, with ML services, guardrails, and human-in-the-loop
capabilities for automated decision support in policy validation scenarios.

Key Components:
- LangGraph-based workflow orchestration
- ML service integrations (classification, anomaly detection, ETA prediction)
- Comprehensive guardrails and security controls
- Evidence-based decision making with audit trails
- Human-in-the-loop integration for complex cases
- RESTful API for external system integration

Architecture:
- Case Ingest → Intelligent Routing → Policy Retrieval (RAG) → Rules & Checklist Builder
  → Decision Orchestrator → Insurer Connector (optional) → Audited Closure
- HITL gates for low/medium confidence, high risk, anomalies, or conflicts
- Complete audit trail with versioned evidence packs
"""

__version__ = "0.1.0"
__author__ = "Policy Validation Team"
__email__ = "team@policyvalidation.com"

# Package metadata
__title__ = "policy-validation-copilot"
__description__ = "Agentic LangGraph Architecture for Automated Policy Validation Decision Support"
__url__ = "https://github.com/policy-validation/copilot"
__license__ = "MIT"

# Version info
VERSION = __version__
VERSION_INFO = tuple(map(int, __version__.split(".")))

# Public API exports
from policy_validation_copilot.config.settings import Settings
from policy_validation_copilot.models.state import PolicyValidationState

__all__ = [
    "Settings",
    "PolicyValidationState",
    "__version__",
    "VERSION",
    "VERSION_INFO",
]
