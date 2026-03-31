"""
LogAgente SQLAlchemy model.

Represents agent action logs in the DERCAS system for auditing and debugging:
- Identification: id (UUID), agente_name (string)
- Context: ot_id (FK nullable, for OT-specific actions)
- Action tracking: accion (action type), resultado (success/error/warning)
- Debug info: raw_llm_response (Text), metadata (JSON)
- Timestamps: created_at for chronological queries
- Relationships: OrdenTrabajo (many-to-one, nullable)
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class LogAgente(Base):
    """
    LogAgente (Agent Action Log) model.
    
    Tracks all agent operations for auditing, debugging, and monitoring.
    Each log entry records:
    - Which agent performed an action (agente_name)
    - What action was performed (accion)
    - What the result was (resultado)
    - Optional reference to an OT (ot_id, nullable for job-level logs)
    - Raw LLM response for debugging (raw_llm_response, nullable)
    - Additional metadata as JSON (metadata, nullable)
    - Timestamp for chronological ordering
    
    Relationships:
    - ot: Many LogAgente entries belong to one OrdenTrabajo
    
    Table name: log_agente
    """
    
    __tablename__ = "log_agente"
    
    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        index=True,
        comment="Unique identifier (UUID) for the log entry"
    )
    
    # OT Reference (optional, for OT-specific logs)
    ot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("orden_trabajo.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK to OrdenTrabajo (nullable for job-level logs)"
    )
    
    # Agent Name - which agent performed this action
    agente_name = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Name of the agent that performed this action (e.g., 'RouterAgent', 'OTSAgent', 'PlanificacionAgent')"
    )
    
    # Action Type - what action was performed
    accion = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Action type (e.g., 'OT_INGESTION', 'PLANNING_PHASE_1', 'GOVERNANCE_CHECK', 'ALERT_SENT')"
    )
    
    # Result - success, error, warning, etc.
    resultado = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Result status: 'success', 'error', 'warning', or custom status code"
    )
    
    # Raw LLM Response - for debugging LLM-based decisions
    raw_llm_response = Column(
        Text,
        nullable=True,
        comment="Raw response from LLM (for debugging agent reasoning)"
    )
    
    # Metadata - additional context as JSON
    metadata = Column(
        JSON,
        nullable=True,
        comment="Additional metadata (error details, counts, parameters, etc.)"
    )
    
    # Timestamp for audit trail
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Timestamp when this log entry was created"
    )
    
    # Relationships
    ot = relationship(
        "OrdenTrabajo",
        back_populates="logs",
        foreign_keys=[ot_id],
        lazy="select",
        comment="Many-to-one relationship: LogAgente belongs to OrdenTrabajo"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_agente_name_created_at', 'agente_name', 'created_at'),
        Index('idx_accion_resultado_created_at', 'accion', 'resultado', 'created_at'),
        Index('idx_ot_id_created_at', 'ot_id', 'created_at'),
    )
    
    def __repr__(self) -> str:
        """String representation of LogAgente instance."""
        return (
            f"LogAgente(id={self.id}, agente_name={self.agente_name}, "
            f"accion={self.accion}, resultado={self.resultado}, ot_id={self.ot_id})"
        )
    
    def __str__(self) -> str:
        """User-friendly string representation."""
        ot_info = f"OT: {self.ot_id}" if self.ot_id else "Job-level"
        return (
            f"[{self.created_at.isoformat()}] {self.agente_name} - "
            f"{self.accion} ({self.resultado}) - {ot_info}"
        )
    
    def is_success(self) -> bool:
        """
        Check if this log entry represents a successful action.
        
        Returns:
            bool: True if resultado is 'success' or similar positive status
        """
        success_statuses = ['success', 'completed', 'ok', 'true']
        return self.resultado.lower() in success_statuses
    
    def is_error(self) -> bool:
        """
        Check if this log entry represents an error.
        
        Returns:
            bool: True if resultado is 'error' or similar negative status
        """
        error_statuses = ['error', 'failed', 'exception', 'false']
        return self.resultado.lower() in error_statuses
    
    def is_warning(self) -> bool:
        """
        Check if this log entry represents a warning.
        
        Returns:
            bool: True if resultado is 'warning' or similar cautionary status
        """
        warning_statuses = ['warning', 'warn', 'caution', 'attention']
        return self.resultado.lower() in warning_statuses
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata as a dictionary.
        
        Returns:
            dict: Metadata dictionary, empty dict if None
        """
        return self.metadata or {}
    
    def set_metadata(self, metadata: Optional[Dict[str, Any]]) -> None:
        """
        Set metadata from a dictionary.
        
        Args:
            metadata: Dictionary to store as metadata
        """
        self.metadata = metadata
    
    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add a single metadata key-value pair.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value
    
    def get_error_message(self) -> Optional[str]:
        """
        Extract error message from metadata if available.
        
        Returns:
            str: Error message from metadata, or None if not available
        """
        metadata = self.get_metadata()
        return metadata.get('error_message') or metadata.get('error')
    
    def get_duration_ms(self) -> Optional[float]:
        """
        Extract execution duration from metadata if available.
        
        Returns:
            float: Duration in milliseconds, or None if not available
        """
        metadata = self.get_metadata()
        duration = metadata.get('duration_ms') or metadata.get('duration')
        if duration is not None:
            try:
                return float(duration)
            except (TypeError, ValueError):
                return None
        return None
    
    def format_for_display(self) -> Dict[str, Any]:
        """
        Format log entry for display in UI/API responses.
        
        Returns:
            dict: Formatted log entry with human-readable fields
        """
        return {
            'id': str(self.id),
            'ot_id': str(self.ot_id) if self.ot_id else None,
            'agente_name': self.agente_name,
            'accion': self.accion,
            'resultado': self.resultado,
            'created_at': self.created_at.isoformat(),
            'is_success': self.is_success(),
            'is_error': self.is_error(),
            'is_warning': self.is_warning(),
            'metadata': self.get_metadata(),
        }


# Common Agent Names (reference)
AGENT_NAMES = {
    'ROUTER': 'RouterAgent',
    'OTS': 'OTSAgent',
    'PLANIFICACION': 'PlanificacionAgent',
    'GOBERNANZA': 'GobernanzaAgent',
    'COMUNICACION': 'ComunicacionAgent',
}

# Common Action Types (reference)
ACTION_TYPES = {
    # OTSAgent actions
    'OT_SYNC': 'OT_SYNC',
    'OT_INGESTION': 'OT_INGESTION',
    'OT_VALIDATION': 'OT_VALIDATION',
    
    # PlanificacionAgent actions
    'PLANNING_PHASE_1': 'PLANNING_PHASE_1',
    'PLANNING_PHASE_2': 'PLANNING_PHASE_2',
    'PLANNING_PHASE_3': 'PLANNING_PHASE_3',
    'ASSIGNMENT_CREATED': 'ASSIGNMENT_CREATED',
    
    # GobernanzaAgent actions
    'GOVERNANCE_CHECK': 'GOVERNANCE_CHECK',
    'INACTIVITY_ALERT': 'INACTIVITY_ALERT',
    'AUTO_CANCEL': 'AUTO_CANCEL',
    'DOCUMENT_CHECK': 'DOCUMENT_CHECK',
    
    # ComunicacionAgent actions
    'ALERT_SENT': 'ALERT_SENT',
    'EMAIL_SENT': 'EMAIL_SENT',
    'TELEGRAM_SENT': 'TELEGRAM_SENT',
    
    # RouterAgent actions
    'INTENT_CLASSIFICATION': 'INTENT_CLASSIFICATION',
    'ROUTE_DECISION': 'ROUTE_DECISION',
    
    # Scheduled job actions
    'SCHEDULED_JOB': 'SCHEDULED_JOB',
}

# Common Result Statuses (reference)
RESULT_STATUSES = {
    'SUCCESS': 'success',
    'ERROR': 'error',
    'WARNING': 'warning',
    'COMPLETED': 'completed',
    'FAILED': 'failed',
    'SKIPPED': 'skipped',
    'PENDING': 'pending',
}

