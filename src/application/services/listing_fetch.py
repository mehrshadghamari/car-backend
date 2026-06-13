"""Fetch shared pool listings via crawl or platform API."""

from src.domain.entities.crawl_target import CrawlTarget
from src.domain.enums.platform_fetch_strategy import PlatformFetchStrategy
from src.domain.value_objects.divar_listing import DivarListingCard


async def fetch_shared_pool_listings(
    divar_port,
    target: CrawlTarget,
    *,
    max_listings: int,
    max_pages: int,
    listing_platform_fetch_strategy: str | None = None,
) -> list[DivarListingCard]:
    ctx = target.vehicle_context
    strategy = (
        listing_platform_fetch_strategy
        or ctx.listing_fetch_strategy
        or PlatformFetchStrategy.CRAWL.value
    )
    brand_model = (ctx.divar_brand_model or "").strip()
    production_year_min = ctx.production_year_min
    production_year_max = ctx.production_year_max
    usage_min = ctx.usage_min
    usage_max = ctx.usage_max

    if strategy == PlatformFetchStrategy.API.value:
        if not brand_model:
            raise ValueError("divar car model slug is required for API listing fetch")
        cards = await divar_port.fetch_finder_posts(
            brand_model=brand_model,
            city=target.city or "tehran",
            category=ctx.listing_category or "light",
            production_year_min=production_year_min,
            production_year_max=production_year_max,
            usage_min=usage_min,
            usage_max=usage_max,
            max_results=max_listings,
        )
        return cards[:max_listings]

    cards = await divar_port.fetch_all_pages(target.listing_url, max_pages=max_pages)
    return cards[:max_listings]
