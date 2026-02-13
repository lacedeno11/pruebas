"""
AgentLog Model for tracking agent actions in PEI Platform.

This module defines the SQLAlchemy ORM model for recording all agent executions,
decisions, and state changes. Used for auditing, debugging, and governance.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class LogResultado(str, Enum):
    """Result status of an agent action."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    WARNING = "WARNING"


class AgentLog(Base):
    """
    AgentLog Model.

    Tracks all agent executions, decisions, and state changes for auditing,
    debugging, and governance compliance. Each log entry captures:
    - Which agent executed
    - What action was performed
    - The result (success/failure/warning)
    - Raw LLM response (for debugging)
    - Additional metadata

    Attributes:
        id: Unique log entry identifier (primary key)
        ot_id: Foreign key to related OT (nullable for system-level logs)
        agent_name: Name of the agent that executed (Router, OTS, Planificación, etc.)
        accion: Description of the action performed
        resultado: Result status (SUCCESS, FAILURE, WARNING)
        raw_llm_response: Raw response from LLM (JSON, for debugging)
        metadata: Additional context data (JSON)
        timestamp: When the action occurred (indexed for performance)
    """

    __tablename__ = "agent_logs"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, doc="Unique log entry identifier")

    # Foreign Key (nullable for system-level logs)
    ot_id: Mapped[int | None] = mapped_column(
        ForeignKey("ots.id", ondelete="CASCADE"),
        nullable=True,
        doc="Foreign key to related OT (nullable for system-level logs)",
    )

    # Agent Information
    agent_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Name of the agent: Router, OTS, Planificación, Gobernanza, Comunicación",
    )

    # Action Description
    accion: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Description of the action performed (e.g., 'Asignación exitosa - Centroide: 8.5 km')",
    )

    # Result Status
    resultado: Mapped[LogResultado] = mapped_column(
        String(20),
        default=LogResultado.SUCCESS,
        nullable=False,
        doc="Result status: SUCCESS, FAILURE, or WARNING",
    )

    # LLM Response (for debugging and audit trail)
    raw_llm_response: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Raw response from LLM (JSON) - for debugging and audit trail",
    )

    # Additional Metadata
    metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Additional context data (JSON) - e.g., distances, priorities, errors",
    )

    # Timestamp (indexed for query performance)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="When the action occurred (UTC) - indexed for performance",
    )

    # Relationships
    ot: Mapped["OT | None"] = relationship(
        "OT",
        back_populates="agent_logs",
        doc="Reference to related OT",
    )

    # Indexes for query performance
    __table_args__ = (
        Index("idx_timestamp", "timestamp"),
        Index("idx_agent_name", "agent_name"),
        Index("idx_agent_timestamp", "agent_name", "timestamp"),
        Index("idx_ot_id", "ot_id"),
    )

    def __repr__(self) -> str:
        """String representation of AgentLog."""
        return (
            f"<AgentLog(id={self.id}, agent={self.agent_name}, "
            f"resultado={self.resultado}, timestamp={self.timestamp})>"
        )

    def to_dict(self) -> dict:
        """Convert AgentLog to dictionary for API responses."""
        return {
            "id": self.id,
            "ot_id": self.ot_id,
            "agent_name": self.agent_name,
            "accion": self.accion,
            "resultado": self.resultado.value if isinstance(self.resultado, LogResultado) else self.resultado,
            "raw_llm_response": self.raw_llm_response,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def create_success_log(
        cls,
        agent_name: str,
        accion: str,
        ot_id: int | None = None,
        metadata: dict | None = None,
        raw_llm_response: dict | None = None,
    ) -> "AgentLog":
        """
        Create a SUCCESS log entry.

        Args:
            agent_name (str): Name of the agent
            accion (str): Description of the action
            ot_id (int | None): Related OT ID
            metadata (dict | None): Additional context
            raw_llm_response (dict | None): Raw LLM response

        Returns:
            AgentLog: Log entry instance (not yet persisted)
        """
        return cls(
            agent_name=agent_name,
            accion=accion,
            resultado=LogResultado.SUCCESS,
            ot_id=ot_id,
            metadata=metadata,
            raw_llm_response=raw_llm_response,
        )

    @classmethod
    def create_failure_log(
        cls,
        agent_name: str,
        accion: str,
        error: str,
        ot_id: int | None = None,
        metadata: dict | None = None,
        raw_llm_response: dict | None = None,
    ) -> "AgentLog":
        """
        Create a FAILURE log entry.

        Args:
            agent_name (str): Name of the agent
            accion (str): Description of the action
            error (str): Error message
            ot_id (int | None): Related OT ID
            metadata (dict | None): Additional context
            raw_llm_response (dict | None): Raw LLM response

        Returns:
            AgentLog: Log entry instance (not yet persisted)
        """
        if metadata is None:
            metadata = {}
        metadata["error"] = error

        return cls(
            agent_name=agent_name,
            accion=accion,
            resultado=LogResultado.FAILURE,
            ot_id=ot_id,
            metadata=metadata,
            raw_llm_response=raw_llm_response,
        )

    @classmethod
    def create_warning_log(
        cls,
        agent_name: str,
        accion: str,
        warning: str,
        ot_id: int | None = None,
        metadata: dict | None = None,
        raw_llm_response: dict | None = None,
    ) -> "AgentLog":
        """
        Create a WARNING log entry.

        Args:
            agent_name (str): Name of the agent
            accion (str): Description of the action
            warning (str): Warning message
            ot_id (int | None): Related OT ID
            metadata (dict | None): Additional context
            raw_llm_response (dict | None): Raw LLM response

        Returns:
            AgentLog: Log entry instance (not yet persisted)
        """
        if metadata is None:
            metadata = {}
        metadata["warning"] = warning

        return cls(
            agent_name=agent_name,
            accion=accion,
            resultado=LogResultado.WARNING,
            ot_id=ot_id,
            metadata=metadata,
            raw_llm_response=raw_llm_response,
        )

