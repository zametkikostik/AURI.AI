#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Building images"
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile app build

echo "==> Starting stack"
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile app up -d

echo "==> Waiting for postgres"
sleep 5

echo "==> Migrations"
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backend \
  alembic upgrade head || {
    echo "Trying local alembic..."
    (cd backend && alembic upgrade head)
  }

echo "==> Health"
curl -sf http://localhost:8000/health | head -c 500 || true
echo
echo "==> Deploy complete"
