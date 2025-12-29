"""Celery application configuration."""

from celery import Celery

from ehr_service.config import settings

celery_app = Celery(
    "ehr_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["ehr_service.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
