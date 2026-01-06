"""
DERCAS-ONCO-XAI V1 - Inference Service Celery Application

Celery application for asynchronous ML processing tasks.
"""

import logging
from celery import Celery
from celery.signals import worker_ready, worker_shutdown

from .config import get_celery_config, get_settings

logger = logging.getLogger(__name__)

# Create Celery application
celery_config = get_celery_config()
celery_app = Celery("inference_service")
celery_app.config_from_object(celery_config)

# Auto-discover tasks
celery_app.autodiscover_tasks(['apps.inference_service.tasks'])


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handle worker ready signal."""
    logger.info("Celery worker ready for inference processing")
    
    # Initialize ML models when worker starts
    from .models_ml import initialize_models
    import asyncio
    
    try:
        # Run async model initialization in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(initialize_models())
        loop.close()
        
        if success:
            logger.info("ML models initialized successfully in Celery worker")
        else:
            logger.error("Failed to initialize ML models in Celery worker")
    except Exception as e:
        logger.error(f"Error initializing ML models in Celery worker: {e}")


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handle worker shutdown signal."""
    logger.info("Celery worker shutting down")
    
    # Cleanup ML models when worker shuts down
    from .models_ml import shutdown_models
    import asyncio
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(shutdown_models())
        loop.close()
        logger.info("ML models cleaned up successfully")
    except Exception as e:
        logger.error(f"Error cleaning up ML models: {e}")


# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        'inference.tasks.process_image': {'queue': 'inference_queue'},
        'inference.tasks.generate_xai': {'queue': 'xai_queue'},
        'inference.tasks.validate_results': {'queue': 'validation_queue'},
    },
    
    # Task execution
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task tracking
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes
    task_soft_time_limit=1740,  # 29 minutes
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    
    # Compression
    task_compression='gzip',
    result_compression='gzip',
    
    # Result backend
    result_expires=3600,  # 1 hour
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)


def get_celery_app():
    """Get the Celery application instance."""
    return celery_app
