#!/usr/bin/env bash
# First-time local setup (SQLite + Python on host). Run once per machine/clone.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"

echo "==> Car Backend — local first-run setup"
echo "    Project: $ROOT"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "    Created .env from .env.example (SQLite)"
fi

mkdir -p data .pids

echo "==> Installing Python dependencies..."
$PYTHON -m pip install -e ".[dev]"

echo "==> Creating database tables..."
$PYTHON scripts/init_db.py

echo "==> Applying schema migrations..."
$PYTHON scripts/migrate_db.py

echo "==> Loading catalog data (Khodro45 4-layer + Divar + platforms)..."
bash scripts/load_all_catalog_data.sh --merge

echo ""
echo "Local first-run complete."
echo ""
echo "Next:"
echo "  bash scripts/local-up.sh      # start API (+ Celery if Redis is up)"
echo "  bash scripts/local-down.sh    # stop"
echo ""
echo "URLs (after local-up):"
echo "  User portal:   http://127.0.0.1:8000/"
echo "  Staff admin:   http://127.0.0.1:8000/portal/a1b2c3d4-e5f6-7890-abcd-ef1234567890/b2c3d4e5-f6a7-8901-bcde-f12345678901/admin/"
echo "  API docs:      http://127.0.0.1:8000/portal/a1b2c3d4-e5f6-7890-abcd-ef1234567890/b2c3d4e5-f6a7-8901-bcde-f12345678901/docs"
echo "  Crawl results: http://127.0.0.1:8000/portal/a1b2c3d4-e5f6-7890-abcd-ef1234567890/b2c3d4e5-f6a7-8901-bcde-f12345678901/results"
