"""
Guardrails and Governance Enforcement for Policy Validation Copilot

This module implements UC-OP-10 with comprehensive security controls including
OWASP LLM Top 10 protections, RBAC/ABAC authorization, PII detection/masking,
allowlist source validation, injection/jailbreak detection, and anti-hallucination
evidence anchoring with security event logging and middleware integration.
"""

# Core guardrails service
from .service import (
    GuardrailsService,
    GuardrailsConfig,
    OWASPLLMControls,
    PIIDetector,
    SourceValidator,
    AntiHallucinationService,
    RBACService,
    create_guardrails_service
)

# Middleware and integration
from .middleware import (
    GuardrailsMiddleware,
    LangGraphGuardrailsIntegration,
    GuardrailsEventLogger,
    create_guardrails_middleware,
    create_langgraph_integration,
    create_event_logger
)

# Factory function for complete guardrails setup
def setup_guardrails(config: GuardrailsConfig = None) -> dict:
    """
    Setup complete guardrails system with all components.
    
    Returns a dictionary with all guardrails components for easy access.
    """
    guardrails_config = config or GuardrailsConfig()
    
    # Create core service
    service = create_guardrails_service(guardrails_config)
    
    # Create middleware
    middleware = create_guardrails_middleware(service)
    
    # Create LangGraph integration
    langgraph_integration = create_langgraph_integration(service)
    
    # Create event logger
    event_logger = create_event_logger(guardrails_config)
    
    return {
        'service': service,
        'middleware': middleware,
        'langgraph_integration': langgraph_integration,
        'event_logger': event_logger,
        'config': guardrails_config
    }


# Convenience functions for common operations
def enforce_guardrails_on_state(state, user_role: str = "agent", user_id: str = "system"):
    """Convenience function to enforce guardrails on a PolicyValidationState."""
    service = create_guardrails_service()
    return service.enforce_guardrails(state, user_role, user_id)


def create_guardrails_node():
    """Create a LangGraph node for guardrails enforcement."""
    integration = create_langgraph_integration()
    return integration.create_guardrails_node()


def get_guardrails_status():
    """Get status of all guardrails components."""
    service = create_guardrails_service()
    return service.get_guardrails_status()


__all__ = [
    # Core service components
    'GuardrailsService',
    'GuardrailsConfig',
    'OWASPLLMControls',
    'PIIDetector',
    'SourceValidator',
    'AntiHallucinationService',
    'RBACService',
    'create_guardrails_service',
    
    # Middleware and integration
    'GuardrailsMiddleware',
    'LangGraphGuardrailsIntegration',
    'GuardrailsEventLogger',
    'create_guardrails_middleware',
    'create_langgraph_integration',
    'create_event_logger',
    
    # Setup and convenience functions
    'setup_guardrails',
    'enforce_guardrails_on_state',
    'create_guardrails_node',
    'get_guardrails_status'
]

