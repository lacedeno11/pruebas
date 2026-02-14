"""
FastAPI router for mock API endpoints.
Exposes MockApiService methods via HTTP endpoints for development and testing.

When SYSTEM_MODE=MOCK, provides:
- GET /api/v1/mock/telcos/ots - Get sample OTs
- POST /api/v1/mock/telcos/update_status - Update OT status
- GET /api/v1/mock/telcodrive/documents/{ot_id} - Get document checklist
- GET /api/v1/mock/health - Service health status

Includes middleware to block access when SYSTEM_MODE != MOCK.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.mock.service import get_mock_service

# ============================================================================
# ROUTER SETUP
# ============================================================================

router = APIRouter(
    prefix="/api/v1/mock",
    tags=["Mock API"],
    responses={
        404: {
            "description": "Mock mode disabled (SYSTEM_MODE != MOCK)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Mock endpoints are only available in MOCK mode"
                    }
                }
            },
        },
    },
)

# ============================================================================
# MIDDLEWARE: CHECK MOCK MODE
# ============================================================================


async def check_mock_mode(request: Request, call_next):
    """
    Middleware to verify SYSTEM_MODE=MOCK before allowing access to mock endpoints.
    
    Returns 404 if not in MOCK mode to prevent accidental exposure in production.
    
    Args:
        request: FastAPI request
        call_next: Next middleware/handler
        
    Returns:
        Response: 404 if not in MOCK mode, otherwise proceeds to endpoint
    """
    settings = get_settings()
    
    if settings.SYSTEM_MODE != "MOCK":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": "Mock endpoints are only available in MOCK mode (SYSTEM_MODE=MOCK)"
            },
        )
    
    return await call_next(request)


# Add middleware to router
router.middleware("http")(check_mock_mode)

# ============================================================================
# TELCOS API SIMULATION
# ============================================================================


@router.get(
    "/telcos/ots",
    response_model=List[Dict],
    summary="Get sample OTs from mock TELCOS API",
    description="Returns list of 20 sample OTs with optional filtering by status and project_type. "
    "Includes 500ms latency simulation and 10% failure rate for chaos testing.",
    tags=["Mock TELCOS API"],
)
async def get_mock_ots(
    status: Optional[str] = Query(
        None,
        description="Filter by OT status (e.g., PREPLANIFICADA, PLANIFICADA, ASIGNADO_TAREA, DETENIDA, ANULADA, FINALIZADA)",
    ),
    project_type: Optional[str] = Query(
        None,
        description="Filter by project type (PUBLICO, PRIVADO, or TERCERIZADO)",
    ),
    limit: int = Query(
        None,
        ge=1,
        le=100,
        description="Maximum results to return (default: all)",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Pagination offset",
    ),
) -> List[Dict]:
    """
    Simulate TELCOS API GET /ots endpoint.
    
    Returns list of 20 mock OTs with realistic data from Ecuador regions.
    Supports filtering by status, project_type, and pagination.
    Includes 500ms simulated latency and 10% failure rate for testing.
    
    **Filters:**
    - `status`: PREPLANIFICADA, PLANIFICADA, ASIGNADO_TAREA, DETENIDA, ANULADA, FINALIZADA
    - `project_type`: PUBLICO, PRIVADO, TERCERIZADO
    
    **Example Request:**
    ```
    GET /api/v1/mock/telcos/ots?status=PREPLANIFICADA&project_type=PUBLICO
    ```
    
    **Example Response:**
    ```json
    [
        {
            "id": "550e8400-...",
            "external_id": "OT-2024-001001",
            "status": "PREPLANIFICADA",
            "project_type": "PUBLICO",
            "cliente_id": "CLI-10001",
            "login_id": "LOGIN-10001",
            "lat": -0.22,
            "long": -78.51,
            "created_at": "2024-02-13T15:30:45",
            "cuadrilla_id": null,
            "geo_error": false
        }
    ]
    ```
    
    Raises:
        RuntimeError: Simulated failure (10% probability) for chaos testing
    """
    service = get_mock_service()
    
    filters = {}
    if status:
        filters["status"] = status
    if project_type:
        filters["project_type"] = project_type
    if limit:
        filters["limit"] = limit
    filters["offset"] = offset
    
    try:
        ots = await service.get_ots(filters=filters if filters else None)
        return ots
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/telcos/update_status",
    response_model=Dict,
    summary="Update OT status in mock TELCOS API",
    description="Simulates TELCOS API status update endpoint. "
    "Returns success/failure response with 10% failure rate for chaos testing.",
    tags=["Mock TELCOS API"],
)
async def update_mock_ot_status(
    request: Dict,
) -> Dict:
    """
    Simulate TELCOS API POST /ots/{external_id}/status endpoint.
    
    Updates OT status in mock data (no persistence).
    Includes 500ms simulated latency and 10% failure rate for chaos testing.
    
    **Request Body:**
    ```json
    {
        "external_id": "OT-2024-001001",
        "status": "PLANIFICADA"
    }
    ```
    
    **Example Response (Success):**
    ```json
    {
        "success": true,
        "message": "OT status updated from PREPLANIFICADA to PLANIFICADA",
        "ot_id": "550e8400-...",
        "external_id": "OT-2024-001001",
        "previous_status": "PREPLANIFICADA",
        "new_status": "PLANIFICADA"
    }
    ```
    
    **Example Response (Not Found):**
    ```json
    {
        "success": false,
        "message": "OT with external_id 'OT-NONEXISTENT' not found"
    }
    ```
    
    Args:
        request: Request body with external_id (str) and status (str)
        
    Returns:
        Dict: Response with success flag, message, and status details
        
    Raises:
        RuntimeError: Simulated failure (10% probability) for chaos testing
        HTTPException: Missing required fields or other errors
    """
    # Extract fields from request
    external_id = request.get("external_id")
    new_status = request.get("status")
    
    if not external_id or not new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must include 'external_id' and 'status'",
        )
    
    service = get_mock_service()
    
    try:
        response = await service.update_ot_status(external_id, new_status)
        return response
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# TELCODRIVE API SIMULATION
# ============================================================================


@router.get(
    "/telcodrive/documents/{ot_id}",
    response_model=Dict,
    summary="Get document checklist from mock TelcoDrive API",
    description="Returns checklist of 29 mandatory documents for PUBLIC projects. "
    "Includes random completion status (80% rate) for realistic testing.",
    tags=["Mock TelcoDrive API"],
)
async def get_mock_telcodrive_documents(
    ot_id: str = Query(
        ...,
        description="OT ID to get documents for",
    ),
) -> Dict:
    """
    Simulate TelcoDrive API GET /documents/{ot_id} endpoint.
    
    Returns document checklist with 29 mandatory documents for PUBLIC projects.
    Uses random completion status (80% rate) for realistic testing.
    Includes 500ms simulated latency.
    
    **Example Request:**
    ```
    GET /api/v1/mock/telcodrive/documents/550e8400-e29b-41d4-a716-446655440000
    ```
    
    **Example Response:**
    ```json
    {
        "ot_id": "550e8400-...",
        "total_documents": 29,
        "completed_documents": 24,
        "completion_percentage": 82.76,
        "documents": [
            {
                "name": "Inspección inicial",
                "completed": true,
                "completed_at": "2024-02-13T16:30:00"
            },
            {
                "name": "Presupuesto aprobado",
                "completed": true,
                "completed_at": "2024-02-13T16:31:00"
            },
            {
                "name": "Fotografías antes",
                "completed": false,
                "completed_at": null
            }
        ]
    }
    ```
    
    Args:
        ot_id: OT ID to retrieve documents for
        
    Returns:
        Dict: Document checklist with total, completed, percentage, and document details
    """
    service = get_mock_service()
    
    response = await service.get_telcodrive_documents(ot_id)
    return response


# ============================================================================
# CUADRILLA OPERATIONS
# ============================================================================


@router.get(
    "/cuadrillas",
    response_model=List[Dict],
    summary="Get mock crews (cuadrillas)",
    description="Returns list of 10 mock crews (5 PRINCIPAL, 5 RESERVA) with optional type filtering.",
    tags=["Mock Cuadrilla Operations"],
)
async def get_mock_cuadrillas(
    type: Optional[str] = Query(
        None,
        description="Filter by crew type (PRINCIPAL or RESERVA)",
    ),
) -> List[Dict]:
    """
    Simulate GET /cuadrillas endpoint.
    
    Returns list of 10 mock crews (5 PRINCIPAL, 5 RESERVA) with realistic data.
    Supports optional filtering by type.
    
    **Example Request:**
    ```
    GET /api/v1/mock/cuadrillas?type=PRINCIPAL
    ```
    
    **Example Response:**
    ```json
    [
        {
            "id": "f47ac10b-...",
            "name": "Cuadrilla Quito-01",
            "type": "PRINCIPAL",
            "last_centroid_lat": -0.22,
            "last_centroid_long": -78.51,
            "daily_capacity": 10,
            "current_load": 7,
            "active": true,
            "created_at": "2024-01-15T10:00:00"
        }
    ]
    ```
    
    Args:
        type: Optional filter for crew type (PRINCIPAL or RESERVA)
        
    Returns:
        List[Dict]: List of crew dictionaries
    """
    service = get_mock_service()
    
    filters = {}
    if type:
        filters["type"] = type
    
    cuadrillas = await service.get_cuadrillas(filters=filters if filters else None)
    return cuadrillas


# ============================================================================
# HEALTH & MONITORING
# ============================================================================


@router.get(
    "/health",
    response_model=Dict,
    summary="Get mock service health status",
    description="Returns statistics about mock API calls, failures, and configuration.",
    tags=["Mock Service Health"],
)
async def get_mock_service_health() -> Dict:
    """
    Get health status of mock service.
    
    Returns statistics including:
    - Total API calls made
    - Simulated failures
    - Actual failure rate percentage
    - Configured latency
    - Service uptime
    
    **Example Response:**
    ```json
    {
        "status": "healthy",
        "call_count": 42,
        "failure_count": 4,
        "failure_rate": 9.52,
        "latency_ms": 500,
        "uptime_seconds": 3600.5
    }
    ```
    
    Returns:
        Dict: Health status with statistics
    """
    service = get_mock_service()
    health = await service.get_health()
    return health


@router.post(
    "/reset",
    response_model=Dict,
    summary="Reset mock service statistics",
    description="Resets call and failure counters for testing.",
    tags=["Mock Service Health"],
)
async def reset_mock_service_stats() -> Dict:
    """
    Reset mock service statistics.
    
    Clears call_count and failure_count for clean test isolation.
    Useful for performance measurements and test setup.
    
    **Example Response:**
    ```json
    {
        "message": "Statistics reset"
    }
    ```
    
    Returns:
        Dict: Confirmation message
    """
    service = get_mock_service()
    result = await service.reset_stats()
    return result


# ============================================================================
# ROOT ENDPOINT
# ============================================================================


@router.get(
    "/",
    response_model=Dict,
    summary="Mock API information",
    description="Returns information about available mock endpoints.",
    tags=["Mock API Info"],
)
async def mock_api_info() -> Dict:
    """
    Get information about mock API.
    
    Returns details about available endpoints and current configuration.
    
    **Example Response:**
    ```json
    {
        "name": "PEI Mock API Service",
        "version": "1.0.0",
        "description": "Mock implementation of TELCOS and TelcoDrive APIs",
        "endpoints": {
            "ots": "GET /api/v1/mock/telcos/ots",
            "update_status": "POST /api/v1/mock/telcos/update_status",
            "documents": "GET /api/v1/mock/telcodrive/documents/{ot_id}",
            "cuadrillas": "GET /api/v1/mock/cuadrillas",
            "health": "GET /api/v1/mock/health"
        },
        "features": {
            "latency_simulation_ms": 500,
            "failure_rate_percent": 10,
            "fixture_ots_count": 20,
            "fixture_cuadrillas_count": 10,
            "fixture_documents_count": 29
        }
    }
    ```
    
    Returns:
        Dict: API information and configuration
    """
    settings = get_settings()
    
    return {
        "name": "PEI Mock API Service",
        "version": "1.0.0",
        "description": "Mock implementation of TELCOS and TelcoDrive APIs for development and testing",
        "mode": settings.SYSTEM_MODE,
        "endpoints": {
            "ots": "GET /api/v1/mock/telcos/ots",
            "update_status": "POST /api/v1/mock/telcos/update_status",
            "documents": "GET /api/v1/mock/telcodrive/documents/{ot_id}",
            "cuadrillas": "GET /api/v1/mock/cuadrillas",
            "health": "GET /api/v1/mock/health",
            "reset": "POST /api/v1/mock/reset",
        },
        "features": {
            "latency_simulation_ms": settings.MOCK_API_LATENCY_MS,
            "failure_rate_percent": 10,
            "fixture_ots_count": 20,
            "fixture_cuadrillas_count": 10,
            "fixture_documents_count": 29,
        },
    }


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = ["router"]

