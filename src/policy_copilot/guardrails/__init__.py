"""
Policy Copilot Guardrails Package

This package contains security and governance enforcement for UC-OP-10:
- RBAC/ABAC enforcement for all operations
- PII masking for LLM/ML payloads
- Source allowlist validation
- Injection/jailbreak/exfiltration detection
- Evidence anchoring validation (anti-hallucination)
- Security event logging and incident response
"""

from typing import Dict, Any, List

from .base import (
    BaseGuardrail,
    GuardrailEngine,
    GuardrailResult,
    GuardrailContext,
    GuardrailDecision,
    GuardrailSeverity,
    GuardrailFlag,
    GuardrailRedaction,
    SecurityEvent,
    guardrail_engine
)

from .rbac_abac import (
    RBACGuardrail,
    ABACGuardrail,
    Permission,
    Role,
    AccessPolicy
)

from .pii_masking import (
    PIIMaskingGuardrail,
    PIIPattern
)

from .source_allowlist import (
    SourceAllowlistGuardrail,
    AllowedSource
)

from .injection_detection import (
    InjectionDetectionGuardrail,
    InjectionPattern
)

from .evidence_anchoring import (
    EvidenceAnchoringGuardrail,
    EvidenceReference
)

__all__ = [
    # Base classes and interfaces
    "BaseGuardrail",
    "GuardrailEngine",
    "GuardrailResult",
    "GuardrailContext",
    "GuardrailDecision",
    "GuardrailSeverity",
    "GuardrailFlag",
    "GuardrailRedaction",
    "SecurityEvent",
    "guardrail_engine",
    
    # RBAC/ABAC guardrails
    "RBACGuardrail",
    "ABACGuardrail",
    "Permission",
    "Role",
    "AccessPolicy",
    
    # PII masking guardrails
    "PIIMaskingGuardrail",
    "PIIPattern",
    
    # Source allowlist guardrails
    "SourceAllowlistGuardrail",
    "AllowedSource",
    
    # Injection detection guardrails
    "InjectionDetectionGuardrail",
    "InjectionPattern",
    
    # Evidence anchoring guardrails
    "EvidenceAnchoringGuardrail",
    "EvidenceReference"
]


def create_guardrail_engine(enable_all: bool = True) -> GuardrailEngine:
    """
    Factory function to create and configure a complete guardrail engine.
    
    Args:
        enable_all: Whether to enable all guardrails by default
        
    Returns:
        Configured guardrail engine with all guardrails registered
    """
    engine = GuardrailEngine()
    
    # Register all guardrails
    guardrails = [
        RBACGuardrail(),
        ABACGuardrail(),
        PIIMaskingGuardrail(),
        SourceAllowlistGuardrail(),
        InjectionDetectionGuardrail(),
        EvidenceAnchoringGuardrail()
    ]
    
    for guardrail in guardrails:
        engine.register_guardrail(guardrail)
        if not enable_all:
            guardrail.disable()
    
    return engine


def create_security_context(
    user_id: str = None,
    user_roles: List[str] = None,
    user_permissions: List[str] = None,
    resource_type: str = "case",
    resource_id: str = None,
    action: str = "read",
    source_ip: str = None,
    session_id: str = None,
    request_id: str = None
) -> GuardrailContext:
    """
    Factory function to create a security context for guardrail evaluation.
    
    Args:
        user_id: User identifier
        user_roles: List of user roles
        user_permissions: List of user permissions
        resource_type: Type of resource being accessed
        resource_id: Resource identifier
        action: Action being performed
        source_ip: Source IP address
        session_id: Session identifier
        request_id: Request correlation ID
        
    Returns:
        Configured guardrail context
    """
    return GuardrailContext(
        user_id=user_id,
        user_roles=user_roles or [],
        user_permissions=user_permissions or [],
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        source_ip=source_ip,
        session_id=session_id,
        request_id=request_id
    )


async def evaluate_payload_security(
    payload: Dict[str, Any],
    context: GuardrailContext,
    engine: GuardrailEngine = None
) -> GuardrailResult:
    """
    Convenience function to evaluate payload security using all guardrails.
    
    Args:
        payload: Payload to evaluate
        context: Security context
        engine: Guardrail engine to use (creates default if None)
        
    Returns:
        Consolidated guardrail result
    """
    if engine is None:
        engine = create_guardrail_engine()
    
    return await engine.evaluate_all(payload, context)


# Pre-configured guardrail engine instance
default_guardrail_engine = create_guardrail_engine()

