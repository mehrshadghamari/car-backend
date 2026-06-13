#!/usr/bin/env bash
# Insert Divar cities + car models into the database.
# Safe to run multiple times — skips rows that already exist (use --merge to refresh display names).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"

echo "==> Ensuring database schema..."
$PYTHON scripts/init_db.py
$PYTHON scripts/migrate_db.py

echo "==> Inserting Divar cities and car models..."
$PYTHON scripts/import_divar_reference_data.py "$@"
