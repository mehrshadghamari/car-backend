#!/usr/bin/env bash
# Import 4-layer car catalog from khodro45data/*.json into the local DB.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> 4-layer schema migration"
python3 scripts/migrate_catalog_4layer.py

echo "==> Khodro45 JSON import (brands → models → years → trims)"
python3 scripts/import_khodro45_catalog.py "$@"

echo "==> Done. Open /admin/ to link Divar listing mappings to trims."
