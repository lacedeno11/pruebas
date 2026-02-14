"""
Custom exception hierarchy for PEI Agentic Platform.
Provides structured error handling with FastAPI integration.

Hierarchy:
    PEIException (base)
    ├── OTException
    ├── PlanningException
    ├── GovernanceException
    ├── ValidationException
    ├── GeoException
    └── MockServiceException
"""

from functools import wraps
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse


# ============================================================================
# BASE EXCEPTION CLASS
# ============================================================================


class PEIException(Exception):
    """
    Base exception class for PEI Agentic Platform.
    
    All custom exceptions inherit from this base class.
    Includes FastAPI HTTP metadata for automatic error responses.
    
    Attributes:
        status_code: HTTP status code to return (default 500)
        detail: Error message/description for client
        headers: Additional HTTP headers (e.g., WWW-Authenticate)
        internal_error: Internal error message for logging (if different from detail)
    """

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers: Optional[Dict[str, str]] = None,
        internal_error: Optional[str] = None,
    ):
        """
        Initialize PEI exception.
        
        Args:
            detail: Error message shown to client
            status_code: HTTP status code (default 500)
            headers: Optional HTTP headers
            internal_error: Optional internal error message for logging
        """
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.headers = headers or {}
        self.internal_error = internal_error or detail


# ============================================================================
# OT (ORDEN DE TRABAJO) EXCEPTIONS
# ============================================================================


class OTException(PEIException):
    """
    Exception for errors related to Order of Work (OT) operations.
    
    Examples:
    - OT not found
    - Invalid OT status
    - Duplicate external_id
    - OT already assigned
    """

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        headers: Optional[Dict[str, str]] = None,
        internal_error: Optional[str] = None,
    ):
        """Initialize OT exception."""
        super().__init__(
            detail=detail,
            status_code=status_code,
            headers=headers,
            internal_error=internal_error,
        )


class OTNotFoundError(OTException):
    """OT with given ID or external_id not found."""

    def __init__(self, ot_id: str):
        super().__init__(
            detail=f"Order of Work with ID '{ot_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            internal_error=f"OT not found: {ot_id}",
        )


class InvalidOTStatusError(OTException):
    """Invalid OT status or invalid status transition."""

    def __init__(self, current_status: str, requested_status: str):
        super().__init__(
            detail=f"Cannot transition from '{current_status}' to '{requested_status}'",
            status_code=status.HTTP_400_BAD_REQUEST,
            internal_error=f"Invalid status transition: {current_status} -> {requested_status}",
        )


class DuplicateOTError(OTException):
    """OT with given external_id already exists."""

    def __init__(self, external_id: str):
        super().__init__(
            detail=f"Order of Work with external_id '{external_id}' already exists",
            status_code=status.HTTP_409_CONFLICT,
            internal_error=f"Duplicate external_id: {external_id}",
        )


class OTAlreadyAssignedError(OTException):
    """OT is already assigned to a crew."""

    def __init__(self, ot_id: str, cuadrilla_id: str):
        super().__init__(
            detail=f"Order of Work '{ot_id}' is already assigned to crew '{cuadrilla_id}'",
            status_code=status.HTTP_409_CONFLICT,
            internal_error=f"OT already assigned: {ot_id} -> {cuadrilla_id}",
        )


# ============================================================================
# PLANNING EXCEPTIONS
# ============================================================================


class PlanningException(PEIException):
    """
    Exception for errors in planning/assignment operations.
    
    Examples:
    - No available crews
    - Assignment algorithm failed
    - Distance constraint violation
    - Capacity exceeded
    """

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        headers: Optional[Dict[str, str]] = None,
        internal_error: Optional[str] = None,
    ):
        """Initialize planning exception."""
        super().__init__(
            detail=detail,
            status_code=status_code,
            headers=headers,
            internal_error=internal_error,
        )


class NoAvailableCrewError(PlanningException):
    """No crews available for assignment."""

    def __init__(self):
        super().__init__(
            detail="No crews available for assignment. All crews are at capacity.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            internal_error="Planning failed: no available crews",
        )


class CrewCapacityExceededError(PlanningException):
    """Assignment would exceed crew daily capacity."""

    def __init__(self, cuadrilla_id: str, current_load: int, capacity: int):
        super().__init__(
            detail=f"Crew '{cuadrilla_id}' cannot accept assignment. "
                   f"Current load {current_load} would exceed capacity {capacity}",
            status_code=status.HTTP_400_BAD_REQUEST,
            internal_error=f"Capacity exceeded: {cuadrilla_id} ({current_load}/{capacity})",
        )


class DistanceConstraintViolationError(PlanningException):
    """Assignment violates distance constraint from crew centroid."""

    def __init__(self, distance_km: float, max_distance_km: float):
        super().__init__(
            detail=f"Assignment location is {distance_km:.2f}km from crew, "
                   f"exceeds maximum {max_distance_km}km",
            status_code=status.HTTP_400_BAD_REQUEST,
            internal_error=f"Distance constraint violated: {distance_km:.2f}km > {max_distance_km}km",
        )


class PlanningAlgorithmError(PlanningException):
    """Unexpected error during planning algorithm execution."""

    def __init__(self, phase: str, reason: str):
        super().__init__(
            detail=f"Planning failed during Phase {phase}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            internal_error=f"Planning algorithm error (Phase {phase}): {reason}",
        )


# ============================================================================
# GOVERNANCE EXCEPTIONS
# ============================================================================


class GovernanceException(PEIException):
    """
    Exception for errors in governance/validation operations.
    
    Examples:
    - Document requirements not met
    - Inactivity validation failed
    - Business rule violation
    """

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        headers: Optional[Dict[str, str]] = None,
        internal_error: Optional[str] = None,
    ):
        """Initialize governance exception."""
        super().__init__(
            detail=detail,
            status_code=status_code,
            headers=headers,
            internal_error=internal_error,
        )


class DocumentRequirementError(GovernanceException):
    """Required documents not met for PUBLIC project."""

    def __init__(self, ot_id: str, required: int, provided: int):
        super().__init__(
            detail=f"Cannot finalize PUBLIC project. "
                   f"Required {required} documents, but only {provided} are complete",
            status_code=status.HTTP_400_BAD_REQUEST,
            internal_error=f"Document requirement failed: {ot_id} ({provided}/{required})",
        )


class InvalidDetentionReasonError(GovernanceException):
    """Detention reason does not match valid ontology."""

    def __init__(self, reason: str, valid_reasons: list):
        super().__init__(
            detail=f"Invalid detention reason '{reason}'. "
                   f"Valid reasons: {', '.join(valid_reasons)}",
            status_code=status.HTTP_400_BAD_REQUEST,
            internal_error=f"Invalid detention reason: {reason}",
        )


class BusinessRuleViolationError(GovernanceException):
    """Business rule violation in governance logic."""

    def __init__(self, rule: str, violation_detail: str):
        super().__init__(
            detail=f"Business rule violation: {violation_detail}",
            status_code=status.HTTP_400_BAD_REQUEST,
            internal_error=f"Business rule '{rule}' violated: {violation_detail}",
        )


class InactivityCheckError(GovernanceException):
    """Error during inactivity check operation."""

    def __init__(self, reason: str):
        super().__init__(
            detail="Failed to perform inactivity check",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            internal_error=f"Inactivity check error: {reason}",
        )


# ============================================================================
# VALIDATION EXCEPTIONS
# ============================================================================


class ValidationException(PEIException):
    """
    Exception for input validation errors.
    
    Examples:
    - Invalid field values
    - Missing required fields
    - Field constraint violations
    """

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
        headers: Optional[Dict[str, str]] = None,
        internal_error: Optional[str] = None,
    ):
        """Initialize validation exception."""
        super().__init__(
            detail=detail,
            status_code=status_code,
            headers=headers,
            internal_error=internal_error,
        )


class InvalidCoordinatesError(ValidationException):
    """Invalid coordinates provided."""

    def __init__(self, lat: float, long: float):
        super().__init__(
            detail=f"Invalid coordinates: latitude {lat}, longitude {long}. "
                   f"Valid ranges: lat [-90, 90], long [-180, 180]",
            internal_error=f"Invalid coordinates: ({lat}, {long})",
        )


class MissingRequiredFieldError(ValidationException):
    """Required field is missing."""

    def __init__(self, field_name: str):
        super().__init__(
            detail=f"Required field '{field_name}' is missing",
            internal_error=f"Missing required field: {field_name}",
        )


class InvalidFieldValueError(ValidationException):
    """Field value does not match expected constraints."""

    def __init__(self, field_name: str, value: Any, constraint: str):
        super().__init__(
            detail=f"Field '{field_name}' value '{value}' violates constraint: {constraint}",
            internal_error=f"Invalid value for {field_name}: {value} ({constraint})",
        )


class DataTypeError(ValidationException):
    """Field value is not of expected data type."""

    def __init__(self, field_name: str, expected_type: str, actual_type: str):
        super().__init__(
            detail=f"Field '{field_name}' expects {expected_type}, got {actual_type}",
            internal_error=f"Type mismatch for {field_name}: expected {expected_type}, got {actual_type}",
        )


# ============================================================================
# GEOGRAPHIC EXCEPTIONS
# ============================================================================


class GeoException(PEIException):
    """
    Exception for geographic/location calculation errors.
    
    Examples:
    - Empty coordinate list
    - Invalid coordinate ranges
    - Distance calculation errors
    """

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        headers: Optional[Dict[str, str]] = None,
        internal_error: Optional[str] = None,
    ):
        """Initialize geo exception."""
        super().__init__(
            detail=detail,
            status_code=status_code,
            headers=headers,
            internal_error=internal_error,
        )


class EmptyCoordinateListError(GeoException):
    """Cannot process empty coordinate list."""

    def __init__(self):
        super().__init__(
            detail="Cannot calculate centroid: coordinate list is empty",
            internal_error="Empty coordinate list for centroid calculation",
        )


class CentroidCalculationError(GeoException):
    """Error calculating centroid from coordinates."""

    def __init__(self, reason: str):
        super().__init__(
            detail="Failed to calculate centroid",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            internal_error=f"Centroid calculation error: {reason}",
        )


class DistanceCalculationError(GeoException):
    """Error calculating distance between points."""

    def __init__(self, coord1: tuple, coord2: tuple, reason: str):
        super().__init__(
            detail="Failed to calculate distance between locations",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            internal_error=f"Distance calculation error ({coord1} -> {coord2}): {reason}",
        )


# ============================================================================
# MOCK SERVICE EXCEPTIONS
# ============================================================================


class MockServiceException(PEIException):
    """
    Exception for mock service operations (development/testing).
    
    Examples:
    - Mock data not found
    - Simulated failure
    - Configuration error
    """

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers: Optional[Dict[str, str]] = None,
        internal_error: Optional[str] = None,
    ):
        """Initialize mock service exception."""
        super().__init__(
            detail=detail,
            status_code=status_code,
            headers=headers,
            internal_error=internal_error,
        )


class MockDataNotFoundError(MockServiceException):
    """Mock data not found."""

    def __init__(self, data_type: str, identifier: str):
        super().__init__(
            detail=f"Mock {data_type} '{identifier}' not found in fixture data",
            status_code=status.HTTP_404_NOT_FOUND,
            internal_error=f"Mock data not found: {data_type}({identifier})",
        )


class MockModeDisabledError(MockServiceException):
    """Mock mode is not enabled but mock endpoint was accessed."""

    def __init__(self):
        super().__init__(
            detail="Mock endpoints are only available in MOCK mode (SYSTEM_MODE=MOCK)",
            status_code=status.HTTP_404_NOT_FOUND,
            internal_error="Mock endpoint accessed in non-MOCK mode",
        )


class SimulatedMockFailureError(MockServiceException):
    """Simulated failure from mock service (for testing error handling)."""

    def __init__(self, operation: str):
        super().__init__(
            detail=f"Mock service simulated failure for: {operation}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            internal_error=f"Simulated mock failure: {operation}",
        )


# ============================================================================
# DATABASE EXCEPTIONS
# ============================================================================


class DatabaseException(PEIException):
    """
    Exception for database operation errors.
    
    Examples:
    - Database connection failure
    - Query execution error
    - Constraint violation
    """

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers: Optional[Dict[str, str]] = None,
        internal_error: Optional[str] = None,
    ):
        """Initialize database exception."""
        super().__init__(
            detail=detail,
            status_code=status_code,
            headers=headers,
            internal_error=internal_error,
        )


class DatabaseConnectionError(DatabaseException):
    """Failed to connect to database."""

    def __init__(self, reason: str):
        super().__init__(
            detail="Database connection failed. Please try again later.",
            internal_error=f"Database connection error: {reason}",
        )


class DatabaseQueryError(DatabaseException):
    """Error executing database query."""

    def __init__(self, query_name: str, reason: str):
        super().__init__(
            detail="Database query failed. Please try again later.",
            internal_error=f"Query '{query_name}' failed: {reason}",
        )


# ============================================================================
# EXTERNAL API EXCEPTIONS
# ============================================================================


class ExternalAPIException(PEIException):
    """
    Exception for errors from external APIs (TELCOS, TelcoDrive, OpenAI, etc).
    
    Examples:
    - API timeout
    - API error response
    - Authentication failure
    """

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        headers: Optional[Dict[str, str]] = None,
        internal_error: Optional[str] = None,
    ):
        """Initialize external API exception."""
        super().__init__(
            detail=detail,
            status_code=status_code,
            headers=headers,
            internal_error=internal_error,
        )


class TELCOSAPIError(ExternalAPIException):
    """Error from TELCOS API."""

    def __init__(self, endpoint: str, status_code: int, reason: str):
        super().__init__(
            detail="Failed to communicate with TELCOS API. Please try again later.",
            internal_error=f"TELCOS API error at {endpoint} ({status_code}): {reason}",
        )


class TelcoDriveAPIError(ExternalAPIException):
    """Error from TelcoDrive API."""

    def __init__(self, operation: str, reason: str):
        super().__init__(
            detail="Failed to access document service. Please try again later.",
            internal_error=f"TelcoDrive API error ({operation}): {reason}",
        )


class OpenAIAPIError(ExternalAPIException):
    """Error from OpenAI API (LLM)."""

    def __init__(self, reason: str):
        super().__init__(
            detail="AI service unavailable. Please try again later.",
            internal_error=f"OpenAI API error: {reason}",
        )


# ============================================================================
# EXCEPTION HANDLER DECORATOR
# ============================================================================


def exception_handler(func: Callable) -> Callable:
    """
    Decorator for consistent exception handling in route handlers.
    
    Catches PEIException and converts to JSONResponse with proper status codes.
    Re-raises other exceptions for FastAPI default handling.
    
    Usage:
        >>> @router.get("/ots/{ot_id}")
        >>> @exception_handler
        >>> async def get_ot(ot_id: str, db: AsyncSession = Depends(get_db)):
        ...     ot = await db.get(OT, ot_id)
        ...     if not ot:
        ...         raise OTNotFoundError(ot_id)
        ...     return ot
    
    Args:
        func: Route handler function
        
    Returns:
        Callable: Wrapped function with exception handling
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except PEIException as e:
            # Log the error internally
            # logger.error(e.internal_error)
            
            # Return JSONResponse with proper HTTP metadata
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "detail": e.detail,
                    "error_type": type(e).__name__,
                },
                headers=e.headers,
            )

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PEIException as e:
            # Log the error internally
            # logger.error(e.internal_error)
            
            # Return JSONResponse with proper HTTP metadata
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "detail": e.detail,
                    "error_type": type(e).__name__,
                },
                headers=e.headers,
            )

    # Return appropriate wrapper based on function type
    if hasattr(func, "__await__"):
        return async_wrapper
    else:
        return sync_wrapper


# ============================================================================
# FASTAPI EXCEPTION RESPONSE
# ============================================================================


async def pei_exception_handler(request, exc: PEIException):
    """
    FastAPI exception handler for PEIException.
    
    Register with FastAPI app:
        >>> from fastapi import FastAPI
        >>> from app.utils.exceptions import PEIException, pei_exception_handler
        >>>
        >>> app = FastAPI()
        >>> app.add_exception_handler(PEIException, pei_exception_handler)
    
    Args:
        request: FastAPI request
        exc: PEIException instance
        
    Returns:
        JSONResponse: Error response with proper status code and headers
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_type": type(exc).__name__,
        },
        headers=exc.headers,
    )

