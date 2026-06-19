"""
celery_app.py — Single source of truth for the Celery application instance.
Both celery_worker.py and eval_tasks.py import from HERE, breaking the circular import.
"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "evalforge",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.eval_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)
