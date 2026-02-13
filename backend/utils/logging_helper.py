"""
Logging configuration and agent action logging utilities.
Handles Python logging setup and persistence of agent actions to database.
"""

import json
import logging
from typing import Any, Dict, Optional


def setup_logging(log_level: str) -> None:
    """
    Configure Python logging with appropriate level and format.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def log_agent_action(
    db_session: Any,
    agente_name: str,
    ot_id: Optional[str],
    accion: str,
    resultado: str,
    raw_llm_response: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log an agent action to the database.

    Args:
        db_session: SQLAlchemy database session
        agente_name: Name of the agent that performed the action
        ot_id: OT ID associated with the action (nullable)
        accion: Action performed
        resultado: Result of the action
        raw_llm_response: Raw LLM response as dictionary (optional)
    """
    # Import here to avoid circular imports
    from backend.models import LogAgente

    log_entry = LogAgente(
        ot_id=ot_id,
        agente_name=agente_name,
        accion=accion,
        resultado=resultado,
        raw_llm_response=raw_llm_response,
    )

    db_session.add(log_entry)
    await db_session.commit()

    logger = logging.getLogger(__name__)
    logger.info(
        f"Agent action logged: {agente_name} - {accion} - {resultado} (OT: {ot_id})"
    )

