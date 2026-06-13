#!/usr/bin/env bash
# Enable OTP sandbox on production (no SMS.ir needed). Test code: 11111
# Run as root: sudo bash scripts/deploy/fix-otp-sandbox.sh
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
  echo "Missing $ENV_FILE"
  exit 1
fi

if grep -q '^OTP_SANDBOX=' "$ENV_FILE"; then
  sed -i 's/^OTP_SANDBOX=.*/OTP_SANDBOX=true/' "$ENV_FILE"
else
  echo 'OTP_SANDBOX=true' >>"$ENV_FILE"
fi

if grep -q '^OTP_SANDBOX_CODE=' "$ENV_FILE"; then
  sed -i 's/^OTP_SANDBOX_CODE=.*/OTP_SANDBOX_CODE=11111/' "$ENV_FILE"
else
  echo 'OTP_SANDBOX_CODE=11111' >>"$ENV_FILE"
fi

chown "${APP_USER}:${APP_USER}" "$ENV_FILE" 2>/dev/null || true
chmod 600 "$ENV_FILE"

echo "==> Restarting car-backend..."
systemctl restart car-backend.service 2>/dev/null || systemctl restart car-backend 2>/dev/null || true

echo ""
echo "OTP sandbox enabled."
echo "  Portal login test code: 11111"
echo "  User portal: https://${DOMAIN}/"
