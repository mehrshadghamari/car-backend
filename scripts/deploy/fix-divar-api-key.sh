#!/usr/bin/env bash
# Copy DIVAR_OPEN_API_KEY from scripts/deploy/config.env or project .env into production .env
# Run as root: sudo bash scripts/deploy/fix-divar-api-key.sh
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/common.sh"
load_deploy_config

if [[ -z "${DIVAR_OPEN_API_KEY:-}" ]]; then
  echo "ERROR: DIVAR_OPEN_API_KEY is empty."
  echo "Set it in scripts/deploy/config.env or in ${ROOT}/.env"
  exit 1
fi

patch_divar_api_key

echo "==> Restarting car-backend + celery..."
systemctl restart car-backend.service 2>/dev/null || true
systemctl restart car-backend-celery-worker.service 2>/dev/null || true

echo ""
echo "Divar API key configured."
echo "  Key prefix: ${DIVAR_OPEN_API_KEY:0:20}..."
