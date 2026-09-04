#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${BACKUP_DIR:-$ROOT/backups}/$STAMP"
mkdir -p "$OUT_DIR"
echo "==> Backup to $OUT_DIR"
if docker compose -f "$ROOT/docker-compose.yml" ps postgres 2>/dev/null | grep -q Up; then
  docker compose -f "$ROOT/docker-compose.yml" exec -T postgres \
    pg_dump -U "${POSTGRES_USER:-auri}" "${POSTGRES_DB:-auri}" \
    | gzip > "$OUT_DIR/postgres.sql.gz"
  echo "Postgres dump OK"
else
  echo "WARN: postgres container not running — skip DB dump"
fi
if curl -sf "http://localhost:6333/collections" >/dev/null 2>&1; then
  curl -sf -X POST "http://localhost:6333/collections/${QDRANT_COLLECTION:-meetings}/snapshots" \
    -o "$OUT_DIR/qdrant_snapshot.json" || true
fi
{
  echo "stamp=$STAMP"
  echo "host=$(hostname)"
  echo "ai_mode=${AI_MODE:-unknown}"
} > "$OUT_DIR/meta.txt"
echo "==> Done: $OUT_DIR"
