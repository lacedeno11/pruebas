from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services import PlanningService, GovernanceService
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def nocturnal_route_optimization():
    """
    Runs at 00:00 daily to recalculate centroids and optimize routes
    """
    db: Session = SessionLocal()
    try:
        settings = get_settings()
        planning_service = PlanningService()
        planning_service.normalize_routes_nocturnal(db)
        logger.info("Nocturnal route optimization completed successfully")
    except Exception as e:
        logger.error(f"Error in nocturnal_route_optimization: {str(e)}")
    finally:
        db.close()


def governance_check():
    """
    Runs every 6 hours to check detention alerts and auto-cancel inactive OTs
    """
    db: Session = SessionLocal()
    try:
        settings = get_settings()
        governance_service = GovernanceService()
        
        # Check detention alerts
        alerted_ots = governance_service.check_detention_alerts(db)
        logger.info(f"Detention alerts check completed: {len(alerted_ots)} OTs alerted")
        
        # Auto-cancel inactive OTs
        cancelled_count = governance_service.auto_cancel_inactive(db)
        logger.info(f"Auto-cancellation completed: {cancelled_count} OTs cancelled")
        
        # Check preplanned timeout
        timeout_ots = governance_service.check_preplanned_timeout(db)
        logger.info(f"Preplanned timeout check completed: {len(timeout_ots)} OTs in timeout")
        
    except Exception as e:
        logger.error(f"Error in governance_check: {str(e)}")
    finally:
        db.close()


def start_scheduler():
    """
    Initialize and start the APScheduler background scheduler
    """
    try:
        settings = get_settings()
        
        # Add nocturnal route optimization job (daily at 00:00)
        scheduler.add_job(
            nocturnal_route_optimization,
            'cron',
            hour=0,
            minute=0,
            id='nocturnal_route_optimization',
            name='Nocturnal Route Optimization',
            replace_existing=True
        )
        
        # Add governance check job (every 6 hours)
        scheduler.add_job(
            governance_check,
            'cron',
            hour='*/6',
            id='governance_check',
            name='Governance Check',
            replace_existing=True
        )
        
        # Start the scheduler
        if not scheduler.running:
            scheduler.start()
            logger.info("APScheduler started successfully")
        else:
            logger.info("APScheduler already running")
            
    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}")


def stop_scheduler():
    """
    Gracefully shutdown the scheduler
    """
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("APScheduler shutdown successfully")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {str(e)}")

