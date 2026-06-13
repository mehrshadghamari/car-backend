#!/usr/bin/env bash
# Restart car-backend API and fix 502 when nginx cannot reach the unix socket.
# Run as root: sudo bash scripts/deploy/fix-car-backend-502.sh
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export DEPLOY_ROOT="$ROOT"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/common.sh"
load_deploy_config

SOCKET_PATH="/run/car-backend/car-backend.sock"

echo "==> Fixing car-backend 502 (socket: ${SOCKET_PATH})"

if [[ -f "$ROOT/scripts/deploy/04-install-systemd.sh" ]]; then
  bash "$ROOT/scripts/deploy/04-install-systemd.sh"
else
  systemctl daemon-reload
  systemctl enable car-backend.service
  systemctl restart car-backend.service
fi

sleep 2

if [[ ! -S "$SOCKET_PATH" ]]; then
  echo ""
  echo "ERROR: Socket still missing. Recent logs:"
  journalctl -u car-backend.service -n 40 --no-pager || true
  exit 1
fi

if ! curl -sf --unix-socket "$SOCKET_PATH" http://localhost/health >/dev/null; then
  echo "ERROR: Socket exists but /health failed"
  journalctl -u car-backend.service -n 40 --no-pager || true
  exit 1
fi

# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/nginx.sh"
nginx_test_and_start reload

echo ""
echo "Fixed."
echo "  Socket:  $SOCKET_PATH"
echo "  Health:  curl --unix-socket $SOCKET_PATH http://localhost/health"
echo "  Public:  curl -I https://${DOMAIN}/health"
