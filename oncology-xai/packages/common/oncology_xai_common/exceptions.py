# DERCAS-ONCO-XAI V1 - Exception Classes
# Standard exception hierarchy for the oncology platform

from typing import Optional, Dict, Any
from fastapi import HTTPException


class OncologyXAIException(Exception):
    """Base exception for all oncology platform errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.details = details or {}
        self.correlation_id = correlation_id
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "errorCode": self.error_code,
            "message": self.message,
            "correlationId": self.correlation_id,
            "details": self.details
        }


class AuthenticationError(OncologyXAIException):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=details,
            correlation_id=correlation_id
        )


class AuthorizationError(OncologyXAIException):
    """Raised when user lacks required permissions."""
    
    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_roles: Optional[list] = None,
        user_roles: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        if not details:
            details = {}
        if required_roles:
            details["required_roles"] = required_roles
        if user_roles:
            details["user_roles"] = user_roles
            
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=details,
            correlation_id=correlation_id
        )


class ValidationError(OncologyXAIException):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        if not details:
            details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
            
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details,
            correlation_id=correlation_id
        )


class NotFoundError(OncologyXAIException):
    """Raised when a requested resource is not found."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        if not details:
            details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
            
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            details=details,
            correlation_id=correlation_id
        )


class ConflictError(OncologyXAIException):
    """Raised when a resource conflict occurs."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        conflict_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        if not details:
            details = {}
        if conflict_type:
            details["conflict_type"] = conflict_type
            
        super().__init__(
            message=message,
            error_code="CONFLICT_ERROR",
            details=details,
            correlation_id=correlation_id
        )


class ExternalServiceError(OncologyXAIException):
    """Raised when an external service call fails."""
    
    def __init__(
        self,
        message: str = "External service error",
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        if not details:
            details = {}
        if service_name:
            details["service_name"] = service_name
        if status_code:
            details["status_code"] = status_code
            
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=details,
            correlation_id=correlation_id
        )


class ModelUnavailableError(OncologyXAIException):
    """Raised when ML model is not available."""
    
    def __init__(
        self,
        message: str = "ML model unavailable",
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        if not details:
            details = {}
        if model_name:
            details["model_name"] = model_name
        if model_version:
            details["model_version"] = model_version
            
        super().__init__(
            message=message,
            error_code="MODEL_UNAVAILABLE",
            details=details,
            correlation_id=correlation_id
        )


class ImageProcessingError(OncologyXAIException):
    """Raised when image processing fails."""
    
    def __init__(
        self,
        message: str = "Image processing failed",
        image_id: Optional[str] = None,
        processing_stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        if not details:
            details = {}
        if image_id:
            details["image_id"] = image_id
        if processing_stage:
            details["processing_stage"] = processing_stage
            
        super().__init__(
            message=message,
            error_code="IMAGE_PROCESSING_ERROR",
            details=details,
            correlation_id=correlation_id
        )


class EHRProcessingError(OncologyXAIException):
    """Raised when EHR processing fails."""
    
    def __init__(
        self,
        message: str = "EHR processing failed",
        ehr_id: Optional[str] = None,
        processing_stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        if not details:
            details = {}
        if ehr_id:
            details["ehr_id"] = ehr_id
        if processing_stage:
            details["processing_stage"] = processing_stage
            
        super().__init__(
            message=message,
            error_code="EHR_PROCESSING_ERROR",
            details=details,
            correlation_id=correlation_id
        )


class OntologyError(OncologyXAIException):
    """Raised when ontology operations fail."""
    
    def __init__(
        self,
        message: str = "Ontology operation failed",
        ontology_name: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        if not details:
            details = {}
        if ontology_name:
            details["ontology_name"] = ontology_name
        if operation:
            details["operation"] = operation
            
        super().__init__(
            message=message,
            error_code="ONTOLOGY_ERROR",
            details=details,
            correlation_id=correlation_id
        )


class JobError(OncologyXAIException):
    """Raised when background job fails."""
    
    def __init__(
        self,
        message: str = "Job execution failed",
        job_id: Optional[str] = None,
        job_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        if not details:
            details = {}
        if job_id:
            details["job_id"] = job_id
        if job_type:
            details["job_type"] = job_type
            
        super().__init__(
            message=message,
            error_code="JOB_ERROR",
            details=details,
            correlation_id=correlation_id
        )


class ClinicalGuardrailError(OncologyXAIException):
    """Raised when clinical guardrails are violated."""
    
    def __init__(
        self,
        message: str = "Clinical guardrail violation",
        guardrail_type: Optional[str] = None,
        violation_details: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        if not details:
            details = {}
        if guardrail_type:
            details["guardrail_type"] = guardrail_type
        if violation_details:
            details["violation_details"] = violation_details
            
        super().__init__(
            message=message,
            error_code="CLINICAL_GUARDRAIL_ERROR",
            details=details,
            correlation_id=correlation_id
        )


def exception_to_http_exception(exc: OncologyXAIException) -> HTTPException:
    """Convert OncologyXAIException to FastAPI HTTPException."""
    
    # Map exception types to HTTP status codes
    status_code_map = {
        AuthenticationError: 401,
        AuthorizationError: 403,
        NotFoundError: 404,
        ConflictError: 409,
        ValidationError: 422,
        ExternalServiceError: 503,
        ModelUnavailableError: 503,
        ImageProcessingError: 422,
        EHRProcessingError: 422,
        OntologyError: 500,
        JobError: 500,
        ClinicalGuardrailError: 422,
    }
    
    status_code = status_code_map.get(type(exc), 500)
    
    return HTTPException(
        status_code=status_code,
        detail=exc.to_dict()
    )
