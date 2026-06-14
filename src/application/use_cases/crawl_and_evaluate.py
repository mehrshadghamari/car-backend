import logging
from uuid import UUID, uuid4

from src.application.ports.car_catalog import CarTrimRepository
from src.application.ports.repositories import (
    CrawlRunRepository,
    CrawlTargetRepository,
    ListingRepository,
    MarketPriceRepository,
    OpportunityRepository,
    PurchaseRequestRepository,
)
from src.application.services.crawl_scheduler import pool_needs_crawl
from src.application.services.listing_fetch import fetch_shared_pool_listings
from src.domain.enums.platform_fetch_strategy import PlatformFetchStrategy
from src.domain.exceptions import ExternalServiceError, ValidationError
from src.application.services.purchase_crawl_targets import validate_trim_listing_mapping
from src.application.use_cases.evaluate_purchase_requests import EvaluatePurchaseRequestsUseCase
from src.domain.compat import utc_now
from src.domain.entities.crawl_run import CrawlRun, CrawlRunStatus
from src.domain.entities.listing import Listing
from src.domain.services.crawl_diagnostics import CrawlDiagnostics
from src.domain.utils.persian_numbers import parse_jalali_year
from src.infrastructure.adapters.pricing_factory import PricingServiceFactory
from src.infrastructure.config import Settings
from src.infrastructure.persistence.platform_repositories import SqlAlchemyPlatformRepository

logger = logging.getLogger(__name__)


class CrawlAndEvaluateUseCase:
    """
    Shared pool crawl: fetch many Divar listings (no year/km URL filters),
    price each with Khodro45 using the listing's own year/km, then evaluate
    active purchase requests against the pool.
    """

    def __init__(
        self,
        crawl_target_repo: CrawlTargetRepository,
        listing_repo: ListingRepository,
        market_price_repo: MarketPriceRepository,
        opportunity_repo: OpportunityRepository,
        crawl_run_repo: CrawlRunRepository,
        purchase_request_repo: PurchaseRequestRepository,
        platform_repo: SqlAlchemyPlatformRepository,
        car_trim_repo: CarTrimRepository,
        divar_port,
        pricing_factory: PricingServiceFactory,
        settings: Settings,
        max_concurrent_details: int = 10,
    ):
        self._crawl_target_repo = crawl_target_repo
        self._listing_repo = listing_repo
        self._market_price_repo = market_price_repo
        self._opportunity_repo = opportunity_repo
        self._crawl_run_repo = crawl_run_repo
        self._purchase_request_repo = purchase_request_repo
        self._platform_repo = platform_repo
        self._car_trim_repo = car_trim_repo
        self._divar_port = divar_port
        self._pricing_factory = pricing_factory
        self._settings = settings
        self._max_concurrent_details = max_concurrent_details

    async def execute(self, crawl_target_id, *, force: bool = False) -> CrawlRun:
        diag = CrawlDiagnostics()
        stale = await self._crawl_run_repo.recover_stale_runs()
        if stale:
            diag.add("warn", f"Recovered {stale} stale crawl run(s) stuck in 'running'")

        target = await self._crawl_target_repo.get_by_id(UUID(str(crawl_target_id)))
        if not target:
            raise ValueError(f"Crawl target not found: {crawl_target_id}")

        if force and not target.is_active:
            target.is_active = True
            target = await self._crawl_target_repo.save(target)
            diag.add("info", "Reactivated crawl target for manual run", crawl_target_id=str(target.id))

        active_purchases = await self._purchase_request_repo.list_active_non_expired()
        active_trim_ids = {p.car_trim_id for p in active_purchases if p.car_trim_id}
        active_mapping_ids = await self._platform_repo.list_active_listing_mapping_ids_for_trims(
            active_trim_ids
        )
        if not force and not pool_needs_crawl(target, active_listing_mapping_ids=active_mapping_ids):
            diag.add(
                "skip",
                "No active purchase request for this listing pool — skipping Divar fetch",
                crawl_target_id=str(target.id),
                listing_mapping_id=str(target.listing_mapping_id) if target.listing_mapping_id else None,
            )
            crawl_run = CrawlRun(
                id=uuid4(),
                crawl_target_id=target.id,
                status=CrawlRunStatus.COMPLETED,
                started_at=utc_now(),
                finished_at=utc_now(),
                posts_found=0,
                opportunities_found=0,
                diagnostics=diag.to_list(),
            )
            saved = await self._crawl_run_repo.save(crawl_run)
            saved.new_opportunity_ids = []  # type: ignore[attr-defined]
            return saved

        ctx = target.vehicle_context
        max_listings = ctx.max_listings_per_check
        max_pages = ctx.max_pages_per_run

        if force:
            diag.add("info", "Manual crawl — scheduler gate bypassed", crawl_target_id=str(target.id))

        listing_platform = await self._platform_repo.get_listing_platform_by_slug(
            ctx.listing_platform or target.source
        )
        if listing_platform:
            ctx.listing_fetch_strategy = listing_platform.fetch_strategy
            pricing_platform_entity = await self._platform_repo.get_pricing_platform_by_slug(
                self._settings.default_pricing_platform
            )
            if pricing_platform_entity:
                ctx.pricing_fetch_strategy = pricing_platform_entity.fetch_strategy
        target.vehicle_context = ctx

        diag.add(
            "info",
            "Shared pool fetch started",
            crawl_target_id=str(target.id),
            car_model_id=str(target.car_model_id) if target.car_model_id else None,
            listing_fetch_strategy=ctx.listing_fetch_strategy,
            brand_model_key=ctx.divar_brand_model,
            listing_url=target.listing_url,
            pricing_fetch_strategy=ctx.pricing_fetch_strategy,
            max_listings=max_listings,
            max_pages=max_pages,
        )

        crawl_run = CrawlRun(
            id=uuid4(),
            crawl_target_id=target.id,
            status=CrawlRunStatus.RUNNING,
            started_at=utc_now(),
        )
        crawl_run = await self._crawl_run_repo.save(crawl_run)
        new_opportunity_ids: list[str] = []

        try:
            await self._validate_active_purchase_listing_mappings(target, diag)

            cards = await fetch_shared_pool_listings(
                self._divar_port,
                target,
                max_listings=max_listings,
                max_pages=max_pages,
                listing_platform_fetch_strategy=(
                    listing_platform.fetch_strategy if listing_platform else None
                ),
            )
            crawl_run.posts_found = len(cards)
            diag.add(
                "info",
                f"Listing platform returned {len(cards)} listing(s) via {ctx.listing_fetch_strategy}",
            )

            if not cards:
                diag.add(
                    "warn",
                    "No listings returned — check divar car model slug or platform strategy",
                    strategy=ctx.listing_fetch_strategy,
                    brand_model_key=ctx.divar_brand_model,
                    url=target.listing_url,
                )

            ingested = 0
            for card in cards:
                try:
                    if await self._ingest_listing(target, card.token, card, diag):
                        ingested += 1
                except Exception as exc:
                    logger.warning("Listing processing error: %s", exc)
                    diag.add("error", str(exc), token=card.token)

            diag.add("info", f"Ingested {ingested} listing(s) into shared pool")

            evaluator = EvaluatePurchaseRequestsUseCase(
                crawl_target_repo=self._crawl_target_repo,
                purchase_request_repo=self._purchase_request_repo,
                listing_repo=self._listing_repo,
                market_price_repo=self._market_price_repo,
                opportunity_repo=self._opportunity_repo,
                platform_repo=self._platform_repo,
                car_trim_repo=self._car_trim_repo,
                pricing_factory=self._pricing_factory,
                settings=self._settings,
            )
            new_opportunity_ids = await evaluator.for_crawl_target(target.id, diag)

            crawl_run.opportunities_found = len(new_opportunity_ids)
            crawl_run.status = CrawlRunStatus.COMPLETED
            crawl_run.finished_at = utc_now()
            diag.add(
                "info",
                f"Crawl completed — {crawl_run.opportunities_found} new opportunity(s) "
                f"from {crawl_run.posts_found} pool listing(s)",
            )
        except Exception as exc:
            logger.exception("Crawl run failed")
            crawl_run.status = CrawlRunStatus.FAILED
            crawl_run.error_message = str(exc)
            crawl_run.finished_at = utc_now()
            diag.add("error", f"Crawl failed: {exc}")

        crawl_run.diagnostics = diag.to_list()
        saved_run = await self._crawl_run_repo.save(crawl_run)
        saved_run.new_opportunity_ids = new_opportunity_ids  # type: ignore[attr-defined]
        return saved_run

    async def _validate_active_purchase_listing_mappings(self, target, diag: CrawlDiagnostics) -> None:
        purchases = await self._purchase_request_repo.list_active_by_crawl_target(target.id)
        if not purchases:
            return

        platform_slug = target.vehicle_context.listing_platform or target.source or "divar"
        seen_trims: set[UUID] = set()
        for purchase in purchases:
            if not purchase.car_trim_id or purchase.car_trim_id in seen_trims:
                continue
            seen_trims.add(purchase.car_trim_id)
            await validate_trim_listing_mapping(
                self._platform_repo,
                self._car_trim_repo,
                purchase.car_trim_id,
                platform_slug,
            )

        diag.add(
            "info",
            "Listing platform mapping validated for active purchase trim(s)",
            trim_count=len(seen_trims),
            platform=platform_slug,
        )

    async def _ingest_listing(
        self, target, token: str, card, diag: CrawlDiagnostics
    ) -> bool:
        """Upsert pool listing from Divar card (pricing is per trim at evaluation)."""
        ctx = target.vehicle_context
        divar_url = self._divar_port.build_listing_url(token)
        use_api_card = ctx.listing_fetch_strategy == PlatformFetchStrategy.API.value

        title = card.title
        price = card.price
        kilometer = card.kilometer
        production_year = parse_jalali_year(card.title)
        color = None
        district = card.district

        missing_year = production_year is None
        missing_km = kilometer is None
        needs_detail = (not use_api_card) or missing_year or missing_km

        if needs_detail:
            try:
                detail = await self._divar_port.fetch_listing_detail(token)
                title = detail.title or title
                price = detail.price or price
                if kilometer is None:
                    kilometer = detail.kilometer
                if production_year is None:
                    production_year = detail.production_year or parse_jalali_year(title or "")
                color = detail.color
                district = detail.district or district
            except ExternalServiceError as exc:
                if use_api_card and production_year is not None and kilometer is not None:
                    diag.add(
                        "warn",
                        "Divar detail skipped after failure; using open API card data",
                        token=token,
                        error=str(exc),
                    )
                else:
                    raise

        listing = Listing(
            id=uuid4(),
            crawl_target_id=target.id,
            car_model_id=target.car_model_id,
            external_token=token,
            title=title,
            price=price,
            kilometer=kilometer,
            production_year=production_year,
            color=color,
            body_condition=None,
            district=district,
            divar_url=divar_url,
        )

        saved_listing, _ = await self._listing_repo.upsert(listing)

        if not saved_listing.production_year or saved_listing.kilometer is None:
            diag.add(
                "skip",
                "Listing missing year or km",
                token=token,
                title=(saved_listing.title or "")[:80],
                divar_url=divar_url,
            )
            return False

        diag.add(
            "ingested",
            "Pool listing ingested",
            token=token,
            divar_url=divar_url,
            title=(saved_listing.title or "")[:80],
            listing_price=saved_listing.price,
            year=saved_listing.production_year,
            km=saved_listing.kilometer,
        )
        return True
