"""Mock API service for simulating TELCOS and TelcoDrive APIs."""

import asyncio
from typing import List, Dict, Any
from datetime import datetime
import random
import uuid


class MockApiService:
    """Service that simulates TELCOS and TelcoDrive API responses."""
    
    def __init__(self, latency_ms: int = 500):
        """
        Initialize the mock API service.
        
        Args:
            latency_ms: Simulated latency in milliseconds (default 500ms)
        """
        self.latency_ms = latency_ms
        
        # Predefined mock OTs with varied project types
        self.mock_ots = [
            {
                "external_id": "OT-2024-001",
                "cliente_id": "CLI-001",
                "login": "login_001",
                "lat": -1.8,
                "long": -78.5,
                "project_type": "PUBLICO",
                "status": "PREPLANIFICADA",
                "created_at": datetime.now().isoformat(),
            },
            {
                "external_id": "OT-2024-002",
                "cliente_id": "CLI-002",
                "login": "login_002",
                "lat": -1.5,
                "long": -78.2,
                "project_type": "PRIVADO",
                "status": "PREPLANIFICADA",
                "created_at": datetime.now().isoformat(),
            },
            {
                "external_id": "OT-2024-003",
                "cliente_id": "CLI-003",
                "login": "login_003",
                "lat": -1.2,
                "long": -78.8,
                "project_type": "TERCERIZADO",
                "status": "PREPLANIFICADA",
                "created_at": datetime.now().isoformat(),
            },
            {
                "external_id": "OT-2024-004",
                "cliente_id": "CLI-004",
                "login": "login_004",
                "lat": -0.8,
                "long": -77.5,
                "project_type": "PUBLICO",
                "status": "PREPLANIFICADA",
                "created_at": datetime.now().isoformat(),
            },
            {
                "external_id": "OT-2024-005",
                "cliente_id": "CLI-005",
                "login": "login_005",
                "lat": -1.0,
                "long": -79.0,
                "project_type": "PRIVADO",
                "status": "PREPLANIFICADA",
                "created_at": datetime.now().isoformat(),
            },
        ]
    
    async def get_ots(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get list of mock OTs with simulated latency.
        
        Args:
            limit: Maximum number of OTs to return
        
        Returns:
            List of OT dictionaries
        """
        # Simulate API latency
        await asyncio.sleep(self.latency_ms / 1000.0)
        
        # Return mock OTs (limited)
        return self.mock_ots[:limit]
    
    async def update_status(self, external_id: str, new_status: str) -> Dict[str, Any]:
        """
        Simulate status update with 95% success rate.
        
        Args:
            external_id: External ID of the OT
            new_status: New status to set
        
        Returns:
            Response dictionary with success/error status
        """
        # Simulate API latency
        await asyncio.sleep(self.latency_ms / 1000.0)
        
        # 95% success rate
        if random.random() < 0.95:
            return {
                "success": True,
                "message": f"OT {external_id} status updated to {new_status}",
                "ot_id": external_id,
                "new_status": new_status,
            }
        else:
            return {
                "success": False,
                "message": f"Failed to update OT {external_id}: Temporary service error",
                "error_code": "SERVICE_ERROR",
            }
    
    async def get_telcodrive_documents(self, ot_id: str) -> Dict[str, Any]:
        """
        Get mock TelcoDrive documents count (0-29 random).
        
        Args:
            ot_id: ID of the OT
        
        Returns:
            Dictionary with document count and list
        """
        # Simulate API latency
        await asyncio.sleep(self.latency_ms / 1000.0)
        
        # Random document count between 0-29
        document_count = random.randint(0, 29)
        
        # Generate document list
        documents = [
            {
                "id": f"DOC-{i+1}",
                "name": f"Document_{i+1}.pdf",
                "uploaded_at": datetime.now().isoformat(),
                "status": "UPLOADED"
            }
            for i in range(document_count)
        ]
        
        return {
            "ot_id": ot_id,
            "document_count": document_count,
            "document_list": documents,
            "required_count": 29,
            "is_complete": document_count >= 29,
        }

