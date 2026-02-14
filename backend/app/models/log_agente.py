"""
SQLAlchemy LogAgente model for PEI Agentic Platform.
Represents logs from LangGraph agent nodes for debugging and tracing.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    UUID,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.ot import OT


# ============================================================================
# LOG AGENTE MODEL
# ============================================================================


class LogAgente(Base):
    """
    Agent Log model for LangGraph agent operations.
    
    Records all agent actions and decisions for debugging, tracing, and analytics.
    Each log entry represents one action by one agent, linked to an OT if relevant.
    
    Attributes:
        id: UUID primary key
        ot_id: Foreign key to OT (nullable, may be system-level log)
        agente_name: Name of agent that performed action (Router, OTS, Planificacion, etc.)
        accion: Description of action performed (e.g., CLASSIFY_INTENT, ASSIGN_OT)
        resultado: Result/status of action (SUCCESS, ERROR, VALIDATION_FAILED, etc.)
        raw_llm_response: Raw JSON response from LLM (nullable)
        timestamp: When action occurred
        correlation_id: Unique ID for request tracing across multiple agents
        metadata: Additional context as JSON (intent, validation details, etc.)
    """

    __tablename__ = "logs_agentes"

    # ========================================================================
    # PRIMARY KEY
    # ========================================================================

    id: Mapped[str] = mapped_column(
        UUID,
        primary_key=True,
        default=lambda: str(__import__("uuid").uuid4()),
        doc="Unique UUID identifier",
    )

    # ========================================================================
    # FOREIGN KEYS
    # ========================================================================

    ot_id: Mapped[Optional[str]] = mapped_column(
        UUID,
        ForeignKey("ots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Associated OT (nullable for system logs)",
    )

    # ========================================================================
    # AGENT ACTION FIELDS
    # ========================================================================

    agente_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Agent that performed action (Router, OTS, Planificacion, Gobernanza, Comunicacion)",
    )

    accion: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Action description (e.g., CLASSIFY_INTENT, ASSIGN_OT, VALIDATE_STATUS)",
    )

    resultado: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Result/status (SUCCESS, ERROR, VALIDATION_FAILED, etc.)",
    )

    # ========================================================================
    # LLM & RESPONSE DATA
    # ========================================================================

    raw_llm_response: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Raw JSON response from LLM (for debugging)",
    )

    # ========================================================================
    # TIMESTAMPS & TRACING
    # ========================================================================

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        index=True,
        doc="When action occurred",
    )

    correlation_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        doc="Request correlation ID for multi-agent tracing",
    )

    # ========================================================================
    # CONTEXT & METADATA
    # ========================================================================

    metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        doc="Additional context (intent, validation details, etc.)",
    )

    # ========================================================================
    # RELATIONSHIPS
    # ========================================================================

    ot: Mapped[Optional["OT"]] = relationship(
        "OT",
        back_populates="logs_agentes",
        foreign_keys=[ot_id],
        doc="Associated OT if this log is OT-specific",
    )

    # ========================================================================
    # COMPOSITE INDEXES
    # ========================================================================

    __table_args__ = (
        # Index for finding logs by agent and OT
        Index("ix_log_agente_ot", "agente_name", "ot_id"),
        # Index for finding logs by correlation ID (request tracing)
        Index("ix_log_correlation_timestamp", "correlation_id", "timestamp"),
        # Index for finding logs by agent and result
        Index("ix_log_agente_resultado", "agente_name", "resultado"),
        # Index for time range queries
        Index("ix_log_timestamp", "timestamp"),
    )

    # ========================================================================
    # STRING REPRESENTATION
    # ========================================================================

    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"<LogAgente(id={self.id}, agente_name={self.agente_name}, "
            f"accion={self.accion}, resultado={self.resultado}, "
            f"ot_id={self.ot_id}, correlation_id={self.correlation_id})>"
        )

    def __str__(self) -> str:
        """Human-readable string."""
        ot_info = f" [OT: {self.ot_id}]" if self.ot_id else ""
        return (
            f"{self.agente_name}: {self.accion} → {self.resultado}{ot_info} "
            f"@ {self.timestamp.isoformat()}"
        )

    # ========================================================================
    # COMPUTED PROPERTIES
    # ========================================================================

    @property
    def is_success(self) -> bool:
        """Check if action was successful."""
        return self.resultado == "SUCCESS"

    @property
    def is_error(self) -> bool:
        """Check if action failed."""
        return self.resultado in ("ERROR", "FAILED", "EXCEPTION")

    @property
    def is_system_log(self) -> bool:
        """Check if this is a system-level log (no OT)."""
        return self.ot_id is None

    @property
    def agent_type(self) -> str:
        """Get agent type (first part of agent name)."""
        # e.g., "RouterAgent" -> "Router"
        return self.agente_name.replace("Agent", "").strip()

    @property
    def has_llm_response(self) -> bool:
        """Check if raw LLM response is available."""
        return self.raw_llm_response is not None

    # ========================================================================
    # METHODS FOR FILTERING & QUERIES
    # ========================================================================

    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """
        Get metadata value by key.
        
        Args:
            key: Metadata key
            default: Default value if key not found
            
        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)

    def set_metadata_value(self, key: str, value: Any) -> None:
        """
        Set metadata value by key.
        
        Args:
            key: Metadata key
            value: Value to set
        """
        self.metadata[key] = value

    def add_metadata(self, data: Dict[str, Any]) -> None:
        """
        Add multiple metadata values.
        
        Args:
            data: Dictionary of key-value pairs to add
        """
        self.metadata.update(data)

    # ========================================================================
    # METHODS FOR LOG CLASSIFICATION
    # ========================================================================

    def is_router_log(self) -> bool:
        """Check if log is from RouterAgent."""
        return "Router" in self.agente_name

    def is_ots_log(self) -> bool:
        """Check if log is from OTSAgent."""
        return "OTS" in self.agente_name

    def is_planning_log(self) -> bool:
        """Check if log is from PlanificacionAgent."""
        return "Planificacion" in self.agente_name

    def is_governance_log(self) -> bool:
        """Check if log is from GobernanzaAgent."""
        return "Gobernanza" in self.agente_name

    def is_communication_log(self) -> bool:
        """Check if log is from ComunicacionAgent."""
        return "Comunicacion" in self.agente_name

    # ========================================================================
    # METHODS FOR ACTION ANALYSIS
    # ========================================================================

    def get_action_type(self) -> str:
        """
        Get high-level action type from accion.
        
        Returns:
            str: Action type (CLASSIFY, INGEST, ASSIGN, VALIDATE, NOTIFY, etc.)
        """
        # Extract first word/component from accion
        parts = self.accion.split("_")
        if parts:
            return parts[0]
        return self.accion

    def is_classification_action(self) -> bool:
        """Check if action is intent classification."""
        return "CLASSIFY" in self.accion or "ROUTE" in self.accion

    def is_ingestion_action(self) -> bool:
        """Check if action is OT ingestion."""
        return "INGEST" in self.accion or "IMPORT" in self.accion

    def is_assignment_action(self) -> bool:
        """Check if action is OT assignment."""
        return "ASSIGN" in self.accion or "PLAN" in self.accion

    def is_validation_action(self) -> bool:
        """Check if action is validation."""
        return "VALIDATE" in self.accion or "CHECK" in self.accion

    def is_notification_action(self) -> bool:
        """Check if action is notification."""
        return "NOTIFY" in self.accion or "ALERT" in self.accion or "SEND" in self.accion

    # ========================================================================
    # DATA CONVERSION METHODS
    # ========================================================================

    def to_dict(self) -> dict:
        """
        Convert LogAgente to dictionary for API responses.
        
        Returns:
            dict: Log data
        """
        return {
            "id": str(self.id),
            "ot_id": str(self.ot_id) if self.ot_id else None,
            "agente_name": self.agente_name,
            "accion": self.accion,
            "resultado": self.resultado,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
            "is_success": self.is_success,
            "is_system_log": self.is_system_log,
        }

    def to_dict_with_response(self) -> dict:
        """
        Convert LogAgente to dictionary including raw LLM response.
        
        Returns:
            dict: Log data with LLM response
        """
        data = self.to_dict()
        if self.raw_llm_response:
            import json

            try:
                data["raw_llm_response"] = json.loads(self.raw_llm_response)
            except json.JSONDecodeError:
                data["raw_llm_response"] = self.raw_llm_response
        return data

    # ========================================================================
    # TRACING & DEBUGGING METHODS
    # ========================================================================

    def get_trace_info(self) -> dict:
        """
        Get information useful for request tracing.
        
        Returns:
            dict: Trace information
        """
        return {
            "correlation_id": self.correlation_id,
            "agent": self.agente_name,
            "action": self.accion,
            "result": self.resultado,
            "timestamp": self.timestamp.isoformat(),
            "ot_id": str(self.ot_id) if self.ot_id else None,
        }

    def get_summary(self) -> str:
        """
        Get one-line summary for logs view.
        
        Returns:
            str: Summary text
        """
        ot_info = f" [{self.ot_id}]" if self.ot_id else ""
        return f"{self.agente_name}: {self.accion} → {self.resultado}{ot_info}"

    # ========================================================================
    # VALIDATION METHODS
    # ========================================================================

    def validate(self) -> tuple[bool, str]:
        """
        Validate log entry consistency.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not self.agente_name:
            return False, "Agent name is required"

        if not self.accion:
            return False, "Action is required"

        if not self.resultado:
            return False, "Result is required"

        if not self.correlation_id:
            return False, "Correlation ID is required"

        if self.timestamp is None:
            return False, "Timestamp is required"

        return True, ""

    # ========================================================================
    # STATIC METHODS FOR LOG CREATION
    # ========================================================================

    @staticmethod
    def create_success_log(
        agente_name: str,
        accion: str,
        correlation_id: str,
        ot_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        raw_llm_response: Optional[str] = None,
    ) -> "LogAgente":
        """
        Create a success log entry.
        
        Args:
            agente_name: Agent name
            accion: Action description
            correlation_id: Request correlation ID
            ot_id: Associated OT ID
            metadata: Additional context
            raw_llm_response: LLM response JSON
            
        Returns:
            LogAgente: New log entry
        """
        return LogAgente(
            agente_name=agente_name,
            accion=accion,
            resultado="SUCCESS",
            correlation_id=correlation_id,
            ot_id=ot_id,
            metadata=metadata or {},
            raw_llm_response=raw_llm_response,
        )

    @staticmethod
    def create_error_log(
        agente_name: str,
        accion: str,
        error_message: str,
        correlation_id: str,
        ot_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "LogAgente":
        """
        Create an error log entry.
        
        Args:
            agente_name: Agent name
            accion: Action description
            error_message: Error message
            correlation_id: Request correlation ID
            ot_id: Associated OT ID
            metadata: Additional context
            
        Returns:
            LogAgente: New log entry
        """
        meta = metadata or {}
        meta["error"] = error_message
        return LogAgente(
            agente_name=agente_name,
            accion=accion,
            resultado="ERROR",
            correlation_id=correlation_id,
            ot_id=ot_id,
            metadata=meta,
        )

    @staticmethod
    def create_validation_log(
        agente_name: str,
        accion: str,
        is_valid: bool,
        correlation_id: str,
        details: Optional[Dict[str, Any]] = None,
        ot_id: Optional[str] = None,
    ) -> "LogAgente":
        """
        Create a validation log entry.
        
        Args:
            agente_name: Agent name
            accion: Action description
            is_valid: Whether validation passed
            correlation_id: Request correlation ID
            details: Validation details
            ot_id: Associated OT ID
            
        Returns:
            LogAgente: New log entry
        """
        resultado = "SUCCESS" if is_valid else "VALIDATION_FAILED"
        meta = details or {}
        meta["is_valid"] = is_valid
        return LogAgente(
            agente_name=agente_name,
            accion=accion,
            resultado=resultado,
            correlation_id=correlation_id,
            ot_id=ot_id,
            metadata=meta,
        )

