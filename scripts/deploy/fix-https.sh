#!/usr/bin/env bash
# Restore HTTPS after nginx was overwritten, or obtain cert if missing.
# Run as root: sudo bash scripts/deploy/fix-https.sh
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

if nginx_has_letsencrypt_cert "$DOMAIN"; then
  echo "==> Let's Encrypt cert found — reinstalling nginx with HTTPS..."
  bash "$ROOT/scripts/deploy/05-install-nginx.sh"
else
  echo "==> No certificate yet — running certbot..."
  bash "$ROOT/scripts/deploy/06-install-ssl.sh"
fi

echo ""
echo "Verify:"
echo "  curl -I https://${DOMAIN}/health"
echo "  curl -I http://${DOMAIN}/   # should 301 to https"
