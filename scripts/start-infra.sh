#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Starting AURI.AI infrastructure..."
docker compose up -d postgres redis minio qdrant ollama

echo "Waiting for services..."
sleep 8

echo "Infra is up. Next:"
echo "  cd backend && pip install -r requirements.txt && alembic upgrade head"
echo "  uvicorn app.main:app --reload --port 8000"
