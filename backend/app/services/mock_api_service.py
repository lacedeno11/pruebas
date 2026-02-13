import asyncio
import random
from datetime import datetime
from typing import List
from uuid import uuid4

from backend.app.schemas.ot_schema import OTResponse, OTStatus, ProjectType


class MockApiService:
    """Mock API Service for simulating TELCOS API responses during development."""

    @staticmethod
    async def get_ots() -> List[OTResponse]:
        """
        Simulate fetching OTs from TELCOS API.

        Returns a list of 20 mock OTs with varying:
        - project_types (PUBLICO, PRIVADO, TERCERIZADO)
        - coordinates within Ecuador bounds (lat: -2 to 1, long: -81 to -75)
        - statuses
        - cliente_id and login_id

        Adds 500ms latency to simulate network delay.
        """
        # Simulate network latency
        await asyncio.sleep(0.5)

        # Ecuador geographical bounds
        lat_min, lat_max = -2.0, 1.0
        long_min, long_max = -81.0, -75.0

        # Sample cliente and login IDs
        clientes = [f"CLI-{i:04d}" for i in range(1, 21)]
        logins = [f"LGN-{i:04d}" for i in range(1, 21)]

        # All possible statuses for variation
        statuses = [
            OTStatus.PREPLANIFICADA,
            OTStatus.PLANIFICADA,
            OTStatus.ASIGNADO_TAREA,
            OTStatus.DETENIDA,
            OTStatus.FINALIZADA,
        ]

        project_types = [
            ProjectType.PUBLICO,
            ProjectType.PRIVADO,
            ProjectType.TERCERIZADO,
        ]

        # Generate 20 mock OTs
        ots = []
        for i in range(20):
            lat = random.uniform(lat_min, lat_max)
            long = random.uniform(long_min, long_max)

            ot = OTResponse(
                id=str(uuid4()),
                external_id=f"OT-EXT-{i+1:05d}",
                status=random.choice(statuses),
                project_type=random.choice(project_types),
                lat=lat,
                long=long,
                cliente_id=clientes[i % len(clientes)],
                login_id=logins[i % len(logins)],
                cuadrilla_id=None,
                error_geo=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            ots.append(ot)

        return ots

    @staticmethod
    async def update_status(ot_id: str, new_status: str) -> dict:
        """
        Simulate updating OT status in TELCOS API.

        Simulates:
        - 90% success rate
        - 10% random failures with error messages
        - 500ms latency

        Args:
            ot_id: The ID of the OT to update
            new_status: The new status value

        Returns:
            dict with success status and message
        """
        await asyncio.sleep(0.5)

        success_chance = random.random()

        if success_chance < 0.9:
            # 90% success
            timestamp = datetime.utcnow().isoformat()
            print(f"[{timestamp}] MockAPI: Updated OT {ot_id} to status {new_status}")
            return {
                "success": True,
                "message": f"Status updated to {new_status}",
                "ot_id": ot_id,
                "timestamp": timestamp,
            }
        else:
            # 10% failure
            error_messages = [
                "Connection timeout",
                "Server temporarily unavailable",
                "Invalid status transition",
                "OT not found",
                "Permission denied",
            ]
            error_msg = random.choice(error_messages)
            timestamp = datetime.utcnow().isoformat()
            print(
                f"[{timestamp}] MockAPI: Failed to update OT {ot_id} - {error_msg}"
            )
            return {
                "success": False,
                "message": error_msg,
                "ot_id": ot_id,
                "timestamp": timestamp,
            }

    @staticmethod
    async def get_documents_status(ot_id: str, project_type: str) -> dict:
        """
        Simulate fetching TelcoDrive document status.

        For PUBLICO projects:
        - Returns random document count between 15-29
        - Includes document names and upload timestamps

        For other project types:
        - Returns 0 documents

        Args:
            ot_id: The ID of the OT
            project_type: The project type (PUBLICO, PRIVADO, TERCERIZADO)

        Returns:
            dict with document count, names, and timestamps
        """
        await asyncio.sleep(0.5)

        if project_type == ProjectType.PUBLICO or project_type == "PUBLICO":
            doc_count = random.randint(15, 29)

            document_names = [
                "Acta de inicio",
                "Autorización cliente",
                "Plano de ubicación",
                "Especificaciones técnicas",
                "Material de instalación",
                "Fotografías before",
                "Prueba de continuidad",
                "Prueba de aislamiento",
                "Mediciones de potencia",
                "Configuración de equipo",
                "Prueba de servicios",
                "Fotografías after",
                "Firmas de aceptación",
                "Acta de finalización",
                "Reporte técnico",
                "Certificado de calidad",
                "Factura de servicios",
                "Anexo fotográfico 1",
                "Anexo fotográfico 2",
                "Datos de contacto cliente",
                "Datos de contacto técnico",
                "Hoja de seguridad",
                "Conformidad de trabajo",
                "Documentación de cambios",
                "Feedback del cliente",
                "Comprobante de pago",
                "Acta de entrega",
                "Registro de garantía",
                "Código QR de seguimiento",
            ]

            documents = []
            for i in range(doc_count):
                documents.append(
                    {
                        "name": document_names[i % len(document_names)],
                        "uploaded_at": datetime.utcnow().isoformat(),
                    }
                )

            return {
                "ot_id": ot_id,
                "document_count": doc_count,
                "required_count": 29,
                "documents": documents,
                "is_complete": doc_count >= 29,
            }
        else:
            # Non-PUBLICO projects don't require documents
            return {
                "ot_id": ot_id,
                "document_count": 0,
                "required_count": 0,
                "documents": [],
                "is_complete": True,
            }

