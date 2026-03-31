import os
from typing import List, Optional

import httpx

from backend.app.schemas.ot_schema import OTResponse
from backend.app.services.mock_api_service import MockApiService


class TelcosApiClient:
    """
    Factory pattern implementation for TELCOS API client.

    Checks SYSTEM_MODE environment variable:
    - MOCK: Uses MockApiService for development/testing
    - PRODUCTION: Uses real HTTP calls via httpx.AsyncClient
    """

    def __init__(self, base_url: Optional[str] = None):
        self.system_mode = os.getenv("SYSTEM_MODE", "MOCK")
        self.base_url = base_url or os.getenv("TELCOS_API_URL", "https://api.telcos.com")
        self.mock_service = MockApiService()

    async def get_ots(self) -> List[OTResponse]:
        """
        Get list of OTs from TELCOS API.

        Uses MockApiService if SYSTEM_MODE=MOCK, otherwise makes HTTP request.
        """
        if self.system_mode == "MOCK":
            return await self.mock_service.get_ots()
        else:
            return await self._fetch_ots_production()

    async def update_status(self, ot_id: str, new_status: str) -> dict:
        """
        Update OT status in TELCOS API.

        Uses MockApiService if SYSTEM_MODE=MOCK, otherwise makes HTTP request.
        """
        if self.system_mode == "MOCK":
            return await self.mock_service.update_status(ot_id, new_status)
        else:
            return await self._update_status_production(ot_id, new_status)

    async def get_documents_status(
        self, ot_id: str, project_type: str
    ) -> dict:
        """
        Get TelcoDrive document status for an OT.

        Uses MockApiService if SYSTEM_MODE=MOCK, otherwise makes HTTP request.
        """
        if self.system_mode == "MOCK":
            return await self.mock_service.get_documents_status(ot_id, project_type)
        else:
            return await self._get_documents_status_production(ot_id, project_type)

    async def _fetch_ots_production(self) -> List[OTResponse]:
        """
        Production implementation: Fetch OTs from real TELCOS API.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/ots")
            response.raise_for_status()
            data = response.json()
            return [OTResponse(**item) for item in data]

    async def _update_status_production(self, ot_id: str, new_status: str) -> dict:
        """
        Production implementation: Update OT status via real TELCOS API.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/ots/{ot_id}/status",
                json={"status": new_status},
            )
            response.raise_for_status()
            return response.json()

    async def _get_documents_status_production(
        self, ot_id: str, project_type: str
    ) -> dict:
        """
        Production implementation: Get document status via real TELCOS API.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/telcodrive/documents/{ot_id}",
                params={"project_type": project_type},
            )
            response.raise_for_status()
            return response.json()


def get_telcos_client(base_url: Optional[str] = None) -> TelcosApiClient:
    """
    Factory function to get TelcosApiClient instance.

    Returns appropriate implementation based on SYSTEM_MODE environment variable.
    """
    return TelcosApiClient(base_url=base_url)

