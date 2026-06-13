#!/usr/bin/env bash
# Obtain Let's Encrypt certificate via certbot + nginx plugin, enable HTTPS redirect.
# Requires: DNS for DOMAIN already points to this server, nginx site on port 80 is live.
# Run as root: sudo bash scripts/deploy/06-install-ssl.sh
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/common.sh"
load_deploy_config

if [[ -z "${CERTBOT_EMAIL:-}" ]]; then
  echo "Set CERTBOT_EMAIL in scripts/deploy/config.env (Let's Encrypt notifications)."
  echo "Example: CERTBOT_EMAIL=admin@${DOMAIN}"
  exit 1
fi

if ! command -v certbot >/dev/null 2>&1; then
  echo "certbot not installed — run 01-install-system.sh first"
  exit 1
fi

echo "==> Requesting SSL certificate for ${DOMAIN} and www.${DOMAIN}..."
echo "    Email: ${CERTBOT_EMAIL}"

certbot --nginx \
  -d "${DOMAIN}" \
  -d "www.${DOMAIN}" \
  --non-interactive \
  --agree-tos \
  --email "${CERTBOT_EMAIL}" \
  --redirect \
  --no-eff-email

nginx -t
systemctl reload nginx

patch_app_env_https
chown "${APP_USER}:${APP_USER}" "$APP_DIR/.env" 2>/dev/null || true

systemctl restart car-backend.service 2>/dev/null || true
systemctl restart car-backend-celery-worker.service 2>/dev/null || true
systemctl restart car-backend-celery-beat.service 2>/dev/null || true

HOOK_DIR="/etc/letsencrypt/renewal-hooks/deploy"
mkdir -p "$HOOK_DIR"
cat >"$HOOK_DIR/car-backend-reload.sh" <<EOF
#!/usr/bin/env bash
systemctl reload nginx
systemctl restart car-backend.service
EOF
chmod +x "$HOOK_DIR/car-backend-reload.sh"

echo ""
echo "HTTPS enabled: https://${DOMAIN}/"
echo "Certificate auto-renewal: systemctl status certbot.timer"
echo "Test renewal (dry-run): certbot renew --dry-run"
