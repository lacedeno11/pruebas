"""Mock API endpoints for testing and development"""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends

from backend.services.mock_api_service import MockApiService
from backend.config.settings import settings

logger = logging.getLogger(__name__)

# Only create router if SYSTEM_MODE is MOCK
if settings.SYSTEM_MODE == "MOCK":
    router = APIRouter(prefix="/api/mock", tags=["mock"])

    @router.get("/telcos/ots")
    async def get_mock_ots() -> list:
        """
        Get mock OTs from TELCOS API simulation.

        This endpoint simulates fetching OTs from the TELCOS API with realistic
        Ecuador coordinates and simulated 500ms latency.

        Returns:
        - List of mock OT objects with:
          - external_id: OT-2024-XXXX format
          - cliente_id: CLI-XXX
          - login_id: LOG-XXXXX
          - status: PREPLANIFICADA
          - project_type: PUBLICO, PRIVADO, or TERCERIZADO
          - lat: Ecuador latitude (-0.1 to -0.3)
          - long: Ecuador longitude (-78.4 to -78.5)
          - Some OTs with null lat/long for ERROR_GEO testing

        Status Codes:
        - 200: Success
        - 500: Internal server error
        """
        try:
            logger.info("GET /api/mock/telcos/ots - Fetching mock OTs")

            mock_service = MockApiService()
            ots = await mock_service.get_ots()

            logger.info(f"Returned {len(ots)} mock OTs")
            return ots

        except Exception as e:
            logger.error(f"Error fetching mock OTs: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @router.post("/telcos/update_status")
    async def update_mock_ot_status(
        status_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update mock OT status in TELCOS API simulation.

        This endpoint simulates updating an OT status with a 10% random failure rate
        to test error handling and retry logic.

        Request Body:
        - ot_id (str): External OT ID (e.g., 'OT-2024-0001')
        - new_status (str): New status to set

        Returns:
        - success (bool): Whether the update was successful (90% success rate)
        - message (str): Status message

        Status Codes:
        - 200: Update completed (success or simulated failure)
        - 400: Invalid request data
        - 500: Internal server error
        """
        try:
            ot_id = status_data.get("ot_id")
            new_status = status_data.get("new_status")

            if not ot_id or not new_status:
                logger.warning("Missing ot_id or new_status in request")
                raise HTTPException(
                    status_code=400,
                    detail="ot_id and new_status are required",
                )

            logger.info(
                f"POST /api/mock/telcos/update_status - "
                f"Updating OT {ot_id} to {new_status}"
            )

            mock_service = MockApiService()
            result = await mock_service.update_status(ot_id, new_status)

            logger.info(f"Update status result: {result}")
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating mock OT status: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @router.get("/telcodrive/documents/{ot_id}")
    async def get_mock_documents(ot_id: str) -> Dict[str, Any]:
        """
        Get mock document count from TelcoDrive API simulation.

        This endpoint simulates fetching document information for an OT with
        realistic document counts and simulated latency.

        Path Parameters:
        - ot_id (str): External OT ID (e.g., 'OT-2024-0001')

        Returns:
        - document_count (int):
          - For PUBLICO projects: 0-29 documents
          - For other projects: 0 documents
        - documents (List[dict]): List of document objects with:
          - name: Document filename
          - uploaded: Boolean flag
          - url: Document URL

        Status Codes:
        - 200: Success
        - 404: OT not found (not simulated, always returns 200)
        - 500: Internal server error

        Example Response:
        ```json
        {
          "document_count": 15,
          "documents": [
            {
              "name": "documento_0.pdf",
              "uploaded": true,
              "url": "https://drive.telconet.ec/doc/OT-2024-0001/0"
            },
            {
              "name": "documento_1.pdf",
              "uploaded": true,
              "url": "https://drive.telconet.ec/doc/OT-2024-0001/1"
            }
          ]
        }
        ```
        """
        try:
            logger.info(
                f"GET /api/mock/telcodrive/documents - "
                f"Fetching documents for OT {ot_id}"
            )

            mock_service = MockApiService()
            documents = await mock_service.get_documents(ot_id)

            logger.info(
                f"Returned {documents['document_count']} documents for OT {ot_id}"
            )
            return documents

        except Exception as e:
            logger.error(f"Error fetching mock documents: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @router.get("/stats")
    async def get_mock_stats() -> Dict[str, Any]:
        """
        Get mock statistics for dashboard testing.

        This endpoint returns simulated statistics for testing the dashboard
        without needing actual data in the database.

        Returns:
        - Mock statistics object with:
          - total_ots (int): Total OTs in system
          - by_status (Dict): OT counts by status
          - by_project_type (Dict): OT counts by project type
          - cuadrillas_workload (List): Cuadrilla workload data
          - alerts_active (int): Number of active alerts
          - recent_assignments (List): Recent assignment operations
          - avg_distance_to_centroid (float): Average distance metrics

        Status Codes:
        - 200: Success
        - 500: Internal server error

        Example Response:
        ```json
        {
          "total_ots": 50,
          "by_status": {
            "PREPLANIFICADA": 10,
            "PLANIFICADA": 15,
            "ASIGNADO_TAREA": 12,
            "DETENIDA": 8,
            "ANULADA": 3,
            "FINALIZADA": 2
          },
          "by_project_type": {
            "PUBLICO": 20,
            "PRIVADO": 20,
            "TERCERIZADO": 10
          },
          "cuadrillas_workload": [
            {
              "cuadrilla_id": 1,
              "name": "Cuadrilla Norte 1",
              "workload": 5,
              "capacity": 10,
              "utilization_pct": 50
            }
          ],
          "alerts_active": 5,
          "recent_assignments": [
            {
              "ot_id": 1,
              "cuadrilla_id": 2,
              "timestamp": "2024-02-13T10:00:00",
              "distance": 3.5
            }
          ],
          "avg_distance_to_centroid": 4.2,
          "timestamp": "2024-02-13T10:05:00"
        }
        ```
        """
        try:
            logger.info("GET /api/mock/stats - Fetching mock statistics")

            # Generate mock statistics
            stats = {
                "total_ots": 50,
                "by_status": {
                    "PREPLANIFICADA": 10,
                    "PLANIFICADA": 15,
                    "ASIGNADO_TAREA": 12,
                    "DETENIDA": 8,
                    "ANULADA": 3,
                    "FINALIZADA": 2,
                },
                "by_project_type": {
                    "PUBLICO": 20,
                    "PRIVADO": 20,
                    "TERCERIZADO": 10,
                },
                "cuadrillas_workload": [
                    {
                        "cuadrilla_id": 1,
                        "name": "Cuadrilla Norte 1",
                        "type": "Principal",
                        "workload": 5,
                        "capacity": 10,
                        "utilization_pct": 50.0,
                    },
                    {
                        "cuadrilla_id": 2,
                        "name": "Cuadrilla Centro 1",
                        "type": "Principal",
                        "workload": 8,
                        "capacity": 10,
                        "utilization_pct": 80.0,
                    },
                    {
                        "cuadrilla_id": 3,
                        "name": "Cuadrilla Sur 1",
                        "type": "Reserva",
                        "workload": 2,
                        "capacity": 8,
                        "utilization_pct": 25.0,
                    },
                ],
                "alerts_active": 5,
                "recent_assignments": [
                    {
                        "ot_id": 1,
                        "cuadrilla_id": 2,
                        "timestamp": "2024-02-13T10:00:00",
                        "distance": 3.5,
                    },
                    {
                        "ot_id": 2,
                        "cuadrilla_id": 1,
                        "timestamp": "2024-02-13T09:55:00",
                        "distance": 2.1,
                    },
                    {
                        "ot_id": 3,
                        "cuadrilla_id": 3,
                        "timestamp": "2024-02-13T09:50:00",
                        "distance": 5.8,
                    },
                ],
                "avg_distance_to_centroid": 3.8,
                "timestamp": "2024-02-13T10:05:00",
            }

            logger.info("Returned mock statistics")
            return stats

        except Exception as e:
            logger.error(f"Error fetching mock statistics: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

else:
    # Create empty router if not in MOCK mode
    router = APIRouter(prefix="/api/mock", tags=["mock"])

    @router.get("")
    async def mock_disabled():
        """
        Mock API is disabled.

        This endpoint is only available when SYSTEM_MODE=MOCK.
        Current mode: {settings.SYSTEM_MODE}
        """
        raise HTTPException(
            status_code=403,
            detail=f"Mock API is disabled. Current mode: {settings.SYSTEM_MODE}",
        )

