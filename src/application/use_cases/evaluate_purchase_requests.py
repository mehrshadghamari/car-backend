"""Evaluate shared pool listings against purchase requests and create opportunities."""

import logging
from uuid import UUID, uuid4

from src.application.ports.repositories import (
    CrawlTargetRepository,
    ListingRepository,
    MarketPriceRepository,
    OpportunityRepository,
    PurchaseRequestRepository,
)
from src.application.ports.car_catalog import CarTrimRepository
from src.application.services.pricing_config_builder import merge_pricing_config
from src.domain.entities.market_price import MarketPrice
from src.infrastructure.adapters.pricing_factory import PricingServiceFactory
from src.domain.compat import utc_now
from src.domain.entities.opportunity import Opportunity, OpportunityStatus
from src.domain.services.crawl_diagnostics import CrawlDiagnostics
from src.domain.services.listing_matcher import listing_matches_purchase_request
from src.domain.services.listing_retention import is_listing_crawl_valid
from src.domain.services.purchase_detail_filters import effective_purchase_request
from src.domain.services.opportunity_scorer import (
    evaluate_hamrah_mechanic_opportunity,
    evaluate_urgent_sale_opportunity,
)
from src.infrastructure.config import Settings
from src.infrastructure.persistence.platform_repositories import SqlAlchemyPlatformRepository

logger = logging.getLogger(__name__)


class EvaluatePurchaseRequestsUseCase:
    """Match pooled listings to purchase filters and create per-request opportunities."""

    def __init__(
        self,
        crawl_target_repo: CrawlTargetRepository,
        purchase_request_repo: PurchaseRequestRepository,
        listing_repo: ListingRepository,
        market_price_repo: MarketPriceRepository,
        opportunity_repo: OpportunityRepository,
        platform_repo: SqlAlchemyPlatformRepository,
        car_trim_repo: CarTrimRepository,
        pricing_factory: PricingServiceFactory,
        settings: Settings,
    ):
        self._crawl_target_repo = crawl_target_repo
        self._purchase_request_repo = purchase_request_repo
        self._listing_repo = listing_repo
        self._market_price_repo = market_price_repo
        self._opportunity_repo = opportunity_repo
        self._platform_repo = platform_repo
        self._car_trim_repo = car_trim_repo
        self._pricing_factory = pricing_factory
        self._settings = settings

    async def for_crawl_target(
        self, crawl_target_id: UUID, diag: CrawlDiagnostics | None = None
    ) -> list[str]:
        target = await self._crawl_target_repo.get_by_id(crawl_target_id)
        if not target:
            return []
        purchases = await self._purchase_request_repo.list_active_by_crawl_target(crawl_target_id)
        listings = await self._listing_repo.list_by_crawl_target(crawl_target_id, active_only=True)
        new_ids: list[str] = []
        for purchase in purchases:
            created = await self._evaluate_purchase(
                purchase, listings, target, diag or CrawlDiagnostics()
            )
            new_ids.extend(created)
        return new_ids

    async def for_purchase_request(
        self, purchase_request_id: UUID, diag: CrawlDiagnostics | None = None
    ) -> list[str]:
        purchase = await self._purchase_request_repo.get_by_id(purchase_request_id)
        if not purchase:
            return []
        target_ids = list(purchase.crawl_target_ids or [])
        if purchase.crawl_target_id and purchase.crawl_target_id not in target_ids:
            target_ids.append(purchase.crawl_target_id)
        if not target_ids:
            return []

        new_ids: list[str] = []
        for target_id in target_ids:
            target = await self._crawl_target_repo.get_by_id(target_id)
            if not target:
                continue
            listings = await self._listing_repo.list_by_crawl_target(target_id, active_only=True)
            created = await self._evaluate_purchase(
                purchase, listings, target, diag or CrawlDiagnostics()
            )
            new_ids.extend(created)
        return new_ids

    async def _evaluate_purchase(
        self, purchase, listings, target, diag: CrawlDiagnostics
    ) -> list[str]:
        trim = await self._car_trim_repo.get_by_id(purchase.car_trim_id) if purchase.car_trim_id else None
        purchase = effective_purchase_request(purchase, trim)
        pricing_platform = await self._pricing_platform_slug(purchase)
        new_ids: list[str] = []
        now = utc_now()
        valid_days = self._settings.crawl_result_valid_days
        filtered_by_year_km = 0
        above_max = 0
        below_floor = 0
        evaluated = 0

        for listing in listings:
            if not listing_matches_purchase_request(listing, purchase):
                filtered_by_year_km += 1
                continue

            if not is_listing_crawl_valid(listing, valid_days=valid_days, now=now):
                existing_stale = await self._opportunity_repo.get_by_listing_and_purchase(
                    listing.id, purchase.id
                )
                if existing_stale and existing_stale.status != OpportunityStatus.EXPIRED:
                    existing_stale.status = OpportunityStatus.EXPIRED
                    await self._opportunity_repo.save(existing_stale)
                continue

            if not listing.production_year or listing.kilometer is None:
                continue

            evaluated += 1
            trim_entity = trim or await self._car_trim_repo.get_by_id(purchase.car_trim_id)
            market = await self._market_price_for_purchase(
                listing, purchase, pricing_platform, diag, trim_entity
            )
            if not market:
                continue

            if pricing_platform == "khodro45":
                if listing.price > market.price_up:
                    above_max += 1
                elif listing.price < market.price_down:
                    below_floor += 1
                tier_matches = evaluate_urgent_sale_opportunity(
                    listing_price=listing.price,
                    price_down=market.price_down,
                    price_mid=market.price_mid,
                    price_up=market.price_up,
                )
            else:
                if listing.price > market.price_mid:
                    above_max += 1
                elif listing.price < market.price_down:
                    below_floor += 1
                tier_matches = evaluate_hamrah_mechanic_opportunity(
                    listing_price=listing.price,
                    price_down=market.price_down,
                    price_mid=market.price_mid,
                    price_up=market.price_up,
                )

            existing = await self._opportunity_repo.get_by_listing_and_purchase(
                listing.id, purchase.id
            )

            if not tier_matches:
                if existing and existing.status != OpportunityStatus.EXPIRED:
                    existing.status = OpportunityStatus.EXPIRED
                    await self._opportunity_repo.save(existing)
                    diag.add(
                        "warn",
                        "Expired opportunity — outside valid price range for purchase filters",
                        purchase_request_id=str(purchase.id),
                        title=(listing.title or "")[:80],
                        listing_price=listing.price,
                    )
                continue

            match = tier_matches[0]
            if existing:
                if existing.status == OpportunityStatus.EXPIRED:
                    continue
                self._apply_match(existing, listing, market, match)
                await self._opportunity_repo.save(existing)
                continue
            opportunity = Opportunity(
                id=uuid4(),
                listing_id=listing.id,
                purchase_request_id=purchase.id,
                crawl_target_id=target.id,
                listing_price=listing.price,
                market_price_down=market.price_down,
                market_price_up=market.price_up,
                market_price_mid=market.price_mid,
                price_basis=match.basis,
                deal_tag=match.deal_tag,
                reference_price=match.reference_price,
                discount_amount=match.discount_amount,
                discount_pct=match.discount_pct,
                score=match.score,
                status=OpportunityStatus.NEW,
                is_below_floor=match.is_below,
                created_at=utc_now(),
            )
            saved = await self._opportunity_repo.save(opportunity)
            new_ids.append(str(saved.id))
            diag.add(
                "opportunity",
                f"Created {match.deal_tag} opportunity for purchase request",
                purchase_request_id=str(purchase.id),
                deal_tag=match.deal_tag,
                listing_price=listing.price,
                reference_price=match.reference_price,
                discount_pct=float(match.discount_pct),
                divar_url=listing.divar_url,
            )

        diag.add(
            "info",
            "Purchase evaluation summary",
            purchase_request_id=str(purchase.id),
            pool_listings=len(listings),
            filtered_by_year_km=filtered_by_year_km,
            evaluated=evaluated,
            above_max=above_max,
            below_floor=below_floor,
            new_opportunities=len(new_ids),
        )
        return new_ids

    async def _pricing_platform_slug(self, purchase) -> str:
        if purchase.pricing_platform_id:
            platform = await self._platform_repo.get_pricing_platform_by_id(
                purchase.pricing_platform_id
            )
            if platform:
                return platform.slug
        return self._settings.default_pricing_platform

    @staticmethod
    def _is_khodro45_price_unavailable(exc: Exception) -> bool:
        msg = str(exc).lower()
        if "khodro45" not in msg:
            return False
        return any(
            token in msg
            for token in (
                "no urgent-sale",
                "section not found",
                "k45_price",
                "has no urgent-sale price",
            )
        )

    async def _market_price_for_purchase(self, listing, purchase, pricing_platform, diag, trim=None):
        if trim is None:
            trim = await self._car_trim_repo.get_by_id(purchase.car_trim_id)
        if not trim:
            return None

        cached = await self._market_price_repo.get_latest_for_listing_and_trim(
            listing.id, trim.id
        )
        if cached:
            return cached

        ttl_hours = self._settings.pricing_cache_ttl_hours
        specs_cached = await self._market_price_repo.get_fresh_for_trim_at_specs(
            trim.id,
            listing.production_year,
            listing.kilometer,
            pricing_platform,
            ttl_hours,
        )
        if specs_cached:
            saved = await self._market_price_repo.save(
                MarketPrice(
                    id=uuid4(),
                    listing_id=listing.id,
                    trim_id=trim.id,
                    price_up=specs_cached.price_up,
                    price_down=specs_cached.price_down,
                    price_mid=specs_cached.price_mid,
                    reference_url=specs_cached.reference_url,
                    fetched_at=specs_cached.fetched_at,
                    pricing_provider=specs_cached.pricing_provider,
                )
            )
            diag.add(
                "info",
                "Reused trim pricing cache for matching year/km",
                purchase_request_id=str(purchase.id),
                trim_id=str(trim.id),
                token=listing.external_token,
                year=listing.production_year,
                km=listing.kilometer,
            )
            return saved

        if not purchase.pricing_platform_id:
            return None

        mapping = await self._platform_repo.get_pricing_mapping_for_trim(
            trim.id, purchase.pricing_platform_id
        )
        if not mapping:
            return None

        pricing_config = merge_pricing_config(mapping, pricing_platform)
        color = purchase.color
        if color and pricing_config.get("color_map"):
            pricing_config = dict(pricing_config)
            if pricing_platform == "hamrah_mechanic":
                pricing_config["default_color"] = pricing_config["color_map"].get(
                    color, pricing_config.get("default_color", "ColorWhite")
                )
            else:
                pricing_config["default_color"] = pricing_config["color_map"].get(
                    color, pricing_config.get("default_color", "Black")
                )

        try:
            port = self._pricing_factory.get(pricing_platform)
            result = await port.get_market_price(
                pricing_config=pricing_config,
                production_year=listing.production_year,
                kilometer=listing.kilometer,
                color=listing.color,
                body_condition=listing.body_condition,
            )
        except Exception as exc:
            if self._is_khodro45_price_unavailable(exc):
                diag.add(
                    "skip",
                    f"Khodro45 price unavailable: {exc}",
                    purchase_request_id=str(purchase.id),
                    trim_id=str(trim.id),
                    token=listing.external_token,
                    year=listing.production_year,
                    km=listing.kilometer,
                )
            else:
                diag.add(
                    "error",
                    f"Trim pricing failed: {exc}",
                    purchase_request_id=str(purchase.id),
                    trim_id=str(trim.id),
                    token=listing.external_token,
                    year=listing.production_year,
                    km=listing.kilometer,
                )
            return None

        saved = await self._market_price_repo.save(
            MarketPrice(
                id=uuid4(),
                listing_id=listing.id,
                trim_id=trim.id,
                price_up=result.price_up,
                price_down=result.price_down,
                price_mid=result.price_mid,
                reference_url=result.reference_url,
                fetched_at=utc_now(),
                pricing_provider=result.provider,
            )
        )
        return saved

    @staticmethod
    def _apply_match(opportunity, listing, market, match) -> None:
        opportunity.listing_price = listing.price
        opportunity.market_price_down = market.price_down
        opportunity.market_price_up = market.price_up
        opportunity.market_price_mid = market.price_mid
        opportunity.price_basis = match.basis
        opportunity.deal_tag = match.deal_tag
        opportunity.reference_price = match.reference_price
        opportunity.discount_amount = match.discount_amount
        opportunity.discount_pct = match.discount_pct
        opportunity.score = match.score
        opportunity.is_below_floor = match.is_below
