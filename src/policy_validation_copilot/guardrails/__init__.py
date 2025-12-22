"""
Guardrails and security enforcement components.

This module contains comprehensive security and governance controls including:
- OWASP LLM Top 10 security controls
- RBAC/ABAC access control enforcement
- PII masking and data protection
- Source allowlist validation
- Anti-hallucination checks
- Injection and jailbreak detection
- Security event logging and monitoring

Key Components:
- PolicyValidationGuardrails: Main guardrails enforcement system
- SecurityContext: Security context for guardrails evaluation
- GuardrailsConfig: Configuration for guardrails system
- PIIMaskingEngine: PII detection and masking
- InjectionDetector: Injection detection and prevention
- SourceAllowlistValidator: Source allowlist validation
- AntiHallucinationValidator: Anti-hallucination verification
- RBACEnforcer: Role-based access control
- SecurityEventLogger: Security event logging

Usage:
    from policy_validation_copilot.guardrails import (
        PolicyValidationGuardrails,
        SecurityContext,
        GuardrailsConfig,
        UserRole,
        create_guardrails_system,
        with_guardrails
    )
    
    # Create guardrails system
    guardrails = create_guardrails_system()
    
    # Create security context
    context = SecurityContext(
        user_id="user123",
        user_role=UserRole.AGENT,
        session_id="session456"
    )
    
    # Enforce guardrails
    result = await guardrails.enforce_guardrails(
        context=context,
        user_input="Some user input to validate"
    )
"""

# Core guardrails system
from .security import (
    PolicyValidationGuardrails,
    SecurityContext,
    GuardrailsConfig,
    PIIMaskingEngine,
    InjectionDetector,
    SourceAllowlistValidator,
    AntiHallucinationValidator,
    RBACEnforcer,
    SecurityEventLogger,
    create_guardrails_system,
    with_guardrails
)

# Enums and types
from .security import (
    OWASPThreatType,
    AccessLevel,
    UserRole
)

# Export all public components
__all__ = [
    # Main classes
    "PolicyValidationGuardrails",
    "SecurityContext", 
    "GuardrailsConfig",
    
    # Component classes
    "PIIMaskingEngine",
    "InjectionDetector", 
    "SourceAllowlistValidator",
    "AntiHallucinationValidator",
    "RBACEnforcer",
    "SecurityEventLogger",
    
    # Enums
    "OWASPThreatType",
    "AccessLevel",
    "UserRole",
    
    # Factory functions and decorators
    "create_guardrails_system",
    "with_guardrails",
]

# Version information
__version__ = "1.0.0"

