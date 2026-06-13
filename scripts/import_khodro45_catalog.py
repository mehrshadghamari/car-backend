"""Import 4-layer car catalog (brand → model → year → trim) from khodro45data/*.json.

Reads JSON exported from Khodro45:
  - brands.json
  - models.json
  - years.json
  - trims.json

Creates Khodro45 trim pricing mappings (seo_slug with cpe- prefix).
Optional listing_mappings.json links trims to Divar Open API keys.

Usage:
  python3 scripts/migrate_catalog_4layer.py          # schema (first time)
  python3 scripts/import_khodro45_catalog.py          # full replace import
  python3 scripts/import_khodro45_catalog.py --merge   # upsert without wiping data
  python3 scripts/import_khodro45_catalog.py --data-dir ./khodro45data
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

DEFAULT_COLOR_MAP = {
    "سفید": "White",
    "مشکی": "Black",
    "قرمز": "Red",
    "نقره‌ای": "Silver",
    "خاکستری": "Gray",
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


def _load(data_dir: Path, name: str) -> list[dict]:
    path = data_dir / name
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _price_slug(seo_slug: str) -> str:
    slug = seo_slug.strip()
    return slug if slug.startswith("cpe-") else f"cpe-{slug}"


def _parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Import Khodro45 4-layer catalog JSON into DB")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=root / "khodro45data",
        help="Directory with brands.json, models.json, years.json, trims.json",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Upsert by khodro45_id (keep existing purchase/crawl data)",
    )
    parser.add_argument(
        "--with-listing-mappings",
        action="store_true",
        help="Also import listing_mappings.json when present",
    )
    return parser.parse_args()


async def _ensure_platforms(session: AsyncSession) -> tuple[PricingPlatformModel, ListingPlatformModel]:
    khodro45 = (
        await session.execute(
            select(PricingPlatformModel).where(PricingPlatformModel.slug == "khodro45")
        )
    ).scalar_one_or_none()
    if not khodro45:
        khodro45 = PricingPlatformModel(
            id=uuid.uuid4(),
            slug="khodro45",
            name="خودرو۴۵",
            fetch_strategy="crawl",
            is_active=True,
        )
        session.add(khodro45)

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
    return khodro45, divar


async def _wipe_catalog(session: AsyncSession) -> None:
    if "sqlite" in get_settings().database_url:
        await session.execute(text("PRAGMA foreign_keys=OFF"))
    for model in WIPE_ORDER:
        await session.execute(delete(model))
    if "sqlite" in get_settings().database_url:
        await session.execute(text("PRAGMA foreign_keys=ON"))
    await session.flush()


async def _upsert_brands(session: AsyncSession, rows: list[dict]) -> dict[int, CarBrandModel]:
    by_k45: dict[int, CarBrandModel] = {}
    seen_slugs: set[str] = set()
    for row in rows:
        k45_id = row["id"]
        slug = row["seo_slug"]
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        existing = (
            await session.execute(select(CarBrandModel).where(CarBrandModel.khodro45_id == k45_id))
        ).scalar_one_or_none()
        if not existing:
            existing = (
                await session.execute(select(CarBrandModel).where(CarBrandModel.slug == slug))
            ).scalar_one_or_none()

        if existing:
            existing.name = row["title"]
            existing.title_en = row.get("title_en")
            existing.slug = slug
            existing.khodro45_id = k45_id
            existing.is_active = True
            entity = existing
        else:
            entity = CarBrandModel(
                id=uuid.uuid4(),
                khodro45_id=k45_id,
                name=row["title"],
                title_en=row.get("title_en"),
                slug=slug,
                is_active=True,
            )
            session.add(entity)

        by_k45[k45_id] = entity

    await session.flush()
    return by_k45


async def _upsert_models(
    session: AsyncSession, rows: list[dict], brand_by_k45: dict[int, CarBrandModel]
) -> dict[int, CarModelModel]:
    by_k45: dict[int, CarModelModel] = {}
    seen_slugs: set[str] = set()
    for row in rows:
        brand = brand_by_k45.get(row["brand_id"])
        if not brand:
            continue
        slug = row["seo_slug"]
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        k45_id = row["id"]

        existing = (
            await session.execute(select(CarModelModel).where(CarModelModel.khodro45_id == k45_id))
        ).scalar_one_or_none()
        if not existing:
            existing = (
                await session.execute(select(CarModelModel).where(CarModelModel.slug == slug))
            ).scalar_one_or_none()

        if existing:
            existing.brand_id = brand.id
            existing.name = row["title"]
            existing.title_en = row.get("title_en")
            existing.slug = slug
            existing.khodro45_id = k45_id
            existing.is_active = True
            entity = existing
        else:
            entity = CarModelModel(
                id=uuid.uuid4(),
                khodro45_id=k45_id,
                brand_id=brand.id,
                name=row["title"],
                title_en=row.get("title_en"),
                slug=slug,
                is_active=True,
            )
            session.add(entity)

        by_k45[k45_id] = entity

    await session.flush()
    return by_k45


async def _upsert_years(
    session: AsyncSession, rows: list[dict], model_by_k45: dict[int, CarModelModel]
) -> dict[tuple[int, int], CarYearModel]:
    by_key: dict[tuple[int, int], CarYearModel] = {}
    for row in rows:
        model = model_by_k45.get(row["model_id"])
        if not model:
            continue
        key = (row["model_id"], row["id"])
        if key in by_key:
            continue

        existing = (
            await session.execute(
                select(CarYearModel).where(
                    CarYearModel.model_id == model.id,
                    CarYearModel.khodro45_id == row["id"],
                )
            )
        ).scalar_one_or_none()

        if existing:
            existing.title = str(row["title"])
            existing.is_active = True
            entity = existing
        else:
            entity = CarYearModel(
                id=uuid.uuid4(),
                khodro45_id=row["id"],
                model_id=model.id,
                title=str(row["title"]),
                is_active=True,
            )
            session.add(entity)

        by_key[key] = entity

    await session.flush()
    return by_key


async def _upsert_trims_and_pricing(
    session: AsyncSession,
    rows: list[dict],
    *,
    model_by_k45: dict[int, CarModelModel],
    year_by_key: dict[tuple[int, int], CarYearModel],
    khodro45: PricingPlatformModel,
) -> tuple[int, int]:
    trim_count = 0
    pricing_count = 0
    seen_trim_platform: set[tuple[uuid.UUID, uuid.UUID]] = set()

    for row in rows:
        model = model_by_k45.get(row["model_id"])
        year = year_by_key.get((row["model_id"], row["year_id"]))
        if not model or not year:
            continue

        seo_slug = (row.get("seo_slug") or "").strip()
        if not seo_slug:
            continue

        existing = (
            await session.execute(
                select(CarTrimModel).where(
                    CarTrimModel.year_id == year.id,
                    CarTrimModel.seo_slug == seo_slug,
                )
            )
        ).scalar_one_or_none()

        if existing:
            existing.name = row["title"]
            existing.title_en = row.get("title_en")
            existing.khodro45_id = row.get("id")
            existing.model_id = model.id
            existing.is_active = True
            trim = existing
        else:
            trim = CarTrimModel(
                id=uuid.uuid4(),
                khodro45_id=row.get("id"),
                model_id=model.id,
                year_id=year.id,
                name=row["title"],
                title_en=row.get("title_en"),
                seo_slug=seo_slug,
                is_active=True,
            )
            session.add(trim)
            await session.flush()
            trim_count += 1

        platform_key = (trim.id, khodro45.id)
        if platform_key in seen_trim_platform:
            continue
        seen_trim_platform.add(platform_key)

        mapping = (
            await session.execute(
                select(TrimPricingMappingModel).where(
                    TrimPricingMappingModel.trim_id == trim.id,
                    TrimPricingMappingModel.pricing_platform_id == khodro45.id,
                )
            )
        ).scalar_one_or_none()

        slug = _price_slug(seo_slug)
        config = {
            "slug": slug,
            "default_color": "Black",
            "color_map": DEFAULT_COLOR_MAP,
        }
        if mapping:
            mapping.slug = slug
            mapping.config = config
            mapping.is_active = True
        else:
            session.add(
                TrimPricingMappingModel(
                    id=uuid.uuid4(),
                    trim_id=trim.id,
                    pricing_platform_id=khodro45.id,
                    slug=slug,
                    config=config,
                    is_active=True,
                )
            )
            pricing_count += 1

    await session.flush()
    return trim_count, pricing_count


async def _import_listing_mappings(
    session: AsyncSession,
    data_dir: Path,
    *,
    divar: ListingPlatformModel,
    trim_by_seo: dict[str, CarTrimModel],
) -> int:
    """Optional listing_mappings.json: [{trim_seo_slug, path, divar_car_model_slug, config?}]"""
    path = data_dir / "listing_mappings.json"
    if not path.exists():
        return 0

    rows = json.loads(path.read_text(encoding="utf-8"))
    created = 0
    for row in rows:
        trim_slug = (row.get("trim_seo_slug") or row.get("seo_slug") or "").strip()
        divar_slug = (
            row.get("divar_car_model_slug")
            or row.get("brand_model_key")
            or ""
        ).strip()
        divar_path = (row.get("path") or "").strip()
        if not trim_slug or not divar_slug or not divar_path:
            continue

        trim = trim_by_seo.get(trim_slug)
        if not trim:
            continue

        divar_model = (
            await session.execute(
                select(DivarCarModelModel).where(DivarCarModelModel.slug == divar_slug)
            )
        ).scalar_one_or_none()
        if not divar_model:
            divar_model = DivarCarModelModel(
                id=uuid.uuid4(),
                slug=divar_slug,
                display=divar_slug,
                is_active=True,
            )
            session.add(divar_model)
            await session.flush()

        mapping = (
            await session.execute(
                select(ListingMappingModel).where(
                    ListingMappingModel.listing_platform_id == divar.id,
                    ListingMappingModel.path == divar_path,
                    ListingMappingModel.divar_car_model_id == divar_model.id,
                )
            )
        ).scalar_one_or_none()

        if not mapping:
            mapping = ListingMappingModel(
                id=uuid.uuid4(),
                listing_platform_id=divar.id,
                path=divar_path,
                divar_car_model_id=divar_model.id,
                config=row.get("config") or {"category": "light"},
                is_active=True,
            )
            session.add(mapping)
            await session.flush()
            created += 1

        link = (
            await session.execute(
                select(ListingMappingTrimModel).where(
                    ListingMappingTrimModel.listing_mapping_id == mapping.id,
                    ListingMappingTrimModel.trim_id == trim.id,
                )
            )
        ).scalar_one_or_none()
        if not link:
            session.add(
                ListingMappingTrimModel(
                    id=uuid.uuid4(),
                    listing_mapping_id=mapping.id,
                    trim_id=trim.id,
                )
            )

    await session.flush()
    return created


async def import_catalog(
    *,
    data_dir: Path,
    merge: bool = False,
    with_listing_mappings: bool = False,
) -> None:
    brands_data = _load(data_dir, "brands.json")
    models_data = _load(data_dir, "models.json")
    years_data = _load(data_dir, "years.json")
    trims_data = _load(data_dir, "trims.json")

    settings = get_settings()
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        khodro45, divar = await _ensure_platforms(session)

        if not merge:
            print("Replacing existing catalog data…")
            await _wipe_catalog(session)
        else:
            print("Merging into existing catalog (upsert by khodro45_id)…")

        brand_by_k45 = await _upsert_brands(session, brands_data)
        model_by_k45 = await _upsert_models(session, models_data, brand_by_k45)
        year_by_key = await _upsert_years(session, years_data, model_by_k45)
        trim_added, pricing_added = await _upsert_trims_and_pricing(
            session,
            trims_data,
            model_by_k45=model_by_k45,
            year_by_key=year_by_key,
            khodro45=khodro45,
        )

        listing_mapping_count = 0
        if with_listing_mappings:
            trim_rows = (
                await session.execute(select(CarTrimModel))
            ).scalars().all()
            trim_by_seo = {t.seo_slug: t for t in trim_rows}
            listing_mapping_count = await _import_listing_mappings(
                session, data_dir, divar=divar, trim_by_seo=trim_by_seo
            )

        await session.commit()

    await engine.dispose()

    print(
        f"Done — {len(brand_by_k45)} brands, {len(model_by_k45)} models, "
        f"{len(year_by_key)} years, +{trim_added} new trims, +{pricing_added} new pricing mappings."
    )
    if with_listing_mappings:
        print(f"Listing mappings created/linked: {listing_mapping_count}")
    elif not (data_dir / "listing_mappings.json").exists():
        print("Tip: add khodro45data/listing_mappings.json + --with-listing-mappings for Divar keys.")


def main() -> None:
    args = _parse_args()
    if not args.data_dir.is_dir():
        raise SystemExit(f"Data directory not found: {args.data_dir}")
    asyncio.run(
        import_catalog(
            data_dir=args.data_dir.resolve(),
            merge=args.merge,
            with_listing_mappings=args.with_listing_mappings,
        )
    )


if __name__ == "__main__":
    main()
