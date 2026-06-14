#!/usr/bin/env bash
# Import 4-layer car catalog from Hamrah Mechanic NDJSON (data.zip / hamrahdata/).
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
  PYTHON="${PYTHON:-python}"
else
  PYTHON="${PYTHON:-python3}"
fi

echo "==> 4-layer schema migration"
$PYTHON scripts/migrate_catalog_4layer.py

if [[ ! -f hamrahdata/data/hamrahmechanic_brands.ndjson ]]; then
  if [[ -f data.zip ]]; then
    echo "==> Extracting data.zip → hamrahdata/"
    $PYTHON scripts/extract_hamrah_data.py
  else
    echo "ERROR: missing hamrahdata/data/*.ndjson (or data.zip)"
    exit 1
  fi
fi

echo "==> Hamrah Mechanic import (brands → models → years → trims)"
$PYTHON scripts/import_hamrah_catalog.py "$@"

echo "==> Done. Open /admin/ to link Divar listing mappings to trims."
