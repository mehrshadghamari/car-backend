#!/usr/bin/env bash
# Shared helpers for VPS deploy scripts.

# Resolve project root when this file is sourced (BASH_SOURCE[0] = common.sh).
if [[ -z "${DEPLOY_ROOT:-}" ]]; then
  _DEPLOY_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  DEPLOY_ROOT="$(cd "$_DEPLOY_LIB_DIR/../.." && pwd)"
fi

load_deploy_config() {
  local root="${DEPLOY_ROOT}"
  APP_DIR="${APP_DIR:-/opt/car-backend}"
  APP_USER="${APP_USER:-deploy}"
  DOMAIN="${DOMAIN:-car-alert.ir}"
  DB_NAME="${DB_NAME:-car_backend}"
  DB_USER="${DB_USER:-car-alert-dbman}"
  USE_POSTGRES="${USE_POSTGRES:-true}"
  GUNICORN_WORKERS="${GUNICORN_WORKERS:-1}"

  _source_deploy_config "$root"

  APP_DIR="${APP_DIR:-/opt/car-backend}"
  APP_USER="${APP_USER:-deploy}"
  DOMAIN="${DOMAIN:-car-alert.ir}"
  DB_NAME="${DB_NAME:-car_backend}"
  DB_USER="${DB_USER:-car-alert-dbman}"
  USE_POSTGRES="${USE_POSTGRES:-true}"
  GUNICORN_WORKERS="${GUNICORN_WORKERS:-1}"
  ENABLE_SSL="${ENABLE_SSL:-true}"
  CERTBOT_EMAIL="${CERTBOT_EMAIL:-$(_read_deploy_config_var "$root" CERTBOT_EMAIL)}"
  METABASE_HOST="${METABASE_HOST:-meta.${DOMAIN}}"
  METABASE_USE_READONLY="${METABASE_USE_READONLY:-false}"
  METABASE_DB_USER="${METABASE_DB_USER:-$DB_USER}"
  METABASE_DB_PASS="${METABASE_DB_PASS:-$(_read_deploy_config_var "$root" DB_PASS)}"
  METABASE_ADMIN_EMAIL="${METABASE_ADMIN_EMAIL:-mehrshad.sodoor2003@gmail.com}"
  METABASE_ADMIN_PASSWORD="${METABASE_ADMIN_PASSWORD:-CarAlertMeta2026}"
  OTP_SANDBOX="${OTP_SANDBOX:-true}"
  OTP_SANDBOX_CODE="${OTP_SANDBOX_CODE:-11111}"
  DIVAR_OPEN_API_KEY="${DIVAR_OPEN_API_KEY:-$(_read_deploy_config_var "$root" DIVAR_OPEN_API_KEY)}"
  if [[ -z "${DIVAR_OPEN_API_KEY:-}" ]]; then
    DIVAR_OPEN_API_KEY="$(_read_local_env_var "$root" DIVAR_OPEN_API_KEY)"
  fi
  PYTHON="${PYTHON:-python3}"
}

_source_deploy_config() {
  local root="$1"
  local file="$root/scripts/deploy/config.env"
  if [[ ! -f "$file" ]]; then
    return 0
  fi
  # shellcheck disable=SC1090
  set -a
  source "$file"
  set +a
}

_read_local_env_var() {
  local root="$1"
  local key="$2"
  local file="$root/.env"
  local line
  if [[ ! -f "$file" ]]; then
    return 0
  fi
  line="$(grep -E "^${key}=" "$file" | tail -1 || true)"
  line="${line#${key}=}"
  line="${line%\"}"
  line="${line#\"}"
  line="${line//$'\r'/}"
  printf '%s' "$line"
}

patch_env_var() {
  local key="$1"
  local value="$2"
  local file="${3:-$APP_DIR/.env}"
  if [[ -z "$value" ]] || [[ ! -f "$file" ]]; then
    return 0
  fi
  EXPORT_KEY="$key" EXPORT_VALUE="$value" EXPORT_FILE="$file" python3 -c '
import os
import pathlib

path = pathlib.Path(os.environ["EXPORT_FILE"])
key = os.environ["EXPORT_KEY"]
value = os.environ["EXPORT_VALUE"]
lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
out = []
found = False
for line in lines:
    if line.startswith(key + "="):
        out.append(f"{key}={value}")
        found = True
    else:
        out.append(line)
if not found:
    out.append(f"{key}={value}")
path.write_text("\n".join(out) + "\n", encoding="utf-8")
'
  chown "${APP_USER}:${APP_USER}" "$file" 2>/dev/null || true
  chmod 600 "$file" 2>/dev/null || true
}

patch_divar_api_key() {
  if [[ -z "${DIVAR_OPEN_API_KEY:-}" ]]; then
    echo "    DIVAR_OPEN_API_KEY not set (skip — add to scripts/deploy/config.env or .env)"
    return 0
  fi
  patch_env_var DIVAR_OPEN_API_KEY "$DIVAR_OPEN_API_KEY" "$APP_DIR/.env"
  echo "    DIVAR_OPEN_API_KEY updated in ${APP_DIR}/.env"
}

_read_deploy_config_var() {
  local root="$1"
  local key="$2"
  local file="$root/scripts/deploy/config.env"
  local line
  if [[ ! -f "$file" ]]; then
    return 0
  fi
  line="$(grep -E "^${key}=" "$file" | tail -1 || true)"
  line="${line#${key}=}"
  line="${line%\"}"
  line="${line#\"}"
  line="${line//$'\r'/}"
  printf '%s' "$line"
}

ensure_python310_debian() {
  PYTHON="${PYTHON:-python3}"

  if "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    return 0
  fi

  echo "==> Python 3.10+ required; trying Debian packages..."

  for ver in 3.12 3.11 3.10; do
    pkg="python${ver}"
    if apt-cache show "$pkg" >/dev/null 2>&1; then
      apt install -y "$pkg" "${pkg}-venv" "${pkg}-dev" || true
      if command -v "$pkg" >/dev/null 2>&1 \
        && "$pkg" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
        PYTHON="$pkg"
        echo "    Using $PYTHON ($($PYTHON --version))"
        return 0
      fi
    fi
  done

  # Debian 11 backports (python3.11)
  if [[ -f /etc/os-release ]] && grep -q 'VERSION_ID="11"' /etc/os-release; then
    apt install -y -t bullseye-backports python3.11 python3.11-venv python3.11-dev || true
    if command -v python3.11 >/dev/null 2>&1; then
      PYTHON=python3.11
      echo "    Using python3.11 from bullseye-backports"
      return 0
    fi
  fi

  echo "ERROR: Python 3.10+ not found. Use Debian 12 (bookworm) or enable bullseye-backports."
  exit 1
}

patch_app_env_https() {
  if [[ ! -f "$APP_DIR/.env" ]]; then
    return 0
  fi

  sed -i \
    -e "s|^APP_HOST=.*|APP_HOST=https://${DOMAIN}|" \
    -e "s|^CORS_ORIGINS=.*|CORS_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}|" \
    "$APP_DIR/.env"

  echo "    Updated APP_HOST and CORS_ORIGINS in ${APP_DIR}/.env"
}

generate_db_password_if_needed() {
  if [[ -z "${DB_PASS:-}" ]]; then
    DB_PASS="12345679"
  fi
}

escape_pg_literal() {
  printf "%s" "$1" | sed "s/'/''/g"
}

setup_postgres_user() {
  if [[ "$USE_POSTGRES" != "true" ]]; then
    echo "Skipping PostgreSQL (USE_POSTGRES=false, using SQLite)"
    return 0
  fi

  generate_db_password_if_needed

  local pg_user pg_pass pg_db
  pg_user="$(escape_pg_literal "$DB_USER")"
  pg_pass="$(escape_pg_literal "$DB_PASS")"
  pg_db="$(escape_pg_literal "$DB_NAME")"

  echo "==> Creating PostgreSQL role and database (${DB_USER} / ${DB_NAME})..."
  sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${pg_user}') THEN
    EXECUTE format('CREATE USER %I WITH PASSWORD %L', '${pg_user}', '${pg_pass}');
  ELSE
    EXECUTE format('ALTER USER %I WITH PASSWORD %L', '${pg_user}', '${pg_pass}');
  END IF;
END
\$\$;
ALTER ROLE "${pg_user}" SET client_encoding TO 'utf8';
ALTER ROLE "${pg_user}" SET default_transaction_isolation TO 'read committed';
ALTER ROLE "${pg_user}" SET timezone TO 'UTC';
SELECT format('CREATE DATABASE %I OWNER %I', '${pg_db}', '${pg_user}')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${pg_db}')\gexec
GRANT ALL PRIVILEGES ON DATABASE "${pg_db}" TO "${pg_user}";
SQL

  sudo -u postgres psql -v ON_ERROR_STOP=1 -d "$DB_NAME" <<SQL
GRANT ALL ON SCHEMA public TO "${pg_user}";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "${pg_user}";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "${pg_user}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "${pg_user}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "${pg_user}";
SQL
}

generate_secret_key() {
  openssl rand -hex 32
}

generate_uuid() {
  python3 -c "import uuid; print(uuid.uuid4())"
}

write_production_env() {
  local auth_secret redis_url db_url app_host cors_origins portal_uuid1 portal_uuid2 staff_base

  auth_secret="$(generate_secret_key)"
  portal_uuid1="${PORTAL_PATH_UUID_1:-$(generate_uuid)}"
  portal_uuid2="${PORTAL_PATH_UUID_2:-$(generate_uuid)}"
  staff_base="/portal/${portal_uuid1}/${portal_uuid2}"

  if [[ "$USE_POSTGRES" == "true" ]]; then
    db_url="postgresql+asyncpg://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}"
    redis_url="redis://localhost:6379"
  else
    db_url="sqlite+aiosqlite:///${APP_DIR}/data/car_backend.db"
    redis_url="redis://localhost:6379"
  fi

  if [[ "${ENABLE_SSL:-true}" == "true" && -n "${CERTBOT_EMAIL:-}" ]]; then
    app_host="https://${DOMAIN}"
    cors_origins="https://${DOMAIN},https://www.${DOMAIN}"
  else
    app_host="http://${DOMAIN}"
    cors_origins="http://${DOMAIN},http://www.${DOMAIN}"
  fi

  cat >"$APP_DIR/.env" <<EOF
# Production — generated by scripts/deploy/02-setup-app.sh
APP_HOST=${app_host}
APP_ENV=production
LOG_LEVEL=INFO

AUTH_SECRET_KEY=${auth_secret}
OTP_SANDBOX=${OTP_SANDBOX}
OTP_SANDBOX_CODE=${OTP_SANDBOX_CODE}
CORS_ORIGINS=${cors_origins}

PORTAL_PATH_UUID_1=${portal_uuid1}
PORTAL_PATH_UUID_2=${portal_uuid2}

DATABASE_URL=${db_url}

REDIS_URL=${redis_url}/0
CELERY_BROKER_URL=${redis_url}/1
CELERY_RESULT_BACKEND=${redis_url}/2

DIVAR_REQUEST_DELAY_MS=300
DIVAR_MAX_CONCURRENT_DETAILS=5
DIVAR_EXTRA_HEADERS_JSON={}
DIVAR_OPEN_API_BASE_URL=https://open-api.divar.ir
DIVAR_OPEN_API_KEY=${DIVAR_OPEN_API_KEY}

HAMRAH_MECHANIC_BASE_URL=https://www.hamrah-mechanic.com
HAMRAH_PRICE_CACHE_TTL_SEC=3600
HAMRAH_CATALOG_CACHE_TTL_SEC=86400

SMS_PROVIDER=dry_run
SMS_SEND_MODE=text
SMS_IR_API_KEY=
SMS_IR_LINE_NUMBER=
SMS_IR_TEMPLATE_ID=
SMS_IR_BASE_URL=https://api.sms.ir/v1
SMS_IR_PATTERN_PARAM_NAMES=discount_label,title,price,gateway_url
SMS_WEBSERVICE_API_KEY=
SMS_WEBSERVICE_SENDER=
SMS_WEBSERVICE_BASE_URL=https://api.sms-webservice.com/api/V3
SMS_WEBSERVICE_PATTERN_TEMPLATE_KEY=
SMS_WEBSERVICE_PATTERN_P1=discount_label
SMS_WEBSERVICE_PATTERN_P2=title
SMS_WEBSERVICE_PATTERN_P3=price_and_gateway
SMS_GATEWAY_TEXT_TEMPLATE={discount_label} زیر قیمت بازار {title} قیمت : {price} تومان  مشاهده آگهی در دیوار : {gateway_url}

CRAWL_POOL_REFRESH_MINUTES=30
PURCHASE_ACTIVE_DAYS=2
PURCHASE_TTL_HOURS=48
CRAWL_RESULT_VALID_DAYS=2
CRAWL_RESULT_DEACTIVATE_DAYS=5
PRICING_CACHE_TTL_HOURS=12
DEFAULT_NEAR_THRESHOLD_PCT=0.02
DEFAULT_MAX_PAGES_PER_RUN=5
SHARED_POOL_LISTINGS_LIMIT=150
SHARED_POOL_MAX_PAGES=10
EOF

  cat >"$APP_DIR/.deploy-credentials.txt" <<EOF
Car Backend deploy credentials — $(date -Iseconds)
Domain: ${DOMAIN}
App dir: ${APP_DIR}

User portal (public):
  https://${DOMAIN}/

Staff URLs (private UUID path):
  Admin:         https://${DOMAIN}${staff_base}/admin/
  API docs:      https://${DOMAIN}${staff_base}/docs
  Crawl results: https://${DOMAIN}${staff_base}/results

OTP sandbox (no SMS yet):
  OTP_SANDBOX=true
  Test code: ${OTP_SANDBOX_CODE}

Default admin login: admin / admin

PostgreSQL:
  database: ${DB_NAME}
  user: ${DB_USER}
  password: ${DB_PASS}
EOF
  chmod 600 "$APP_DIR/.deploy-credentials.txt"
}
