"""
Mock API Service for simulating TELCOS and TelcoDrive API responses.
Used in development/testing when SYSTEM_MODE=MOCK.
"""

import asyncio
import random
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class MockApiService:
    """
    Simulates TELCOS and TelcoDrive API responses for development and testing.
    
    Provides realistic mock data with:
    - 15-20 OTs with various project types and statuses
    - Realistic Ecuadorian coordinates
    - 90% success rate for status updates
    - Random document counts for PUBLICO projects (15-29)
    - 500ms latency simulation for each method
    """

    def __init__(self):
        """Initialize mock service with realistic OT data."""
        self.mock_ots: Dict[str, Dict] = {}
        self._initialize_mock_ots()

    def _initialize_mock_ots(self):
        """Initialize mock OT database with 15-20 realistic entries."""
        # Generate 18 mock OTs
        for i in range(18):
            mock_ot = self._generate_mock_ot(i + 1)
            self.mock_ots[mock_ot["external_id"]] = mock_ot

    def _generate_mock_ot(self, index: int) -> Dict:
        """
        Generate a single mock OT with realistic data.
        
        Args:
            index: Sequential index for generating unique IDs
            
        Returns:
            Dictionary containing mock OT data with realistic Ecuadorian coordinates
        """
        # Project types with distribution: 40% PUBLICO, 35% PRIVADO, 25% TERCERIZADO
        project_types = ["PUBLICO"] * 7 + ["PRIVADO"] * 6 + ["TERCERIZADO"] * 5
        project_type = project_types[index % len(project_types)]

        # OT statuses with distribution for variety
        statuses = [
            "PREPLANIFICADA",
            "PLANIFICADA",
            "ASIGNADO_TAREA",
            "DETENIDA",
            "FINALIZADA",
        ]
        status = statuses[index % len(statuses)]

        # Realistic Ecuadorian coordinates
        # Ecuador latitude range: -2.0 to -0.5
        # Ecuador longitude range: -79.5 to -78.0
        lat = round(random.uniform(-2.0, -0.5), 6)
        lon = round(random.uniform(-79.5, -78.0), 6)

        # Random past date for creation (within last 90 days)
        days_ago = random.randint(1, 90)
        created_at = datetime.utcnow() - timedelta(days=days_ago)

        return {
            "external_id": f"OT-{2024001 + index}",
            "cliente_id": f"CLIENT-{1000 + (index % 50)}",
            "login_id": f"TECH-{100 + (index % 20)}",
            "status": status,
            "project_type": project_type,
            "lat": lat,
            "long": lon,
            "created_at": created_at.isoformat(),
            "geo_error": False if random.random() > 0.1 else True,  # 10% have geo errors
            "detencion_motivo": "Client unavailable" if status == "DETENIDA" else None,
        }

    async def get_telcos_ots(self) -> List[Dict]:
        """
        Fetch OT list from TELCOS API (mocked).
        
        Simulates 500ms latency and returns 15-20 mock OTs with
        realistic data, various statuses, and Ecuadorian coordinates.
        
        Returns:
            List of OT dictionaries from mock TELCOS API
        """
        # Simulate API latency (500ms)
        await asyncio.sleep(0.5)

        # Return all mock OTs as a list
        return list(self.mock_ots.values())

    async def update_ot_status(self, external_id: str, new_status: str) -> bool:
        """
        Update OT status in TELCOS API (mocked).
        
        Simulates 500ms latency and returns success/failure with 90% success rate.
        
        Args:
            external_id: External ID of the OT to update
            new_status: New status value
            
        Returns:
            True if update was successful (90% probability), False otherwise
        """
        # Simulate API latency (500ms)
        await asyncio.sleep(0.5)

        # Check if OT exists
        if external_id not in self.mock_ots:
            return False

        # 90% success rate
        success_probability = 0.9
        if random.random() < success_probability:
            # Update the status
            self.mock_ots[external_id]["status"] = new_status
            self.mock_ots[external_id]["updated_at"] = datetime.utcnow().isoformat()
            return True
        else:
            # Simulate API failure (10% of the time)
            return False

    async def get_telcodrive_documents(self, ot_external_id: str) -> Optional[int]:
        """
        Fetch document count from TelcoDrive API (mocked).
        
        Simulates 500ms latency and returns random document count (15-29)
        for PUBLICO projects. Returns None if OT not found.
        
        Args:
            ot_external_id: External ID of the OT
            
        Returns:
            Document count (15-29) if OT is PUBLICO, otherwise 0
            None if OT not found
        """
        # Simulate API latency (500ms)
        await asyncio.sleep(0.5)

        # Check if OT exists
        if ot_external_id not in self.mock_ots:
            return None

        ot = self.mock_ots[ot_external_id]

        # Return random document count (15-29) for PUBLICO projects
        # Return 0 for other project types (documents not required)
        if ot["project_type"] == "PUBLICO":
            return random.randint(15, 29)
        else:
            return 0

