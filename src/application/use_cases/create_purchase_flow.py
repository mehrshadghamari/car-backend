from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
import logging
from typing import Any
from uuid import UUID, uuid4

from src.application.ports.car_catalog import CarBrandRepository, CarModelRepository, CarTrimRepository
from src.application.ports.repositories import (
    CrawlTargetRepository,
    ListingRepository,
    MarketPriceRepository,
    OpportunityRepository,
    PurchaseRequestRepository,
)
from src.application.services.ensure_trim_mappings import ensure_pricing_mapping
from src.application.services.purchase_crawl_targets import resolve_crawl_targets_for_trim
from src.application.services.pricing_config_builder import merge_khodro45_pricing_config
from src.application.use_cases.evaluate_purchase_requests import EvaluatePurchaseRequestsUseCase
from src.domain.compat import utc_now
from src.domain.entities.crawl_target import CrawlTarget
from src.domain.entities.purchase_request import PurchaseRequest
from src.domain.enums.platform_fetch_strategy import PlatformFetchStrategy
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.domain.services.trim_production_year import resolve_production_year_range
from src.domain.services.url_builder import build_khodro45_price_url
from src.infrastructure.adapters.pricing_factory import PricingServiceFactory
from src.infrastructure.config import Settings
from src.infrastructure.persistence.platform_repositories import SqlAlchemyPlatformRepository

logger = logging.getLogger(__name__)


@dataclass
class CreatePurchaseFlowInput:
    user_id: UUID
    car_trim_id: UUID
    pricing_platform_slug: str | None = None
    listing_platform_slugs: list[str] | None = None
    city: str = "tehran"
    color: str | None = None
    production_year_min: int | None = None
    production_year_max: int | None = None
    usage_min: int | None = None
    usage_max: int | None = None
    near_threshold_pct: Decimal | None = None
    poll_interval_sec: int | None = None
    max_listings_per_check: int | None = None
    ttl_hours: int | None = None
    is_active: bool = True


@dataclass
class PurchaseFlowResult:
    purchase_request: PurchaseRequest
    crawl_targets: list[CrawlTarget]
    divar_url: str
    pricing_preview_url: str
    pricing_platform_slug: str
    expires_at: Any
    immediate_opportunities: int = 0
    listing_mapping_configured: bool = False


class CreatePurchaseFlowUseCase:
    """Create purchase request for a trim; link shared pools via listing mappings."""

    def __init__(
        self,
        car_trim_repo: CarTrimRepository,
        car_model_repo: CarModelRepository,
        car_brand_repo: CarBrandRepository,
        crawl_target_repo: CrawlTargetRepository,
        purchase_request_repo: PurchaseRequestRepository,
        platform_repo: SqlAlchemyPlatformRepository,
        listing_repo: ListingRepository,
        market_price_repo: MarketPriceRepository,
        opportunity_repo: OpportunityRepository,
        pricing_factory: PricingServiceFactory,
        settings: Settings,
    ):
        self._car_trim_repo = car_trim_repo
        self._car_model_repo = car_model_repo
        self._car_brand_repo = car_brand_repo
        self._crawl_target_repo = crawl_target_repo
        self._purchase_request_repo = purchase_request_repo
        self._platform_repo = platform_repo
        self._listing_repo = listing_repo
        self._market_price_repo = market_price_repo
        self._opportunity_repo = opportunity_repo
        self._pricing_factory = pricing_factory
        self._settings = settings

    async def execute(self, input_dto: CreatePurchaseFlowInput) -> PurchaseFlowResult:
        trim = await self._car_trim_repo.get_by_id(input_dto.car_trim_id)
        if not trim:
            raise EntityNotFoundError("تریم خودرو پیدا نشد")

        car_model = await self._car_model_repo.get_by_id(trim.model_id)
        if not car_model or not car_model.is_active:
            raise ValidationError("مدل خودرو فعال نیست")

        pricing_slug = input_dto.pricing_platform_slug or self._settings.default_pricing_platform
        pricing_platform = await self._platform_repo.get_pricing_platform_by_slug(pricing_slug)
        if not pricing_platform:
            raise ValidationError(f"پلتفرم قیمت‌گذاری «{pricing_slug}» پیدا نشد")

        pricing_mapping = await ensure_pricing_mapping(
            self._platform_repo,
            trim=trim,
            pricing_platform_id=pricing_platform.id,
        )

        brand = await self._car_brand_repo.get_by_id(car_model.brand_id)
        if not brand:
            raise ValidationError("برند خودرو پیدا نشد")

        listing_slugs = input_dto.listing_platform_slugs or ["divar"]

        poll_interval = input_dto.poll_interval_sec or self._settings.crawl_pool_refresh_sec
        if input_dto.ttl_hours is not None:
            expires_at = utc_now() + timedelta(hours=input_dto.ttl_hours)
        else:
            expires_at = utc_now() + timedelta(days=self._settings.purchase_active_days)

        city = input_dto.city

        year_min, year_max = resolve_production_year_range(
            trim,
            production_year_min=input_dto.production_year_min,
            production_year_max=input_dto.production_year_max,
        )

        pricing_fetch_strategy = pricing_platform.fetch_strategy or PlatformFetchStrategy.CRAWL.value

        crawl_targets, filtered_divar_url = await resolve_crawl_targets_for_trim(
            platform_repo=self._platform_repo,
            crawl_target_repo=self._crawl_target_repo,
            trim=trim,
            car_model=car_model,
            brand=brand,
            city=city,
            settings=self._settings,
            listing_platform_slugs=listing_slugs,
            production_year_min=year_min,
            production_year_max=year_max,
            usage_min=input_dto.usage_min,
            usage_max=input_dto.usage_max,
            pricing_fetch_strategy=pricing_fetch_strategy,
        )
        listing_mapping_configured = bool(crawl_targets)

        preview_year = year_min or year_max or 1403
        preview_km = input_dto.usage_max or input_dto.usage_min or 30000
        pricing_preview_url = self._build_pricing_preview_url(
            pricing_slug, pricing_mapping, preview_year, preview_km, input_dto.color
        )

        purchase_request = PurchaseRequest(
            id=uuid4(),
            user_id=input_dto.user_id,
            car_trim_id=trim.id,
            car_model_id=trim.model_id,
            crawl_target_id=crawl_targets[0].id if crawl_targets else None,
            pricing_platform_id=pricing_platform.id,
            city=city,
            color=input_dto.color,
            production_year_min=year_min,
            production_year_max=year_max,
            usage_min=input_dto.usage_min,
            usage_max=input_dto.usage_max,
            generated_divar_url=filtered_divar_url,
            is_active=input_dto.is_active,
            near_threshold_pct=input_dto.near_threshold_pct,
            poll_interval_sec=poll_interval,
            max_listings_per_check=self._settings.shared_pool_listings_limit,
            expires_at=expires_at,
            crawl_target_ids=[t.id for t in crawl_targets],
        )
        purchase_request = await self._purchase_request_repo.save(purchase_request)

        immediate_opps: list[str] = []
        if crawl_targets:
            try:
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
                immediate_opps = await evaluator.for_purchase_request(purchase_request.id)
            except Exception:
                logger.exception(
                    "Immediate evaluation failed for purchase %s", purchase_request.id
                )

        return PurchaseFlowResult(
            purchase_request=purchase_request,
            crawl_targets=crawl_targets,
            divar_url=filtered_divar_url,
            pricing_preview_url=pricing_preview_url,
            pricing_platform_slug=pricing_slug,
            expires_at=expires_at,
            immediate_opportunities=len(immediate_opps),
            listing_mapping_configured=listing_mapping_configured,
        )

    def _build_pricing_preview_url(
        self, pricing_slug: str, pricing_mapping, year: int, km: int, color: str | None
    ) -> str:
        if pricing_slug == "khodro45":
            config = merge_khodro45_pricing_config(pricing_mapping)
            slug = config.get("slug", pricing_mapping.slug)
            color_id = config.get("default_color", "Black")
            if color and config.get("color_map"):
                color_id = config["color_map"].get(color, color_id)
            return build_khodro45_price_url(slug, year, km, color_id, self._settings.khodro45_base_url)
        return ""
