#!/usr/bin/env bash
# Stop Docker stack. Use RESET=1 to also remove DB volume.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Stopping Docker stack..."
if [ "${RESET:-0}" = "1" ]; then
  docker compose down -v
  echo "Stopped and removed volumes (database wiped)."
else
  docker compose down
  echo "Stopped (data kept). Full reset: RESET=1 bash scripts/docker-down.sh"
fi
