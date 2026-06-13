#!/usr/bin/env bash
# Install Metabase (Docker) on meta.car-alert.ir — connect to main app PostgreSQL.
# Optional read-only user: set METABASE_USE_READONLY=true in config.env first.
# Run as root: sudo bash scripts/deploy/07-install-metabase.sh
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export DEPLOY_ROOT="$ROOT"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/common.sh"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/nginx.sh"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/metabase-postgres.sh"
load_deploy_config

METABASE_PORT="${METABASE_PORT:-3000}"
METABASE_HOST="${METABASE_HOST:-meta.${DOMAIN}}"
METABASE_ADMIN_EMAIL="${METABASE_ADMIN_EMAIL:-mehrshad.sodoor2003@gmail.com}"
METABASE_ADMIN_PASSWORD="${METABASE_ADMIN_PASSWORD:-CarAlertMeta2026}"
METABASE_DATA="/var/lib/metabase"
PG_HOST_FOR_METABASE="127.0.0.1"

# Default: same credentials as the FastAPI app (full access in Metabase).
MB_DB_USER="$DB_USER"
MB_DB_PASS="$DB_PASS"

if [[ "${METABASE_USE_READONLY:-false}" == "true" ]]; then
  echo "==> Creating optional read-only Metabase user (metabase_readonly)..."
  MB_DB_USER="${METABASE_DB_USER:-metabase_readonly}"
  MB_DB_PASS="${METABASE_DB_PASS:-CarAlertMetaDb2026}"
  sed "s/YOUR_STRONG_PASSWORD/${MB_DB_PASS//\//\\/}/g" \
    "$ROOT/scripts/deploy/sql/metabase-setup.sql" \
    | sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1
  ensure_metabase_pg_access "$DB_NAME" "$MB_DB_USER"
else
  echo "==> Metabase will use main app database user (${DB_USER})"
  ensure_metabase_pg_access "$DB_NAME" "$DB_USER"
fi

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

mkdir -p "$METABASE_DATA"
chmod 755 "$METABASE_DATA"

echo "==> Starting Metabase (host network — Postgres host: 127.0.0.1)..."
docker rm -f metabase 2>/dev/null || true
docker run -d \
  --name metabase \
  --restart unless-stopped \
  --network host \
  -v "${METABASE_DATA}:/metabase-data" \
  -e "MB_DB_FILE=/metabase-data/metabase.db" \
  -e "MB_JETTY_PORT=${METABASE_PORT}" \
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
Metabase credentials — $(date -Iseconds)

=== Metabase web login (register on first visit) ===
URL:      https://${METABASE_HOST}/
Email:    ${METABASE_ADMIN_EMAIL}
Password: ${METABASE_ADMIN_PASSWORD}

=== PostgreSQL in Metabase (main app database) ===
Settings → Admin → Databases → Add → PostgreSQL

  Display name: Car Backend
  Host:         ${PG_HOST_FOR_METABASE}
  Port:         5432
  Database:     ${DB_NAME}
  Username:     ${MB_DB_USER}
  Password:     ${MB_DB_PASS}
  SSL:          OFF

Advanced JDBC options (if needed): sslmode=disable

Note: using app DB user (${MB_DB_USER}). For read-only only, set
METABASE_USE_READONLY=true in config.env and re-run this script.

SSL for Metabase URL:
  sudo bash ${APP_DIR}/scripts/deploy/08-install-metabase-ssl.sh
EOF
chmod 600 "$CREDS"
chown "${APP_USER}:${APP_USER}" "$CREDS" 2>/dev/null || true

echo ""
echo "Metabase installed."
echo "  URL: https://${METABASE_HOST}/ (or http if SSL not done yet)"
echo "  DB:  host=${PG_HOST_FOR_METABASE} db=${DB_NAME} user=${MB_DB_USER}"
echo "  Saved: ${CREDS}"
