#!/usr/bin/env bash
# Pull latest code, reinstall deps, migrate DB, restart services.
# Run as root: sudo bash scripts/deploy/vps-update.sh
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/common.sh"
load_deploy_config

echo "==> Updating Car Backend at ${APP_DIR}..."

sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only

sudo -u "$APP_USER" bash -lc "
  set -euo pipefail
  source '${APP_DIR}/venv/bin/activate'
  pip install -e '${APP_DIR}'
  pip install gunicorn
  export PYTHONPATH='${APP_DIR}'
  cd '${APP_DIR}'
  alembic upgrade head
  python3 scripts/migrate_db.py
"

systemctl restart car-backend.service
systemctl restart car-backend-celery-worker.service 2>/dev/null || true
systemctl restart car-backend-celery-beat.service 2>/dev/null || true

echo "Update complete. Check: curl -s http://${DOMAIN}/health"
