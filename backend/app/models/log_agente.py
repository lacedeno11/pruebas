"""
LogAgente (Agent Action Log) SQLAlchemy Model

Represents a log entry for agent actions in the DERCAS PEI system.

Agent Types:
    ROUTER: Request routing and intent classification
    OTS: OT ingestion from external APIs
    PLANIFICACION: Crew assignment planning (3-phase algorithm)
    GOBERNANZA: State monitoring and governance enforcement
    COMUNICACION: Notification delivery and communications

Result States:
    SUCCESS: Action completed successfully
    FAILURE: Action failed with error
    PENDING: Action in progress or awaiting response

Log Records:
    - System-level logs: ot_id is NULL (for operational logs)
    - OT-specific logs: ot_id is set (for work order audit trail)
    - Raw LLM responses: Stored as JSON for debugging
    - Error details: Stored for troubleshooting and monitoring

Usage:
    - Audit trail for all system operations
    - Debugging agent decisions and LLM outputs
    - Tracking notification delivery status
    - Performance monitoring and analytics
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class LogAgente(Base):
    """
    Agent Action Log model.
    
    Records all actions performed by system agents (Router, OTS, Planning,
    Governance, Communications) for audit trail, debugging, and monitoring.
    
    Each log entry captures:
    - Which agent performed the action
    - What action was performed (description)
    - Whether it succeeded, failed, or is pending
    - Associated OT (if applicable)
    - Raw LLM response for debugging
    - Error details for troubleshooting
    
    Table: logs_agentes
    """

    __tablename__ = "logs_agentes"

    # ========================================================================
    # Primary Key
    # ========================================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        doc="Unique database identifier for log entry",
    )

    # ========================================================================
    # Association with OT
    # ========================================================================

    ot_id = Column(
        Integer,
        ForeignKey("ots.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Associated OT ID (nullable for system-level logs)",
    )

    # ========================================================================
    # Agent Information
    # ========================================================================

    agente_name = Column(
        Enum(
            "ROUTER",
            "OTS",
            "PLANIFICACION",
            "GOBERNANZA",
            "COMUNICACION",
            name="agente_type",
        ),
        nullable=False,
        index=True,
        doc="Agent that performed the action",
    )

    # ========================================================================
    # Action Details
    # ========================================================================

    accion = Column(
        Text,
        nullable=False,
        doc="Description of the action performed",
    )

    # ========================================================================
    # Result Status
    # ========================================================================

    resultado = Column(
        Enum(
            "SUCCESS",
            "FAILURE",
            "PENDING",
            name="log_resultado",
        ),
        nullable=False,
        default="PENDING",
        index=True,
        doc="Result of the action: SUCCESS, FAILURE, or PENDING",
    )

    # ========================================================================
    # LLM & Error Information
    # ========================================================================

    raw_llm_response = Column(
        JSON,
        nullable=True,
        doc="Raw response from LLM (for debugging agent decisions)",
    )

    error_details = Column(
        Text,
        nullable=True,
        doc="Error message or traceback if resultado=FAILURE",
    )

    # ========================================================================
    # Timestamps
    # ========================================================================

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="UTC timestamp when log entry was created",
    )

    # ========================================================================
    # Relationships
    # ========================================================================

    ot = relationship(
        "OT",
        back_populates="logs",
        foreign_keys=[ot_id],
        doc="Associated OT (if applicable)",
    )

    # ========================================================================
    # Indexes
    # ========================================================================

    __table_args__ = (
        # Composite index for efficient agent action queries
        Index("idx_log_agente_name_resultado", "agente_name", "resultado"),
        # Composite index for OT audit trail queries
        Index("idx_log_ot_created_at", "ot_id", "created_at"),
        # Index for time-based queries (recent logs)
        Index("idx_log_created_at", "created_at"),
    )

    # ========================================================================
    # String Representation
    # ========================================================================

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"LogAgente(id={self.id}, ot_id={self.ot_id}, "
            f"agente_name={self.agente_name}, resultado={self.resultado})"
        )

    # ========================================================================
    # Properties for Common Operations
    # ========================================================================

    @property
    def is_success(self) -> bool:
        """Check if action was successful."""
        return self.resultado == "SUCCESS"

    @property
    def is_failure(self) -> bool:
        """Check if action failed."""
        return self.resultado == "FAILURE"

    @property
    def is_pending(self) -> bool:
        """Check if action is pending."""
        return self.resultado == "PENDING"

    @property
    def has_error(self) -> bool:
        """Check if error details are present."""
        return self.error_details is not None

    @property
    def has_llm_response(self) -> bool:
        """Check if LLM response is present."""
        return self.raw_llm_response is not None

    @property
    def is_system_log(self) -> bool:
        """Check if this is a system-level log (not OT-specific)."""
        return self.ot_id is None

    @property
    def is_ot_log(self) -> bool:
        """Check if this is an OT-specific log."""
        return self.ot_id is not None

    # ========================================================================
    # Status Check Methods
    # ========================================================================

    def mark_success(self, llm_response: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark log entry as successful.
        
        Args:
            llm_response: Optional raw LLM response data
        """
        self.resultado = "SUCCESS"
        if llm_response:
            self.raw_llm_response = llm_response
        self.error_details = None

    def mark_failure(
        self,
        error_message: str,
        llm_response: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Mark log entry as failed.
        
        Args:
            error_message: Error message or traceback
            llm_response: Optional raw LLM response data
        """
        self.resultado = "FAILURE"
        self.error_details = error_message
        if llm_response:
            self.raw_llm_response = llm_response

    def mark_pending(self) -> None:
        """Mark log entry as pending."""
        self.resultado = "PENDING"

    # ========================================================================
    # Log Message Methods
    # ========================================================================

    def get_summary(self) -> str:
        """
        Get a summary of the log entry.
        
        Returns:
            Formatted summary string
        """
        status_emoji = {
            "SUCCESS": "✓",
            "FAILURE": "✗",
            "PENDING": "⏳",
        }.get(self.resultado, "?")

        ot_info = f" [OT-{self.ot_id}]" if self.ot_id else " [SYSTEM]"

        return (
            f"{status_emoji} {self.agente_name}: {self.accion[:100]}{ot_info}"
        )

    def get_full_message(self) -> str:
        """
        Get full log message with error details.
        
        Returns:
            Complete log message
        """
        message = self.get_summary()

        if self.is_failure and self.error_details:
            message += f"\n  Error: {self.error_details[:200]}"

        if self.has_llm_response:
            message += f"\n  LLM Response: {str(self.raw_llm_response)[:200]}"

        return message

    # ========================================================================
    # Query Helper Methods
    # ========================================================================

    @staticmethod
    def filter_by_agent(agent_name: str) -> "LogAgente":
        """
        Filter logs by agent name.
        
        Args:
            agent_name: Agent type (ROUTER, OTS, PLANIFICACION, GOBERNANZA, COMUNICACION)
            
        Returns:
            Query filter for SQLAlchemy
        """
        from sqlalchemy import select

        return select(LogAgente).where(LogAgente.agente_name == agent_name)

    @staticmethod
    def filter_by_result(resultado: str) -> "LogAgente":
        """
        Filter logs by result status.
        
        Args:
            resultado: Result status (SUCCESS, FAILURE, PENDING)
            
        Returns:
            Query filter for SQLAlchemy
        """
        from sqlalchemy import select

        return select(LogAgente).where(LogAgente.resultado == resultado)

    @staticmethod
    def filter_by_ot(ot_id: int) -> "LogAgente":
        """
        Filter logs by associated OT.
        
        Args:
            ot_id: OT ID to filter by
            
        Returns:
            Query filter for SQLAlchemy
        """
        from sqlalchemy import select

        return select(LogAgente).where(LogAgente.ot_id == ot_id)

    @staticmethod
    def filter_by_date_range(
        start_date: datetime,
        end_date: datetime,
    ) -> "LogAgente":
        """
        Filter logs by date range.
        
        Args:
            start_date: Start datetime (inclusive)
            end_date: End datetime (inclusive)
            
        Returns:
            Query filter for SQLAlchemy
        """
        from sqlalchemy import select

        return select(LogAgente).where(
            LogAgente.created_at >= start_date,
            LogAgente.created_at <= end_date,
        )

    # ========================================================================
    # Statistics Methods
    # ========================================================================

    def get_agent_type(self) -> str:
        """Get agent type name."""
        return self.agente_name

    def get_result_color(self) -> str:
        """
        Get color code for result status (for UI display).
        
        Returns:
            Color code: 'green' for SUCCESS, 'red' for FAILURE, 'yellow' for PENDING
        """
        return {
            "SUCCESS": "green",
            "FAILURE": "red",
            "PENDING": "yellow",
        }.get(self.resultado, "gray")

    def get_result_emoji(self) -> str:
        """
        Get emoji for result status.
        
        Returns:
            Emoji: ✅ for SUCCESS, ❌ for FAILURE, ⏳ for PENDING
        """
        return {
            "SUCCESS": "✅",
            "FAILURE": "❌",
            "PENDING": "⏳",
        }.get(self.resultado, "❓")


# ============================================================================
# Type Hints
# ============================================================================

__all__ = ["LogAgente"]

