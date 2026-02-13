import asyncio
import random
from typing import List, Dict, Any
from datetime import datetime
from app.config import get_settings


class MockApiService:
    """Mock API service for TELCOS and TelcoDrive APIs"""

    def __init__(self):
        self.settings = get_settings()
        self.ot_id_counter = 1000

    async def get_ots(self) -> List[Dict[str, Any]]:
        """
        Get mock OTs with varied status, project types, and Ecuador-bounded coordinates
        """
        await asyncio.sleep(0.5)  # Simulate 500ms latency

        statuses = ["PREPLANIFICADA", "PLANIFICADA", "ASIGNADO_TAREA", "DETENIDA", "FINALIZADA"]
        project_types = ["PUBLICO", "PRIVADO", "TERCERIZADO"]
        
        # Ecuador bounds: lat -5 to 2, long -92 to -75
        ots = []
        for i in range(random.randint(15, 20)):
            self.ot_id_counter += 1
            lat = random.uniform(-5, 2)
            long = random.uniform(-92, -75)
            
            ot = {
                "external_id": f"OT-{self.ot_id_counter}",
                "status": random.choice(statuses),
                "project_type": random.choice(project_types),
                "lat": round(lat, 6),
                "long": round(long, 6),
                "cliente_id": f"CLI-{random.randint(1000, 9999)}",
                "login_id": f"LOGIN-{random.randint(1000, 9999)}",
                "geo_error": random.choice([True, False]) if random.random() < 0.1 else False,
                "detention_reason": None,
            }
            ots.append(ot)
        
        return ots

    async def update_ot_status(self, external_id: str, new_status: str) -> Dict[str, Any]:
        """
        Simulate OT status update with success/failure response
        """
        await asyncio.sleep(0.5)  # Simulate 500ms latency
        
        success = random.random() > 0.1  # 90% success rate
        
        return {
            "success": success,
            "message": f"OT {external_id} status updated to {new_status}" if success else f"Failed to update OT {external_id}",
            "external_id": external_id,
            "new_status": new_status,
        }

    async def get_telcodrive_documents(self, ot_id: str) -> Dict[str, Any]:
        """
        Get mock documents count for TelcoDrive
        - For PUBLICO projects: random 10-29
        - For others: random with possibility of fewer documents
        """
        await asyncio.sleep(0.5)  # Simulate 500ms latency
        
        # Simulate document count (in real scenario, would depend on project_type)
        document_count = random.randint(10, 29)
        
        documents = [
            {"id": i, "name": f"Document_{i}.pdf", "uploaded_at": datetime.utcnow().isoformat()}
            for i in range(1, document_count + 1)
        ]
        
        return {
            "ot_id": ot_id,
            "document_count": document_count,
            "documents": documents,
            "complete": document_count >= 29,
        }

