#!/usr/bin/env bash
# Production: load Hamrah 4-layer catalog + Divar cities/models + platforms.
# Run on VPS: sudo -u deploy bash scripts/deploy/09-import-catalog.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/common.sh"
load_deploy_config

# shellcheck disable=SC1091
source "$APP_DIR/venv/bin/activate"
export PYTHONPATH="$APP_DIR"
cd "$APP_DIR"

bash scripts/load_all_catalog_data.sh --merge

echo ""
echo "Verify on production:"
echo "  curl -s https://${DOMAIN}/api/v1/car-brands | head -c 200"
echo "  curl -s 'https://${DOMAIN}/api/v1/divar/cities?limit=5'"
