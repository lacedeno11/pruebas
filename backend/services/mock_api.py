"""
Mock API Service for TELCOS and TelcoDrive integration.
Simulates external API responses for development and testing.
"""

import asyncio
import os
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum


class OTStatus(str, Enum):
    """OT Status enumeration"""
    PREPLANIFICADA = "PREPLANIFICADA"
    PLANIFICADA = "PLANIFICADA"
    ASIGNADO_TAREA = "ASIGNADO_TAREA"
    DETENIDA = "DETENIDA"
    ANULADA = "ANULADA"
    FINALIZADA = "FINALIZADA"


class ProjectType(str, Enum):
    """Project Type enumeration"""
    PUBLICO = "PUBLICO"
    PRIVADO = "PRIVADO"
    TERCERIZADO = "TERCERIZADO"


class MockApiService:
    """
    Mock API Service for simulating TELCOS and TelcoDrive APIs.
    
    This service provides:
    - Mock OT data generation (15-20 OTs with varied data)
    - Status update simulation (90% success rate)
    - Document count simulation for PUBLICO projects
    - 500ms simulated latency to test loading states
    """

    # Ecuador region coordinates
    LAT_MIN = -2.5
    LAT_MAX = -2.0
    LONG_MIN = -80.2
    LONG_MAX = -79.8

    # Mock data cache
    _mock_ots: Optional[List[Dict[str, Any]]] = None

    @staticmethod
    def is_mock_mode() -> bool:
        """Check if system is in MOCK mode"""
        return os.getenv("SYSTEM_MODE", "MOCK") == "MOCK"

    @staticmethod
    def _generate_coordinates() -> tuple[float, float]:
        """Generate random coordinates in Ecuador region"""
        lat = round(random.uniform(MockApiService.LAT_MIN, MockApiService.LAT_MAX), 4)
        long = round(random.uniform(MockApiService.LONG_MIN, MockApiService.LONG_MAX), 4)
        return lat, long

    @classmethod
    def _generate_mock_ots(cls) -> List[Dict[str, Any]]:
        """Generate 15-20 mock OTs with varied data"""
        ots = []
        total_ots = random.randint(15, 20)
        base_date = datetime.now() - timedelta(days=45)

        # Define projects for grouping
        projects = [
            {"name": "DataLegal", "type": ProjectType.PUBLICO},
            {"name": "FiberNet", "type": ProjectType.PRIVADO},
            {"name": "CloudInfra", "type": ProjectType.TERCERIZADO},
            {"name": "SecureVPN", "type": ProjectType.PUBLICO},
            {"name": "MobileFirst", "type": ProjectType.PRIVADO},
        ]

        # Generate OTs with varied status distribution
        statuses = [
            OTStatus.PREPLANIFICADA,
            OTStatus.PLANIFICADA,
            OTStatus.ASIGNADO_TAREA,
            OTStatus.DETENIDA,
            OTStatus.FINALIZADA,
        ]

        for i in range(total_ots):
            ot_id = 1000 + i
            project = random.choice(projects)
            created_at = base_date + timedelta(days=random.randint(0, 45))

            # 2-3 OTs with missing coordinates for ERROR_GEO testing
            if i < 3 and random.random() < 0.3:
                lat, long = None, None
            else:
                lat, long = cls._generate_coordinates()

            ot = {
                "id": ot_id,
                "external_id": f"OT-{str(ot_id).zfill(6)}",
                "cliente_id": random.randint(1, 20),
                "orden_servicio_id": random.randint(1, 30),
                "login_id": random.randint(1, 50),
                "status": random.choice(statuses),
                "project_type": project["type"],
                "lat": lat,
                "long": long,
                "cuadrilla_id": random.randint(1, 10) if random.random() > 0.3 else None,
                "created_at": created_at.isoformat(),
                "updated_at": (created_at + timedelta(days=random.randint(0, 45))).isoformat(),
                "geo_error": lat is None or long is None,
            }
            ots.append(ot)

        return ots

    async def get_ots(self) -> List[Dict[str, Any]]:
        """
        Fetch mock OTs from simulated API.
        
        Returns:
            List of 15-20 mock OTs with varied data
            
        Raises:
            Exception: If system is not in MOCK mode
        """
        if not self.is_mock_mode():
            raise Exception("MockApiService can only be used when SYSTEM_MODE=MOCK")

        # Simulate 500ms API latency
        await asyncio.sleep(0.5)

        # Generate or return cached mock OTs
        if self._mock_ots is None:
            self._mock_ots = self._generate_mock_ots()

        return self._mock_ots

    async def update_status(
        self, ot_id: int, new_status: str
    ) -> Dict[str, Any]:
        """
        Simulate status update with 90% success rate.
        
        Args:
            ot_id: Work Order ID
            new_status: New status to update to
            
        Returns:
            Success/error response dict
        """
        if not self.is_mock_mode():
            raise Exception("MockApiService can only be used when SYSTEM_MODE=MOCK")

        # Simulate 500ms API latency
        await asyncio.sleep(0.5)

        # 90% success rate
        success = random.random() < 0.9

        if success:
            return {
                "success": True,
                "ot_id": ot_id,
                "new_status": new_status,
                "updated_at": datetime.now().isoformat(),
                "message": f"OT {ot_id} status updated to {new_status}",
            }
        else:
            return {
                "success": False,
                "ot_id": ot_id,
                "error": "Failed to update status in external system",
                "message": f"Error updating OT {ot_id}: Connection timeout",
            }

    async def get_telcodrive_documents(self, ot_id: int) -> Dict[str, Any]:
        """
        Get document count for PUBLICO projects from TelcoDrive.
        
        Args:
            ot_id: Work Order ID
            
        Returns:
            Document count (0-29) for the OT
        """
        if not self.is_mock_mode():
            raise Exception("MockApiService can only be used when SYSTEM_MODE=MOCK")

        # Simulate 500ms API latency
        await asyncio.sleep(0.5)

        # Return document count between 0-29
        # Some have full 29, some have partial, some have 0
        doc_count = random.randint(0, 29)

        # Higher probability of having many documents
        if random.random() < 0.6:
            doc_count = random.randint(20, 29)
        elif random.random() < 0.8:
            doc_count = random.randint(10, 19)

        return {
            "ot_id": ot_id,
            "document_count": doc_count,
            "required_count": 29,
            "is_complete": doc_count >= 29,
            "documents": [
                {
                    "id": f"DOC-{i+1:03d}",
                    "name": f"Document {i+1}",
                    "status": "uploaded" if i < doc_count else "pending",
                }
                for i in range(29)
            ],
        }

    async def reset_mock_data(self) -> Dict[str, Any]:
        """Reset cached mock data to generate new OTs on next call"""
        self._mock_ots = None
        await asyncio.sleep(0.1)
        return {
            "success": True,
            "message": "Mock data cache cleared",
        }


# Global instance
mock_api_service = MockApiService()

