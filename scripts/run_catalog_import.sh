#!/usr/bin/env bash
# Import 4-layer car catalog from Hamrah Mechanic NDJSON (data.zip / hamrahdata/).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> 4-layer schema migration"
python3 scripts/migrate_catalog_4layer.py

if [[ ! -f hamrahdata/data/hamrahmechanic_brands.ndjson ]]; then
  if [[ -f data.zip ]]; then
    echo "==> Extracting data.zip → hamrahdata/"
    unzip -o -q data.zip -d hamrahdata
  else
    echo "ERROR: missing hamrahdata/data/*.ndjson (or data.zip)"
    exit 1
  fi
fi

echo "==> Hamrah Mechanic import (brands → models → years → trims)"
python3 scripts/import_hamrah_catalog.py "$@"

echo "==> Done. Open /admin/ to link Divar listing mappings to trims."
