#!/usr/bin/env bash
# Pull latest code and redeploy (safe to run after every git push).
#
# Usage (on VPS as root):
#   cd /opt/car-backend
#   sudo bash scripts/deploy/redeploy.sh
#
# Options (env):
#   SKIP_GIT=1          skip git pull
#   SKIP_MIGRATE=1      skip alembic + migrate_db.py
#   IMPORT_CATALOG=1    also reload Khodro45 + Divar catalog data
#   SKIP_NGINX=1        skip nginx reload (keeps HTTPS config if not skipped)
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export DEPLOY_ROOT="$ROOT"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/common.sh"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/nginx.sh"
load_deploy_config

VENV="$APP_DIR/venv"
HEALTH_URL="https://${DOMAIN}/health"
HTTP_HEALTH="http://${DOMAIN}/health"

echo "=========================================="
echo " Car Backend — redeploy"
echo " Domain:  ${DOMAIN}"
echo " App dir: ${APP_DIR}"
echo "=========================================="

if [[ ! -d "$APP_DIR/.git" ]]; then
  echo "ERROR: ${APP_DIR} is not a git repo"
  exit 1
fi

if [[ "${SKIP_GIT:-0}" != "1" ]]; then
  echo ""
  echo "==> [1/5] git pull..."
  sudo -u "$APP_USER" git -C "$APP_DIR" fetch origin
  sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only
  echo "    $(sudo -u "$APP_USER" git -C "$APP_DIR" log -1 --oneline)"
else
  echo ""
  echo "==> [1/5] git pull (skipped)"
fi

echo ""
echo "==> [2/5] Python dependencies..."
sudo -u "$APP_USER" bash -lc "
  set -euo pipefail
  source '${VENV}/bin/activate'
  pip install -q --upgrade pip wheel
  pip install -q -e '${APP_DIR}'
  pip install -q gunicorn
"

if [[ "${SKIP_MIGRATE:-0}" != "1" ]]; then
  echo ""
  echo "==> [3/5] Database migrations..."
  sudo -u "$APP_USER" bash -lc "
    set -euo pipefail
    source '${VENV}/bin/activate'
    export PYTHONPATH='${APP_DIR}'
    cd '${APP_DIR}'
    alembic upgrade head
    python3 scripts/migrate_db.py
  "
else
  echo ""
  echo "==> [3/5] Database migrations (skipped)"
fi

if [[ "${IMPORT_CATALOG:-0}" == "1" ]]; then
  echo ""
  echo "==> Importing catalog data..."
  sudo -u "$APP_USER" bash "$APP_DIR/scripts/load_all_catalog_data.sh" --merge
fi

echo ""
echo "==> [4/5] Nginx + systemd..."
if [[ "${SKIP_NGINX:-0}" != "1" ]]; then
  bash "$APP_DIR/scripts/deploy/05-install-nginx.sh"
else
  echo "    nginx (skipped)"
  systemctl restart car-backend.service
  systemctl restart car-backend-celery-worker.service 2>/dev/null || true
  systemctl restart car-backend-celery-beat.service 2>/dev/null || true
fi

echo ""
echo "==> [5/5] Health check..."
sleep 2

if [[ -S /run/car-backend/car-backend.sock ]]; then
  if curl -sf --unix-socket /run/car-backend/car-backend.sock http://localhost/health >/dev/null; then
    echo "    API socket: OK"
  else
    echo "    WARNING: socket exists but /health failed"
    journalctl -u car-backend.service -n 25 --no-pager || true
    exit 1
  fi
else
  echo "    ERROR: Gunicorn socket missing"
  journalctl -u car-backend.service -n 25 --no-pager || true
  exit 1
fi

if nginx_has_letsencrypt_cert "$DOMAIN"; then
  if curl -sf "$HEALTH_URL" >/dev/null; then
    echo "    HTTPS:      OK ($HEALTH_URL)"
  else
    echo "    WARNING: HTTPS health check failed — try: sudo bash scripts/deploy/fix-https.sh"
  fi
else
  if curl -sf "$HTTP_HEALTH" >/dev/null; then
    echo "    HTTP:       OK ($HTTP_HEALTH)"
    echo "    Tip: enable HTTPS with scripts/deploy/06-install-ssl.sh"
  else
    echo "    WARNING: public health check failed"
  fi
fi

STAFF_BASE=""
if [[ -f "$APP_DIR/.env" ]]; then
  u1="$(grep '^PORTAL_PATH_UUID_1=' "$APP_DIR/.env" | cut -d= -f2- | tr -d '"' || true)"
  u2="$(grep '^PORTAL_PATH_UUID_2=' "$APP_DIR/.env" | cut -d= -f2- | tr -d '"' || true)"
  if [[ -n "$u1" && -n "$u2" ]]; then
    STAFF_BASE="/portal/${u1}/${u2}"
  fi
fi

echo ""
echo "=========================================="
echo " Redeploy complete"
echo "=========================================="
echo " User site:  https://${DOMAIN}/"
if [[ -n "$STAFF_BASE" ]]; then
  echo " Admin:      https://${DOMAIN}${STAFF_BASE}/admin/"
  echo " API docs:   https://${DOMAIN}${STAFF_BASE}/docs"
fi
echo " Logs:       journalctl -u car-backend.service -f"
echo "=========================================="
