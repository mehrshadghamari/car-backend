"""Auto-create pricing mappings when missing; listing mappings are configured manually."""

from uuid import UUID, uuid4

from src.domain.entities.car_catalog import CarBrand, CarModel, CarTrim
from src.domain.entities.platform import ListingMapping, TrimPricingMapping
from src.infrastructure.persistence.platform_repositories import SqlAlchemyPlatformRepository

DEFAULT_KHODRO45_COLOR_MAP = {
    "سفید": "White",
    "مشکی": "Black",
    "قرمز": "Red",
    "نقره‌ای": "Silver",
    "خاکستری": "Gray",
}

DEFAULT_HAMRAH_COLOR_MAP = {
    "سفید": "ColorWhite",
    "مشکی": "ColorBlack",
    "قرمز": "ColorRed",
    "نقره‌ای": "ColorSilver",
    "خاکستری": "ColorGray",
    "نوک مدادی": "ColorGray",
}


async def ensure_pricing_mapping(
    platform_repo: SqlAlchemyPlatformRepository,
    *,
    trim: CarTrim,
    pricing_platform_id: UUID,
    brand: CarBrand | None = None,
    car_model: CarModel | None = None,
) -> TrimPricingMapping:
    existing = await platform_repo.get_pricing_mapping_for_trim(trim.id, pricing_platform_id)
    if existing:
        return existing

    platform = await platform_repo.get_pricing_platform_by_id(pricing_platform_id)
    platform_slug = platform.slug if platform else "khodro45"

    if platform_slug == "hamrah_mechanic":
        brand_slug = (brand.slug if brand else "").strip()
        model_slug = (car_model.title_en or car_model.slug if car_model else "").strip()
        if car_model and "--" in car_model.slug:
            model_slug = (car_model.title_en or car_model.slug.split("--", 1)[1]).strip()
        type_id = str(trim.seo_slug).strip()
        return await platform_repo.save_trim_pricing_mapping(
            TrimPricingMapping(
                id=uuid4(),
                trim_id=trim.id,
                pricing_platform_id=pricing_platform_id,
                slug=type_id,
                config={
                    "brand": brand_slug,
                    "model": model_slug,
                    "type_id": type_id,
                    "default_color": "ColorWhite",
                    "default_body_condition": "WithoutColor",
                    "color_map": DEFAULT_HAMRAH_COLOR_MAP,
                },
                is_active=True,
            )
        )

    slug = trim.khodro45_price_slug
    return await platform_repo.save_trim_pricing_mapping(
        TrimPricingMapping(
            id=uuid4(),
            trim_id=trim.id,
            pricing_platform_id=pricing_platform_id,
            slug=slug,
            config={
                "slug": slug,
                "default_color": "Black",
                "color_map": DEFAULT_KHODRO45_COLOR_MAP,
            },
            is_active=True,
        )
    )


async def ensure_listing_mappings_for_trim(
    platform_repo: SqlAlchemyPlatformRepository,
    *,
    trim: CarTrim,
    listing_platform_slug: str,
) -> list[ListingMapping]:
    """Return configured listing mappings only — no auto-create."""
    return await platform_repo.get_listing_mappings_for_trim(trim.id, listing_platform_slug)
