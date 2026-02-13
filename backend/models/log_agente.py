"""
LogAgente (Agent Action Log) SQLAlchemy model for the PEI Platform.
Tracks all agent actions and decisions for auditing and debugging.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship

from backend.db.database import Base


class ActionResult(str, Enum):
    """Enumeration of agent action result statuses."""

    SUCCESS = "SUCCESS"  # Action completed successfully
    FAILURE = "FAILURE"  # Action failed with error
    PENDING = "PENDING"  # Action is pending/in progress


class LogAgente(Base):
    """
    LogAgente (Agent Action Log) database model.

    Tracks all actions executed by agents in the PEI Platform system.
    Each log entry records what action an agent performed, the result,
    and any relevant LLM responses or metadata for auditing and debugging.

    Attributes:
        id: Primary key, unique identifier in database
        ot_id: Foreign key to associated OT (nullable if action is not OT-specific)
        agente_name: Name of the agent that performed the action (indexed for filtering)
        accion: Description of the action performed
        resultado: Result status (SUCCESS, FAILURE, or PENDING)
        raw_llm_response: Raw response from LLM if applicable (nullable)
        metadata: Additional metadata as JSON (nullable)
        created_at: Timestamp when action was logged

    Relationships:
        ot: Many-to-one relationship with OT model (back_populates to ots)

    Example Log Entries:
        - OTSAgent fetching and registering OTs
        - PlanificacionAgent assigning OTs to cuadrillas
        - GobernanzaAgent sending alerts or auto-cancelling OTs
        - ComunicacionAgent sending notifications
        - RouterAgent routing user requests to appropriate agents
    """

    __tablename__ = "log_agentes"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # OT association (nullable for non-OT-specific actions)
    ot_id = Column(Integer, ForeignKey("ots.id"), nullable=True, index=True)

    # Agent information
    agente_name = Column(String(255), nullable=False, index=True)
    accion = Column(String(500), nullable=False)

    # Action result
    resultado = Column(
        SQLEnum(ActionResult),
        nullable=False,
        default=ActionResult.PENDING,
        index=True,
    )

    # LLM and metadata
    raw_llm_response = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    ot = relationship("OT", back_populates="logs", foreign_keys=[ot_id])

    # Indexes for common queries
    __table_args__ = (
        Index("idx_log_agentes_agente_created", "agente_name", "created_at"),
        Index("idx_log_agentes_resultado_created", "resultado", "created_at"),
        Index("idx_log_agentes_ot_agente", "ot_id", "agente_name"),
    )

    def __repr__(self) -> str:
        """String representation of LogAgente instance."""
        return (
            f"<LogAgente(id={self.id}, agente_name={self.agente_name}, "
            f"accion={self.accion}, resultado={self.resultado})>"
        )

    @classmethod
    def log_action(
        cls,
        db_session,
        agente_name: str,
        accion: str,
        resultado: ActionResult,
        ot_id: Optional[int] = None,
        raw_llm_response: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> "LogAgente":
        """
        Convenient class method to create and persist a log entry.

        This method provides a simple interface for agents to log their actions
        without needing to manually create LogAgente instances and commit them.

        Args:
            db_session: SQLAlchemy database session
            agente_name: Name of the agent (e.g., 'OTSAgent', 'PlanificacionAgent')
            accion: Description of the action performed
            resultado: ActionResult enum (SUCCESS, FAILURE, or PENDING)
            ot_id: Optional ID of associated OT
            raw_llm_response: Optional raw response from LLM if applicable
            metadata: Optional dictionary of additional metadata

        Returns:
            The created and persisted LogAgente instance

        Usage Example:
            >>> from backend.models import LogAgente
            >>> from backend.models.log_agente import ActionResult
            >>>
            >>> log_entry = LogAgente.log_action(
            ...     db_session=db,
            ...     agente_name="OTSAgent",
            ...     accion="Fetched 18 OTs from TELCOS API",
            ...     resultado=ActionResult.SUCCESS,
            ...     metadata={"ot_count": 18, "geo_errors": 2}
            ... )
            >>>
            >>> log_entry = LogAgente.log_action(
            ...     db_session=db,
            ...     agente_name="PlanificacionAgent",
            ...     accion="Assigned OT-2024001 to Cuadrilla 1",
            ...     resultado=ActionResult.SUCCESS,
            ...     ot_id=123,
            ...     metadata={"cuadrilla_id": 1, "distance_km": 3.45}
            ... )
        """
        # Create new log entry
        log_entry = cls(
            agente_name=agente_name,
            accion=accion,
            resultado=resultado,
            ot_id=ot_id,
            raw_llm_response=raw_llm_response,
            metadata=metadata,
        )

        # Persist to database
        db_session.add(log_entry)
        db_session.commit()

        return log_entry

    def is_success(self) -> bool:
        """Check if action was successful."""
        return self.resultado == ActionResult.SUCCESS

    def is_failure(self) -> bool:
        """Check if action failed."""
        return self.resultado == ActionResult.FAILURE

    def is_pending(self) -> bool:
        """Check if action is still pending."""
        return self.resultado == ActionResult.PENDING

    def mark_success(self, db_session) -> None:
        """
        Mark this log entry as successful and commit to database.

        Args:
            db_session: SQLAlchemy database session
        """
        self.resultado = ActionResult.SUCCESS
        db_session.commit()

    def mark_failure(self, db_session) -> None:
        """
        Mark this log entry as failed and commit to database.

        Args:
            db_session: SQLAlchemy database session
        """
        self.resultado = ActionResult.FAILURE
        db_session.commit()

    def update_metadata(self, db_session, new_metadata: dict) -> None:
        """
        Update or merge metadata for this log entry.

        Args:
            db_session: SQLAlchemy database session
            new_metadata: Dictionary to merge with existing metadata
        """
        if self.metadata is None:
            self.metadata = {}

        # Merge new metadata
        self.metadata.update(new_metadata)
        db_session.commit()

