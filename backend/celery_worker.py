"""
celery_worker.py — Entrypoint for running the Celery worker process.
Import celery_app from celery_app.py (not from eval_tasks.py).
Run with: celery -A celery_worker worker --loglevel=info
"""
from celery_app import celery_app  # noqa: F401

# Import tasks so Celery registers them
import app.tasks.eval_tasks  # noqa: F401
