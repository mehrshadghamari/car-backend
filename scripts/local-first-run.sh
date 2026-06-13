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

echo "==> Importing Divar cities and car models..."
$PYTHON scripts/import_divar_reference_data.py

echo "==> Seeding car catalog (Peugeot 207, Divar + Khodro45 + Hamrah)..."
$PYTHON scripts/seed_catalog.py

echo ""
echo "Local first-run complete."
echo ""
echo "Next:"
echo "  bash scripts/local-up.sh      # start API (+ Celery if Redis is up)"
echo "  bash scripts/local-down.sh    # stop"
echo ""
echo "URLs (after local-up):"
echo "  Landing:       http://127.0.0.1:8000/"
echo "  Crawl results: http://127.0.0.1:8000/results"
echo "  Admin:         http://127.0.0.1:8000/admin/  (admin / admin)"
echo "  API docs:      http://127.0.0.1:8000/docs"
