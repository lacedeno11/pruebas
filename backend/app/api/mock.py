from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.services.mock_api_service import MockApiService

router = APIRouter()
mock_service = MockApiService()


class UpdateStatusRequest(BaseModel):
    """Request schema for updating OT status."""
    ot_id: str
    new_status: str


class UpdateStatusResponse(BaseModel):
    """Response schema for status update."""
    success: bool
    message: str
    ot_id: str
    new_status: str


class DocumentsResponse(BaseModel):
    """Response schema for document count."""
    ot_id: str
    document_count: int
    is_complete: bool


@router.get("/mock/telcos/ots", response_model=List[Dict[str, Any]])
async def get_mock_ots():
    """
    Get mock OTs from simulated TELCOS system.
    
    This endpoint is only available when SYSTEM_MODE=MOCK.
    Returns 5-10 realistic mock OTs with varying statuses, coordinates, and project types.
    Each request includes a 500ms simulated latency to represent network delay.
    
    Returns:
    - List of OT dictionaries with fields:
      - external_id: Unique identifier from TELCOS
      - status: Current OT status
      - project_type: Type of project (PUBLICO, PRIVADO, TERCERIZADO)
      - cliente_id: Customer ID
      - login_id: Service point ID
      - lat: Latitude coordinate
      - long: Longitude coordinate
    """
    try:
        ots = await mock_service.get_ots()
        return ots
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch mock OTs: {str(e)}")


@router.post("/mock/telcos/update_status", response_model=UpdateStatusResponse)
async def update_mock_status(request: UpdateStatusRequest):
    """
    Update OT status in the mock TELCOS system.
    
    This endpoint is only available when SYSTEM_MODE=MOCK.
    Simulates updating an OT status with random success/failure for testing error handling.
    Includes 500ms simulated latency.
    
    Request Body:
    - ot_id: External OT ID to update
    - new_status: New status value (PREPLANIFICADA, PLANIFICADA, ASIGNADO_TAREA, DETENIDA, ANULADA, FINALIZADA)
    
    Returns:
    - success: Boolean indicating if status update was successful
    - message: Status message
    - ot_id: The OT ID that was updated
    - new_status: The new status that was set
    """
    try:
        result = await mock_service.update_status(request.ot_id, request.new_status)
        return UpdateStatusResponse(
            success=result["success"],
            message=result["message"],
            ot_id=request.ot_id,
            new_status=request.new_status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update mock status: {str(e)}")


@router.get("/mock/telcodrive/documents", response_model=DocumentsResponse)
async def get_mock_documents(ot_id: str):
    """
    Get document count from mock TelcoDrive system.
    
    This endpoint is only available when SYSTEM_MODE=MOCK.
    Returns random document count (0-29) for the specified OT, typically for PUBLICO projects.
    Includes 500ms simulated latency.
    
    Query Parameters:
    - ot_id: External OT ID to get documents for
    
    Returns:
    - ot_id: The OT ID
    - document_count: Number of documents (0-29)
    - is_complete: Boolean indicating if document_count == 29
    """
    try:
        result = await mock_service.get_telcodrive_documents(ot_id)
        return DocumentsResponse(
            ot_id=ot_id,
            document_count=result["document_count"],
            is_complete=result["document_count"] == 29
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch mock documents: {str(e)}")

