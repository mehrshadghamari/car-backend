#!/usr/bin/env bash
# Stop local API / Celery processes started by local-up.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec bash "$ROOT/scripts/kill-api.sh"
