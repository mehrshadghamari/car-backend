"""Import Divar cities and car models from JSON (or RTF) into reference tables.

Usage:
  PYTHONPATH=src python3 scripts/import_divar_reference_data.py
  PYTHONPATH=src python3 scripts/import_divar_reference_data.py --merge
  bash scripts/insert_divar_data.sh
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from src.infrastructure.persistence.database import async_session_factory
from src.infrastructure.persistence.models import DivarCarModelModel, DivarCityModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CITIES = PROJECT_ROOT / "data/divar/cities.json"
DEFAULT_BRAND_MODELS = PROJECT_ROOT / "data/divar/brand_models.json"
FALLBACK_CITIES_RTF = PROJECT_ROOT / "cities 2.rtf"
FALLBACK_BRAND_MODELS_RTF = PROJECT_ROOT / "divar 2.JSON.rtf"


def _parse_rtf_reference(path: Path, root_key: str) -> list[dict]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"\\u(-?\d+)\s*", lambda m: chr(int(m.group(1))), raw)
    raw = raw.replace("\\uc0", "").replace("\\{", "{").replace("\\}", "}")
    raw = re.sub(r"\\\s*\n", "\n", raw)
    raw = raw.replace("\\", "")
    marker = f'"{root_key}"'
    pos = raw.find(marker)
    if pos < 0:
        raise ValueError(f"Could not find {root_key} in {path}")
    start = raw.rfind("{", 0, pos)
    depth = 0
    for i, ch in enumerate(raw[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                data = json.loads(raw[start : i + 1])
                return data[root_key]
    raise ValueError(f"Unbalanced JSON in {path}")


def _load_items(path: Path, root_key: str) -> list[dict]:
    if path.suffix.lower() == ".rtf":
        return _parse_rtf_reference(path, root_key)
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data[root_key]


def _resolve_source_path(preferred: Path, rtf_fallback: Path) -> Path:
    if preferred.exists():
        return preferred
    if rtf_fallback.exists():
        return rtf_fallback
    raise FileNotFoundError(
        f"Neither {preferred} nor {rtf_fallback} exists — add Divar reference data files."
    )


def _cache_json(path: Path, root_key: str, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({root_key: items}, ensure_ascii=False, indent=2), encoding="utf-8")


async def _db_totals(session) -> tuple[int, int]:
    city_total = (
        await session.execute(select(func.count()).select_from(DivarCityModel))
    ).scalar_one()
    model_total = (
        await session.execute(select(func.count()).select_from(DivarCarModelModel))
    ).scalar_one()
    return city_total, model_total


async def import_reference_data(
    *,
    cities_path: Path,
    brand_models_path: Path,
    merge: bool = False,
    write_json_cache: bool = True,
) -> tuple[int, int, int, int]:
    cities = _load_items(cities_path, "cities")
    brand_models = _load_items(brand_models_path, "brand_models")

    if write_json_cache:
        if cities_path.suffix.lower() == ".rtf":
            _cache_json(DEFAULT_CITIES, "cities", cities)
        if brand_models_path.suffix.lower() == ".rtf":
            _cache_json(DEFAULT_BRAND_MODELS, "brand_models", brand_models)

    city_count = 0
    model_count = 0
    async with async_session_factory() as session:
        for row in cities:
            slug = (row.get("slug") or "").strip()
            display = (row.get("display") or "").strip()
            if not slug or not display:
                continue
            existing = (
                await session.execute(select(DivarCityModel).where(DivarCityModel.slug == slug))
            ).scalar_one_or_none()
            if existing:
                if merge:
                    existing.display = display
                    existing.is_active = True
                continue
            session.add(DivarCityModel(id=uuid.uuid4(), slug=slug, display=display, is_active=True))
            city_count += 1

        for row in brand_models:
            slug = (row.get("slug") or "").strip()
            display = (row.get("display") or "").strip()
            if not slug or not display:
                continue
            existing = (
                await session.execute(
                    select(DivarCarModelModel).where(DivarCarModelModel.slug == slug)
                )
            ).scalar_one_or_none()
            if existing:
                if merge:
                    existing.display = display
                    existing.is_active = True
                continue
            session.add(
                DivarCarModelModel(id=uuid.uuid4(), slug=slug, display=display, is_active=True)
            )
            model_count += 1

        await session.commit()
        city_total, model_total = await _db_totals(session)

    return city_count, model_count, city_total, model_total


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Divar cities and car models into the database")
    parser.add_argument(
        "--cities",
        type=Path,
        default=DEFAULT_CITIES,
        help="Path to cities JSON or RTF (default: data/divar/cities.json)",
    )
    parser.add_argument(
        "--brand-models",
        type=Path,
        default=DEFAULT_BRAND_MODELS,
        help="Path to brand_models JSON or RTF (default: data/divar/brand_models.json)",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Update display names for slugs that already exist in DB",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Do not write data/divar/*.json when loading from RTF",
    )
    args = parser.parse_args()

    cities_path = _resolve_source_path(args.cities, FALLBACK_CITIES_RTF)
    brand_models_path = _resolve_source_path(args.brand_models, FALLBACK_BRAND_MODELS_RTF)

    city_new, model_new, city_total, model_total = asyncio.run(
        import_reference_data(
            cities_path=cities_path,
            brand_models_path=brand_models_path,
            merge=args.merge,
            write_json_cache=not args.no_cache,
        )
    )
    print(f"Source cities:       {cities_path}")
    print(f"Source car models:   {brand_models_path}")
    print(f"Inserted cities:     {city_new}")
    print(f"Inserted car models: {model_new}")
    print(f"Total in DB:         {city_total} cities, {model_total} Divar car models")


if __name__ == "__main__":
    main()
