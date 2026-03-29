"""
MockApiService: Simulates external TELCOS APIs for development and testing.

This service provides mock implementations of:
- OT ingestion from TELCOS APIs
- Status update operations with realistic success/failure rates
- Document checklist retrieval for PUBLICO projects

Features:
- 500ms latency simulation for realistic UI testing
- 100 pre-generated OT records for consistency
- 95% success rate on status transitions (5% random failures for error testing)
- Quito, Ecuador coordinates with realistic variations
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class OTStatus(str, Enum):
    """OT Status enumeration matching backend schema."""
    PREPLANIFICADA = "PREPLANIFICADA"
    PLANIFICADA = "PLANIFICADA"
    ASIGNADO_TAREA = "ASIGNADO_TAREA"
    DETENIDA = "DETENIDA"
    ANULADA = "ANULADA"
    FINALIZADA = "FINALIZADA"
    ERROR_GEO = "ERROR_GEO"


class ProjectType(str, Enum):
    """Project type enumeration."""
    PUBLICO = "PUBLICO"
    PRIVADO = "PRIVADO"
    TERCERIZADO = "TERCERIZADO"


class MockApiService:
    """
    Mock implementation of external TELCOS APIs.
    
    Provides simulated responses for:
    - GET /api/telcos/ots: OT ingestion
    - POST /api/telcos/update_status: Status transitions
    - GET /api/telcodrive/documents: Document checklist
    
    All methods include 500ms latency simulation via asyncio.sleep(0.5).
    """

    # Pre-generated pool of 100 OT records for consistency across calls
    MOCK_DATA_POOL: List[Dict[str, Any]] = []

    # Base coordinates for Quito, Ecuador
    QUITO_LAT_BASE = -0.1807
    QUITO_LON_BASE = -78.4678
    QUITO_VARIATION = 0.5  # ±0.5 degrees variation

    @classmethod
    def _initialize_mock_pool(cls) -> None:
        """Initialize MOCK_DATA_POOL with 100 pre-generated OT records."""
        if cls.MOCK_DATA_POOL:
            return  # Already initialized

        random.seed(42)  # Seed for reproducibility
        statuses = [s.value for s in OTStatus if s != OTStatus.ERROR_GEO]
        project_types = [p.value for p in ProjectType]

        for i in range(1, 101):
            # Generate realistic coordinates within Quito region
            lat = cls.QUITO_LAT_BASE + random.uniform(-cls.QUITO_VARIATION, cls.QUITO_VARIATION)
            lon = cls.QUITO_LON_BASE + random.uniform(-cls.QUITO_VARIATION, cls.QUITO_VARIATION)

            # Random project type
            project_type = random.choice(project_types)

            # Create deterministic but varied data
            ot_record = {
                "id": i,
                "external_id": f"OT-2024-{i:05d}",
                "cliente_id": f"CLI-{random.randint(1000, 9999)}",
                "login": f"LOGIN-{random.randint(100000, 999999)}",
                "lat": round(lat, 6),
                "long": round(lon, 6),
                "status": random.choice(statuses),
                "project_type": project_type,
                "created_at": (datetime.utcnow() - timedelta(days=random.randint(0, 30))).isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            cls.MOCK_DATA_POOL.append(ot_record)

    async def get_ots_from_telcos(
        self, page: int = 1, limit: int = 50
    ) -> Dict[str, Any]:
        """
        Mock GET /api/telcos/ots endpoint.
        
        Returns paginated list of OTs with realistic Quito coordinates.
        Includes 500ms latency simulation.
        
        Args:
            page: Page number (1-indexed)
            limit: Items per page (max 50)
            
        Returns:
            Dict with 'data' (OT list), 'total', 'page', 'page_size'
        """
        # Initialize pool on first call
        self._initialize_mock_pool()

        # Simulate 500ms network latency
        await asyncio.sleep(0.5)

        # Validate pagination parameters
        limit = min(limit, 50)  # Max 50 items per page
        offset = (page - 1) * limit
        paginated_data = self.MOCK_DATA_POOL[offset : offset + limit]

        return {
            "data": paginated_data,
            "total": len(self.MOCK_DATA_POOL),
            "page": page,
            "page_size": limit,
        }

    async def update_status_in_telcos(
        self, ot_id: str, new_status: str
    ) -> Dict[str, Any]:
        """
        Mock POST /api/telcos/update_status endpoint.
        
        Simulates status transition with:
        - 95% success rate
        - 5% random failures for error handling testing
        - 500ms latency simulation
        
        Args:
            ot_id: OT external ID (e.g., "OT-2024-00001")
            new_status: Target status string
            
        Returns:
            Dict with 'success', 'message', 'ot_id', 'new_status'
        """
        # Simulate 500ms network latency
        await asyncio.sleep(0.5)

        # Simulate 95% success / 5% failure
        success = random.random() < 0.95

        if success:
            return {
                "success": True,
                "message": f"Estado de {ot_id} actualizado a {new_status}",
                "ot_id": ot_id,
                "new_status": new_status,
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            # Simulate realistic error scenarios
            error_reasons = [
                "OT en estado no transicional",
                "Validación fallida en TELCOS",
                "Cuadrilla no disponible",
                "Recurso bloqueado por otro usuario",
            ]
            return {
                "success": False,
                "message": f"Error actualizando {ot_id}: {random.choice(error_reasons)}",
                "ot_id": ot_id,
                "error_code": random.choice(["INVALID_STATE", "VALIDATION_ERROR", "CONFLICT"]),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def get_documents_status(self, ot_id: str) -> Dict[str, Any]:
        """
        Mock GET /api/telcodrive/documents endpoint.
        
        Returns document checklist for PUBLICO projects with:
        - Random uploaded count (0-29)
        - List of pending documents
        - 500ms latency simulation
        
        Args:
            ot_id: OT external ID
            
        Returns:
            Dict with 'ot_id', 'documents' containing:
            - 'uploaded': Current count (0-29)
            - 'required': Always 29 for PUBLICO projects
            - 'pending': List of missing document names
        """
        # Simulate 500ms network latency
        await asyncio.sleep(0.5)

        # Random uploaded count (0-29)
        uploaded_count = random.randint(0, 29)
        required_count = 29

        # List of typical required documents for PUBLICO projects
        all_documents = [
            "Acta de entrega",
            "Fotografía fachada",
            "Fotografía punto interior",
            "Fotografía equipos",
            "Fotografía cableado",
            "Firma técnico responsable",
            "Firma cliente",
            "Prueba de conectividad",
            "Certificado fibra óptica",
            "Reporte de mediciones",
            "Comprobante de instalación",
            "Checklist de inspección",
            "Autorización cliente",
            "Declaración jurada",
            "Número de serie equipos",
            "Configuración ONT",
            "Contraseña WiFi",
            "Número de soporte técnico",
            "Fecha de activación",
            "Hoja de ruta",
            "Comprobante de pago",
            "Contrato firmado",
            "Cédula técnico",
            "Licencia de conducir",
            "Seguro responsabilidad civil",
            "Certificado capacitación",
            "Comprobante afiliación",
            "Carnet vigencia",
            "Documento identificación",
        ]

        # Randomly select which documents are pending
        pending_documents = random.sample(all_documents, required_count - uploaded_count)

        return {
            "ot_id": ot_id,
            "documents": {
                "uploaded": uploaded_count,
                "required": required_count,
                "pending": pending_documents,
                "completion_percentage": round((uploaded_count / required_count) * 100, 2),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check endpoint to verify mock service is operational.
        
        Returns:
            Dict with 'status', 'service', 'mode'
        """
        return {
            "status": "operational",
            "service": "MockApiService",
            "mode": "MOCK",
            "timestamp": datetime.utcnow().isoformat(),
        }

