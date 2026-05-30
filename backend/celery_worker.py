"""
Celery Worker Entry Point
Run with: celery -A celery_worker worker --loglevel=info
"""
from app.tasks.eval_tasks import celery_app  # noqa: F401
