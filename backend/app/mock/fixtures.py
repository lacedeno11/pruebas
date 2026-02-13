"""
Mock API fixture data for PEI Agentic Platform.
Provides realistic sample data for development and testing without requiring TELCOS API access.

Fixture data includes:
- 20 sample OTs with varied statuses, project types, and Ecuador coordinates
- 10 crews (5 PRINCIPAL, 5 RESERVA) with realistic Ecuadorian names
- 29 document types for PUBLIC projects with random completion status
- Helper functions for random selection
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# ============================================================================
# ECUADOR COORDINATES & REGIONS
# ============================================================================

# Major cities and regions in Ecuador with realistic coordinates
ECUADOR_REGIONS = {
    "Quito": {"lat": -0.22, "long": -78.51, "radius": 0.5},  # Capital, Sierra
    "Guayaquil": {"lat": -2.20, "long": -79.87, "radius": 0.5},  # Largest city, Costa
    "Cuenca": {"lat": -2.90, "long": -79.00, "radius": 0.4},  # Sierra
    "Manta": {"lat": -0.96, "long": -80.73, "radius": 0.3},  # Costa
    "Ambato": {"lat": -1.24, "long": -78.64, "radius": 0.3},  # Sierra
    "Machala": {"lat": -3.27, "long": -79.96, "radius": 0.3},  # Costa
    "Latacunga": {"lat": -0.93, "long": -78.61, "radius": 0.3},  # Sierra
    "Ibarra": {"lat": 0.35, "long": -77.12, "radius": 0.3},  # Northern Sierra
}


def _generate_coordinates(region: str) -> Tuple[float, float]:
    """Generate random coordinates within a region."""
    center = ECUADOR_REGIONS.get(region, ECUADOR_REGIONS["Quito"])
    lat = center["lat"] + random.uniform(-center["radius"], center["radius"])
    long = center["long"] + random.uniform(-center["radius"], center["radius"])
    return (round(lat, 4), round(long, 4))


# ============================================================================
# MOCK OTS
# ============================================================================

MOCK_OTS: List[Dict] = [
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001001",
        "status": "PREPLANIFICADA",
        "project_type": "PUBLICO",
        "cliente_id": "CLI-10001",
        "login_id": "LOGIN-10001",
        "lat": -0.22,
        "long": -78.51,
        "created_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001002",
        "status": "PLANIFICADA",
        "project_type": "PUBLICO",
        "cliente_id": "CLI-10002",
        "login_id": "LOGIN-10002",
        "lat": -0.25,
        "long": -78.48,
        "created_at": (datetime.utcnow() - timedelta(days=4)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=4)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001003",
        "status": "ASIGNADO_TAREA",
        "project_type": "PRIVADO",
        "cliente_id": "CLI-10003",
        "login_id": "LOGIN-10003",
        "lat": -0.20,
        "long": -78.55,
        "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001004",
        "status": "DETENIDA",
        "project_type": "PRIVADO",
        "cliente_id": "CLI-10004",
        "login_id": "LOGIN-10004",
        "lat": -0.18,
        "long": -78.53,
        "created_at": (datetime.utcnow() - timedelta(days=15)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001005",
        "status": "FINALIZADA",
        "project_type": "TERCERIZADO",
        "cliente_id": "CLI-10005",
        "login_id": "LOGIN-10005",
        "lat": -0.19,
        "long": -78.49,
        "created_at": (datetime.utcnow() - timedelta(days=10)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001006",
        "status": "PREPLANIFICADA",
        "project_type": "PUBLICO",
        "cliente_id": "CLI-10006",
        "login_id": "LOGIN-10006",
        "lat": -2.20,
        "long": -79.87,
        "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001007",
        "status": "PLANIFICADA",
        "project_type": "PRIVADO",
        "cliente_id": "CLI-10007",
        "login_id": "LOGIN-10007",
        "lat": -2.18,
        "long": -79.89,
        "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001008",
        "status": "ASIGNADO_TAREA",
        "project_type": "PUBLICO",
        "cliente_id": "CLI-10008",
        "login_id": "LOGIN-10008",
        "lat": -2.22,
        "long": -79.85,
        "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(hours=12)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001009",
        "status": "ANULADA",
        "project_type": "TERCERIZADO",
        "cliente_id": "CLI-10009",
        "login_id": "LOGIN-10009",
        "lat": -2.19,
        "long": -79.91,
        "created_at": (datetime.utcnow() - timedelta(days=20)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001010",
        "status": "PREPLANIFICADA",
        "project_type": "PRIVADO",
        "cliente_id": "CLI-10010",
        "login_id": "LOGIN-10010",
        "lat": -2.21,
        "long": -79.88,
        "created_at": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001011",
        "status": "PREPLANIFICADA",
        "project_type": "PUBLICO",
        "cliente_id": "CLI-10011",
        "login_id": "LOGIN-10011",
        "lat": -2.90,
        "long": -79.00,
        "created_at": (datetime.utcnow() - timedelta(days=6)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=6)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001012",
        "status": "PLANIFICADA",
        "project_type": "PRIVADO",
        "cliente_id": "CLI-10012",
        "login_id": "LOGIN-10012",
        "lat": -2.88,
        "long": -79.02,
        "created_at": (datetime.utcnow() - timedelta(days=4)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001013",
        "status": "ASIGNADO_TAREA",
        "project_type": "TERCERIZADO",
        "cliente_id": "CLI-10013",
        "login_id": "LOGIN-10013",
        "lat": -2.92,
        "long": -78.99,
        "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(hours=8)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001014",
        "status": "DETENIDA",
        "project_type": "PUBLICO",
        "cliente_id": "CLI-10014",
        "login_id": "LOGIN-10014",
        "lat": -2.89,
        "long": -79.01,
        "created_at": (datetime.utcnow() - timedelta(days=21)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001015",
        "status": "FINALIZADA",
        "project_type": "PRIVADO",
        "cliente_id": "CLI-10015",
        "login_id": "LOGIN-10015",
        "lat": -0.96,
        "long": -80.73,
        "created_at": (datetime.utcnow() - timedelta(days=8)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001016",
        "status": "PREPLANIFICADA",
        "project_type": "TERCERIZADO",
        "cliente_id": "CLI-10016",
        "login_id": "LOGIN-10016",
        "lat": -0.94,
        "long": -80.75,
        "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001017",
        "status": "PLANIFICADA",
        "project_type": "PUBLICO",
        "cliente_id": "CLI-10017",
        "login_id": "LOGIN-10017",
        "lat": -0.98,
        "long": -80.71,
        "created_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001018",
        "status": "ASIGNADO_TAREA",
        "project_type": "PRIVADO",
        "cliente_id": "CLI-10018",
        "login_id": "LOGIN-10018",
        "lat": -0.97,
        "long": -80.74,
        "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(hours=5)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001019",
        "status": "DETENIDA",
        "project_type": "PUBLICO",
        "cliente_id": "CLI-10019",
        "login_id": "LOGIN-10019",
        "lat": -0.95,
        "long": -80.76,
        "created_at": (datetime.utcnow() - timedelta(days=25)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
    {
        "id": str(uuid.uuid4()),
        "external_id": "OT-2024-001020",
        "status": "FINALIZADA",
        "project_type": "TERCERIZADO",
        "cliente_id": "CLI-10020",
        "login_id": "LOGIN-10020",
        "lat": -0.99,
        "long": -80.72,
        "created_at": (datetime.utcnow() - timedelta(days=12)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        "cuadrilla_id": None,
        "geo_error": False,
    },
]

# ============================================================================
# MOCK CUADRILLAS (CREWS)
# ============================================================================

CUADRILLA_NAMES = [
    # PRINCIPAL crews (main crews)
    "Cuadrilla Quito-01",
    "Cuadrilla Guayaquil-01",
    "Cuadrilla Cuenca-01",
    "Cuadrilla Manta-01",
    "Cuadrilla Ambato-01",
    # RESERVA crews (reserve/overflow crews)
    "Cuadrilla Quito-02 (Reserva)",
    "Cuadrilla Guayaquil-02 (Reserva)",
    "Cuadrilla Cuenca-02 (Reserva)",
    "Cuadrilla Manta-02 (Reserva)",
    "Cuadrilla Ambato-02 (Reserva)",
]

MOCK_CUADRILLAS: List[Dict] = [
    {
        "id": str(uuid.uuid4()),
        "name": CUADRILLA_NAMES[0],
        "type": "PRINCIPAL",
        "last_centroid_lat": -0.22,
        "last_centroid_long": -78.51,
        "daily_capacity": 10,
        "current_load": random.randint(3, 9),
        "active": True,
        "created_at": (datetime.utcnow() - timedelta(days=30)).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "name": CUADRILLA_NAMES[1],
        "type": "PRINCIPAL",
        "last_centroid_lat": -2.20,
        "last_centroid_long": -79.87,
        "daily_capacity": 10,
        "current_load": random.randint(4, 10),
        "active": True,
        "created_at": (datetime.utcnow() - timedelta(days=30)).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "name": CUADRILLA_NAMES[2],
        "type": "PRINCIPAL",
        "last_centroid_lat": -2.90,
        "last_centroid_long": -79.00,
        "daily_capacity": 12,
        "current_load": random.randint(5, 11),
        "active": True,
        "created_at": (datetime.utcnow() - timedelta(days=30)).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "name": CUADRILLA_NAMES[3],
        "type": "PRINCIPAL",
        "last_centroid_lat": -0.96,
        "last_centroid_long": -80.73,
        "daily_capacity": 8,
        "current_load": random.randint(2, 7),
        "active": True,
        "created_at": (datetime.utcnow() - timedelta(days=30)).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "name": CUADRILLA_NAMES[4],
        "type": "PRINCIPAL",
        "last_centroid_lat": -1.24,
        "last_centroid_long": -78.64,
        "daily_capacity": 10,
        "current_load": random.randint(3, 9),
        "active": True,
        "created_at": (datetime.utcnow() - timedelta(days=30)).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "name": CUADRILLA_NAMES[5],
        "type": "RESERVA",
        "last_centroid_lat": -0.20,
        "last_centroid_long": -78.54,
        "daily_capacity": 8,
        "current_load": random.randint(0, 3),
        "active": True,
        "created_at": (datetime.utcnow() - timedelta(days=20)).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "name": CUADRILLA_NAMES[6],
        "type": "RESERVA",
        "last_centroid_lat": -2.19,
        "last_centroid_long": -79.90,
        "daily_capacity": 8,
        "current_load": random.randint(0, 3),
        "active": True,
        "created_at": (datetime.utcnow() - timedelta(days=20)).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "name": CUADRILLA_NAMES[7],
        "type": "RESERVA",
        "last_centroid_lat": -2.91,
        "last_centroid_long": -79.01,
        "daily_capacity": 10,
        "current_load": random.randint(0, 4),
        "active": True,
        "created_at": (datetime.utcnow() - timedelta(days=20)).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "name": CUADRILLA_NAMES[8],
        "type": "RESERVA",
        "last_centroid_lat": -0.96,
        "last_centroid_long": -80.73,
        "daily_capacity": 6,
        "current_load": random.randint(0, 2),
        "active": True,
        "created_at": (datetime.utcnow() - timedelta(days=20)).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "name": CUADRILLA_NAMES[9],
        "type": "RESERVA",
        "last_centroid_lat": -1.24,
        "last_centroid_long": -78.64,
        "daily_capacity": 8,
        "current_load": random.randint(0, 3),
        "active": True,
        "created_at": (datetime.utcnow() - timedelta(days=20)).isoformat(),
    },
]

# ============================================================================
# MOCK DOCUMENTS (FOR PUBLIC PROJECTS)
# ============================================================================

MOCK_DOCUMENTS: List[str] = [
    "Inspección inicial",
    "Presupuesto aprobado",
    "Permisos de acceso",
    "Fotografías antes",
    "Instalación de ductos",
    "Tendido de fibra óptica",
    "Conexión de equipos",
    "Pruebas de conectividad",
    "Fotografías después",
    "Certificado de instalación",
    "Firma del cliente",
    "Reporte técnico",
    "Checklist de equipos",
    "Configuración de routers",
    "Pruebas de velocidad",
    "Documentación de SNs",
    "Acta de entrega",
    "Facturación",
    "Garantía registrada",
    "Capacitación del usuario",
    "Manual de usuario entregado",
    "Contacto de soporte registrado",
    "Inspección final",
    "Aprobación de gerencia",
    "Archivo fotográfico completo",
    "Video de instalación",
    "Ruta GPS registrada",
    "Formulario de satisfacción",
    "Cierre administrativo",
]


def get_document_checklist() -> Dict[str, bool]:
    """
    Generate a random document checklist for PUBLIC projects.
    Returns dict mapping document name to completion status.
    """
    return {doc: random.random() > 0.2 for doc in MOCK_DOCUMENTS}  # 80% completion rate


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_random_ot() -> Dict:
    """
    Get a random OT from the mock data.
    
    Returns:
        dict: A copy of a random OT from MOCK_OTS
    
    Example:
        >>> ot = get_random_ot()
        >>> print(ot["external_id"])
        "OT-2024-001005"
    """
    return MOCK_OTS[random.randint(0, len(MOCK_OTS) - 1)].copy()


def get_random_cuadrilla() -> Dict:
    """
    Get a random Cuadrilla from the mock data.
    
    Returns:
        dict: A copy of a random Cuadrilla from MOCK_CUADRILLAS
    
    Example:
        >>> crew = get_random_cuadrilla()
        >>> print(crew["name"])
        "Cuadrilla Quito-01"
    """
    return MOCK_CUADRILLAS[random.randint(0, len(MOCK_CUADRILLAS) - 1)].copy()


def get_random_ots(count: int = 5) -> List[Dict]:
    """
    Get multiple random OTs.
    
    Args:
        count: Number of OTs to return
        
    Returns:
        list: List of random OTs (may contain duplicates)
        
    Example:
        >>> ots = get_random_ots(3)
        >>> len(ots)
        3
    """
    return [get_random_ot() for _ in range(count)]


def get_random_cuadrillas(count: int = 3) -> List[Dict]:
    """
    Get multiple random Cuadrillas.
    
    Args:
        count: Number of Cuadrillas to return
        
    Returns:
        list: List of random Cuadrillas (may contain duplicates)
        
    Example:
        >>> crews = get_random_cuadrillas(2)
        >>> len(crews)
        2
    """
    return [get_random_cuadrilla() for _ in range(count)]


def filter_ots_by_status(status: Optional[str] = None) -> List[Dict]:
    """
    Filter OTs by status.
    
    Args:
        status: Status to filter by (e.g., "PREPLANIFICADA"), or None for all
        
    Returns:
        list: Filtered list of OT copies
        
    Example:
        >>> preplanificadas = filter_ots_by_status("PREPLANIFICADA")
        >>> all(ot["status"] == "PREPLANIFICADA" for ot in preplanificadas)
        True
    """
    if status is None:
        return [ot.copy() for ot in MOCK_OTS]
    return [ot.copy() for ot in MOCK_OTS if ot["status"] == status]


def filter_ots_by_project_type(project_type: Optional[str] = None) -> List[Dict]:
    """
    Filter OTs by project type.
    
    Args:
        project_type: Project type to filter by (PUBLICO, PRIVADO, TERCERIZADO), or None for all
        
    Returns:
        list: Filtered list of OT copies
        
    Example:
        >>> public_ots = filter_ots_by_project_type("PUBLICO")
        >>> all(ot["project_type"] == "PUBLICO" for ot in public_ots)
        True
    """
    if project_type is None:
        return [ot.copy() for ot in MOCK_OTS]
    return [ot.copy() for ot in MOCK_OTS if ot["project_type"] == project_type]


def get_ot_by_external_id(external_id: str) -> Optional[Dict]:
    """
    Get an OT by its external_id.
    
    Args:
        external_id: External ID to search for
        
    Returns:
        dict: OT if found, None otherwise
        
    Example:
        >>> ot = get_ot_by_external_id("OT-2024-001005")
        >>> ot["external_id"]
        "OT-2024-001005"
    """
    for ot in MOCK_OTS:
        if ot["external_id"] == external_id:
            return ot.copy()
    return None


def get_cuadrilla_by_name(name: str) -> Optional[Dict]:
    """
    Get a Cuadrilla by its name.
    
    Args:
        name: Crew name to search for
        
    Returns:
        dict: Cuadrilla if found, None otherwise
        
    Example:
        >>> crew = get_cuadrilla_by_name("Cuadrilla Quito-01")
        >>> crew["type"]
        "PRINCIPAL"
    """
    for crew in MOCK_CUADRILLAS:
        if crew["name"] == name:
            return crew.copy()
    return None


def get_cuadrillas_by_type(crew_type: Optional[str] = None) -> List[Dict]:
    """
    Get Cuadrillas filtered by type.
    
    Args:
        crew_type: Type to filter by (PRINCIPAL, RESERVA), or None for all
        
    Returns:
        list: Filtered list of Cuadrilla copies
        
    Example:
        >>> principal_crews = get_cuadrillas_by_type("PRINCIPAL")
        >>> len(principal_crews)
        5
    """
    if crew_type is None:
        return [crew.copy() for crew in MOCK_CUADRILLAS]
    return [crew.copy() for crew in MOCK_CUADRILLAS if crew["type"] == crew_type]


def count_ots_by_status() -> Dict[str, int]:
    """
    Count OTs by status.
    
    Returns:
        dict: Mapping of status to count
        
    Example:
        >>> counts = count_ots_by_status()
        >>> counts["PREPLANIFICADA"]
        4
    """
    counts: Dict[str, int] = {}
    for ot in MOCK_OTS:
        status = ot["status"]
        counts[status] = counts.get(status, 0) + 1
    return counts


def count_ots_by_project_type() -> Dict[str, int]:
    """
    Count OTs by project type.
    
    Returns:
        dict: Mapping of project type to count
        
    Example:
        >>> counts = count_ots_by_project_type()
        >>> counts["PUBLICO"]
        8
    """
    counts: Dict[str, int] = {}
    for ot in MOCK_OTS:
        ptype = ot["project_type"]
        counts[ptype] = counts.get(ptype, 0) + 1
    return counts


# ============================================================================
# FIXTURE DATA SUMMARY
# ============================================================================

FIXTURE_SUMMARY = {
    "total_ots": len(MOCK_OTS),
    "total_cuadrillas": len(MOCK_CUADRILLAS),
    "total_documents": len(MOCK_DOCUMENTS),
    "principal_crews": len([c for c in MOCK_CUADRILLAS if c["type"] == "PRINCIPAL"]),
    "reserva_crews": len([c for c in MOCK_CUADRILLAS if c["type"] == "RESERVA"]),
    "ots_by_status": count_ots_by_status(),
    "ots_by_project_type": count_ots_by_project_type(),
}

