import asyncio
import random
from typing import Dict, List, Any
from datetime import datetime, timedelta


class MockApiService:
    """
    Mock API service that simulates TELCOS and TelcoDrive API responses.
    Used when SYSTEM_MODE=MOCK for development and testing.
    """

    def __init__(self):
        """Initialize the mock service with seed data."""
        self.mock_ot_id_counter = 1000

    async def get_ots(self) -> List[Dict[str, Any]]:
        """
        Fetch mock OT (Orden de Trabajo) data from TELCOS system.
        
        Returns:
            List of OT dictionaries with realistic data (5-10 OTs with varying statuses,
            coordinates, and project types).
        """
        # Simulate 500ms latency
        await asyncio.sleep(0.5)

        statuses = [
            "PREPLANIFICADA",
            "PLANIFICADA",
            "ASIGNADO_TAREA",
            "DETENIDA",
            "ANULADA",
            "FINALIZADA",
        ]
        project_types = ["PUBLICO", "PRIVADO", "TERCERIZADO"]

        # Ecuador coordinates (approximately)
        ecuador_coordinates = [
            (-1.831239, -78.183406),  # Quito
            (-0.931476, -78.610087),  # Latacunga
            (-1.038889, -78.614722),  # Machachi
            (-1.270833, -78.525556),  # Sangolquí
            (-0.352222, -78.505556),  # Cayambe
            (-1.611389, -78.677222),  # Machachi area
            (-1.206389, -78.488056),  # El Quinche
            (-0.210556, -78.505278),  # Tabacundo
            (-1.673611, -78.632222),  # Latacunga area
            (-0.622778, -78.591389),  # Ambato area
        ]

        ots = []
        num_ots = random.randint(5, 10)

        for i in range(num_ots):
            lat, lon = random.choice(ecuador_coordinates)
            # Add small random variation to coordinates
            lat += random.uniform(-0.05, 0.05)
            lon += random.uniform(-0.05, 0.05)

            ot = {
                "external_id": f"OT-{self.mock_ot_id_counter + i:06d}",
                "status": random.choice(statuses),
                "project_type": random.choice(project_types),
                "cliente_id": f"CLI-{random.randint(1000, 9999)}",
                "login_id": f"SVC-{random.randint(10000, 99999)}",
                "lat": round(lat, 6),
                "long": round(lon, 6),
                "created_at": (
                    datetime.utcnow() - timedelta(days=random.randint(1, 30))
                ).isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            ots.append(ot)

        self.mock_ot_id_counter += num_ots
        return ots

    async def update_status(self, ot_id: str, new_status: str) -> Dict[str, Any]:
        """
        Update OT status in TELCOS system (simulated).
        
        Args:
            ot_id: External OT ID to update
            new_status: New status value
        
        Returns:
            Dictionary with success flag and message
        """
        # Simulate 500ms latency
        await asyncio.sleep(0.5)

        # Simulate random success/failure (90% success rate)
        success = random.random() < 0.9

        if success:
            return {
                "success": True,
                "message": f"OT {ot_id} status updated to {new_status}",
                "ot_id": ot_id,
                "new_status": new_status,
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": f"Failed to update OT {ot_id}: API timeout",
                "ot_id": ot_id,
                "error_code": "TELCOS_TIMEOUT",
            }

    async def get_telcodrive_documents(self, ot_id: str) -> Dict[str, Any]:
        """
        Get document count from TelcoDrive for a specific OT.
        
        Args:
            ot_id: External OT ID to check documents for
        
        Returns:
            Dictionary with document count (0-29 for PUBLICO projects)
        """
        # Simulate 500ms latency
        await asyncio.sleep(0.5)

        # Return document count between 0-29
        document_count = random.randint(0, 29)

        return {
            "ot_id": ot_id,
            "document_count": document_count,
            "is_complete": document_count == 29,
            "timestamp": datetime.utcnow().isoformat(),
        }

