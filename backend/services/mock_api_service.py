"""
Mock API Service for simulating TELCOS and TelcoDrive API responses.
Used for development and testing when SYSTEM_MODE=MOCK.
"""

import asyncio
import random
import uuid
from typing import Any, Dict, List

from backend.config import Settings


class MockApiService:
    """
    Mock API service that simulates responses from TELCOS and TelcoDrive APIs.
    Includes simulated latency for testing UI loading states.
    """

    def __init__(self, settings: Settings):
        """Initialize mock service with settings."""
        self.settings = settings

    async def _simulate_latency(self) -> None:
        """Simulate API latency based on MOCK_API_LATENCY_MS setting."""
        latency_seconds = self.settings.mock_api_latency_ms / 1000.0
        await asyncio.sleep(latency_seconds)

    async def get_ots(self) -> List[Dict[str, Any]]:
        """
        Return mock list of OTs with realistic Ecuadorian coordinates.
        
        Returns:
            List of OT dictionaries with fields: external_id, cliente_id, login_id, lat, long, project_type
        """
        await self._simulate_latency()

        # Sample OTs with Ecuadorian coordinates (Quito and Guayaquil area)
        mock_ots = [
            {
                "external_id": "OT-2024-001",
                "cliente_id": str(uuid.uuid4()),
                "login_id": str(uuid.uuid4()),
                "lat": -0.2298,  # Quito
                "long": -78.5249,
                "project_type": "PUBLICO",
            },
            {
                "external_id": "OT-2024-002",
                "cliente_id": str(uuid.uuid4()),
                "login_id": str(uuid.uuid4()),
                "lat": -0.3522,  # Quito area
                "long": -78.5149,
                "project_type": "PRIVADO",
            },
            {
                "external_id": "OT-2024-003",
                "cliente_id": str(uuid.uuid4()),
                "login_id": str(uuid.uuid4()),
                "lat": -2.1962,  # Guayaquil
                "long": -79.8852,
                "project_type": "PUBLICO",
            },
            {
                "external_id": "OT-2024-004",
                "cliente_id": str(uuid.uuid4()),
                "login_id": str(uuid.uuid4()),
                "lat": -2.2045,  # Guayaquil area
                "long": -79.8743,
                "project_type": "TERCERIZADO",
            },
            {
                "external_id": "OT-2024-005",
                "cliente_id": str(uuid.uuid4()),
                "login_id": str(uuid.uuid4()),
                "lat": -0.1807,  # Quito outskirts
                "long": -78.4575,
                "project_type": "PRIVADO",
            },
        ]

        return mock_ots

    async def update_status(self, ot_id: str, new_status: str) -> Dict[str, Any]:
        """
        Simulate status update with 90% success rate.
        
        Args:
            ot_id: OT ID to update
            new_status: New status value
            
        Returns:
            Dict with success flag and message
        """
        await self._simulate_latency()

        # 90% success rate
        success = random.random() < 0.9

        return {
            "ot_id": ot_id,
            "success": success,
            "new_status": new_status if success else "FAILED",
            "message": f"Status updated to {new_status}" if success else "Failed to update status",
        }

    async def get_telcodrive_documents(self, ot_id: str) -> Dict[str, Any]:
        """
        Simulate TelcoDrive document count retrieval.
        
        Args:
            ot_id: OT ID for which to get document count
            
        Returns:
            Dict with document count (0-29 for PUBLICO projects)
        """
        await self._simulate_latency()

        # Random document count between 0 and 29
        document_count = random.randint(0, 29)

        return {
            "ot_id": ot_id,
            "document_count": document_count,
            "max_required": 29,
            "is_complete": document_count >= 29,
        }

