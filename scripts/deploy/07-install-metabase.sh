#!/usr/bin/env bash
# Install Metabase (Docker) on meta.car-alert.ir + read-only DB user.
# Debian VPS — needs ~512 MB RAM extra for Metabase.
# Run as root: sudo bash scripts/deploy/07-install-metabase.sh
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

METABASE_PORT="${METABASE_PORT:-3000}"
METABASE_HOST="${METABASE_HOST:-meta.${DOMAIN}}"
METABASE_DB_PASS="${METABASE_DB_PASS:-$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 24)}"
METABASE_DATA="/var/lib/metabase"

if [[ "$USE_POSTGRES" != "true" ]]; then
  echo "Metabase needs PostgreSQL. Set USE_POSTGRES=true in config.env."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "==> Installing Docker on Debian..."
  apt update
  apt install -y ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt update
  apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

echo "==> Creating read-only DB user metabase_readonly..."
sed "s/YOUR_STRONG_PASSWORD/${METABASE_DB_PASS}/" "$ROOT/scripts/deploy/sql/metabase-setup.sql" \
  | sudo -u postgres psql -v ON_ERROR_STOP=1 -d "$DB_NAME"

mkdir -p "$METABASE_DATA"
chmod 755 "$METABASE_DATA"

echo "==> Starting Metabase container..."
docker rm -f metabase 2>/dev/null || true
docker run -d \
  --name metabase \
  --restart unless-stopped \
  -p "127.0.0.1:${METABASE_PORT}:3000" \
  -v "${METABASE_DATA}:/metabase-data" \
  -e "MB_DB_FILE=/metabase-data/metabase.db" \
  metabase/metabase:latest

SITE="/etc/nginx/sites-available/metabase"
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

CREDS="${APP_DIR}/.metabase-credentials.txt"
cat >"$CREDS" <<EOF
Metabase — $(date -Iseconds)
URL: http://${METABASE_HOST}/
Local: http://127.0.0.1:${METABASE_PORT}/

PostgreSQL connection (use in Metabase setup wizard):
  Type:     PostgreSQL
  Host:     localhost
  Port:     5432
  Database: ${DB_NAME}
  Username: metabase_readonly
  Password: ${METABASE_DB_PASS}

SSL (after DNS for ${METABASE_HOST} points to server):
  sudo bash ${APP_DIR}/scripts/deploy/08-install-metabase-ssl.sh
EOF
chmod 600 "$CREDS"

echo ""
echo "Metabase installed."
if [[ -f /etc/letsencrypt/live/${METABASE_HOST}/fullchain.pem ]]; then
  echo "  Open: https://${METABASE_HOST}/"
else
  echo "  Open: http://${METABASE_HOST}/"
  echo "  HTTPS:  sudo bash ${APP_DIR}/scripts/deploy/08-install-metabase-ssl.sh"
fi
echo "  Credentials saved: ${CREDS}"
echo ""
echo "First visit: create Metabase admin account, then add PostgreSQL database with settings above."
echo "Useful views: v_purchase_requests_detail, v_opportunities_detail, v_sms_deliveries, v_crawl_runs_daily"
