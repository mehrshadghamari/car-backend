#!/usr/bin/env bash
# Seed SMS providers + templates. Loads credentials from sms.seed.env or .env.
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

export PYTHONPATH="${PYTHONPATH:-$ROOT}"
python3 "$ROOT/scripts/seed_sms_config.py" "$@"
