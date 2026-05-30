#!/bin/bash
# start.sh — Production startup script for Railway API service
# Runs DB migrations before starting the server (safe: alembic is idempotent)

set -e  # Exit on any error

echo "🚀 EvalForge API starting..."
echo "   Environment: ${ENVIRONMENT:-production}"
echo "   Port: ${PORT:-8000}"

# ── Run migrations ────────────────────────────────────────────────────────────
echo "🔄 Running database migrations..."
alembic upgrade head
echo "✅ Migrations complete"

# ── Start server ──────────────────────────────────────────────────────────────
echo "🌐 Starting API server..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 2 \
    --log-level info \
    --access-log
