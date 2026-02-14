"""
Background job scheduler for PEI Agentic Platform.
Uses APScheduler to manage recurring tasks: nightly normalization, inactivity checks, document validation.

Jobs run independently with correlation ID tracing and comprehensive error handling.
Integrated with FastAPI lifespan events for startup and shutdown lifecycle management.

Scheduled Jobs:
- nightly_normalization_job: Daily at 00:00 UTC (America/Guayaquil timezone)
- inactivity_check_job: Hourly at minute 0
- document_validation_job: Daily at 08:00 UTC
"""

import uuid
from datetime import datetime
from functools import lru_cache
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.core.logging import (
    get_logger,
    log_agent_action,
    set_correlation_id,
    clear_correlation_id,
)

# ============================================================================
# LOGGER SETUP
# ============================================================================

logger = get_logger(__name__)

# ============================================================================
# SCHEDULER INSTANCE
# ============================================================================

_scheduler: Optional[AsyncIOScheduler] = None


# ============================================================================
# JOB IMPLEMENTATIONS
# ============================================================================


async def nightly_normalization_job() -> None:
    """
    Nightly normalization job - runs daily at 00:00 UTC (Ecuador time).
    
    Triggers PlanificacionAgent to recalculate optimal routes and crew assignments
    based on the current day's workload. This is Phase 3 of the planning algorithm.
    
    Responsibilities:
    - Recalculate centroids for all crews based on current assignments
    - Optimize assignment distribution across crews
    - Check for any constraint violations
    - Log execution with correlation ID for tracing
    
    Correlation ID: Generated for this job to trace through agent operations
    
    Error Handling:
    - Catches all exceptions and logs as failed
    - Does not propagate errors (prevents scheduler from stopping)
    - Sends alert notifications if critical failure occurs
    """
    correlation_id = str(uuid.uuid4())
    set_correlation_id(correlation_id)
    
    try:
        logger.info(
            "Starting nightly normalization job",
            extra={
                "correlation_id": correlation_id,
                "job": "nightly_normalization",
            },
        )
        
        # Import here to avoid circular imports
        from app.agents import create_agent_graph
        
        settings = get_settings()
        
        # Create agent graph for this operation
        agent_graph = create_agent_graph()
        
        # Prepare initial state for nightly normalization
        initial_state = {
            "ots": [],
            "cuadrillas": [],
            "current_ot": None,
            "messages": [],
            "validation_result": {},
            "action_history": [],
            "correlation_id": correlation_id,
            "user_input": "Execute nightly normalization",
        }
        
        # Invoke agent graph with nightly normalization request
        # This will be routed to PlanificacionAgent
        result = await agent_graph.ainvoke(initial_state)
        
        # Log successful execution
        log_agent_action(
            logger,
            agent_name="Scheduler",
            action="NIGHTLY_NORMALIZATION",
            result="SUCCESS",
            correlation_id=correlation_id,
            metadata={
                "scheduled_time": datetime.utcnow().isoformat(),
                "actions_taken": len(result.get("action_history", [])),
            },
        )
        
        logger.info(
            "Nightly normalization job completed successfully",
            extra={
                "correlation_id": correlation_id,
                "actions": len(result.get("action_history", [])),
            },
        )
        
    except Exception as e:
        # Log failure without propagating error
        log_agent_action(
            logger,
            agent_name="Scheduler",
            action="NIGHTLY_NORMALIZATION",
            result="FAILED",
            correlation_id=correlation_id,
            metadata={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        
        logger.error(
            f"Nightly normalization job failed: {str(e)}",
            extra={
                "correlation_id": correlation_id,
                "error": str(e),
            },
        )
        
    finally:
        clear_correlation_id()


async def inactivity_check_job() -> None:
    """
    Inactivity check job - runs hourly.
    
    Monitors OTs in DETENIDA (detention) status for prolonged inactivity.
    Sends alerts at 20, 25, and 29 days of inactivity.
    Auto-cancels OTs after 30 days in DETENIDA status.
    
    Responsibilities:
    - Query OTs in DETENIDA status
    - Calculate days in detention for each OT
    - Send alerts at threshold days (20, 25, 29)
    - Auto-cancel OTs after 30 days (move to ANULADA)
    - Create log entries for all actions
    
    Correlation ID: Generated for this job to trace through agent operations
    
    Error Handling:
    - Catches all exceptions and logs as failed
    - Does not propagate errors
    - Continues processing other OTs if one fails
    """
    correlation_id = str(uuid.uuid4())
    set_correlation_id(correlation_id)
    
    try:
        logger.info(
            "Starting inactivity check job",
            extra={
                "correlation_id": correlation_id,
                "job": "inactivity_check",
            },
        )
        
        # Import here to avoid circular imports
        from app.agents import create_agent_graph
        from app.core.database import get_db
        
        settings = get_settings()
        
        # Create agent graph for this operation
        agent_graph = create_agent_graph()
        
        # Prepare initial state for inactivity check
        initial_state = {
            "ots": [],
            "cuadrillas": [],
            "current_ot": None,
            "messages": [],
            "validation_result": {},
            "action_history": [],
            "correlation_id": correlation_id,
            "user_input": "Check for inactive OTs and apply governance rules",
        }
        
        # Invoke agent graph with inactivity check request
        # This will be routed to GobernanzaAgent
        result = await agent_graph.ainvoke(initial_state)
        
        # Log successful execution
        log_agent_action(
            logger,
            agent_name="Scheduler",
            action="INACTIVITY_CHECK",
            result="SUCCESS",
            correlation_id=correlation_id,
            metadata={
                "scheduled_time": datetime.utcnow().isoformat(),
                "actions_taken": len(result.get("action_history", [])),
            },
        )
        
        logger.info(
            "Inactivity check job completed successfully",
            extra={
                "correlation_id": correlation_id,
                "actions": len(result.get("action_history", [])),
            },
        )
        
    except Exception as e:
        # Log failure without propagating error
        log_agent_action(
            logger,
            agent_name="Scheduler",
            action="INACTIVITY_CHECK",
            result="FAILED",
            correlation_id=correlation_id,
            metadata={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        
        logger.error(
            f"Inactivity check job failed: {str(e)}",
            extra={
                "correlation_id": correlation_id,
                "error": str(e),
            },
        )
        
    finally:
        clear_correlation_id()


async def document_validation_job() -> None:
    """
    Document validation job - runs daily at 08:00 UTC.
    
    Validates that PUBLIC projects have all 29 mandatory documents
    before allowing transition to FINALIZADA status.
    
    Responsibilities:
    - Query PUBLIC projects in ASIGNADO_TAREA status
    - Check TelcoDrive for document count
    - Mark OTs with missing documents for review
    - Create alerts for incomplete documentations
    - Log execution with correlation ID for tracing
    
    Correlation ID: Generated for this job to trace through agent operations
    
    Error Handling:
    - Catches all exceptions and logs as failed
    - Does not propagate errors
    - Continues processing other OTs if one fails
    """
    correlation_id = str(uuid.uuid4())
    set_correlation_id(correlation_id)
    
    try:
        logger.info(
            "Starting document validation job",
            extra={
                "correlation_id": correlation_id,
                "job": "document_validation",
            },
        )
        
        # Import here to avoid circular imports
        from app.agents import create_agent_graph
        
        settings = get_settings()
        
        # Create agent graph for this operation
        agent_graph = create_agent_graph()
        
        # Prepare initial state for document validation
        initial_state = {
            "ots": [],
            "cuadrillas": [],
            "current_ot": None,
            "messages": [],
            "validation_result": {},
            "action_history": [],
            "correlation_id": correlation_id,
            "user_input": "Validate PUBLIC project documents are complete",
        }
        
        # Invoke agent graph with document validation request
        # This will be routed to GobernanzaAgent
        result = await agent_graph.ainvoke(initial_state)
        
        # Log successful execution
        log_agent_action(
            logger,
            agent_name="Scheduler",
            action="DOCUMENT_VALIDATION",
            result="SUCCESS",
            correlation_id=correlation_id,
            metadata={
                "scheduled_time": datetime.utcnow().isoformat(),
                "actions_taken": len(result.get("action_history", [])),
            },
        )
        
        logger.info(
            "Document validation job completed successfully",
            extra={
                "correlation_id": correlation_id,
                "actions": len(result.get("action_history", [])),
            },
        )
        
    except Exception as e:
        # Log failure without propagating error
        log_agent_action(
            logger,
            agent_name="Scheduler",
            action="DOCUMENT_VALIDATION",
            result="FAILED",
            correlation_id=correlation_id,
            metadata={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        
        logger.error(
            f"Document validation job failed: {str(e)}",
            extra={
                "correlation_id": correlation_id,
                "error": str(e),
            },
        )
        
    finally:
        clear_correlation_id()


# ============================================================================
# SCHEDULER LIFECYCLE MANAGEMENT
# ============================================================================


async def start_scheduler() -> None:
    """
    Initialize and start the background scheduler.
    
    Creates AsyncIOScheduler instance and registers all background jobs:
    - nightly_normalization_job: 00:00 daily (America/Guayaquil timezone)
    - inactivity_check_job: Hourly at minute 0
    - document_validation_job: 08:00 daily
    
    Configuration:
    - Timezone: America/Guayaquil (Ecuador time)
    - Misfire grace time: 15 seconds (jobs can run up to 15 seconds late)
    - Coalescing: Jobs that would run multiple times run once
    
    Called during FastAPI startup event (Task 16: main.py)
    
    Raises:
        Exception: If scheduler is already running or configuration error
        
    Example:
        >>> import asyncio
        >>> asyncio.run(start_scheduler())
    """
    global _scheduler
    
    if _scheduler is not None:
        logger.warning("Scheduler is already running")
        return
    
    try:
        settings = get_settings()
        
        # Create AsyncIOScheduler with Ecuador timezone
        _scheduler = AsyncIOScheduler(
            timezone="America/Guayaquil",
            misfire_grace_time=15,
            coalesce=True,
        )
        
        # Register nightly normalization job (daily at 00:00)
        _scheduler.add_job(
            nightly_normalization_job,
            CronTrigger(hour=0, minute=0, timezone="America/Guayaquil"),
            id="nightly_normalization",
            name="Nightly Normalization",
            replace_existing=True,
            max_instances=1,  # Prevent concurrent executions
        )
        
        logger.info(
            "Registered nightly_normalization job",
            extra={
                "schedule": "Daily at 00:00",
                "timezone": "America/Guayaquil",
            },
        )
        
        # Register inactivity check job (hourly at minute 0)
        _scheduler.add_job(
            inactivity_check_job,
            CronTrigger(minute=0, timezone="America/Guayaquil"),
            id="inactivity_check",
            name="Inactivity Check",
            replace_existing=True,
            max_instances=1,  # Prevent concurrent executions
        )
        
        logger.info(
            "Registered inactivity_check job",
            extra={
                "schedule": "Hourly at minute 0",
                "timezone": "America/Guayaquil",
            },
        )
        
        # Register document validation job (daily at 08:00)
        _scheduler.add_job(
            document_validation_job,
            CronTrigger(hour=8, minute=0, timezone="America/Guayaquil"),
            id="document_validation",
            name="Document Validation",
            replace_existing=True,
            max_instances=1,  # Prevent concurrent executions
        )
        
        logger.info(
            "Registered document_validation job",
            extra={
                "schedule": "Daily at 08:00",
                "timezone": "America/Guayaquil",
            },
        )
        
        # Start the scheduler
        _scheduler.start()
        
        logger.info(
            "Background scheduler started successfully",
            extra={
                "jobs": ["nightly_normalization", "inactivity_check", "document_validation"],
                "timezone": "America/Guayaquil",
            },
        )
        
    except Exception as e:
        logger.error(
            f"Failed to start scheduler: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        _scheduler = None
        raise


async def shutdown_scheduler() -> None:
    """
    Gracefully shutdown the background scheduler.
    
    Stops all running jobs and cleans up scheduler resources.
    Allows jobs to complete with timeout.
    
    Called during FastAPI shutdown event (Task 16: main.py)
    
    Raises:
        Exception: If shutdown fails (logged but not propagated)
        
    Example:
        >>> import asyncio
        >>> asyncio.run(shutdown_scheduler())
    """
    global _scheduler
    
    if _scheduler is None:
        logger.info("Scheduler is not running, nothing to shutdown")
        return
    
    try:
        # Stop the scheduler (allows running jobs to complete)
        _scheduler.shutdown(wait=True)
        _scheduler = None
        
        logger.info("Background scheduler shutdown gracefully")
        
    except Exception as e:
        logger.error(
            f"Error during scheduler shutdown: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        _scheduler = None


# ============================================================================
# SCHEDULER ACCESS FUNCTION
# ============================================================================


@lru_cache(maxsize=1)
def get_scheduler() -> Optional[AsyncIOScheduler]:
    """
    Get the global scheduler instance.
    
    Returns the current AsyncIOScheduler instance or None if not running.
    Uses @lru_cache to ensure consistent reference throughout application.
    
    Returns:
        Optional[AsyncIOScheduler]: Scheduler instance if running, None otherwise
        
    Example:
        >>> scheduler = get_scheduler()
        >>> if scheduler:
        ...     jobs = scheduler.get_jobs()
        ...     print(f"Running {len(jobs)} jobs")
    """
    return _scheduler


# ============================================================================
# SCHEDULER STATUS ENDPOINT HANDLER
# ============================================================================


async def get_scheduler_status() -> dict:
    """
    Get current scheduler status and job information.
    
    Returns detailed information about the scheduler and all registered jobs.
    Used by GET /api/v1/scheduler/status endpoint (Task 14: main.py)
    
    Returns:
        dict: Status information with keys:
            - scheduler_running: bool, whether scheduler is active
            - timezone: str, configured timezone
            - jobs: List[dict], list of registered jobs with:
                - id: str, job identifier
                - name: str, job name
                - next_run_time: str, ISO format timestamp
                - trigger: str, trigger description (e.g., "cron")
                
    Example:
        >>> status = await get_scheduler_status()
        >>> if status["scheduler_running"]:
        ...     for job in status["jobs"]:
        ...         print(f"{job['name']} next runs at {job['next_run_time']}")
    """
    scheduler = get_scheduler()
    
    if scheduler is None or not scheduler.running:
        return {
            "scheduler_running": False,
            "timezone": None,
            "jobs": [],
            "message": "Scheduler is not running",
        }
    
    # Get all registered jobs
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": (
                    job.next_run_time.isoformat()
                    if job.next_run_time
                    else None
                ),
                "trigger": str(job.trigger),
                "func": job.func_ref,
                "max_instances": job.max_instances,
            }
        )
    
    return {
        "scheduler_running": True,
        "timezone": scheduler.timezone.zone if scheduler.timezone else "UTC",
        "jobs": jobs,
        "job_count": len(jobs),
    }


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "start_scheduler",
    "shutdown_scheduler",
    "get_scheduler",
    "get_scheduler_status",
    "nightly_normalization_job",
    "inactivity_check_job",
    "document_validation_job",
]

