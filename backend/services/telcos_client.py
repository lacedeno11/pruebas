"""
TelcosClient - Abstraction layer for TELCOS and TelcoDrive APIs.
Routes requests to MockApiService when SYSTEM_MODE=MOCK, otherwise uses real HTTP endpoints.
"""

from typing import Any, Dict, List

import httpx

from backend.config import Settings
from backend.services.mock_api_service import MockApiService


class TelcosClient:
    """
    Client for TELCOS and TelcoDrive APIs with mock/production mode switching.
    """

    def __init__(self, settings: Settings):
        """
        Initialize TelcosClient with settings.

        Args:
            settings: Application settings with SYSTEM_MODE configuration
        """
        self.settings = settings
        self.is_mock_mode = settings.system_mode.upper() == "MOCK"
        self.mock_service = MockApiService(settings) if self.is_mock_mode else None
        self.http_client = httpx.AsyncClient() if not self.is_mock_mode else None

    async def fetch_ots(self) -> List[Dict[str, Any]]:
        """
        Fetch OTs from TELCOS API.

        Returns:
            List of OT dictionaries with fields: external_id, cliente_id, login_id, lat, long, project_type
        """
        if self.is_mock_mode:
            return await self.mock_service.get_ots()

        # Production: call real TELCOS API
        response = await self.http_client.get(
            "https://api.telcos.example.com/api/ots",
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    async def update_ot_status(self, ot_id: str, new_status: str) -> Dict[str, Any]:
        """
        Update OT status in TELCOS system.

        Args:
            ot_id: OT ID to update
            new_status: New status value

        Returns:
            Dict with success status and message
        """
        if self.is_mock_mode:
            return await self.mock_service.update_status(ot_id, new_status)

        # Production: call real TELCOS API
        response = await self.http_client.post(
            f"https://api.telcos.example.com/api/ots/{ot_id}/status",
            json={"status": new_status},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    async def get_documents_status(self, ot_id: str) -> Dict[str, Any]:
        """
        Get document count from TelcoDrive for an OT.

        Args:
            ot_id: OT ID to check documents for

        Returns:
            Dict with document_count and related metadata
        """
        if self.is_mock_mode:
            return await self.mock_service.get_telcodrive_documents(ot_id)

        # Production: call real TelcoDrive API
        response = await self.http_client.get(
            f"https://api.telcodrive.example.com/api/documents/{ot_id}",
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        """Close HTTP client connections."""
        if self.http_client:
            await self.http_client.aclose()

