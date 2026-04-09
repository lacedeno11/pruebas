"""
Mock API endpoints for development and testing.
Only available when SYSTEM_MODE=MOCK.
Provides access to mock data and testing capabilities.
"""

import logging
import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import require_mock_mode
from backend.database.base import get_db
from backend.database import schemas
from backend.services.mock_api import MockApiService

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/mock", tags=["mock"])

# Initialize service
mock_service = MockApiService()


# ============================================================================
# GET Endpoints
# ============================================================================


@router.get("/system-mode", response_model=schemas.SystemModeResponse)
async def get_system_mode():
    """
    Get current system mode (MOCK or PRODUCTION).
    
    Returns:
        Current system mode and description
    """
    mode = os.getenv("SYSTEM_MODE", "MOCK")
    return {
        "mode": mode,
        "description": "Mock mode - using simulated data" if mode == "MOCK" else "Production mode - using real APIs",
    }


@router.get("/ots", response_model=List[schemas.OTResponse])
async def get_mock_ots(
    mock_mode: dict = Depends(require_mock_mode),
):
    """
    Get mock OTs from MockApiService.
    
    This endpoint is only available when SYSTEM_MODE=MOCK.
    Returns 15-20 mock OTs with varied data including some with missing coordinates.
    
    Returns:
        List of mock OT objects
        
    Raises:
        403: If not in MOCK mode
    """
    try:
        # Call mock service to get OTs
        mock_ots = await mock_service.get_ots()
        
        logger.info(f"Fetched {len(mock_ots)} mock OTs from MockApiService")
        
        # Convert to OTResponse schema
        return mock_ots
    except Exception as e:
        logger.error(f"Error fetching mock OTs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching mock OTs",
        )


@router.get("/telcodrive/{ot_id}", response_model=dict)
async def get_telcodrive_documents(
    ot_id: int,
    mock_mode: dict = Depends(require_mock_mode),
):
    """
    Get mock document count from TelcoDrive for a specific OT.
    
    This endpoint is only available when SYSTEM_MODE=MOCK.
    
    Path Parameters:
    - ot_id: OT ID
    
    Returns:
        Document count and OT details
        
    Raises:
        403: If not in MOCK mode
    """
    try:
        # Get document count from mock service
        doc_count = await mock_service.get_telcodrive_documents(ot_id)
        
        return {
            "ot_id": ot_id,
            "document_count": doc_count,
            "required_count": 29,
            "ready_for_finalization": doc_count >= 29,
        }
    except Exception as e:
        logger.error(f"Error fetching TelcoDrive documents for OT {ot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching TelcoDrive documents",
        )


# ============================================================================
# POST Endpoints
# ============================================================================


@router.post("/ots/sync", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def sync_mock_ots(
    mock_mode: dict = Depends(require_mock_mode),
    db=Depends(get_db),
):
    """
    Sync mock OTs from MockApiService and register them in database.
    
    This endpoint is only available when SYSTEM_MODE=MOCK.
    Triggers the OTSAgent to fetch and register mock OTs.
    
    Returns:
        Sync operation status
        
    Raises:
        403: If not in MOCK mode
    """
    try:
        # TODO: Integrate with OTSAgent via Orchestrator
        # For now, return placeholder response
        
        logger.info("Mock OT sync initiated")
        
        return {
            "success": True,
            "message": "Mock OT synchronization initiated",
            "note": "OTSAgent integration pending",
        }
    except Exception as e:
        logger.error(f"Error syncing mock OTs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error syncing mock OTs",
        )


@router.put("/ots/{ot_id}/status", response_model=dict)
async def update_mock_ot_status(
    ot_id: int,
    request: schemas.MockStatusUpdateRequest,
    mock_mode: dict = Depends(require_mock_mode),
):
    """
    Update OT status in mock API.
    
    This endpoint is only available when SYSTEM_MODE=MOCK.
    Simulates status change with 90% success rate.
    
    Path Parameters:
    - ot_id: OT ID
    
    Request Body:
    - new_status: New OT status
    
    Returns:
        Status update confirmation with success/failure
        
    Raises:
        403: If not in MOCK mode
    """
    try:
        # Call mock service to update status
        result = await mock_service.update_status(ot_id, request.new_status)
        
        if result.get("success"):
            logger.info(f"Updated mock OT {ot_id} status to {request.new_status}")
        else:
            logger.warning(f"Failed to update mock OT {ot_id} status: {result.get('error')}")
        
        return result
    except Exception as e:
        logger.error(f"Error updating mock OT {ot_id} status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating OT status",
        )


@router.post("/reset-mock-data", response_model=dict)
async def reset_mock_data(
    mock_mode: dict = Depends(require_mock_mode),
    db=Depends(get_db),
):
    """
    Reset and regenerate all mock data.
    
    This endpoint is only available when SYSTEM_MODE=MOCK.
    Clears current mock data and generates new random mock OTs.
    
    Returns:
        Reset operation status
        
    Raises:
        403: If not in MOCK mode
    """
    try:
        # Delete all OTs from database
        from backend.database import models
        db.query(models.OrdenTrabajo).delete()
        db.commit()
        
        logger.info("Mock data reset completed")
        
        return {
            "success": True,
            "message": "Mock data reset and regenerated",
            "note": "All OTs cleared from database. Re-sync mock OTs to repopulate.",
        }
    except Exception as e:
        logger.error(f"Error resetting mock data: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resetting mock data",
        )

