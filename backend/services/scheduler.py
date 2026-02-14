"""
Scheduler service for PEI Platform using APScheduler.
Manages recurring jobs for governance checks and route optimization.
"""

import asyncio
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from backend.config import get_settings


# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


async def run_gobernanza_check():
    """
    Scheduled job for governance checks.
    
    Runs every 1 hour to:
    1. Check for inactive OTs (PREPLANIFICADA > 48 hours)
    2. Check for OTs in detention with alerts (days 20, 25, 29)
    3. Auto-cancel OTs in detention >= 30 days
    4. Validate PUBLICO project document completion
    
    Invokes GobernanzaAgent via PEIGraphRunner with event_type='scheduled_governance'.
    """
    try:
        # Import here to avoid circular imports
        from backend.agents.graph_runner import PEIGraphRunner
        
        config = get_settings()
        graph_runner = PEIGraphRunner(config)
        
        # Prepare initial state for governance check
        initial_state = {
            "user_input": "Perform scheduled governance check",
            "event_type": "scheduled_governance",
            "ot_data": {},
            "current_ot_id": None,
            "cuadrilla_id": None,
            "action_result": "",
            "error_message": None,
            "agent_logs": [],
            "next_agent": "gobernanza",
        }
        
        # Run the graph with governance check
        final_state = await graph_runner.run_graph(initial_state)
        
        print(f"✅ Governance check completed: {final_state.get('action_result', 'No result')}")
        
    except Exception as e:
        print(f"❌ Governance check failed: {str(e)}")


async def run_nightly_normalization():
    """
    Scheduled job for nightly route optimization and centroid recalculation.
    
    Runs daily at 00:00 (midnight) to:
    1. Recalculate all cuadrilla centroids from assigned OTs
    2. Optimize routes for each cuadrilla (PHASE 3 of planning algorithm)
    3. Update cuadrilla positions for next day operations
    
    Invokes PlanificacionAgent via PEIGraphRunner to perform Phase 3 optimization.
    """
    try:
        # Import here to avoid circular imports
        from backend.agents.graph_runner import PEIGraphRunner
        
        config = get_settings()
        graph_runner = PEIGraphRunner(config)
        
        # Prepare initial state for nightly normalization
        initial_state = {
            "user_input": "Perform nightly route normalization and centroid recalculation",
            "event_type": "nightly_normalization",
            "ot_data": {},
            "current_ot_id": None,
            "cuadrilla_id": None,
            "action_result": "",
            "error_message": None,
            "agent_logs": [],
            "next_agent": "planificacion",
        }
        
        # Run the graph with planning optimization
        final_state = await graph_runner.run_graph(initial_state)
        
        print(f"✅ Nightly normalization completed: {final_state.get('action_result', 'No result')}")
        
    except Exception as e:
        print(f"❌ Nightly normalization failed: {str(e)}")


def setup_scheduler() -> AsyncIOScheduler:
    """
    Create and configure the AsyncIOScheduler with recurring jobs.
    
    Sets up two scheduled jobs:
    1. Governance check: Every 1 hour to monitor OT statuses and auto-cancel
    2. Nightly normalization: Daily at 00:00 (midnight) for route optimization
    
    Returns:
        Configured AsyncIOScheduler instance ready to be started
        
    Note:
        The scheduler is configured but not started by this function.
        Call start_scheduler() to begin job execution.
    """
    # Create AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    
    # Add governance check job - runs every 1 hour
    scheduler.add_job(
        run_gobernanza_check,
        trigger=IntervalTrigger(hours=1),
        id="governance_check",
        name="Hourly Governance Check",
        replace_existing=True,
        misfire_grace_time=60,  # Allow 60 seconds grace period for missed executions
    )
    
    # Add nightly normalization job - runs daily at 00:00 (midnight)
    scheduler.add_job(
        run_nightly_normalization,
        trigger=CronTrigger(hour=0, minute=0),
        id="nightly_normalization",
        name="Nightly Route Normalization",
        replace_existing=True,
        misfire_grace_time=300,  # Allow 5 minutes grace period for missed executions
    )
    
    return scheduler


def start_scheduler() -> AsyncIOScheduler:
    """
    Start the global scheduler instance.
    
    Creates and starts the scheduler if not already running.
    Should be called during application startup.
    
    Returns:
        The running AsyncIOScheduler instance
        
    Example:
        >>> scheduler = start_scheduler()
        >>> # Scheduler is now running in the background
    """
    global _scheduler
    
    if _scheduler is None:
        _scheduler = setup_scheduler()
        _scheduler.start()
        print("🚀 Scheduler started successfully")
    else:
        print("⚠️ Scheduler already running")
    
    return _scheduler


def stop_scheduler():
    """
    Stop the global scheduler instance.
    
    Should be called during application shutdown to gracefully
    stop all scheduled jobs.
    
    Example:
        >>> stop_scheduler()
        >>> # Scheduler is now stopped
    """
    global _scheduler
    
    if _scheduler is not None:
        _scheduler.shutdown()
        _scheduler = None
        print("🛑 Scheduler stopped successfully")
    else:
        print("⚠️ Scheduler not running")


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """
    Get the current global scheduler instance.
    
    Returns:
        The global AsyncIOScheduler instance if running, None otherwise
    """
    return _scheduler

