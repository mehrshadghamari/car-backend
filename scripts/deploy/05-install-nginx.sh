#!/usr/bin/env bash
# Nginx reverse proxy to Gunicorn unix socket for car-alert.ir
# Preserves HTTPS if Let's Encrypt cert already exists (safe to re-run after git pull).
# Run as root: sudo bash scripts/deploy/05-install-nginx.sh
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/common.sh"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/nginx.sh"
load_deploy_config

SOCKET_PATH="/run/car-backend/car-backend.sock"
SITE="/etc/nginx/sites-available/car-backend"

echo "==> Installing Nginx site for ${DOMAIN}..."

if nginx_write_car_backend_site "$SITE" "$DOMAIN" "$APP_DIR" "$SOCKET_PATH"; then
  echo "    HTTPS enabled (Let's Encrypt cert found)"
  patch_app_env_https
else
  echo "    HTTP only — run: sudo bash ${APP_DIR}/scripts/deploy/06-install-ssl.sh"
fi

rm -f /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-enabled/000-car-backend-baseline
ln -sf "$SITE" /etc/nginx/sites-enabled/car-backend

nginx_test_and_start reload

systemctl restart car-backend.service 2>/dev/null || true

echo ""
if nginx_has_letsencrypt_cert "$DOMAIN"; then
  echo "Site: https://${DOMAIN}/"
else
  echo "Site: http://${DOMAIN}/"
  echo ""
  echo "HTTPS:"
  echo "  sudo bash ${APP_DIR}/scripts/deploy/06-install-ssl.sh"
fi
