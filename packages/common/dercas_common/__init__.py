"""
DERCAS-ONCO-XAI Common Package

Shared utilities, models, and middleware for the DERCAS-ONCO-XAI platform.
"""

__version__ = "0.1.0"

from .models import *
from .auth import *
from .middleware import *
from .errors import *
from .utils import *

__all__ = [
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
    "MLJob",
    "CaseStatus",
    "PatternType",
    "MutationType",
    "JobStatus",
    "JobType",
    
    # Auth
    "JWTAuth",
    "get_current_user",
    "require_roles",
    "verify_jwt_token",
    
    # Middleware
    "CorrelationIdMiddleware",
    "add_correlation_id",
    "get_correlation_id",
    
    # Errors
    "DercasError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ConflictError",
    "InternalServerError",
    "ErrorResponse",
    
    # Utils
    "generate_id",
    "get_timestamp",
    "hash_content",
    "sanitize_phi",
]
