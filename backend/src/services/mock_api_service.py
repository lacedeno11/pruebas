"""
Mock API Service for PEI Platform (SYSTEM_MODE=MOCK).

This service simulates the Telcos API for development and testing.
Returns realistic mock data with configurable latency to simulate network delays.
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import Any

from src.config.settings import settings

logger = logging.getLogger(__name__)


class MockApiService:
    """
    Mock API service simulating Telcos API responses.

    This service is used when SYSTEM_MODE=MOCK in settings. It generates
    realistic mock OT data for testing the planning and governance agents
    without requiring actual API connectivity.

    Features:
    - Generates 15-20 realistic mock OTs with Ecuador coordinates
    - Includes 2-3 OTs without coordinates for ERROR_GEO testing
    - Simulates network latency via asyncio.sleep()
    - Provides 90% success rate for status updates
    - Returns realistic document counts for Telcodrive
    """

    # Ecuador geographic bounds for realistic coordinates
    ECUADOR_LAT_MIN = -5.0
    ECUADOR_LAT_MAX = 2.0
    ECUADOR_LON_MIN = -81.0
    ECUADOR_LON_MAX = -75.0

    # Sample client and login IDs
    SAMPLE_CLIENTS = [
        "TELCONET",
        "DataLegal",
        "CloudTech",
        "TelecomunicaEcuador",
        "NetworkPro",
        "ConnectIT",
    ]

    SAMPLE_LOGINS = [
        "tech_user_1",
        "installer_001",
        "coord_pou",
        "maintenance_team",
        "field_supervisor",
        "dispatch_001",
    ]

    async def get_ots(self) -> list[dict[str, Any]]:
        """
        Fetch a list of mock OTs from simulated Telcos API.

        Returns a list of 15-20 OTs with:
        - Most with valid Ecuador coordinates
        - 2-3 without coordinates (is_geo_error = True)
        - Random project types
        - All with status = PREPLANIFICADA
        - Realistic external IDs and client info

        The method simulates network latency as configured in settings.

        Returns:
            list[dict]: List of OT dictionaries with keys:
                - external_id (str): Unique ID from Telcos system
                - cliente_id (str): Client identifier
                - login_id (str): Login identifier
                - lat (float): Latitude (may be None)
                - long (float): Longitude (may be None)
                - project_type (str): PUBLICO, PRIVADO, or TERCERIZADO
                - status (str): Always PREPLANIFICADA initially

        Example:
            ots = await api_service.get_ots()
            # Returns:
            # [
            #     {
            #         "external_id": "OT-20240101-0001",
            #         "cliente_id": "TELCONET",
            #         "login_id": "tech_user_1",
            #         "lat": -0.35, "long": -78.50,
            #         "project_type": "PUBLICO",
            #         "status": "PREPLANIFICADA"
            #     },
            #     ...
            # ]
        """
        # Simulate network latency
        await asyncio.sleep(settings.mock_api_latency_ms / 1000)

        ots = []
        total_ots = random.randint(15, 20)

        # Generate OTs with valid coordinates
        valid_ots_count = total_ots - 3  # Reserve 2-3 for GEO_ERROR
        for i in range(valid_ots_count):
            ots.append(
                {
                    "external_id": f"OT-{datetime.utcnow().strftime('%Y%m%d')}-{i+1:04d}",
                    "cliente_id": random.choice(self.SAMPLE_CLIENTS),
                    "login_id": random.choice(self.SAMPLE_LOGINS),
                    "lat": random.uniform(self.ECUADOR_LAT_MIN, self.ECUADOR_LAT_MAX),
                    "long": random.uniform(self.ECUADOR_LON_MIN, self.ECUADOR_LON_MAX),
                    "project_type": random.choice(["PUBLICO", "PRIVADO", "TERCERIZADO"]),
                    "status": "PREPLANIFICADA",
                }
            )

        # Generate OTs without coordinates (for ERROR_GEO testing)
        for i in range(3):
            ots.append(
                {
                    "external_id": f"OT-{datetime.utcnow().strftime('%Y%m%d')}-{valid_ots_count+i+1:04d}",
                    "cliente_id": random.choice(self.SAMPLE_CLIENTS),
                    "login_id": random.choice(self.SAMPLE_LOGINS),
                    "lat": None,
                    "long": None,
                    "project_type": random.choice(["PUBLICO", "PRIVADO", "TERCERIZADO"]),
                    "status": "PREPLANIFICADA",
                }
            )

        logger.info(f"Mock API: Generated {len(ots)} OTs ({valid_ots_count} with coords, 3 GEO_ERROR)")
        return ots

    async def update_status(
        self, ot_external_id: str, new_status: str
    ) -> dict[str, Any]:
        """
        Update the status of an OT (simulated).

        Simulates the Telcos API status update endpoint with a 90% success rate
        to test error handling and retry logic.

        The method simulates network latency as configured in settings.

        Args:
            ot_external_id (str): The external ID of the OT to update
            new_status (str): The new status to set

        Returns:
            dict: Response with keys:
                - success (bool): True if update succeeded, False otherwise
                - message (str): Status message
                - data (dict): Updated OT data (if successful)

        Example:
            result = await api_service.update_status("OT-20240101-0001", "PLANIFICADA")
            # Returns:
            # {
            #     "success": True,
            #     "message": "Status updated successfully",
            #     "data": {"external_id": "OT-20240101-0001", "status": "PLANIFICADA"}
            # }
        """
        # Simulate network latency
        await asyncio.sleep(settings.mock_api_latency_ms / 1000)

        # 90% success rate
        success = random.random() < 0.9

        if success:
            logger.info(f"Mock API: Updated OT {ot_external_id} to status {new_status}")
            return {
                "success": True,
                "message": "Status updated successfully",
                "data": {
                    "external_id": ot_external_id,
                    "status": new_status,
                    "updated_at": datetime.utcnow().isoformat(),
                },
            }
        else:
            logger.warning(
                f"Mock API: Failed to update OT {ot_external_id} (simulated failure)"
            )
            return {
                "success": False,
                "message": "Failed to update status (simulated API error)",
                "error": "TEMPORARY_ERROR",
            }

    async def get_telcodrive_documents(
        self, ot_external_id: str
    ) -> dict[str, Any]:
        """
        Get the document count for an OT from Telcodrive.

        Simulates fetching document information from the Telcodrive system.
        For PUBLICO projects, returns 0-29 documents (testing the requirement
        that PUBLICO projects need exactly 29 documents to transition to FINALIZADA).

        The method simulates network latency as configured in settings.

        Args:
            ot_external_id (str): The external ID of the OT

        Returns:
            dict: Response with keys:
                - success (bool): Always True for mock service
                - document_count (int): Number of documents (0-29 for PUBLICO)
                - documents (list): List of document metadata (simplified)

        Example:
            result = await api_service.get_telcodrive_documents("OT-20240101-0001")
            # Returns:
            # {
            #     "success": True,
            #     "document_count": 25,
            #     "documents": [
            #         {"id": "doc_001", "type": "INSTALACION", "status": "VALIDADO"},
            #         ...
            #     ]
            # }
        """
        # Simulate network latency
        await asyncio.sleep(settings.mock_api_latency_ms / 1000)

        # Generate random document count (0-29 to test the 29-doc requirement)
        document_count = random.randint(0, 29)

        # Create mock document list
        documents = [
            {
                "id": f"doc_{i+1:03d}",
                "type": random.choice(
                    [
                        "INSTALACION",
                        "REPARACION",
                        "INSPECCION",
                        "CERTIFICACION",
                        "PRUEBA",
                    ]
                ),
                "status": random.choice(["VALIDADO", "PENDIENTE", "RECHAZADO"]),
                "created_at": datetime.utcnow().isoformat(),
            }
            for i in range(document_count)
        ]

        logger.info(
            f"Mock API: Retrieved {document_count} documents for OT {ot_external_id}"
        )

        return {
            "success": True,
            "document_count": document_count,
            "documents": documents,
            "ot_external_id": ot_external_id,
        }

    async def get_ot_details(self, ot_external_id: str) -> dict[str, Any]:
        """
        Get detailed information for a specific OT.

        Args:
            ot_external_id (str): The external ID of the OT

        Returns:
            dict: OT details or error response
        """
        # Simulate network latency
        await asyncio.sleep(settings.mock_api_latency_ms / 1000)

        # Return a mock OT
        return {
            "success": True,
            "data": {
                "external_id": ot_external_id,
                "cliente_id": random.choice(self.SAMPLE_CLIENTS),
                "login_id": random.choice(self.SAMPLE_LOGINS),
                "lat": random.uniform(self.ECUADOR_LAT_MIN, self.ECUADOR_LAT_MAX),
                "long": random.uniform(self.ECUADOR_LON_MIN, self.ECUADOR_LON_MAX),
                "project_type": random.choice(["PUBLICO", "PRIVADO", "TERCERIZADO"]),
                "status": "PREPLANIFICADA",
            },
        }

    async def health_check(self) -> dict[str, Any]:
        """
        Check the health status of the mock API.

        Returns:
            dict: Health status
        """
        return {
            "status": "healthy",
            "service": "mock_api",
            "timestamp": datetime.utcnow().isoformat(),
        }

