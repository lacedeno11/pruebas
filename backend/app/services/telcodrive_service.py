from typing import Dict, Any
from backend.app.core.config import settings
from backend.app.services.mock_api_service import MockApiService


class TelcoDriveService:
    """
    Wrapper service for TelcoDrive integration.
    Handles document validation and storage operations for OT projects.
    Switches between mock and real implementations based on SYSTEM_MODE.
    """

    def __init__(self):
        """Initialize TelcoDriveService with appropriate backend based on SYSTEM_MODE."""
        self.system_mode = settings.SYSTEM_MODE
        
        if self.system_mode == "MOCK":
            self.api_client = MockApiService()
        else:
            # In PRODUCTION mode, would initialize real TelcoDrive API client
            # For now, stub implementation using MockApiService
            self.api_client = MockApiService()

    async def get_documents(self, ot_id: str) -> Dict[str, Any]:
        """
        Get document information for a specific OT from TelcoDrive.
        
        Args:
            ot_id: External OT ID to retrieve documents for
        
        Returns:
            Dictionary containing:
            - ot_id: The OT ID
            - document_count: Number of documents uploaded
            - is_complete: Boolean indicating if document_count == 29
            - timestamp: When the check was performed
        """
        return await self.api_client.get_telcodrive_documents(ot_id)

    async def validate_publico_documents(self, ot_id: str) -> bool:
        """
        Validate that a PUBLICO project has all required documents (29 documents).
        
        Args:
            ot_id: External OT ID to validate
        
        Returns:
            True if document count is exactly 29, False otherwise
        """
        result = await self.get_documents(ot_id)
        return result.get("document_count", 0) == 29

    async def get_document_count(self, ot_id: str) -> int:
        """
        Get the document count for a specific OT.
        
        Args:
            ot_id: External OT ID to check
        
        Returns:
            Number of documents uploaded for the OT
        """
        result = await self.get_documents(ot_id)
        return result.get("document_count", 0)

