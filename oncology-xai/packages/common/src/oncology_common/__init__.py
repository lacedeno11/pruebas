"""Oncology XAI Common Package - Shared utilities and models."""

from oncology_common.models.base import (
    BaseModel,
    BaseResponse,
    PaginatedResponse,
    ErrorResponse,
    ErrorDetail,
)
from oncology_common.models.entities import (
    Patient,
    PatientCreate,
    Case,
    CaseCreate,
    CaseStatus,
    Image,
    ImageCreate,
    ImageFormat,
    ResultBundle,
    PatternResult,
    GeneticResult,
    MutationStatus,
    PatternType,
    MutationType,
    EHRDocument,
    EHREntity,
    EHRMapping,
    GraphSnapshot,
    ExplanationReport,
    OntologyVersion,
    UpdateProposal,
    ProposalStatus,
    AuditEvent,
)
from oncology_common.auth.jwt import JWTValidator, TokenPayload
from oncology_common.middleware.correlation import CorrelationMiddleware
from oncology_common.middleware.logging import LoggingMiddleware

__version__ = "0.1.0"

__all__ = [
    # Base models
    "BaseModel",
    "BaseResponse",
    "PaginatedResponse",
    "ErrorResponse",
    "ErrorDetail",
    # Entities
    "Patient",
    "PatientCreate",
    "Case",
    "CaseCreate",
    "CaseStatus",
    "Image",
    "ImageCreate",
    "ImageFormat",
    "ResultBundle",
    "PatternResult",
    "GeneticResult",
    "MutationStatus",
    "PatternType",
    "MutationType",
    "EHRDocument",
    "EHREntity",
    "EHRMapping",
    "GraphSnapshot",
    "ExplanationReport",
    "OntologyVersion",
    "UpdateProposal",
    "ProposalStatus",
    "AuditEvent",
    # Auth
    "JWTValidator",
    "TokenPayload",
    # Middleware
    "CorrelationMiddleware",
    "LoggingMiddleware",
]
