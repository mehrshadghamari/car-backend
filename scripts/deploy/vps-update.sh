#!/usr/bin/env bash
# Alias for redeploy.sh (kept for backward compatibility).
# Run as root: sudo bash scripts/deploy/vps-update.sh
exec "$(cd "$(dirname "$0")" && pwd)/redeploy.sh" "$@"
