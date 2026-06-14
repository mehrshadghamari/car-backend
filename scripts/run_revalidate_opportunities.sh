#!/usr/bin/env bash
# Re-score active opportunities (Hamrah: discount vs mid; Khodro45: vs max).
# Run on VPS:
#   sudo -u deploy bash scripts/run_revalidate_opportunities.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Missing .env — run from project root with .env present"
  exit 1
fi

if [[ -f "$ROOT/venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/venv/bin/activate"
  PYTHON="${PYTHON:-python}"
else
  PYTHON="${PYTHON:-python3}"
fi

export PYTHONPATH="$ROOT"
exec "$PYTHON" scripts/revalidate_opportunities.py "$@"
