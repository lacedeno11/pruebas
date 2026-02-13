"""
TelcosService adapter for API integration.
Abstracts the underlying API implementation (mock or real).
Routes requests to appropriate API client based on SYSTEM_MODE.
"""

from typing import List, Dict, Optional
from backend.config import get_settings
from backend.services.mock_api_service import MockApiService


class TelcosService:
    """
    Adapter service for TELCOS and TelcoDrive API integration.
    
    Acts as a facade that abstracts the underlying API implementation.
    In MOCK mode, uses MockApiService for development/testing.
    In PRODUCTION mode, uses real API client (to be implemented).
    
    This service is injected into agents and API routes for consistent
    API access throughout the application.
    """

    def __init__(self):
        """
        Initialize TelcosService with appropriate API client.
        
        Checks SYSTEM_MODE from configuration:
        - MOCK: Creates MockApiService for development/testing
        - PRODUCTION: Creates real API client (placeholder for now)
        """
        self.config = get_settings()
        self.system_mode = self.config.SYSTEM_MODE.upper()

        if self.system_mode == "MOCK":
            self.api_client = MockApiService()
        else:
            # PRODUCTION mode - real API client (placeholder)
            # To be implemented when real TELCOS API is available
            self.api_client = None  # Placeholder for real API client

    async def fetch_ots(self) -> List[Dict]:
        """
        Fetch list of OTs from TELCOS API.
        
        Returns:
            List of OT dictionaries from TELCOS system.
            In MOCK mode, returns 15-20 realistic mock OTs.
            In PRODUCTION mode, returns real OTs from TELCOS API.
            
        Raises:
            Exception: If API client is not available or API call fails
        """
        if self.api_client is None:
            raise Exception("API client not configured for PRODUCTION mode")

        return await self.api_client.get_telcos_ots()

    async def update_status(self, external_id: str, new_status: str) -> bool:
        """
        Update OT status in TELCOS API.
        
        Args:
            external_id: External ID of the OT to update
            new_status: New status value (e.g., FINALIZADA, DETENIDA)
            
        Returns:
            True if status update was successful, False otherwise
            
        Raises:
            Exception: If API client is not available or API call fails
        """
        if self.api_client is None:
            raise Exception("API client not configured for PRODUCTION mode")

        return await self.api_client.update_ot_status(external_id, new_status)

    async def get_documents_status(self, ot_external_id: str) -> Optional[int]:
        """
        Get document count for an OT from TelcoDrive API.
        
        Used to validate PUBLICO projects have required 29 documents
        before marking as FINALIZADA.
        
        Args:
            ot_external_id: External ID of the OT
            
        Returns:
            Document count if available, None if OT not found
            In MOCK mode, returns random 15-29 for PUBLICO projects, 0 otherwise
            
        Raises:
            Exception: If API client is not available or API call fails
        """
        if self.api_client is None:
            raise Exception("API client not configured for PRODUCTION mode")

        return await self.api_client.get_telcodrive_documents(ot_external_id)

