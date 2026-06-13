"""Auto-create pricing mappings when missing; listing mappings are configured manually."""

from uuid import UUID, uuid4

from src.domain.entities.car_catalog import CarTrim
from src.domain.entities.platform import ListingMapping, TrimPricingMapping
from src.infrastructure.persistence.platform_repositories import SqlAlchemyPlatformRepository

DEFAULT_COLOR_MAP = {
    "سفید": "White",
    "مشکی": "Black",
    "قرمز": "Red",
    "نقره‌ای": "Silver",
    "خاکستری": "Gray",
}


async def ensure_pricing_mapping(
    platform_repo: SqlAlchemyPlatformRepository,
    *,
    trim: CarTrim,
    pricing_platform_id: UUID,
) -> TrimPricingMapping:
    existing = await platform_repo.get_pricing_mapping_for_trim(trim.id, pricing_platform_id)
    if existing:
        return existing

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
                "color_map": DEFAULT_COLOR_MAP,
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
