#!/usr/bin/env bash
# Initialize DB, run migrations, import Divar reference data, seed catalog.
# Run as APP_USER from project root after 02-setup-app.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/common.sh"
load_deploy_config

# shellcheck disable=SC1091
source "$APP_DIR/venv/bin/activate"
export PYTHONPATH="$APP_DIR"

if [[ ! -f "$APP_DIR/.env" ]]; then
  echo "Missing $APP_DIR/.env — run 02-setup-app.sh first"
  exit 1
fi

echo "==> Seeding database (this may take a few minutes)..."

cd "$APP_DIR"
python3 scripts/init_db.py
python3 scripts/migrate_db.py

# init_db creates the full schema from SQLAlchemy models; do not run alembic upgrade
# here or it tries to CREATE TABLE again. Stamp head so future updates use alembic.
echo "==> Stamping Alembic revision (schema already applied)..."
alembic stamp head

python3 scripts/import_divar_reference_data.py
python3 scripts/seed_catalog.py

echo ""
echo "Database ready."
echo "Next: sudo bash scripts/deploy/04-install-systemd.sh"
