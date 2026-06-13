#!/usr/bin/env bash
# Full first-time VPS deploy helper.
#
# Recommended clone path: /opt/car-backend
#
# Quick start on a fresh Debian VPS (as root):
#   adduser --disabled-password --gecos "" deploy
#   usermod -aG sudo deploy
#   git clone <your-repo-url> /opt/car-backend
#   cd /opt/car-backend
#   cp scripts/deploy/config.env.example scripts/deploy/config.env
#   # edit config.env: GIT_REPO, DOMAIN, APP_USER
#   sudo bash scripts/deploy/vps-first-deploy.sh
#
# Updates (after code changes):
#   sudo bash scripts/deploy/vps-update.sh
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/common.sh"
load_deploy_config

echo "=========================================="
echo " Car Backend — VPS first deploy"
echo " Domain:  ${DOMAIN}"
echo " App dir: ${APP_DIR}"
echo " User:    ${APP_USER}"
echo "=========================================="

if ! id "$APP_USER" &>/dev/null; then
  echo "==> Creating user ${APP_USER}..."
  adduser --disabled-password --gecos "" "$APP_USER"
fi

bash "$ROOT/scripts/deploy/01-install-system.sh"

if [[ -n "${GIT_REPO:-}" && ! -d "$APP_DIR/.git" ]]; then
  echo "==> Cloning ${GIT_REPO} -> ${APP_DIR}..."
  mkdir -p "$(dirname "$APP_DIR")"
  git clone "$GIT_REPO" "$APP_DIR"
fi

if [[ ! -f "$APP_DIR/pyproject.toml" ]]; then
  echo "Project not found at ${APP_DIR}."
  echo "Clone manually, then re-run:"
  echo "  git clone <repo> ${APP_DIR}"
  exit 1
fi

chown -R "$APP_USER:$APP_USER" "$APP_DIR"

if [[ "$USE_POSTGRES" == "true" ]]; then
  generate_db_password_if_needed
  export DB_PASS
fi

echo "==> PostgreSQL setup..."
setup_postgres_user

echo "==> App + venv + .env..."
sudo -u "$APP_USER" env DB_USER="${DB_USER}" DB_PASS="${DB_PASS}" DB_NAME="${DB_NAME}" bash "$APP_DIR/scripts/deploy/02-setup-app.sh"

echo "==> Database seed..."
sudo -u "$APP_USER" bash "$APP_DIR/scripts/deploy/03-seed-database.sh"

bash "$APP_DIR/scripts/deploy/04-install-systemd.sh"
bash "$APP_DIR/scripts/deploy/05-install-nginx.sh"

SSL_OK=false
if [[ "${ENABLE_SSL:-true}" == "true" && -n "${CERTBOT_EMAIL:-}" ]]; then
  echo "==> SSL certificate (certbot)..."
  if bash "$APP_DIR/scripts/deploy/06-install-ssl.sh"; then
    SSL_OK=true
  else
    echo "WARNING: SSL failed (DNS may not be ready). Run later:"
    echo "  sudo bash ${APP_DIR}/scripts/deploy/06-install-ssl.sh"
  fi
fi

echo ""
echo "=========================================="
echo " Deploy complete"
echo "=========================================="
if $SSL_OK; then
  echo " Users:  https://${DOMAIN}/"
  echo " Staff:  see ${APP_DIR}/.deploy-credentials.txt (UUID path)"
  echo " Health: https://${DOMAIN}/health"
else
  echo " Users:  http://${DOMAIN}/"
  echo " Staff:  see ${APP_DIR}/.deploy-credentials.txt (UUID path)"
  echo " Health: http://${DOMAIN}/health"
fi
echo ""
echo " Credentials: ${APP_DIR}/.deploy-credentials.txt"
echo " Logs:        journalctl -u car-backend.service -f"
echo "=========================================="
