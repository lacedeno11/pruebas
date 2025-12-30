"""
DERCAS-ONCO-XAI V1 - Error Handling

Standardized error schemas and exception handling for the oncology platform.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """Standardized error codes for the platform."""
    
    # Authentication & Authorization
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    
    # Validation Errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
    
    # Resource Errors
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RESOURCE_LOCKED = "RESOURCE_LOCKED"
    RESOURCE_EXPIRED = "RESOURCE_EXPIRED"
    
    # Business Logic Errors
    INVALID_CASE_STATUS = "INVALID_CASE_STATUS"
    CASE_NOT_READY = "CASE_NOT_READY"
    PROCESSING_IN_PROGRESS = "PROCESSING_IN_PROGRESS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CLINICAL_VALIDATION_FAILED = "CLINICAL_VALIDATION_FAILED"
    
    # File & Storage Errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    STORAGE_ERROR = "STORAGE_ERROR"
    CHECKSUM_MISMATCH = "CHECKSUM_MISMATCH"
    
    # ML & AI Errors
    MODEL_NOT_AVAILABLE = "MODEL_NOT_AVAILABLE"
    INFERENCE_FAILED = "INFERENCE_FAILED"
    LOW_CONFIDENCE_RESULT = "LOW_CONFIDENCE_RESULT"
    PROCESSING_TIMEOUT = "PROCESSING_TIMEOUT"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"
    
    # External Service Errors
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # System Errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    MAINTENANCE_MODE = "MAINTENANCE_MODE"


class ErrorDetail(BaseModel):
    """Detailed error information."""
    field: Optional[str] = Field(None, description="Field name that caused the error")
    message: str = Field(..., description="Detailed error message")
    code: Optional[str] = Field(None, description="Specific error code for this detail")
    value: Optional[Any] = Field(None, description="Invalid value that caused the error")


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    error_code: ErrorCode = Field(..., description="Standardized error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    case_id: Optional[str] = Field(None, description="Associated case ID if applicable")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    service: Optional[str] = Field(None, description="Service that generated the error")
    
    # Additional context
    request_id: Optional[str] = Field(None, description="Request ID")
    user_id: Optional[str] = Field(None, description="User ID if authenticated")
    trace_id: Optional[str] = Field(None, description="Distributed tracing ID")


# Custom Exception Classes
class PlatformException(Exception):
    """Base exception for platform-specific errors."""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: Optional[List[ErrorDetail]] = None,
        correlation_id: Optional[str] = None,
        case_id: Optional[str] = None,
        service: Optional[str] = None
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or []
        self.correlation_id = correlation_id
        self.case_id = case_id
        self.service = service
        super().__init__(message)
    
    def to_error_response(self) -> ErrorResponse:
        """Convert exception to error response model."""
        return ErrorResponse(
            error_code=self.error_code,
            message=self.message,
            details=self.details,
            correlation_id=self.correlation_id,
            case_id=self.case_id,
            service=self.service
        )


class AuthenticationError(PlatformException):
    """Authentication-related errors."""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            error_code=ErrorCode.AUTHENTICATION_FAILED,
            message=message,
            **kwargs
        )


class AuthorizationError(PlatformException):
    """Authorization-related errors."""
    
    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(
            error_code=ErrorCode.AUTHORIZATION_FAILED,
            message=message,
            **kwargs
        )


class ValidationError(PlatformException):
    """Validation-related errors."""
    
    def __init__(self, message: str = "Validation failed", **kwargs):
        super().__init__(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message,
            **kwargs
        )


class ResourceNotFoundError(PlatformException):
    """Resource not found errors."""
    
    def __init__(self, resource_type: str, resource_id: str, **kwargs):
        message = f"{resource_type} with ID '{resource_id}' not found"
        super().__init__(
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            message=message,
            **kwargs
        )


class ResourceConflictError(PlatformException):
    """Resource conflict errors."""
    
    def __init__(self, message: str = "Resource conflict", **kwargs):
        super().__init__(
            error_code=ErrorCode.RESOURCE_CONFLICT,
            message=message,
            **kwargs
        )


class BusinessLogicError(PlatformException):
    """Business logic validation errors."""
    
    def __init__(self, error_code: ErrorCode, message: str, **kwargs):
        super().__init__(
            error_code=error_code,
            message=message,
            **kwargs
        )


class FileError(PlatformException):
    """File and storage-related errors."""
    
    def __init__(self, error_code: ErrorCode, message: str, **kwargs):
        super().__init__(
            error_code=error_code,
            message=message,
            **kwargs
        )


class MLError(PlatformException):
    """Machine learning and AI-related errors."""
    
    def __init__(self, error_code: ErrorCode, message: str, **kwargs):
        super().__init__(
            error_code=error_code,
            message=message,
            **kwargs
        )


class ExternalServiceError(PlatformException):
    """External service-related errors."""
    
    def __init__(self, service_name: str, message: str, **kwargs):
        full_message = f"External service '{service_name}' error: {message}"
        super().__init__(
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message=full_message,
            **kwargs
        )


# HTTP Exception Mapping
def map_error_to_http_status(error_code: ErrorCode) -> int:
    """Map error codes to HTTP status codes."""
    mapping = {
        # 400 Bad Request
        ErrorCode.VALIDATION_ERROR: status.HTTP_400_BAD_REQUEST,
        ErrorCode.INVALID_INPUT: status.HTTP_400_BAD_REQUEST,
        ErrorCode.MISSING_REQUIRED_FIELD: status.HTTP_400_BAD_REQUEST,
        ErrorCode.INVALID_FORMAT: status.HTTP_400_BAD_REQUEST,
        ErrorCode.VALUE_OUT_OF_RANGE: status.HTTP_400_BAD_REQUEST,
        ErrorCode.INVALID_CASE_STATUS: status.HTTP_400_BAD_REQUEST,
        ErrorCode.INVALID_FILE_FORMAT: status.HTTP_400_BAD_REQUEST,
        ErrorCode.FILE_CORRUPTED: status.HTTP_400_BAD_REQUEST,
        ErrorCode.CHECKSUM_MISMATCH: status.HTTP_400_BAD_REQUEST,
        
        # 401 Unauthorized
        ErrorCode.AUTHENTICATION_FAILED: status.HTTP_401_UNAUTHORIZED,
        ErrorCode.TOKEN_EXPIRED: status.HTTP_401_UNAUTHORIZED,
        ErrorCode.TOKEN_INVALID: status.HTTP_401_UNAUTHORIZED,
        
        # 403 Forbidden
        ErrorCode.AUTHORIZATION_FAILED: status.HTTP_403_FORBIDDEN,
        ErrorCode.INSUFFICIENT_PERMISSIONS: status.HTTP_403_FORBIDDEN,
        
        # 404 Not Found
        ErrorCode.RESOURCE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
        ErrorCode.FILE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
        ErrorCode.MODEL_NOT_AVAILABLE: status.HTTP_404_NOT_FOUND,
        
        # 409 Conflict
        ErrorCode.RESOURCE_ALREADY_EXISTS: status.HTTP_409_CONFLICT,
        ErrorCode.RESOURCE_CONFLICT: status.HTTP_409_CONFLICT,
        ErrorCode.PROCESSING_IN_PROGRESS: status.HTTP_409_CONFLICT,
        
        # 413 Payload Too Large
        ErrorCode.FILE_TOO_LARGE: status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        
        # 422 Unprocessable Entity
        ErrorCode.CASE_NOT_READY: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ErrorCode.REVIEW_REQUIRED: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ErrorCode.CLINICAL_VALIDATION_FAILED: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ErrorCode.LOW_CONFIDENCE_RESULT: status.HTTP_422_UNPROCESSABLE_ENTITY,
        
        # 423 Locked
        ErrorCode.RESOURCE_LOCKED: status.HTTP_423_LOCKED,
        
        # 429 Too Many Requests
        ErrorCode.RATE_LIMIT_EXCEEDED: status.HTTP_429_TOO_MANY_REQUESTS,
        
        # 500 Internal Server Error
        ErrorCode.INTERNAL_SERVER_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorCode.DATABASE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorCode.STORAGE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorCode.INFERENCE_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorCode.WORKFLOW_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorCode.CONFIGURATION_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorCode.DEPENDENCY_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
        
        # 502 Bad Gateway
        ErrorCode.EXTERNAL_SERVICE_ERROR: status.HTTP_502_BAD_GATEWAY,
        ErrorCode.NETWORK_ERROR: status.HTTP_502_BAD_GATEWAY,
        
        # 503 Service Unavailable
        ErrorCode.SERVICE_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
        ErrorCode.MAINTENANCE_MODE: status.HTTP_503_SERVICE_UNAVAILABLE,
        
        # 504 Gateway Timeout
        ErrorCode.PROCESSING_TIMEOUT: status.HTTP_504_GATEWAY_TIMEOUT,
        
        # 410 Gone
        ErrorCode.RESOURCE_EXPIRED: status.HTTP_410_GONE,
    }
    
    return mapping.get(error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


def create_http_exception(
    error_code: ErrorCode,
    message: str,
    details: Optional[List[ErrorDetail]] = None,
    correlation_id: Optional[str] = None,
    case_id: Optional[str] = None,
    service: Optional[str] = None
) -> HTTPException:
    """Create HTTPException from error information."""
    error_response = ErrorResponse(
        error_code=error_code,
        message=message,
        details=details,
        correlation_id=correlation_id,
        case_id=case_id,
        service=service
    )
    
    status_code = map_error_to_http_status(error_code)
    
    return HTTPException(
        status_code=status_code,
        detail=error_response.model_dump()
    )


def platform_exception_to_http_exception(exc: PlatformException) -> HTTPException:
    """Convert PlatformException to HTTPException."""
    status_code = map_error_to_http_status(exc.error_code)
    
    return HTTPException(
        status_code=status_code,
        detail=exc.to_error_response().model_dump()
    )


# Utility functions for common error scenarios
def create_validation_error(
    field: str,
    message: str,
    value: Any = None,
    correlation_id: Optional[str] = None
) -> ValidationError:
    """Create a validation error for a specific field."""
    detail = ErrorDetail(
        field=field,
        message=message,
        code="FIELD_VALIDATION_ERROR",
        value=value
    )
    
    return ValidationError(
        message=f"Validation failed for field '{field}': {message}",
        details=[detail],
        correlation_id=correlation_id
    )


def create_case_not_found_error(case_id: str, correlation_id: Optional[str] = None) -> ResourceNotFoundError:
    """Create a case not found error."""
    return ResourceNotFoundError(
        resource_type="Case",
        resource_id=case_id,
        correlation_id=correlation_id
    )


def create_image_not_found_error(image_id: str, correlation_id: Optional[str] = None) -> ResourceNotFoundError:
    """Create an image not found error."""
    return ResourceNotFoundError(
        resource_type="Image",
        resource_id=image_id,
        correlation_id=correlation_id
    )


def create_patient_not_found_error(patient_id: str, correlation_id: Optional[str] = None) -> ResourceNotFoundError:
    """Create a patient not found error."""
    return ResourceNotFoundError(
        resource_type="Patient",
        resource_id=patient_id,
        correlation_id=correlation_id
    )


def create_insufficient_permissions_error(
    required_permission: str,
    correlation_id: Optional[str] = None
) -> AuthorizationError:
    """Create an insufficient permissions error."""
    return AuthorizationError(
        message=f"Insufficient permissions. Required: {required_permission}",
        correlation_id=correlation_id
    )


def create_case_status_error(
    current_status: str,
    required_status: str,
    case_id: str,
    correlation_id: Optional[str] = None
) -> BusinessLogicError:
    """Create a case status validation error."""
    return BusinessLogicError(
        error_code=ErrorCode.INVALID_CASE_STATUS,
        message=f"Case {case_id} is in status '{current_status}', but '{required_status}' is required",
        case_id=case_id,
        correlation_id=correlation_id
    )


def create_file_format_error(
    filename: str,
    allowed_formats: List[str],
    correlation_id: Optional[str] = None
) -> FileError:
    """Create a file format validation error."""
    return FileError(
        error_code=ErrorCode.INVALID_FILE_FORMAT,
        message=f"File '{filename}' has invalid format. Allowed formats: {', '.join(allowed_formats)}",
        correlation_id=correlation_id
    )


def create_processing_timeout_error(
    job_id: str,
    timeout_seconds: int,
    correlation_id: Optional[str] = None
) -> MLError:
    """Create a processing timeout error."""
    return MLError(
        error_code=ErrorCode.PROCESSING_TIMEOUT,
        message=f"Processing job {job_id} timed out after {timeout_seconds} seconds",
        correlation_id=correlation_id
    )
