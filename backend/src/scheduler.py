"""
APScheduler job definitions for PEI Platform.

This module defines scheduled jobs for background tasks:
- Governance checks (every 6 hours): Review OT statuses, send alerts, auto-cancel detentions
- Nightly normalization (every day at 00:00): Reoptimize routes and recalculate centroids

Jobs are managed by an AsyncIOScheduler and integrated with FastAPI startup/shutdown events.
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler | None = None


async def run_governance_check() -> None:
    """
    Execute governance check job.

    This job:
    1) Creates a new database session
    2) Executes the governance check via PEIAgentExecutor
    3) Checks OTs in DETENIDA status and sends alerts
    4) Auto-cancels OTs at day 30 of detention
    5) Checks PREPLANIFICADA OTs >48 hours and sends alerts
    6) Logs completion

    Scheduled to run every 6 hours: 00:00, 06:00, 12:00, 18:00 UTC

    This implements the UC-PEI-08 requirement: "Anulación Automática por Inactividad"
    """
    try:
        logger.info("Starting governance check job")

        # Import here to avoid circular imports
        from src.agents.executor import PEIAgentExecutor

        # Create a database session for this job
        async with AsyncSessionLocal() as db_session:
            # Initialize executor
            executor = PEIAgentExecutor()

            # Execute governance check
            result = await executor.execute_scheduled("governance", db_session)

            logger.info(
                f"Governance check completed at {datetime.utcnow().isoformat()}. "
                f"Result: {result.get('status', 'unknown')}"
            )

    except Exception as e:
        logger.error(f"Governance check job failed: {str(e)}", exc_info=True)
        # In production, this would trigger an alert
        raise


async def run_nightly_normalization() -> None:
    """
    Execute nightly route normalization job.

    This job:
    1) Creates a new database session
    2) Calls the Planificación Agent to reoptimize routes
    3) Recalculates centroids for all cuadrillas
    4) Updates assignments if better routes are found
    5) Logs completion

    Scheduled to run daily at 00:00 UTC (midnight)

    This implements Phase 3 of the planning algorithm: "Normalización Nocturna"
    - Re-calculates routes to minimize total displacement for the next day
    - Allows moving OTs between cuadrillas if better proximity is found
    """
    try:
        logger.info("Starting nightly normalization job")

        # Import here to avoid circular imports
        from src.agents.executor import PEIAgentExecutor

        # Create a database session for this job
        async with AsyncSessionLocal() as db_session:
            # Initialize executor
            executor = PEIAgentExecutor()

            # Execute nightly normalization
            result = await executor.execute_scheduled("normalization", db_session)

            logger.info(
                f"Nightly normalization completed at {datetime.utcnow().isoformat()}. "
                f"Result: {result.get('status', 'unknown')}"
            )

    except Exception as e:
        logger.error(f"Nightly normalization job failed: {str(e)}", exc_info=True)
        # In production, this would trigger an alert
        raise


def init_scheduler() -> AsyncIOScheduler:
    """
    Initialize the APScheduler scheduler with all job definitions.

    Creates an AsyncIOScheduler, adds scheduled jobs, and starts the scheduler.
    Should be called during FastAPI startup event.

    Returns:
        AsyncIOScheduler: The configured and started scheduler instance

    Jobs scheduled:
    1. Governance check: Every 6 hours (cron: hour='*/6')
    2. Nightly normalization: Daily at 00:00 UTC (cron: hour=0, minute=0)

    Example usage in main.py:
        @app.on_event("startup")
        async def startup():
            global scheduler
            scheduler = init_scheduler()

        @app.on_event("shutdown")
        async def shutdown():
            await shutdown_scheduler()
    """
    global scheduler

    try:
        logger.info("Initializing APScheduler")

        # Create AsyncIOScheduler
        scheduler = AsyncIOScheduler()

        # Add governance check job (every 6 hours)
        scheduler.add_job(
            run_governance_check,
            trigger=CronTrigger(hour="*/6"),
            id="governance_check",
            name="Governance Check",
            replace_existing=True,
            max_instances=1,  # Prevent multiple concurrent executions
        )
        logger.info("Added governance check job (every 6 hours)")

        # Add nightly normalization job (every day at 00:00 UTC)
        scheduler.add_job(
            run_nightly_normalization,
            trigger=CronTrigger(hour=0, minute=0),
            id="nightly_normalization",
            name="Nightly Normalization",
            replace_existing=True,
            max_instances=1,  # Prevent multiple concurrent executions
        )
        logger.info("Added nightly normalization job (daily at 00:00 UTC)")

        # Start the scheduler
        scheduler.start()
        logger.info("APScheduler started successfully")

        return scheduler

    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {str(e)}", exc_info=True)
        raise


async def shutdown_scheduler() -> None:
    """
    Gracefully shutdown the APScheduler scheduler.

    Waits for running jobs to complete before shutting down.
    Should be called during FastAPI shutdown event.

    Example usage in main.py:
        @app.on_event("shutdown")
        async def shutdown():
            await shutdown_scheduler()
    """
    global scheduler

    if scheduler is None:
        logger.warning("Scheduler is not initialized")
        return

    try:
        logger.info("Shutting down APScheduler")
        scheduler.shutdown(wait=True)
        scheduler = None
        logger.info("APScheduler shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {str(e)}", exc_info=True)
        raise


def get_scheduler() -> AsyncIOScheduler | None:
    """
    Get the global scheduler instance.

    Returns:
        AsyncIOScheduler | None: The scheduler instance if initialized, None otherwise
    """
    return scheduler


def is_scheduler_running() -> bool:
    """
    Check if the scheduler is running.

    Returns:
        bool: True if scheduler is initialized and running, False otherwise
    """
    return scheduler is not None and scheduler.running

