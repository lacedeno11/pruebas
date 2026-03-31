"""
APScheduler initialization and management for DERCAS backend.

This module provides:
- AsyncIOScheduler setup with persistent job store
- Job registration with proper schedules
- start_scheduler() and stop_scheduler() functions
- Integration points for FastAPI lifecycle events
- Job execution history tracking and error recovery
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.job import Job

from backend.app.scheduler.jobs import (
    nightly_optimization_job,
    governance_check_job,
    sync_ots_job,
)


# Configure logging
logger = logging.getLogger(__name__)


class SchedulerManager:
    """
    Manages APScheduler lifecycle and job execution tracking.
    
    Features:
    - AsyncIOScheduler initialization with custom configuration
    - Job registration with defined schedules
    - Execution history tracking
    - Error recovery and logging
    - Thread-safe operations
    """
    
    def __init__(self):
        """Initialize the SchedulerManager with AsyncIOScheduler."""
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.job_history: Dict[str, List[Dict]] = {}
        self.is_running = False
        
        # Configuration for the scheduler
        self.config = {
            'apscheduler.schedulers.asyncio.class': 'apscheduler.schedulers.asyncio:AsyncIOScheduler',
            'apscheduler.jobstores.default.class': 'apscheduler.jobstores.memory:MemoryJobStore',
            'apscheduler.executors.default.class': 'apscheduler.executors.asyncio:AsyncIOExecutor',
            'apscheduler.executors.default.max_workers': '20',
            'apscheduler.job_defaults.coalesce': 'true',
            'apscheduler.job_defaults.max_instances': '1',
        }
    
    def initialize_scheduler(self):
        """
        Initialize the AsyncIOScheduler with proper configuration.
        
        Sets up:
        - AsyncIOExecutor for async job execution
        - MemoryJobStore for job persistence during runtime
        - Max workers for parallel job execution
        - Job defaults (coalesce, max_instances)
        """
        try:
            if self.scheduler is None:
                # Create scheduler with AsyncIOExecutor
                self.scheduler = AsyncIOScheduler(
                    executors={
                        'default': AsyncIOExecutor(max_workers=20)
                    },
                    job_defaults={
                        'coalesce': True,
                        'max_instances': 1
                    }
                )
                
                logger.info("APScheduler initialized successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {str(e)}")
            return False
    
    def register_jobs(self):
        """
        Register all scheduled jobs with their schedules.
        
        Jobs registered:
        1. nightly_optimization_job - Cron: 00:00 (midnight) daily
        2. governance_check_job - Interval: every 6 hours
        3. sync_ots_job - Interval: every 30 minutes
        """
        if self.scheduler is None:
            logger.error("Scheduler not initialized. Call initialize_scheduler() first.")
            return False
        
        try:
            # Job 1: Nightly optimization at midnight
            self.scheduler.add_job(
                nightly_optimization_job,
                'cron',
                hour=0,
                minute=0,
                id='nightly_optimization',
                name='Nightly Route Optimization (Phase 3)',
                replace_existing=True,
                misfire_grace_time=60,
            )
            logger.info("Registered job: nightly_optimization (00:00 daily)")
            
            # Job 2: Governance checks every 6 hours
            self.scheduler.add_job(
                governance_check_job,
                'interval',
                hours=6,
                id='governance_check',
                name='Governance Rule Checking',
                replace_existing=True,
                misfire_grace_time=60,
            )
            logger.info("Registered job: governance_check (every 6 hours)")
            
            # Job 3: OT synchronization every 30 minutes
            self.scheduler.add_job(
                sync_ots_job,
                'interval',
                minutes=30,
                id='sync_ots',
                name='OT Synchronization from TELCOS API',
                replace_existing=True,
                misfire_grace_time=60,
            )
            logger.info("Registered job: sync_ots (every 30 minutes)")
            
            return True
        except Exception as e:
            logger.error(f"Failed to register jobs: {str(e)}")
            return False
    
    async def start_scheduler(self) -> bool:
        """
        Start the scheduler and its jobs.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            if self.scheduler is None:
                self.initialize_scheduler()
            
            if not self.scheduler.running:
                self.scheduler.start()
                self.is_running = True
                logger.info("Scheduler started successfully")
                
                # Log all registered jobs
                jobs = self.scheduler.get_jobs()
                logger.info(f"Total jobs registered: {len(jobs)}")
                for job in jobs:
                    logger.info(
                        f"  - {job.id}: {job.name} "
                        f"(next_run: {job.next_run_time})"
                    )
                
                return True
            else:
                logger.warning("Scheduler is already running")
                return True
        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}")
            self.is_running = False
            return False
    
    async def stop_scheduler(self) -> bool:
        """
        Stop the scheduler and its jobs.
        
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        try:
            if self.scheduler is not None and self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                self.is_running = False
                logger.info("Scheduler stopped successfully")
                return True
            else:
                logger.warning("Scheduler is not running")
                return True
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {str(e)}")
            return False
    
    def get_jobs(self) -> List[Job]:
        """
        Get all registered jobs.
        
        Returns:
            List of Job objects
        """
        if self.scheduler is None:
            return []
        return self.scheduler.get_jobs()
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get a specific job by ID.
        
        Args:
            job_id: The job ID
            
        Returns:
            Job object or None if not found
        """
        if self.scheduler is None:
            return None
        return self.scheduler.get_job(job_id)
    
    def pause_job(self, job_id: str) -> bool:
        """
        Pause a specific job.
        
        Args:
            job_id: The job ID to pause
            
        Returns:
            bool: True if paused successfully, False otherwise
        """
        try:
            job = self.get_job(job_id)
            if job:
                job.pause()
                logger.info(f"Job {job_id} paused")
                return True
            else:
                logger.warning(f"Job {job_id} not found")
                return False
        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {str(e)}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused job.
        
        Args:
            job_id: The job ID to resume
            
        Returns:
            bool: True if resumed successfully, False otherwise
        """
        try:
            job = self.get_job(job_id)
            if job:
                job.resume()
                logger.info(f"Job {job_id} resumed")
                return True
            else:
                logger.warning(f"Job {job_id} not found")
                return False
        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {str(e)}")
            return False
    
    def record_job_execution(self, job_id: str, status: str, details: Dict = None):
        """
        Record job execution history for tracking and debugging.
        
        Args:
            job_id: The job ID
            status: Execution status ('success' or 'error')
            details: Additional execution details
        """
        if job_id not in self.job_history:
            self.job_history[job_id] = []
        
        execution_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'status': status,
            'details': details or {}
        }
        
        self.job_history[job_id].append(execution_record)
        
        # Keep only last 100 executions per job
        if len(self.job_history[job_id]) > 100:
            self.job_history[job_id] = self.job_history[job_id][-100:]
    
    def get_job_history(self, job_id: str, limit: int = 20) -> List[Dict]:
        """
        Get execution history for a specific job.
        
        Args:
            job_id: The job ID
            limit: Maximum number of history records to return
            
        Returns:
            List of execution history records
        """
        if job_id not in self.job_history:
            return []
        
        history = self.job_history[job_id]
        return history[-limit:] if limit > 0 else history
    
    def clear_job_history(self, job_id: str = None):
        """
        Clear execution history.
        
        Args:
            job_id: Specific job to clear history for. If None, clear all history.
        """
        if job_id:
            if job_id in self.job_history:
                del self.job_history[job_id]
                logger.info(f"Cleared history for job {job_id}")
        else:
            self.job_history.clear()
            logger.info("Cleared all job history")


# Global scheduler manager instance
_scheduler_manager = SchedulerManager()


async def initialize_scheduler() -> bool:
    """
    Initialize the scheduler during FastAPI startup.
    
    This function should be called in FastAPI's startup event:
    ```python
    @app.on_event("startup")
    async def startup_event():
        await initialize_scheduler()
    ```
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    global _scheduler_manager
    
    # Initialize scheduler
    if not _scheduler_manager.initialize_scheduler():
        logger.error("Failed to initialize scheduler")
        return False
    
    # Register all jobs
    if not _scheduler_manager.register_jobs():
        logger.error("Failed to register jobs")
        return False
    
    # Start scheduler
    if not await _scheduler_manager.start_scheduler():
        logger.error("Failed to start scheduler")
        return False
    
    return True


async def shutdown_scheduler() -> bool:
    """
    Shutdown the scheduler during FastAPI shutdown.
    
    This function should be called in FastAPI's shutdown event:
    ```python
    @app.on_event("shutdown")
    async def shutdown_event():
        await shutdown_scheduler()
    ```
    
    Returns:
        bool: True if shutdown successful, False otherwise
    """
    global _scheduler_manager
    return await _scheduler_manager.stop_scheduler()


def get_scheduler_manager() -> SchedulerManager:
    """
    Get the global scheduler manager instance.
    
    Useful for accessing scheduler status, jobs, and history from endpoints.
    
    Returns:
        SchedulerManager instance
    """
    global _scheduler_manager
    return _scheduler_manager


# Job IDs for reference in endpoints
JOB_IDS = {
    'nightly_optimization': 'nightly_optimization',
    'governance_check': 'governance_check',
    'sync_ots': 'sync_ots',
}

JOB_NAMES = {
    'nightly_optimization': 'Nightly Route Optimization (Phase 3)',
    'governance_check': 'Governance Rule Checking',
    'sync_ots': 'OT Synchronization from TELCOS API',
}

JOB_SCHEDULES = {
    'nightly_optimization': 'Cron: 00:00 (midnight) daily',
    'governance_check': 'Interval: every 6 hours',
    'sync_ots': 'Interval: every 30 minutes',
}

