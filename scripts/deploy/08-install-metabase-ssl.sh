#!/usr/bin/env bash
# HTTPS for Metabase at meta.car-alert.ir (or METABASE_HOST in config.env).
# Requires: DNS A record for METABASE_HOST → this VPS, nginx site for Metabase.
# Run as root: sudo bash scripts/deploy/08-install-metabase-ssl.sh
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

domain_has_dns() {
  local host="$1"
  local answer
  if command -v dig >/dev/null 2>&1; then
    answer="$(dig +short A "$host" 2>/dev/null | grep -E '^[0-9.]+$' | head -1 || true)"
    [[ -n "$answer" ]] && return 0
    answer="$(dig +short AAAA "$host" 2>/dev/null | head -1 || true)"
    [[ -n "$answer" ]]
    return
  fi
  getent ahosts "$host" >/dev/null 2>&1
}

export DEPLOY_ROOT="$ROOT"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/nginx.sh"

DOMAIN="$(read_cfg DOMAIN car-alert.ir)"
METABASE_HOST="$(read_cfg METABASE_HOST "meta.${DOMAIN}")"
METABASE_PORT="$(read_cfg METABASE_PORT 3000)"
CERTBOT_EMAIL="$(read_cfg CERTBOT_EMAIL mehrshad.sodoor2003@gmail.com)"
APP_DIR="$(read_cfg APP_DIR /opt/car-backend)"
SITE="/etc/nginx/sites-available/metabase"

if [[ -z "${CERTBOT_EMAIL:-}" ]]; then
  echo "Missing CERTBOT_EMAIL in $CONFIG_ENV"
  exit 1
fi

if ! domain_has_dns "$METABASE_HOST"; then
  echo "DNS not found for ${METABASE_HOST}"
  echo "Add an A record: meta → your VPS IP, wait a few minutes, then re-run."
  exit 1
fi

if ! command -v certbot >/dev/null 2>&1; then
  echo "Install certbot first: sudo bash $ROOT/scripts/deploy/01-install-system.sh"
  exit 1
fi

if [[ ! -f "$SITE" ]]; then
  echo "==> Creating nginx site for ${METABASE_HOST}..."
  LISTEN_LINES="$(nginx_listen_http)"
  cat >"$SITE" <<EOF
server {
${LISTEN_LINES}
    server_name ${METABASE_HOST};

    location / {
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
        proxy_pass http://127.0.0.1:${METABASE_PORT};
    }
}
EOF
  ln -sf "$SITE" /etc/nginx/sites-enabled/metabase
  nginx_test_and_start reload
fi

echo "==> SSL certificate for ${METABASE_HOST}"
echo "    Email: ${CERTBOT_EMAIL}"

certbot --nginx \
  -d "${METABASE_HOST}" \
  --non-interactive \
  --agree-tos \
  --email "${CERTBOT_EMAIL}" \
  --redirect \
  --no-eff-email

nginx_test_and_start reload

CREDS="${APP_DIR}/.metabase-credentials.txt"
if [[ -f "$CREDS" ]]; then
  sed -i "s|^URL: http://|URL: https://|" "$CREDS" 2>/dev/null || true
fi

echo ""
echo "Metabase HTTPS: https://${METABASE_HOST}/"
echo "Test: curl -I https://${METABASE_HOST}/"
