"""Scheduler for automated governance checks and route optimization."""

import schedule
import time
import asyncio
import logging
from datetime import datetime

from backend.agents.gobernanza_agent import governance_node
from backend.agents.planificacion_agent import planning_node
from backend.graph.state import PEIState, ActionType, create_initial_state
from backend.database.models import AgentLog
from backend.database.db import SessionLocal

# Configure logging
logger = logging.getLogger(__name__)


def _run_async_task(async_func, *args, **kwargs):
    """
    Helper to run async functions from sync scheduler context.
    
    Args:
        async_func: Async function to run
        *args: Positional arguments
        **kwargs: Keyword arguments
    
    Returns:
        Result of async function
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(async_func(*args, **kwargs))
    except RuntimeError:
        # If no loop exists, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(async_func(*args, **kwargs))


def _execute_governance_check():
    """
    Execute governance checks (Check 1, 2, 3).
    
    This is scheduled to run at:
    - Every 1 hour for Check 1 (48h PREPLANIFICADA alerts)
    - Every 6 hours for Check 2 and 3 (DETENIDA checks)
    """
    logger.info("Executing governance checks...")
    
    try:
        # Create initial state for governance action
        state = create_initial_state(
            action=ActionType.GOVERNANCE.value,
        )
        
        # Run governance node
        result_state = _run_async_task(governance_node, state)
        
        # Log execution
        db = SessionLocal()
        try:
            agent_response = result_state.get("agent_responses", [])
            if agent_response:
                last_response = agent_response[-1] if agent_response else {}
                resultado = f"Governance checks executed: {last_response.get('response', {})}"
            else:
                resultado = "Governance checks executed"
            
            agent_log = AgentLog(
                agente_name="Scheduler",
                accion="Execute Governance Checks",
                resultado=resultado,
                timestamp=datetime.utcnow(),
            )
            db.add(agent_log)
            db.commit()
            logger.info("Governance checks completed successfully")
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Governance checks failed: {str(e)}")
        
        # Log error
        db = SessionLocal()
        try:
            agent_log = AgentLog(
                agente_name="Scheduler",
                accion="Execute Governance Checks",
                resultado=f"ERROR: {str(e)}",
                timestamp=datetime.utcnow(),
            )
            db.add(agent_log)
            db.commit()
        finally:
            db.close()


def _execute_nightly_optimization():
    """
    Execute nightly route optimization (Phase 3 of planning algorithm).
    
    This is scheduled to run at 00:00 UTC daily.
    
    Phase 3 recalculates all crew centroids from assigned OTs and stores
    them in Cuadrilla.last_centroid_lat/long for use in Phase 2 planning.
    """
    logger.info("Executing nightly route optimization...")
    
    try:
        # Create initial state for planning action
        state = create_initial_state(
            action=ActionType.PLAN.value,
        )
        
        # Run planning node (which includes Phase 3)
        result_state = _run_async_task(planning_node, state)
        
        # Log execution
        db = SessionLocal()
        try:
            agent_response = result_state.get("agent_responses", [])
            if agent_response:
                last_response = agent_response[-1] if agent_response else {}
                resultado = f"Route optimization executed: {last_response.get('response', {})}"
            else:
                resultado = "Route optimization executed"
            
            agent_log = AgentLog(
                agente_name="Scheduler",
                accion="Execute Nightly Optimization",
                resultado=resultado,
                timestamp=datetime.utcnow(),
            )
            db.add(agent_log)
            db.commit()
            logger.info("Nightly route optimization completed successfully")
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Nightly optimization failed: {str(e)}")
        
        # Log error
        db = SessionLocal()
        try:
            agent_log = AgentLog(
                agente_name="Scheduler",
                accion="Execute Nightly Optimization",
                resultado=f"ERROR: {str(e)}",
                timestamp=datetime.utcnow(),
            )
            db.add(agent_log)
            db.commit()
        finally:
            db.close()


def setup_schedule():
    """
    Set up all scheduled jobs.
    
    Schedules:
    - Every 1 hour: Governance Check 1 (48h PREPLANIFICADA alerts)
    - Every 6 hours: Governance Check 2 & 3 (DETENIDA checks)
    - Daily at 00:00: Nightly route optimization (Phase 3)
    """
    
    # Schedule Check 1: 48h PREPLANIFICADA alerts (every 1 hour)
    schedule.every(1).hour.do(_execute_governance_check)
    logger.info("Scheduled: Governance checks every 1 hour")
    
    # Schedule Check 2 & 3: DETENIDA checks (every 6 hours)
    # These run as part of governance_node when called
    schedule.every(6).hours.do(_execute_governance_check)
    logger.info("Scheduled: DETENIDA governance checks every 6 hours")
    
    # Schedule Phase 3: Nightly route optimization (daily at 00:00)
    schedule.every().day.at("00:00").do(_execute_nightly_optimization)
    logger.info("Scheduled: Nightly route optimization at 00:00 UTC")


def run_scheduler():
    """
    Run the scheduler in an infinite loop.
    
    This function is meant to be run in a background thread or separate process.
    It continuously checks scheduled jobs and executes them when their time arrives.
    
    The scheduler keeps running until interrupted (e.g., by SIGINT).
    """
    
    logger.info("Starting governance scheduler...")
    
    # Set up all scheduled jobs
    setup_schedule()
    
    # Log startup
    db = SessionLocal()
    try:
        agent_log = AgentLog(
            agente_name="Scheduler",
            accion="Scheduler Started",
            resultado="Governance scheduler started with scheduled jobs",
            timestamp=datetime.utcnow(),
        )
        db.add(agent_log)
        db.commit()
    finally:
        db.close()
    
    logger.info("Scheduler started successfully")
    
    # Main scheduler loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every 60 seconds if a job needs to run
    
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user")
    
    except Exception as e:
        logger.error(f"Scheduler error: {str(e)}")
    
    finally:
        # Log shutdown
        db = SessionLocal()
        try:
            agent_log = AgentLog(
                agente_name="Scheduler",
                accion="Scheduler Stopped",
                resultado="Governance scheduler stopped",
                timestamp=datetime.utcnow(),
            )
            db.add(agent_log)
            db.commit()
        finally:
            db.close()
        
        logger.info("Scheduler stopped")


def get_scheduled_jobs():
    """
    Get information about all scheduled jobs.
    
    Returns:
        list: List of scheduled job information
    """
    jobs_info = []
    
    for job in schedule.jobs:
        job_info = {
            "job_function": job.job_func.func.__name__,
            "interval": job.interval,
            "unit": job.unit,
            "at_time": getattr(job, 'at_time', None),
            "next_run": job.next_run.isoformat() if job.next_run else None,
        }
        jobs_info.append(job_info)
    
    return jobs_info


def clear_schedule():
    """
    Clear all scheduled jobs.
    
    Useful for testing or resetting the scheduler.
    """
    schedule.clear()
    logger.info("All scheduled jobs cleared")


# Example usage / testing
if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting scheduler (standalone mode)...")
    run_scheduler()

