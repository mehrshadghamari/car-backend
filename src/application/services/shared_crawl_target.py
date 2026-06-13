"""Find-or-create shared Divar crawl targets per listing mapping (unfiltered pool)."""

from uuid import UUID, uuid4

from src.application.ports.repositories import CrawlTargetRepository
from src.domain.entities.crawl_target import CrawlTarget, VehicleContext
from src.domain.entities.platform import ListingMapping
from src.domain.services.url_builder import build_divar_search_url
from src.infrastructure.config import Settings


async def find_or_create_shared_crawl_target(
    *,
    crawl_target_repo: CrawlTargetRepository,
    listing_mapping: ListingMapping,
    listing_platform_slug: str,
    city: str,
    listing_fetch_strategy: str,
    pricing_fetch_strategy: str,
    listing_category: str,
    settings: Settings,
    production_year_min: int | None = None,
    production_year_max: int | None = None,
    usage_min: int | None = None,
    usage_max: int | None = None,
) -> CrawlTarget:
    pool_year = production_year_min if production_year_min == production_year_max else production_year_min
    existing = await crawl_target_repo.get_shared_pool(
        listing_mapping_id=listing_mapping.id,
        city=city,
        source=listing_platform_slug,
        pool_production_year=pool_year,
    )
    pool_listings = settings.shared_pool_listings_limit
    pool_pages = settings.shared_pool_max_pages

    vehicle_context = VehicleContext(
        listing_platform=listing_platform_slug,
        listing_fetch_strategy=listing_fetch_strategy,
        pricing_fetch_strategy=pricing_fetch_strategy,
        listing_category=listing_category,
        divar_brand_model=listing_mapping.divar_brand_model.strip(),
        max_pages_per_run=pool_pages,
        max_listings_per_check=pool_listings,
        production_year_min=production_year_min,
        production_year_max=production_year_max,
        usage_min=usage_min,
        usage_max=usage_max,
    )

    pool_url = build_divar_search_url(
        city=city,
        divar_path=listing_mapping.path,
        production_year_min=production_year_min,
        production_year_max=production_year_max,
        usage_min=usage_min,
        usage_max=usage_max,
    )

    if existing:
        await crawl_target_repo.deactivate_duplicate_shared_pools(
            listing_mapping.id,
            city,
            listing_platform_slug,
            existing.id,
            pool_production_year=pool_year,
        )
        existing.listing_url = pool_url
        existing.vehicle_context = vehicle_context
        existing.pool_production_year = pool_year
        existing.is_active = True
        return await crawl_target_repo.save(existing)

    target = CrawlTarget(
        id=uuid4(),
        source=listing_platform_slug,
        listing_url=pool_url,
        vehicle_context=vehicle_context,
        is_active=True,
        poll_interval_sec=settings.crawl_pool_refresh_sec,
        listing_mapping_id=listing_mapping.id,
        city=city,
        is_shared_pool=True,
        pool_production_year=pool_year,
    )
    return await crawl_target_repo.save(target)
