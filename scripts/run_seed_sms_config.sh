#!/usr/bin/env bash
# Seed SMS providers + templates. Loads credentials from sms.seed.env or .env.
# Run on VPS:
#   sudo -u deploy bash scripts/run_seed_sms_config.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/scripts/deploy/sms.seed.env" ]]; then
  # shellcheck disable=SC1091
  set -a
  source "$ROOT/scripts/deploy/sms.seed.env"
  set +a
elif [[ -f "$ROOT/.env" ]]; then
  # shellcheck disable=SC1091
  set -a
  source "$ROOT/.env"
  set +a
fi

if [[ -f "$ROOT/venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/venv/bin/activate"
  PYTHON="${PYTHON:-python}"
else
  PYTHON="${PYTHON:-python3}"
fi

export PYTHONPATH="$ROOT"
exec "$PYTHON" "$ROOT/scripts/seed_sms_config.py" "$@"
