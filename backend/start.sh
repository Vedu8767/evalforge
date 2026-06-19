#!/bin/bash
echo "🚀 EvalForge starting..."
echo "   Port: ${PORT:-8000}"

# Start Celery worker in background
celery -A celery_worker worker --loglevel=info --concurrency=1 &
echo "✅ Celery worker started in background"

# Start API server in foreground
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1 \
    --log-level info
