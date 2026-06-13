"""Resolve shared crawl targets from configured listing mappings (no auto-create)."""

from uuid import UUID

from src.application.ports.car_catalog import CarBrandRepository, CarModelRepository, CarTrimRepository
from src.application.ports.repositories import CrawlTargetRepository, PurchaseRequestRepository
from src.application.services.shared_crawl_target import find_or_create_shared_crawl_target
from src.domain.entities.car_catalog import CarBrand, CarModel, CarTrim
from src.domain.entities.crawl_target import CrawlTarget
from src.domain.entities.purchase_request import PurchaseRequest
from src.domain.enums.platform_fetch_strategy import PlatformFetchStrategy
from src.domain.exceptions import ValidationError
from src.domain.services.trim_production_year import resolve_production_year_range
from src.domain.services.url_builder import build_divar_search_url
from src.infrastructure.config import Settings
from src.infrastructure.persistence.platform_repositories import SqlAlchemyPlatformRepository


def listing_mapping_required_message(trim_label: str, platform_slug: str = "divar") -> str:
    return (
        f"برای تریم «{trim_label}» نگاشت پلتفرم آگهی ({platform_slug}) تنظیم نشده است. "
        "لطفاً در پنل ادمین → Listing mappings پیکربندی کنید."
    )


def _trim_label(trim: CarTrim | None, trim_id: UUID) -> str:
    if not trim:
        return str(trim_id)
    return " — ".join(p for p in (trim.brand_name, trim.model_name, trim.year_title, trim.name) if p) or trim.name


async def validate_trim_listing_mapping(
    platform_repo: SqlAlchemyPlatformRepository,
    car_trim_repo: CarTrimRepository,
    trim_id: UUID,
    listing_platform_slug: str = "divar",
) -> None:
    mappings = await platform_repo.get_listing_mappings_for_trim(trim_id, listing_platform_slug)
    if mappings:
        return
    trim = await car_trim_repo.get_by_id(trim_id)
    raise ValidationError(
        listing_mapping_required_message(_trim_label(trim, trim_id), listing_platform_slug)
    )


async def resolve_crawl_targets_for_trim(
    *,
    platform_repo: SqlAlchemyPlatformRepository,
    crawl_target_repo: CrawlTargetRepository,
    trim: CarTrim,
    car_model: CarModel,
    brand: CarBrand,
    city: str,
    settings: Settings,
    listing_platform_slugs: list[str] | None = None,
    production_year_min: int | None = None,
    production_year_max: int | None = None,
    usage_min: int | None = None,
    usage_max: int | None = None,
    pricing_fetch_strategy: str = PlatformFetchStrategy.CRAWL.value,
) -> tuple[list[CrawlTarget], str]:
    """
    Build shared crawl targets only when listing mappings exist in admin.
    Returns empty list when not configured (purchase create stays allowed).
    """
    year_min, year_max = resolve_production_year_range(
        trim,
        production_year_min=production_year_min,
        production_year_max=production_year_max,
    )
    slugs = listing_platform_slugs or ["divar"]
    listing_platform_entity = await platform_repo.get_listing_platform_by_slug("divar")
    listing_fetch_strategy = (
        listing_platform_entity.fetch_strategy
        if listing_platform_entity
        else PlatformFetchStrategy.CRAWL.value
    )

    crawl_targets: list[CrawlTarget] = []
    divar_url = ""

    for listing_slug in slugs:
        mappings = await platform_repo.get_listing_mappings_for_trim(trim.id, listing_slug)
        for listing_mapping in mappings:
            mapping_config = listing_mapping.config or {}
            listing_category = mapping_config.get("category", "light")
            pool_city = city or "tehran"

            if listing_slug == "divar" and not divar_url:
                divar_url = build_divar_search_url(
                    city=pool_city,
                    divar_path=listing_mapping.path,
                    production_year_min=year_min,
                    production_year_max=year_max,
                    usage_min=usage_min,
                    usage_max=usage_max,
                )

            shared_target = await find_or_create_shared_crawl_target(
                crawl_target_repo=crawl_target_repo,
                listing_mapping=listing_mapping,
                listing_platform_slug=listing_slug,
                city=pool_city,
                listing_fetch_strategy=listing_fetch_strategy,
                pricing_fetch_strategy=pricing_fetch_strategy,
                listing_category=listing_category,
                settings=settings,
                production_year_min=year_min,
                production_year_max=year_max,
                usage_min=usage_min,
                usage_max=usage_max,
            )
            crawl_targets.append(shared_target)

    return crawl_targets, divar_url


async def attach_crawl_targets_to_purchase(
    *,
    purchase: PurchaseRequest,
    trim: CarTrim,
    car_model: CarModel,
    brand: CarBrand,
    platform_repo: SqlAlchemyPlatformRepository,
    crawl_target_repo: CrawlTargetRepository,
    purchase_request_repo: PurchaseRequestRepository,
    car_trim_repo: CarTrimRepository,
    settings: Settings,
    listing_platform_slugs: list[str] | None = None,
    pricing_fetch_strategy: str = PlatformFetchStrategy.CRAWL.value,
) -> tuple[list[CrawlTarget], str]:
    """Validate listing mapping exists, link crawl targets, persist purchase."""
    slugs = listing_platform_slugs or ["divar"]
    for slug in slugs:
        await validate_trim_listing_mapping(platform_repo, car_trim_repo, trim.id, slug)

    targets, divar_url = await resolve_crawl_targets_for_trim(
        platform_repo=platform_repo,
        crawl_target_repo=crawl_target_repo,
        trim=trim,
        car_model=car_model,
        brand=brand,
        city=purchase.city,
        settings=settings,
        listing_platform_slugs=slugs,
        production_year_min=purchase.production_year_min,
        production_year_max=purchase.production_year_max,
        usage_min=purchase.usage_min,
        usage_max=purchase.usage_max,
        pricing_fetch_strategy=pricing_fetch_strategy,
    )
    if not targets:
        raise ValidationError(
            listing_mapping_required_message(_trim_label(trim, trim.id), slugs[0])
        )

    purchase.crawl_target_id = targets[0].id
    purchase.crawl_target_ids = [t.id for t in targets]
    if divar_url:
        purchase.generated_divar_url = divar_url
    await purchase_request_repo.save(purchase)
    return targets, divar_url
