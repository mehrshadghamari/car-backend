"""Import 4-layer car catalog (brand → model → year → trim) from Hamrah Mechanic NDJSON.

Reads data exported from Hamrah Mechanic:
  - hamrahmechanic_brands.ndjson
  - hamrahmechanic_models.ndjson
  - hamrahmechanic_years.ndjson
  - hamrahmechanic_trims.ndjson

Creates Hamrah trim pricing mappings for min/mid/max price crawling.

Usage:
  python3 scripts/migrate_catalog_4layer.py
  python3 scripts/import_hamrah_catalog.py
  python3 scripts/import_hamrah_catalog.py --merge
  python3 scripts/import_hamrah_catalog.py --data-dir ./hamrahdata/data
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.config import get_settings
from src.infrastructure.persistence.models import (
    CarBrandModel,
    CarModelModel,
    CarTrimModel,
    CarYearModel,
    CrawlRunModel,
    CrawlTargetModel,
    DivarCarModelModel,
    GatewayClickModel,
    ListingMappingModel,
    ListingMappingTrimModel,
    ListingModel,
    ListingPlatformModel,
    MarketPriceModel,
    OpportunityDeliveryModel,
    OpportunityModel,
    OpportunityPageViewModel,
    PricingPlatformModel,
    PurchaseRequestCrawlTargetModel,
    PurchaseRequestModel,
    TrimPricingMappingModel,
)

DEFAULT_HAMRAH_COLOR_MAP = {
    "سفید": "ColorWhite",
    "مشکی": "ColorBlack",
    "قرمز": "ColorRed",
    "نقره‌ای": "ColorSilver",
    "خاکستری": "ColorGray",
    "نوک مدادی": "ColorGray",
}

WIPE_ORDER = (
    GatewayClickModel,
    OpportunityPageViewModel,
    OpportunityDeliveryModel,
    OpportunityModel,
    MarketPriceModel,
    ListingModel,
    CrawlRunModel,
    PurchaseRequestCrawlTargetModel,
    PurchaseRequestModel,
    CrawlTargetModel,
    ListingMappingTrimModel,
    TrimPricingMappingModel,
    CarTrimModel,
    CarYearModel,
    CarModelModel,
    CarBrandModel,
)


def _load_ndjson(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _brand_slug(row: dict) -> str:
    return (row.get("brandEnglishName") or "").strip().lower()


def _model_slug(row: dict) -> str:
    return (row.get("modelEnglishName") or "").strip()


def _model_db_slug(brand_slug: str, row: dict) -> str:
    model_slug = _model_slug(row)
    if not brand_slug or not model_slug:
        return ""
    return f"{brand_slug}--{model_slug}"


def _parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Import Hamrah Mechanic 4-layer catalog into DB")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=root / "hamrahdata" / "data",
        help="Directory with hamrahmechanic_*.ndjson files",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Upsert by slug keys (keep existing purchase/crawl data)",
    )
    return parser.parse_args()


async def _ensure_platforms(session: AsyncSession) -> tuple[PricingPlatformModel, ListingPlatformModel]:
    hamrah = (
        await session.execute(
            select(PricingPlatformModel).where(PricingPlatformModel.slug == "hamrah_mechanic")
        )
    ).scalar_one_or_none()
    if not hamrah:
        hamrah = PricingPlatformModel(
            id=uuid.uuid4(),
            slug="hamrah_mechanic",
            name="همراه مکانیک",
            fetch_strategy="crawl",
            is_active=True,
        )
        session.add(hamrah)

    divar = (
        await session.execute(
            select(ListingPlatformModel).where(ListingPlatformModel.slug == "divar")
        )
    ).scalar_one_or_none()
    if not divar:
        divar = ListingPlatformModel(
            id=uuid.uuid4(),
            slug="divar",
            name="دیوار",
            fetch_strategy="api",
            is_active=True,
        )
        session.add(divar)

    await session.flush()
    return hamrah, divar


async def _wipe_catalog(session: AsyncSession) -> None:
    if "sqlite" in get_settings().database_url:
        await session.execute(text("PRAGMA foreign_keys=OFF"))
    for model in WIPE_ORDER:
        await session.execute(delete(model))
    if "sqlite" in get_settings().database_url:
        await session.execute(text("PRAGMA foreign_keys=ON"))
    await session.flush()


async def _upsert_brands(session: AsyncSession, rows: list[dict]) -> dict[int, CarBrandModel]:
    by_hamrah_id: dict[int, CarBrandModel] = {}
    for row in rows:
        hamrah_id = row["brandId"]
        slug = _brand_slug(row)
        if not slug:
            continue

        existing = (
            await session.execute(select(CarBrandModel).where(CarBrandModel.slug == slug))
        ).scalar_one_or_none()

        if existing:
            existing.name = row["brandName"]
            existing.title_en = row.get("brandEnglishName")
            existing.slug = slug
            existing.khodro45_id = None
            existing.is_active = True
            entity = existing
        else:
            entity = CarBrandModel(
                id=uuid.uuid4(),
                khodro45_id=None,
                name=row["brandName"],
                title_en=row.get("brandEnglishName"),
                slug=slug,
                is_active=True,
            )
            session.add(entity)

        by_hamrah_id[hamrah_id] = entity

    await session.flush()
    return by_hamrah_id


async def _upsert_models(
    session: AsyncSession,
    rows: list[dict],
    brand_by_hamrah: dict[int, CarBrandModel],
) -> dict[tuple[int, int], CarModelModel]:
    by_key: dict[tuple[int, int], CarModelModel] = {}
    for row in rows:
        brand = brand_by_hamrah.get(row["brandId"])
        if not brand:
            continue
        slug = _model_db_slug(brand.slug, row)
        if not slug:
            continue
        key = (row["brandId"], row["carModelId"])

        existing = (
            await session.execute(
                select(CarModelModel).where(CarModelModel.slug == slug)
            )
        ).scalar_one_or_none()

        if existing:
            existing.brand_id = brand.id
            existing.name = row["modelName"]
            existing.title_en = row.get("modelEnglishName")
            existing.slug = slug
            existing.khodro45_id = None
            existing.is_active = True
            entity = existing
        else:
            entity = CarModelModel(
                id=uuid.uuid4(),
                khodro45_id=None,
                brand_id=brand.id,
                name=row["modelName"],
                title_en=row.get("modelEnglishName"),
                slug=slug,
                is_active=True,
            )
            session.add(entity)

        by_key[key] = entity

    await session.flush()
    return by_key


async def _upsert_years(
    session: AsyncSession,
    rows: list[dict],
    model_by_key: dict[tuple[int, int], CarModelModel],
    models_for_car_model_id: dict[int, list[dict]],
) -> dict[tuple[uuid.UUID, int], CarYearModel]:
    by_key: dict[tuple[uuid.UUID, int], CarYearModel] = {}
    for row in rows:
        model_rows = models_for_car_model_id.get(row["carModelId"], [])
        for model_row in model_rows:
            model = model_by_key.get((model_row["brandId"], model_row["carModelId"]))
            if not model:
                continue
            year_value = row["year"]
            key = (model.id, year_value)
            if key in by_key:
                continue
            title = str(year_value)

            existing = (
                await session.execute(
                    select(CarYearModel).where(
                        CarYearModel.model_id == model.id,
                        CarYearModel.title == title,
                    )
                )
            ).scalar_one_or_none()

            if existing:
                existing.title = title
                existing.khodro45_id = None
                existing.is_active = True
                entity = existing
            else:
                entity = CarYearModel(
                    id=uuid.uuid4(),
                    khodro45_id=None,
                    model_id=model.id,
                    title=title,
                    is_active=True,
                )
                session.add(entity)

            by_key[key] = entity

    await session.flush()
    return by_key


async def _ensure_year(
    session: AsyncSession,
    *,
    model: CarModelModel,
    year_value: int,
    year_by_key: dict[tuple[uuid.UUID, int], CarYearModel],
) -> CarYearModel | None:
    key = (model.id, year_value)
    existing = year_by_key.get(key)
    if existing:
        return existing

    title = str(year_value)
    db_year = (
        await session.execute(
            select(CarYearModel).where(
                CarYearModel.model_id == model.id,
                CarYearModel.title == title,
            )
        )
    ).scalar_one_or_none()
    if db_year:
        year_by_key[key] = db_year
        return db_year

    entity = CarYearModel(
        id=uuid.uuid4(),
        khodro45_id=None,
        model_id=model.id,
        title=title,
        is_active=True,
    )
    session.add(entity)
    await session.flush()
    year_by_key[key] = entity
    return entity


async def _upsert_trims_and_pricing(
    session: AsyncSession,
    rows: list[dict],
    *,
    model_by_key: dict[tuple[int, int], CarModelModel],
    brand_by_hamrah: dict[int, CarBrandModel],
    models_for_car_model_id: dict[int, list[dict]],
    brand_rows_by_id: dict[int, dict],
    year_by_key: dict[tuple[uuid.UUID, int], CarYearModel],
    hamrah: PricingPlatformModel,
) -> tuple[int, int]:
    trim_count = 0
    pricing_count = 0
    seen_trim_platform: set[tuple[uuid.UUID, uuid.UUID]] = set()

    for row in rows:
        model_rows = models_for_car_model_id.get(row["carModelId"], [])
        if not model_rows:
            continue

        for model_row in model_rows:
            model = model_by_key.get((model_row["brandId"], model_row["carModelId"]))
            if not model:
                continue
            year = await _ensure_year(
                session,
                model=model,
                year_value=row["carYear"],
                year_by_key=year_by_key,
            )
            if not year:
                continue

            type_id = str(row["carTypeId"])
            brand_row = brand_rows_by_id.get(model_row.get("brandId"), {})
            brand_slug = _brand_slug(brand_row)
            model_slug = _model_slug(model_row)
            if not brand_slug or not model_slug:
                continue

            trim_name = (row.get("carTypeName") or "").strip()
            if not trim_name:
                continue

            existing = (
                await session.execute(
                    select(CarTrimModel).where(
                        CarTrimModel.year_id == year.id,
                        CarTrimModel.seo_slug == type_id,
                    )
                )
            ).scalar_one_or_none()

            if existing:
                existing.name = trim_name
                existing.title_en = row.get("carTypeEnglishName")
                existing.khodro45_id = None
                existing.model_id = model.id
                existing.is_active = True
                trim = existing
            else:
                trim = CarTrimModel(
                    id=uuid.uuid4(),
                    khodro45_id=None,
                    model_id=model.id,
                    year_id=year.id,
                    name=trim_name,
                    title_en=row.get("carTypeEnglishName"),
                    seo_slug=type_id,
                    is_active=True,
                )
                session.add(trim)
                await session.flush()
                trim_count += 1

            platform_key = (trim.id, hamrah.id)
            if platform_key in seen_trim_platform:
                continue
            seen_trim_platform.add(platform_key)

            mapping = (
                await session.execute(
                    select(TrimPricingMappingModel).where(
                        TrimPricingMappingModel.trim_id == trim.id,
                        TrimPricingMappingModel.pricing_platform_id == hamrah.id,
                    )
                )
            ).scalar_one_or_none()

            config = {
                "brand": brand_slug,
                "model": model_slug,
                "type_id": type_id,
                "default_color": "ColorWhite",
                "default_body_condition": "WithoutColor",
                "color_map": DEFAULT_HAMRAH_COLOR_MAP,
            }
            if mapping:
                mapping.slug = type_id
                mapping.config = config
                mapping.is_active = True
            else:
                session.add(
                    TrimPricingMappingModel(
                        id=uuid.uuid4(),
                        trim_id=trim.id,
                        pricing_platform_id=hamrah.id,
                        slug=type_id,
                        config=config,
                        is_active=True,
                    )
                )
                pricing_count += 1

    await session.flush()
    return trim_count, pricing_count


async def _deactivate_khodro45(session: AsyncSession) -> None:
    """Remove Khodro45 pricing mappings; keep platform row for legacy reads only."""
    khodro = (
        await session.execute(
            select(PricingPlatformModel).where(PricingPlatformModel.slug == "khodro45")
        )
    ).scalar_one_or_none()
    if not khodro:
        return
    await session.execute(
        delete(TrimPricingMappingModel).where(
            TrimPricingMappingModel.pricing_platform_id == khodro.id
        )
    )
    khodro.is_active = False
    await session.flush()


async def _remove_khodro45_catalog_rows(session: AsyncSession) -> None:
    """Drop legacy Khodro45 catalog rows (khodro45_id set) after Hamrah upsert."""
    khodro_trim_ids = (
        await session.execute(
            select(CarTrimModel.id).where(CarTrimModel.khodro45_id.is_not(None))
        )
    ).scalars().all()
    if khodro_trim_ids:
        await session.execute(
            delete(TrimPricingMappingModel).where(
                TrimPricingMappingModel.trim_id.in_(khodro_trim_ids)
            )
        )
    await session.execute(delete(CarTrimModel).where(CarTrimModel.khodro45_id.is_not(None)))
    await session.execute(delete(CarYearModel).where(CarYearModel.khodro45_id.is_not(None)))
    await session.execute(delete(CarModelModel).where(CarModelModel.khodro45_id.is_not(None)))
    await session.execute(delete(CarBrandModel).where(CarBrandModel.khodro45_id.is_not(None)))
    await session.flush()


async def import_catalog(*, data_dir: Path, merge: bool = False) -> None:
    brands_data = _load_ndjson(data_dir / "hamrahmechanic_brands.ndjson")
    models_data = _load_ndjson(data_dir / "hamrahmechanic_models.ndjson")
    years_data = _load_ndjson(data_dir / "hamrahmechanic_years.ndjson")
    trims_data = _load_ndjson(data_dir / "hamrahmechanic_trims.ndjson")

    model_rows_by_key = {(row["brandId"], row["carModelId"]): row for row in models_data}
    models_for_car_model_id: dict[int, list[dict]] = {}
    for row in models_data:
        models_for_car_model_id.setdefault(row["carModelId"], []).append(row)
    brand_rows_by_id = {row["brandId"]: row for row in brands_data}

    settings = get_settings()
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        hamrah, _divar = await _ensure_platforms(session)

        if not merge:
            print("Replacing existing catalog data (removing Khodro45 catalog)…")
            await _wipe_catalog(session)
        else:
            print("Merging Hamrah catalog (upsert by slug keys)…")

        brand_by_hamrah = await _upsert_brands(session, brands_data)
        model_by_key = await _upsert_models(session, models_data, brand_by_hamrah)
        year_by_key = await _upsert_years(session, years_data, model_by_key, models_for_car_model_id)
        trim_added, pricing_added = await _upsert_trims_and_pricing(
            session,
            trims_data,
            model_by_key=model_by_key,
            brand_by_hamrah=brand_by_hamrah,
            models_for_car_model_id=models_for_car_model_id,
            brand_rows_by_id=brand_rows_by_id,
            year_by_key=year_by_key,
            hamrah=hamrah,
        )

        await _deactivate_khodro45(session)
        if merge:
            await _remove_khodro45_catalog_rows(session)

        await session.commit()

    await engine.dispose()

    print(
        f"Done — {len(brand_by_hamrah)} brands, {len(model_by_key)} models, "
        f"{len(year_by_key)} years, +{trim_added} new trims, +{pricing_added} new Hamrah pricing mappings."
    )


def main() -> None:
    args = _parse_args()
    if not args.data_dir.is_dir():
        raise SystemExit(f"Data directory not found: {args.data_dir}")
    asyncio.run(import_catalog(data_dir=args.data_dir.resolve(), merge=args.merge))


if __name__ == "__main__":
    main()
