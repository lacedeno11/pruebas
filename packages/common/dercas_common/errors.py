"""
DERCAS-ONCO-XAI Error Handling

Standardized error schemas and exception classes.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .middleware import get_correlation_id

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standardized error response schema."""
    error_code: str
    message: str
    correlation_id: Optional[str] = None
    details: Dict[str, Any] = {}
    timestamp: str
    
    class Config:
        schema_extra = {
            "example": {
                "error_code": "MODEL_UNAVAILABLE",
                "message": "Pattern model is not available",
                "correlation_id": "corr_123e4567-e89b-12d3-a456-426614174000",
                "details": {
                    "model_profile": "lung_patterns_v3"
                },
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class DercasError(Exception):
    """Base exception class for DERCAS-ONCO-XAI."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)
    
    def to_response(self, correlation_id: Optional[str] = None) -> ErrorResponse:
        """Convert exception to error response."""
        from datetime import datetime
        
        return ErrorResponse(
            error_code=self.error_code,
            message=self.message,
            correlation_id=correlation_id,
            details=self.details,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


class ValidationError(DercasError):
    """Validation error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class AuthenticationError(DercasError):
    """Authentication error."""
    
    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(DercasError):
    """Authorization error."""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=details,
            status_code=status.HTTP_403_FORBIDDEN
        )


class NotFoundError(DercasError):
    """Resource not found error."""
    
    def __init__(self, resource: str, resource_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"{resource} not found: {resource_id}"
        details = details or {}
        details.update({"resource": resource, "resource_id": resource_id})
        
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            details=details,
            status_code=status.HTTP_404_NOT_FOUND
        )


class ConflictError(DercasError):
    """Resource conflict error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            details=details,
            status_code=status.HTTP_409_CONFLICT
        )


class InternalServerError(DercasError):
    """Internal server error."""
    
    def __init__(self, message: str = "Internal server error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="INTERNAL_ERROR",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Domain-specific errors
class ModelUnavailableError(DercasError):
    """ML model unavailable error."""
    
    def __init__(self, model_name: str, details: Optional[Dict[str, Any]] = None):
        message = f"Model not available: {model_name}"
        details = details or {}
        details.update({"model_name": model_name})
        
        super().__init__(
            message=message,
            error_code="MODEL_UNAVAILABLE",
            details=details,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class ImageDecodeError(DercasError):
    """Image decoding error."""
    
    def __init__(self, image_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"Failed to decode image: {image_id}"
        details = details or {}
        details.update({"image_id": image_id})
        
        super().__init__(
            message=message,
            error_code="IMAGE_DECODE_ERROR",
            details=details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class EHRParseError(DercasError):
    """EHR parsing error."""
    
    def __init__(self, ehr_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"Failed to parse EHR: {ehr_id}"
        details = details or {}
        details.update({"ehr_id": ehr_id})
        
        super().__init__(
            message=message,
            error_code="EHR_PARSE_ERROR",
            details=details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class JobFailedError(DercasError):
    """Job execution failed error."""
    
    def __init__(self, job_id: str, job_type: str, details: Optional[Dict[str, Any]] = None):
        message = f"Job failed: {job_type} ({job_id})"
        details = details or {}
        details.update({"job_id": job_id, "job_type": job_type})
        
        super().__init__(
            message=message,
            error_code="JOB_FAILED",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class OntologyInconsistentError(DercasError):
    """Ontology inconsistency error."""
    
    def __init__(self, ontology_name: str, details: Optional[Dict[str, Any]] = None):
        message = f"Ontology inconsistent: {ontology_name}"
        details = details or {}
        details.update({"ontology_name": ontology_name})
        
        super().__init__(
            message=message,
            error_code="ONTOLOGY_INCONSISTENT",
            details=details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class SourceNotAllowedError(DercasError):
    """Source not allowed error."""
    
    def __init__(self, source_url: str, details: Optional[Dict[str, Any]] = None):
        message = f"Source not allowed: {source_url}"
        details = details or {}
        details.update({"source_url": source_url})
        
        super().__init__(
            message=message,
            error_code="SOURCE_NOT_ALLOWED",
            details=details,
            status_code=status.HTTP_403_FORBIDDEN
        )


class ReasonerFailedError(DercasError):
    """Reasoner execution failed error."""
    
    def __init__(self, reasoner_type: str, details: Optional[Dict[str, Any]] = None):
        message = f"Reasoner failed: {reasoner_type}"
        details = details or {}
        details.update({"reasoner_type": reasoner_type})
        
        super().__init__(
            message=message,
            error_code="REASONER_FAILED",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class GPUOutOfMemoryError(DercasError):
    """GPU out of memory error."""
    
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="GPU out of memory",
            error_code="GPU_OOM",
            details=details,
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE
        )


class TimeoutError(DercasError):
    """Operation timeout error."""
    
    def __init__(self, operation: str, timeout_seconds: int, details: Optional[Dict[str, Any]] = None):
        message = f"Operation timed out: {operation} (timeout: {timeout_seconds}s)"
        details = details or {}
        details.update({"operation": operation, "timeout_seconds": timeout_seconds})
        
        super().__init__(
            message=message,
            error_code="TIMEOUT",
            details=details,
            status_code=status.HTTP_408_REQUEST_TIMEOUT
        )


# Exception handlers
async def dercas_exception_handler(request: Request, exc: DercasError) -> JSONResponse:
    """Global exception handler for DercasError."""
    correlation_id = get_correlation_id()
    
    # Log the error
    logger.error(
        f"DercasError: {exc.error_code} - {exc.message}",
        extra={
            "correlation_id": correlation_id,
            "error_code": exc.error_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True
    )
    
    # Return standardized error response
    error_response = exc.to_response(correlation_id)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Global exception handler for HTTPException."""
    correlation_id = get_correlation_id()
    
    # Convert HTTPException to DercasError format
    error_response = ErrorResponse(
        error_code="HTTP_ERROR",
        message=exc.detail,
        correlation_id=correlation_id,
        details={"status_code": exc.status_code},
        timestamp=__import__('datetime').datetime.utcnow().isoformat() + "Z"
    )
    
    # Log the error
    logger.warning(
        f"HTTPException: {exc.status_code} - {exc.detail}",
        extra={
            "correlation_id": correlation_id,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unexpected exceptions."""
    correlation_id = get_correlation_id()
    
    # Log the unexpected error
    logger.error(
        f"Unexpected error: {type(exc).__name__} - {str(exc)}",
        extra={
            "correlation_id": correlation_id,
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True
    )
    
    # Return generic error response (don't expose internal details)
    error_response = ErrorResponse(
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        correlation_id=correlation_id,
        details={},
        timestamp=__import__('datetime').datetime.utcnow().isoformat() + "Z"
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.dict()
    )


def setup_exception_handlers(app):
    """Setup exception handlers for FastAPI app."""
    app.add_exception_handler(DercasError, dercas_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)


# Utility functions
def raise_not_found(resource: str, resource_id: str, details: Optional[Dict[str, Any]] = None):
    """Utility function to raise NotFoundError."""
    raise NotFoundError(resource, resource_id, details)


def raise_validation_error(message: str, details: Optional[Dict[str, Any]] = None):
    """Utility function to raise ValidationError."""
    raise ValidationError(message, details)


def raise_auth_error(message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
    """Utility function to raise AuthenticationError."""
    raise AuthenticationError(message, details)


def raise_authz_error(message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
    """Utility function to raise AuthorizationError."""
    raise AuthorizationError(message, details)


def raise_conflict_error(message: str, details: Optional[Dict[str, Any]] = None):
    """Utility function to raise ConflictError."""
    raise ConflictError(message, details)


def raise_internal_error(message: str = "Internal server error", details: Optional[Dict[str, Any]] = None):
    """Utility function to raise InternalServerError."""
    raise InternalServerError(message, details)
