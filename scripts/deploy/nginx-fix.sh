#!/usr/bin/env bash
# Fix nginx when vps-first-deploy failed at "enable nginx".
# Run as root: sudo bash scripts/deploy/nginx-fix.sh
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/nginx.sh"

echo "==> Diagnosing nginx..."
nginx_diagnose

echo ""
echo "==> Applying baseline fix..."
ensure_nginx_baseline

if [[ -f "$ROOT/scripts/deploy/config.env" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/scripts/deploy/lib/common.sh"
  load_deploy_config
  if [[ -f "$ROOT/pyproject.toml" ]]; then
    echo ""
    echo "==> Re-applying app nginx site..."
    bash "$ROOT/scripts/deploy/05-install-nginx.sh" || true
  fi
fi

echo ""
echo "Done. Test: curl -I http://127.0.0.1/"
