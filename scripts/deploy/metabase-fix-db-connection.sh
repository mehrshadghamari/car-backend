#!/usr/bin/env bash
# Fix Metabase → PostgreSQL using app DB credentials (car-alert-dbman).
# Run as root: sudo bash scripts/deploy/metabase-fix-db-connection.sh
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

METABASE_PORT="${METABASE_PORT:-3000}"
METABASE_DATA="/var/lib/metabase"

echo "==> Metabase DB connection (app credentials)"
echo "    Host: 127.0.0.1  DB: ${DB_NAME}  User: ${DB_USER}"

if ! PGPASSWORD="$DB_PASS" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" >/dev/null 2>&1; then
  echo "ERROR: App DB login failed — check DB_USER/DB_PASS in config.env"
  exit 1
fi
echo "    PostgreSQL login OK"

docker rm -f metabase 2>/dev/null || true
mkdir -p "$METABASE_DATA"
docker run -d \
  --name metabase \
  --restart unless-stopped \
  --network host \
  -v "${METABASE_DATA}:/metabase-data" \
  -e "MB_DB_FILE=/metabase-data/metabase.db" \
  -e "MB_JETTY_PORT=${METABASE_PORT}" \
  metabase/metabase:latest

CREDS="${APP_DIR}/.metabase-credentials.txt"
cat >"$CREDS" <<EOF
Metabase — use app database

Web:  https://${METABASE_HOST}/
Email: ${METABASE_ADMIN_EMAIL}
Pass:  ${METABASE_ADMIN_PASSWORD}

PostgreSQL in Metabase:
  Host:     127.0.0.1
  Port:     5432
  Database: ${DB_NAME}
  Username: ${DB_USER}
  Password: ${DB_PASS}
  SSL:      OFF  (sslmode=disable if advanced options shown)
EOF
chmod 600 "$CREDS"
chown "${APP_USER}:${APP_USER}" "$CREDS" 2>/dev/null || true

echo ""
echo "Done. In Metabase add database with user ${DB_USER} / same password as app."
