"""Mock API Service for simulating TELCOS and TelcoDrive APIs"""

import asyncio
import random
import logging
from typing import List, Dict, Any
from backend.config.settings import settings
from backend.utils.constants import PROJECT_TYPES, OT_STATUS, MOCK_LATENCY_MS

logger = logging.getLogger(__name__)


class MockApiService:
    """Service that simulates TELCOS and TelcoDrive API responses"""

    def __init__(self):
        """Initialize the mock API service"""
        self.latency_seconds = MOCK_LATENCY_MS / 1000.0

    async def get_ots(self) -> List[Dict[str, Any]]:
        """
        Simulate fetching OTs from TELCOS API.

        Returns a list of 10-20 mock OT objects with realistic Ecuador coordinates.
        Some OTs have missing coordinates for ERROR_GEO testing.

        Returns:
            List of OT dictionaries
        """
        await asyncio.sleep(self.latency_seconds)

        logger.info("MockApiService: Fetching OTs from mock TELCOS API")

        ots = []
        num_ots = random.randint(10, 20)

        for i in range(num_ots):
            ot_id = f"OT-2024-{1000 + i:04d}"

            # Some OTs (10% chance) have missing coordinates for ERROR_GEO testing
            has_coords = random.random() > 0.1

            ot = {
                "external_id": ot_id,
                "cliente_id": f"CLI-{random.randint(100, 999)}",
                "login_id": f"LOG-{random.randint(10000, 99999)}",
                "status": OT_STATUS["PREPLANIFICADA"],
                "project_type": random.choice(
                    [
                        PROJECT_TYPES["PUBLICO"],
                        PROJECT_TYPES["PRIVADO"],
                        PROJECT_TYPES["TERCERIZADO"],
                    ]
                ),
                "lat": round(random.uniform(-0.30, -0.10), 6)
                if has_coords
                else None,
                "long": round(random.uniform(-78.50, -78.40), 6)
                if has_coords
                else None,
            }
            ots.append(ot)

        logger.info(f"MockApiService: Generated {len(ots)} mock OTs")
        return ots

    async def update_status(self, ot_id: str, new_status: str) -> Dict[str, Any]:
        """
        Simulate updating an OT status in TELCOS API.

        Simulates a 10% failure rate for robustness testing.

        Args:
            ot_id: External OT ID
            new_status: New status to set

        Returns:
            Dictionary with success and message
        """
        await asyncio.sleep(self.latency_seconds)

        logger.info(
            f"MockApiService: Updating OT {ot_id} to status {new_status}"
        )

        # Simulate 10% failure rate
        if random.random() < 0.1:
            logger.warning(f"MockApiService: Simulated failure for OT {ot_id}")
            return {
                "success": False,
                "message": f"Simulated API error updating OT {ot_id}",
            }

        return {
            "success": True,
            "message": f"OT {ot_id} status updated to {new_status}",
        }

    async def get_documents(self, ot_id: str) -> Dict[str, Any]:
        """
        Simulate fetching document count from TelcoDrive API.

        For PUBLICO projects, returns 0-29 documents.
        For others, returns empty or 0 documents.

        Args:
            ot_id: External OT ID

        Returns:
            Dictionary with document_count and documents list
        """
        await asyncio.sleep(self.latency_seconds)

        logger.info(f"MockApiService: Fetching documents for OT {ot_id}")

        # Simulate document count based on project type
        # In reality, we'd need to know the project type, so we simulate it here
        is_publico = random.random() < 0.5  # 50% chance of PUBLICO

        if is_publico:
            # PUBLICO projects have 0-29 documents
            document_count = random.randint(0, 29)
        else:
            # Non-PUBLICO projects have 0 documents (mock)
            document_count = 0

        documents = [
            {
                "name": f"documento_{i}.pdf",
                "uploaded": True,
                "url": f"https://drive.telconet.ec/doc/{ot_id}/{i}",
            }
            for i in range(document_count)
        ]

        logger.info(
            f"MockApiService: Generated {document_count} documents for OT {ot_id}"
        )

        return {
            "document_count": document_count,
            "documents": documents,
        }

