#!/usr/bin/env bash
# Load all catalog/reference data into the database:
#   1. 4-layer schema migration
#   2. Hamrah Mechanic catalog (brand → model → year → trim) from data.zip / hamrahdata/
#   3. Divar cities + Divar car models
#   4. Listing/pricing platforms (default pricing: hamrah_mechanic)
#
# Safe to re-run (--merge upserts without wiping existing rows).
#
# Usage (from project root):
#   bash scripts/load_all_catalog_data.sh
#   bash scripts/load_all_catalog_data.sh --merge
# On VPS (recommended):
#   sudo -u deploy bash scripts/deploy/09-import-catalog.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ "${1:-}" == "--merge" ]]; then
  MERGE_FLAG=(--merge)
fi

# Use project venv when present (required on VPS — system python has no deps).
if [[ -f "$ROOT/venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/venv/bin/activate"
  PYTHON="${PYTHON:-python}"
elif [[ -n "${VIRTUAL_ENV:-}" ]]; then
  PYTHON="${PYTHON:-python}"
else
  PYTHON="${PYTHON:-python3}"
fi
export PYTHONPATH="$ROOT"

echo "=========================================="
echo " Load all catalog data"
echo " Project: $ROOT"
echo "=========================================="

if [[ ! -f .env ]]; then
  echo "Missing .env — copy from .env.example first"
  exit 1
fi

echo ""
echo "==> [1/4] 4-layer schema (car_brands, car_models, car_years, car_trims)..."
$PYTHON scripts/migrate_catalog_4layer.py

echo ""
echo "==> [2/4] Hamrah Mechanic catalog (brands → models → years → trims)..."
if [[ ! -f hamrahdata/data/hamrahmechanic_brands.ndjson ]]; then
  if [[ -f data.zip ]]; then
    echo "    Extracting data.zip → hamrahdata/"
    unzip -o -q data.zip -d hamrahdata
  else
    echo "ERROR: missing hamrahdata/data/hamrahmechanic_brands.ndjson (or data.zip)"
    exit 1
  fi
fi
# Full replace (default): wipes Khodro45 catalog + purchase/crawl data. Pass --merge to upsert only.
$PYTHON scripts/import_hamrah_catalog.py "${MERGE_FLAG[@]}"

echo ""
echo "==> [3/4] Divar reference (cities + Divar car models)..."
echo "    Uses data/divar/*.json or fallback RTF files in repo root"
$PYTHON scripts/import_divar_reference_data.py "${MERGE_FLAG[@]}"

echo ""
echo "==> [4/4] Listing/pricing platforms (divar, hamrah_mechanic)..."
$PYTHON scripts/seed_catalog.py

echo ""
echo "==> Row counts:"
$PYTHON <<'PY'
import asyncio
from sqlalchemy import func, select

from src.infrastructure.persistence.database import async_session_factory
from src.infrastructure.persistence.models import (
    CarBrandModel,
    CarModelModel,
    CarTrimModel,
    CarYearModel,
    DivarCarModelModel,
    DivarCityModel,
    ListingPlatformModel,
    PricingPlatformModel,
)

async def main():
    async with async_session_factory() as session:
        async def count(model):
            return await session.scalar(select(func.count()).select_from(model)) or 0

        print(f"  car_brands:          {await count(CarBrandModel)}")
        print(f"  car_models:          {await count(CarModelModel)}")
        print(f"  car_years:           {await count(CarYearModel)}")
        print(f"  car_trims:           {await count(CarTrimModel)}")
        print(f"  divar_cities:        {await count(DivarCityModel)}")
        print(f"  divar_car_models:    {await count(DivarCarModelModel)}")
        print(f"  listing_platforms:   {await count(ListingPlatformModel)}")
        print(f"  pricing_platforms:   {await count(PricingPlatformModel)}")

asyncio.run(main())
PY

echo ""
echo "Done."
echo "  Landing brands API:  /api/v1/car-brands"
echo "  Divar cities API:    /api/v1/divar/cities"
echo "  Admin:               /admin/"
