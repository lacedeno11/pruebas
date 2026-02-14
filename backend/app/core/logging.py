"""
Structured logging configuration for PEI Agentic Platform.
Provides correlation ID injection for multi-agent request tracing and JSON logging.
"""

import contextvars
import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from .config import get_settings

# ============================================================================
# CONTEXT VARIABLES FOR REQUEST TRACING
# ============================================================================

# Context variable for storing correlation_id across async tasks
correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id",
    default=None,
)

# Context variable for storing service name
service_name_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "service_name",
    default="pei-agentic-platform",
)


def get_correlation_id() -> Optional[str]:
    """
    Get current correlation ID from context.
    
    Used to trace requests across multiple agents in the LangGraph.
    
    Returns:
        Optional[str]: Current correlation ID or None if not set
        
    Example:
        >>> set_correlation_id("550e8400-e29b-41d4-a716-446655440000")
        >>> corr_id = get_correlation_id()
        >>> print(corr_id)
        550e8400-e29b-41d4-a716-446655440000
    """
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """
    Set correlation ID in context.
    
    Should be called at the start of each request to enable tracing
    across multiple agents and services.
    
    Args:
        correlation_id: Unique identifier for request tracing
        
    Example:
        >>> import uuid
        >>> set_correlation_id(str(uuid.uuid4()))
    """
    correlation_id_var.set(correlation_id)


def clear_correlation_id() -> None:
    """
    Clear correlation ID from context.
    
    Should be called at the end of request processing.
    """
    correlation_id_var.set(None)


# ============================================================================
# JSON FORMATTER
# ============================================================================


class JSONFormatter(logging.Formatter):
    """
    Custom logging formatter that outputs structured JSON logs.
    
    Each log entry includes:
    - timestamp: ISO 8601 timestamp
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - correlation_id: Request tracing ID across agents
    - service_name: Service name (pei-agentic-platform)
    - logger_name: Name of the logger
    - message: Log message
    - extra: Any additional context fields
    
    Example JSON output:
        {
            "timestamp": "2024-02-13T15:30:45.123456Z",
            "level": "INFO",
            "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
            "service_name": "pei-agentic-platform",
            "logger_name": "pei.agents.router_agent",
            "message": "Routing OT to Planificacion Agent",
            "extra": {
                "ot_id": "123e4567-e89b-12d3-a456-426614174000",
                "agent": "Router",
                "intent": "PLAN_OTS"
            }
        }
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as JSON.
        
        Args:
            record: LogRecord from logging module
            
        Returns:
            str: JSON-formatted log line
        """
        # Create base log object
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "correlation_id": get_correlation_id(),
            "service_name": service_name_var.get(),
            "logger_name": record.name,
            "message": record.getMessage(),
        }

        # Add exception information if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Extract extra fields from the record
        # Standard fields to exclude from extra
        standard_fields = {
            "name",
            "msg",
            "args",
            "created",
            "msecs",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "process",
            "processName",
            "thread",
            "threadName",
        }

        # Collect extra fields
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in standard_fields:
                extra_fields[key] = value

        if extra_fields:
            log_obj["extra"] = extra_fields

        # Return JSON string
        return json.dumps(log_obj, default=str)


# ============================================================================
# LOGGER CONFIGURATION FUNCTIONS
# ============================================================================


def _configure_file_handler(logger: logging.Logger, log_dir: str) -> None:
    """
    Configure rotating file handler for log persistence.
    
    Creates logs directory if it doesn't exist and sets up file rotation:
    - Max file size: 10MB
    - Backup count: 5 (keeps up to 6 files: current + 5 backups)
    - Format: JSON
    
    Args:
        logger: Logger instance to configure
        log_dir: Directory to store log files
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    # Create rotating file handler
    log_file = os.path.join(log_dir, "app.log")
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,  # Keep 5 backup files
    )

    # Set formatter
    file_handler.setFormatter(JSONFormatter())

    # Add handler to logger
    logger.addHandler(file_handler)


def _configure_console_handler(logger: logging.Logger) -> None:
    """
    Configure console handler for development/debugging.
    
    Outputs to stderr with JSON formatting.
    
    Args:
        logger: Logger instance to configure
    """
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)


def _set_log_level(logger: logging.Logger, level_str: str) -> None:
    """
    Set log level from string.
    
    Args:
        logger: Logger instance to configure
        level_str: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    level = getattr(logging, level_str.upper(), logging.INFO)
    logger.setLevel(level)


# ============================================================================
# LOGGER FACTORY
# ============================================================================


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a configured logger.
    
    Usage:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing OT", extra={"ot_id": "123"})
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    settings = get_settings()

    # Create or get logger
    logger = logging.getLogger(name)

    # Skip if logger already configured (check for existing handlers)
    if logger.handlers:
        return logger

    # Set log level
    _set_log_level(logger, settings.LOG_LEVEL)

    # Prevent propagation to root logger
    logger.propagate = False

    # Configure file handler
    _configure_file_handler(logger, settings.LOG_DIR)

    # Configure console handler
    _configure_console_handler(logger)

    return logger


# ============================================================================
# LOGGING UTILITIES
# ============================================================================


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **extra_fields,
) -> None:
    """
    Log message with correlation ID and extra fields.
    
    Automatically includes correlation_id from context.
    
    Usage:
        >>> logger = get_logger(__name__)
        >>> log_with_context(
        ...     logger,
        ...     logging.INFO,
        ...     "OT assigned to crew",
        ...     ot_id="123",
        ...     cuadrilla_id="456",
        ...     distance_km=8.5,
        ... )
    
    Args:
        logger: Logger instance
        level: Log level (logging.INFO, logging.ERROR, etc.)
        message: Log message
        **extra_fields: Additional context fields to include
    """
    logger.log(level, message, extra=extra_fields)


def log_agent_action(
    logger: logging.Logger,
    agent_name: str,
    action: str,
    result: str,
    ot_id: Optional[str] = None,
    **additional_context,
) -> None:
    """
    Log agent action with structured context.
    
    Specifically designed for logging LangGraph agent operations.
    
    Usage:
        >>> logger = get_logger(__name__)
        >>> log_agent_action(
        ...     logger,
        ...     agent_name="RouterAgent",
        ...     action="Route request",
        ...     result="SUCCESS",
        ...     ot_id="123",
        ...     intent="PLAN_OTS",
        ...     next_agent="PlanificacionAgent",
        ... )
    
    Args:
        logger: Logger instance
        agent_name: Name of the agent
        action: Action performed by agent
        result: Result status (SUCCESS, ERROR, VALIDATION_FAILED, etc.)
        ot_id: Optional OT ID for the action
        **additional_context: Additional context fields
    """
    extra = {
        "agent": agent_name,
        "action": action,
        "result": result,
        **additional_context,
    }

    if ot_id:
        extra["ot_id"] = ot_id

    message = f"[{agent_name}] {action}: {result}"
    logger.info(message, extra=extra)


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    context: str,
    **additional_context,
) -> None:
    """
    Log error with correlation ID and context.
    
    Usage:
        >>> logger = get_logger(__name__)
        >>> try:
        ...     result = some_operation()
        ... except Exception as e:
        ...     log_error_with_context(
        ...         logger,
        ...         e,
        ...         "OT assignment failed",
        ...         ot_id="123",
        ...         cuadrilla_id="456",
        ...     )
    
    Args:
        logger: Logger instance
        error: Exception object
        context: Context description
        **additional_context: Additional context fields
    """
    extra = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        **additional_context,
    }

    logger.error(
        f"{context}: {type(error).__name__}: {str(error)}",
        exc_info=True,
        extra=extra,
    )


# ============================================================================
# FASTAPI MIDDLEWARE FOR CORRELATION ID
# ============================================================================


async def logging_middleware(request, call_next):
    """
    FastAPI middleware to inject correlation ID into request context.
    
    Extracts or generates correlation ID from request headers and sets it
    in context for use across all agents and services during request handling.
    
    Adds or uses these headers:
    - X-Correlation-ID: Unique request identifier
    - X-Request-ID: Alternative name for same ID
    
    Usage in main.py:
        >>> from fastapi import FastAPI
        >>> from app.core.logging import logging_middleware
        >>>
        >>> app = FastAPI()
        >>> app.middleware("http")(logging_middleware)
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/route handler
        
    Returns:
        Response with correlation ID header
        
    Example:
        Request header: X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
        All logs within this request will include this correlation_id.
    """
    import uuid

    # Extract correlation ID from request headers
    correlation_id = (
        request.headers.get("X-Correlation-ID")
        or request.headers.get("X-Request-ID")
        or str(uuid.uuid4())
    )

    # Set correlation ID in context
    set_correlation_id(correlation_id)

    # Process request
    response = await call_next(request)

    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id

    # Clear correlation ID from context
    clear_correlation_id()

    return response


# ============================================================================
# INITIALIZATION
# ============================================================================


def init_logging() -> None:
    """
    Initialize application logging on startup.
    
    Configures root logger and creates application logger.
    
    Call this during FastAPI startup:
        >>> from fastapi import FastAPI
        >>> from app.core.logging import init_logging
        >>>
        >>> app = FastAPI()
        >>>
        >>> @app.on_event("startup")
        >>> async def startup():
        ...     init_logging()
    """
    settings = get_settings()

    # Configure root logger
    root_logger = logging.getLogger()
    _set_log_level(root_logger, settings.LOG_LEVEL)

    # Get application logger
    app_logger = get_logger("pei.agentic")

    # Log startup message
    app_logger.info(
        "PEI Agentic Platform initialized",
        extra={
            "system_mode": settings.SYSTEM_MODE,
            "log_level": settings.LOG_LEVEL,
        },
    )


# ============================================================================
# MODULE-LEVEL LOGGER
# ============================================================================

# Create module-level logger for this module
logger = get_logger(__name__)

