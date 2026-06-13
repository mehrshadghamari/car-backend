#!/usr/bin/env bash
# Ensure secret staff URL UUIDs exist in .env and print private admin/docs/dashboard links.
# Run as root: sudo bash scripts/deploy/fix-portal-routing.sh
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/common.sh"
load_deploy_config

ENV_FILE="$APP_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — run 02-setup-app.sh first"
  exit 1
fi

uuid1="${PORTAL_PATH_UUID_1:-}"
uuid2="${PORTAL_PATH_UUID_2:-}"

if [[ -z "$uuid1" ]] || ! grep -q '^PORTAL_PATH_UUID_1=' "$ENV_FILE" 2>/dev/null; then
  uuid1="$(generate_uuid)"
  if grep -q '^PORTAL_PATH_UUID_1=' "$ENV_FILE"; then
    sed -i "s/^PORTAL_PATH_UUID_1=.*/PORTAL_PATH_UUID_1=${uuid1}/" "$ENV_FILE"
  else
    echo "PORTAL_PATH_UUID_1=${uuid1}" >>"$ENV_FILE"
  fi
else
  uuid1="$(grep '^PORTAL_PATH_UUID_1=' "$ENV_FILE" | cut -d= -f2- | tr -d '"')"
fi

if [[ -z "$uuid2" ]] || ! grep -q '^PORTAL_PATH_UUID_2=' "$ENV_FILE" 2>/dev/null; then
  uuid2="$(generate_uuid)"
  if grep -q '^PORTAL_PATH_UUID_2=' "$ENV_FILE"; then
    sed -i "s/^PORTAL_PATH_UUID_2=.*/PORTAL_PATH_UUID_2=${uuid2}/" "$ENV_FILE"
  else
    echo "PORTAL_PATH_UUID_2=${uuid2}" >>"$ENV_FILE"
  fi
else
  uuid2="$(grep '^PORTAL_PATH_UUID_2=' "$ENV_FILE" | cut -d= -f2- | tr -d '"')"
fi

staff_base="/portal/${uuid1}/${uuid2}"
chown "${APP_USER}:${APP_USER}" "$ENV_FILE" 2>/dev/null || true
chmod 600 "$ENV_FILE"

echo "==> Restarting car-backend..."
systemctl restart car-backend.service 2>/dev/null || systemctl restart car-backend 2>/dev/null || true

{
  echo ""
  echo "Portal routing — $(date -Iseconds)"
  echo ""
  echo "Public (users only):"
  echo "  https://${DOMAIN}/"
  echo ""
  echo "Staff (keep private — two UUID path segments):"
  echo "  Admin:         https://${DOMAIN}${staff_base}/admin/"
  echo "  API docs:      https://${DOMAIN}${staff_base}/docs"
  echo "  Crawl results: https://${DOMAIN}${staff_base}/results"
  echo "  Trim mapping:  https://${DOMAIN}${staff_base}/trim-mapping"
  echo ""
  echo "Old URLs (/admin, /docs, /results) return 404."
} | tee -a "$APP_DIR/.deploy-credentials.txt"

echo ""
echo "Saved to ${APP_DIR}/.deploy-credentials.txt"
