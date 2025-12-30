# DERCAS-ONCO-XAI V1 - Common Package
# Shared utilities, models, and schemas for all services

"""
Common package for DERCAS-ONCO-XAI V1 platform.

This package contains:
- Authentication utilities (JWT verification with JWKS)
- Correlation-id middleware
- Standard error schemas
- Shared Pydantic models (Patient, Case, Image, ResultBundle, etc.)
"""

__version__ = "1.0.0"

from .auth import JWTAuth, get_current_user, require_roles
from .middleware import CorrelationIdMiddleware, correlation_id_context
from .models import (
    Patient,
    Case,
    Image,
    ResultBundle,
    PatternResult,
    GeneticResult,
    XAIArtifact,
    EHRDocument,
    EHREntity,
    EHRMapping,
    CaseGraphSnapshot,
    ExplanationReport,
    OntologyVersion,
    OntologyUpdateProposal,
    AuditEvent,
)
from .schemas import (
    ErrorResponse,
    HealthResponse,
    PaginatedResponse,
    JobStatus,
    CaseStatus,
    PatternType,
    MutationType,
    MutationStatus,
    OntologyName,
)
from .exceptions import (
    OncologyXAIException,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    NotFoundError,
    ConflictError,
    ExternalServiceError,
)

__all__ = [
    # Auth
    "JWTAuth",
    "get_current_user",
    "require_roles",
    # Middleware
    "CorrelationIdMiddleware",
    "correlation_id_context",
    # Models
    "Patient",
    "Case",
    "Image",
    "ResultBundle",
    "PatternResult",
    "GeneticResult",
    "XAIArtifact",
    "EHRDocument",
    "EHREntity",
    "EHRMapping",
    "CaseGraphSnapshot",
    "ExplanationReport",
    "OntologyVersion",
    "OntologyUpdateProposal",
    "AuditEvent",
    # Schemas
    "ErrorResponse",
    "HealthResponse",
    "PaginatedResponse",
    "JobStatus",
    "CaseStatus",
    "PatternType",
    "MutationType",
    "MutationStatus",
    "OntologyName",
    # Exceptions
    "OncologyXAIException",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "ExternalServiceError",
]
