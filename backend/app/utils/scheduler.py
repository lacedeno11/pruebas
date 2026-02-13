import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


async def check_detained_alerts_job():
    """Scheduled job to check for OTs detained and trigger alerts on days 20, 25, 29."""
    try:
        from backend.app.agents.gobernanza_agent import GobernanzaAgent
        from backend.app.core import get_db
        
        agent = GobernanzaAgent()
        db = next(get_db())
        try:
            await agent.check_detained_ots({"ot_id": None, "db": db})
            logger.info("check_detained_alerts_job completed successfully")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in check_detained_alerts_job: {str(e)}")


async def auto_cancel_detained_ots_job():
    """Scheduled job to automatically cancel OTs detained for more than 30 days."""
    try:
        from backend.app.agents.gobernanza_agent import GobernanzaAgent
        from backend.app.core import get_db
        
        agent = GobernanzaAgent()
        db = next(get_db())
        try:
            await agent.auto_cancel_ots({"ot_id": None, "db": db})
            logger.info("auto_cancel_detained_ots_job completed successfully")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in auto_cancel_detained_ots_job: {str(e)}")


async def check_preplanificada_alerts_job():
    """Scheduled job to check for OTs in PREPLANIFICADA status for more than 48 hours."""
    try:
        from backend.app.agents.gobernanza_agent import GobernanzaAgent
        from backend.app.core import get_db
        
        agent = GobernanzaAgent()
        db = next(get_db())
        try:
            await agent.check_preplanificada_alerts({"ot_id": None, "db": db})
            logger.info("check_preplanificada_alerts_job completed successfully")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in check_preplanificada_alerts_job: {str(e)}")


async def nightly_route_optimization_job():
    """Scheduled job for nocturnal route optimization (stub implementation)."""
    try:
        from backend.app.agents.gobernanza_agent import GobernanzaAgent
        from backend.app.core import get_db
        
        agent = GobernanzaAgent()
        db = next(get_db())
        try:
            # Stub implementation - placeholder for future nocturnal optimization
            logger.info("nightly_route_optimization_job: Running nocturnal route optimization")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in nightly_route_optimization_job: {str(e)}")


def setup_scheduler() -> AsyncIOScheduler:
    """
    Set up and return an AsyncIOScheduler with cron jobs for the PEI Platform.
    
    Scheduled jobs:
    - check_detained_alerts: Daily at 09:00
    - auto_cancel_detained_ots: Daily at 00:01
    - check_preplanificada_alerts: Every 6 hours (00:00, 06:00, 12:00, 18:00)
    - nightly_route_optimization: Daily at 00:00
    
    Returns:
        AsyncIOScheduler: Configured scheduler instance ready to start
    """
    scheduler = AsyncIOScheduler()
    
    # Check detained OT alerts daily at 09:00
    scheduler.add_job(
        check_detained_alerts_job,
        trigger=CronTrigger(hour=9, minute=0),
        id="check_detained_alerts",
        name="Check Detained OT Alerts",
        replace_existing=True,
    )
    
    # Auto-cancel OTs detained for >30 days daily at 00:01
    scheduler.add_job(
        auto_cancel_detained_ots_job,
        trigger=CronTrigger(hour=0, minute=1),
        id="auto_cancel_detained_ots",
        name="Auto-Cancel Detained OTs",
        replace_existing=True,
    )
    
    # Check PREPLANIFICADA alerts every 6 hours
    scheduler.add_job(
        check_preplanificada_alerts_job,
        trigger=CronTrigger(hour="0,6,12,18", minute=0),
        id="check_preplanificada_alerts",
        name="Check PREPLANIFICADA Alerts",
        replace_existing=True,
    )
    
    # Nightly route optimization daily at 00:00
    scheduler.add_job(
        nightly_route_optimization_job,
        trigger=CronTrigger(hour=0, minute=0),
        id="nightly_route_optimization",
        name="Nightly Route Optimization",
        replace_existing=True,
    )
    
    logger.info("Scheduler configured with 4 jobs")
    return scheduler

