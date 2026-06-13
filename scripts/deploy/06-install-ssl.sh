#!/usr/bin/env bash
# Obtain Let's Encrypt certificate via certbot + nginx plugin, enable HTTPS redirect.
# Run as root: sudo bash scripts/deploy/06-install-ssl.sh
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_ENV="$ROOT/scripts/deploy/config.env"
CONFIG_EXAMPLE="$ROOT/scripts/deploy/config.env.example"

read_cfg() {
  local key="$1"
  local default="${2:-}"
  local val="" file key_line
  for file in "$CONFIG_ENV" "$CONFIG_EXAMPLE"; do
    [[ -f "$file" ]] || continue
    key_line="$(grep -E "^${key}=" "$file" | tail -1 || true)"
    [[ -n "$key_line" ]] || continue
    val="${key_line#${key}=}"
    val="${val%\"}"
    val="${val#\"}"
    val="${val//$'\r'/}"
    break
  done
  if [[ -n "$val" ]]; then
    printf '%s' "$val"
  else
    printf '%s' "$default"
  fi
}

export DEPLOY_ROOT="$ROOT"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/common.sh"

DOMAIN="${DOMAIN:-$(read_cfg DOMAIN car-alert.ir)}"
APP_DIR="${APP_DIR:-$(read_cfg APP_DIR /opt/car-backend)}"
APP_USER="${APP_USER:-$(read_cfg APP_USER deploy)}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-$(read_cfg CERTBOT_EMAIL mehrshad.sodoor2003@gmail.com)}"

if [[ -z "${CERTBOT_EMAIL:-}" ]]; then
  echo "Missing CERTBOT_EMAIL. Edit: $CONFIG_ENV"
  exit 1
fi

if ! command -v certbot >/dev/null 2>&1; then
  echo "certbot not installed — run 01-install-system.sh first"
  exit 1
fi

echo "==> Requesting SSL certificate for ${DOMAIN} and www.${DOMAIN}..."
echo "    Config: ${CONFIG_ENV}"
echo "    Email:  ${CERTBOT_EMAIL}"

certbot --nginx \
  -d "${DOMAIN}" \
  -d "www.${DOMAIN}" \
  --non-interactive \
  --agree-tos \
  --email "${CERTBOT_EMAIL}" \
  --redirect \
  --no-eff-email

# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/nginx.sh"
nginx_test_and_start reload

patch_app_env_https
chown "${APP_USER}:${APP_USER}" "$APP_DIR/.env" 2>/dev/null || true

systemctl restart car-backend.service 2>/dev/null || true
systemctl restart car-backend-celery-worker.service 2>/dev/null || true
systemctl restart car-backend-celery-beat.service 2>/dev/null || true

HOOK_DIR="/etc/letsencrypt/renewal-hooks/deploy"
mkdir -p "$HOOK_DIR"
cat >"$HOOK_DIR/car-backend-reload.sh" <<'EOF'
#!/usr/bin/env bash
systemctl reload nginx
systemctl restart car-backend.service
EOF
chmod +x "$HOOK_DIR/car-backend-reload.sh"

echo ""
echo "HTTPS enabled: https://${DOMAIN}/"
echo "Test: curl -I https://${DOMAIN}/health"
echo "Renewal check: certbot renew --dry-run"
