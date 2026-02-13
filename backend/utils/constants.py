"""Constants and enumerations for the PEI Platform"""

# OT Status enum
OT_STATUS = {
    "PREPLANIFICADA": "PREPLANIFICADA",
    "PLANIFICADA": "PLANIFICADA",
    "ASIGNADO_TAREA": "ASIGNADO_TAREA",
    "DETENIDA": "DETENIDA",
    "ANULADA": "ANULADA",
    "FINALIZADA": "FINALIZADA",
    "ERROR_GEO": "ERROR_GEO",  # Special status for geo-validation failures
}

# Project Types
PROJECT_TYPES = {
    "PUBLICO": "PUBLICO",
    "PRIVADO": "PRIVADO",
    "TERCERIZADO": "TERCERIZADO",
}

# Cuadrilla Types
CUADRILLA_TYPES = {
    "PRINCIPAL": "Principal",
    "RESERVA": "Reserva",
}

# Business Rules Constants
MAX_DISTANCE_KM = 10.0
ALERT_DAYS = [20, 25, 29]
AUTO_CANCEL_DAYS = 30
INACTIVITY_ALERT_HOURS = 48
MOCK_LATENCY_MS = 500
DOCUMENT_REQUIREMENT_PUBLICO = 29

# Alert Types
ALERT_TYPES = {
    "WARNING_20": "WARNING_20",
    "WARNING_25": "WARNING_25",
    "FINAL_WARNING": "FINAL_WARNING",
    "AUTO_CANCELLED": "AUTO_CANCELLED",
    "INACTIVITY_48H": "INACTIVITY_48H",
}

# Channel Types for Notifications
NOTIFICATION_CHANNELS = {
    "EMAIL": "EMAIL",
    "TELEGRAM": "TELEGRAM",
}

# OT Status Transitions (allowed transitions)
ALLOWED_TRANSITIONS = {
    "PREPLANIFICADA": ["PLANIFICADA", "ANULADA"],
    "PLANIFICADA": ["ASIGNADO_TAREA", "DETENIDA", "ANULADA"],
    "ASIGNADO_TAREA": ["DETENIDA", "FINALIZADA", "ANULADA"],
    "DETENIDA": ["PLANIFICADA", "ANULADA"],
    "ANULADA": [],  # Terminal state
    "FINALIZADA": [],  # Terminal state
    "ERROR_GEO": ["PREPLANIFICADA", "ANULADA"],
}

# Status by Priority
STATUS_PRIORITY = {
    "PREPLANIFICADA": 5,
    "PLANIFICADA": 4,
    "ASIGNADO_TAREA": 3,
    "DETENIDA": 2,
    "FINALIZADA": 1,
    "ANULADA": 0,
}

# Project Type Priority
PROJECT_TYPE_PRIORITY = {
    "PUBLICO": 3,
    "PRIVADO": 2,
    "TERCERIZADO": 1,
}

