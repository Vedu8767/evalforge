#!/bin/bash
set -e

echo "🚀 EvalForge API starting..."
echo "   Environment: ${ENVIRONMENT:-production}"
echo "   Port: ${PORT:-8000}"

echo "🌐 Starting API server..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1 \
    --log-level info
