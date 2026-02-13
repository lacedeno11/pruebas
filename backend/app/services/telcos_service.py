from typing import Dict, List, Any
from backend.app.core.config import settings
from backend.app.services.mock_api_service import MockApiService


class TelcosService:
    """
    Factory/wrapper service for TELCOS API integration.
    Switches between mock and real API implementations based on SYSTEM_MODE.
    """

    def __init__(self):
        """Initialize TelcosService with appropriate backend based on SYSTEM_MODE."""
        self.system_mode = settings.SYSTEM_MODE
        
        if self.system_mode == "MOCK":
            self.api_client = MockApiService()
        else:
            # In PRODUCTION mode, would initialize real TELCOS API client
            # For now, stub implementation using MockApiService
            self.api_client = MockApiService()

    async def get_ots(self) -> List[Dict[str, Any]]:
        """
        Fetch OTs (Órdenes de Trabajo) from TELCOS system.
        
        Returns:
            List of OT dictionaries with external_id, status, project_type,
            cliente_id, login_id, coordinates, and timestamps.
        """
        return await self.api_client.get_ots()

    async def update_status(self, ot_id: str, new_status: str) -> Dict[str, Any]:
        """
        Update OT status in TELCOS system.
        
        Args:
            ot_id: External OT ID to update
            new_status: New status value
        
        Returns:
            Dictionary with success flag and response data
        """
        return await self.api_client.update_status(ot_id, new_status)

    async def get_telcodrive_documents(self, ot_id: str) -> Dict[str, Any]:
        """
        Get document count from TelcoDrive for a specific OT.
        This method is also available but typically called through TelcoDriveService.
        
        Args:
            ot_id: External OT ID to check documents for
        
        Returns:
            Dictionary with document count and completion status
        """
        return await self.api_client.get_telcodrive_documents(ot_id)

