#!/usr/bin/env bash
# Create venv, .env, install Python deps. Run as APP_USER from project root.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/common.sh"
load_deploy_config

PYTHON="${PYTHON:-python3}"
if ! "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1 \
      && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
      PYTHON="$candidate"
      break
    fi
  done
fi
VENV="$APP_DIR/venv"

echo "==> Car Backend app setup"
echo "    APP_DIR=$APP_DIR"
echo "    DOMAIN=$DOMAIN"

mkdir -p "$APP_DIR/data" "$APP_DIR/.logs"

if [[ ! -d "$VENV" ]]; then
  echo "==> Creating virtualenv..."
  "$PYTHON" -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --upgrade pip wheel
pip install -e "$ROOT"
pip install gunicorn

if [[ ! -f "$APP_DIR/.env" ]]; then
  echo "==> Creating production .env..."
  generate_db_password_if_needed
  write_production_env
  chmod 600 "$APP_DIR/.env"
  echo "    Saved credentials: $APP_DIR/.deploy-credentials.txt (keep safe)"
else
  echo "==> Using existing $APP_DIR/.env"
fi

echo ""
echo "App setup complete."
echo "Next: bash scripts/deploy/03-seed-database.sh"
