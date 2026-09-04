#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.bluegreen.yml"
STATE_FILE="${STATE_FILE:-$ROOT/.active_slot}"
ACTIVE="$(cat "$STATE_FILE" 2>/dev/null || echo blue)"
if [[ "$ACTIVE" == "blue" ]]; then NEXT=green; else NEXT=blue; fi
echo "==> Active slot: $ACTIVE → deploying $NEXT"
$COMPOSE build "backend-$NEXT"
$COMPOSE up -d "backend-$NEXT"
for i in $(seq 1 30); do
  PORT=$([ "$NEXT" = "blue" ] && echo 8001 || echo 8002)
  if curl -sf "http://127.0.0.1:${PORT}/ready" >/dev/null 2>&1; then
    echo "Ready on port $PORT"; break
  fi
  sleep 2
  if [[ $i -eq 30 ]]; then echo "ERROR: $NEXT failed readiness"; exit 1; fi
done
$COMPOSE run --rm "backend-$NEXT" alembic upgrade head || true
echo "$NEXT" > "$STATE_FILE"
$COMPOSE stop "backend-$ACTIVE" || true
echo "==> Blue/green complete. Live: $NEXT"
