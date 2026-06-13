#!/usr/bin/env bash
# Alias for local-first-run.sh (kept for backward compatibility).
set -euo pipefail
exec "$(dirname "$0")/local-first-run.sh"
