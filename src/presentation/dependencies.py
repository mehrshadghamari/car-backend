from collections.abc import AsyncGenerator

import httpx
import redis.asyncio as aioredis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.external import DivarListingPort, HamrahMechanicPricingPort, NotificationPort
from src.application.ports.repositories import (
    CrawlRunRepository,
    CrawlTargetRepository,
    DeliveryRepository,
    ListingRepository,
    MarketPriceRepository,
    OpportunityRepository,
    PurchaseRequestRepository,
    UserRepository,
)
from src.application.ports.car_catalog import (
    CarBrandRepository,
    CarModelRepository,
    CarTrimRepository,
    CarYearRepository,
)
from src.application.use_cases.create_purchase_flow import CreatePurchaseFlowUseCase
from src.application.use_cases.run_purchase_crawl import RunPurchaseCrawlUseCase
from src.application.use_cases.crawl_and_evaluate import CrawlAndEvaluateUseCase
from src.application.use_cases.preview_urls import PreviewUrlsUseCase
from src.application.use_cases.send_opportunity_sms import SendOpportunitySmsUseCase
from src.application.use_cases.gateway_preview import GatewayPreviewUseCase
from src.application.use_cases.gateway_redirect import GatewayRedirectUseCase
from src.infrastructure.adapters.pricing_factory import PricingServiceFactory
from src.infrastructure.persistence.crawl_results_repository import SqlAlchemyCrawlResultsRepository
from src.infrastructure.persistence.platform_repositories import SqlAlchemyPlatformRepository
from src.infrastructure.persistence.share_batch_repository import SqlAlchemyShareBatchRepository
from src.application.use_cases.manage_crawl_targets import ManageCrawlTargetsUseCase
from src.application.use_cases.manage_purchase_requests import ManagePurchaseRequestsUseCase
from src.application.use_cases.manage_users import ManageUsersUseCase
from src.application.use_cases.match_and_notify import MatchAndNotifyUseCase
from src.application.use_cases.metrics import MetricsUseCase
from src.infrastructure.adapters.divar.divar_adapter import DivarListingAdapter
from src.infrastructure.adapters.hamrah_mechanic.hamrah_adapter import HamrahMechanicPricingAdapter
from src.infrastructure.adapters.sms.sms_ir_adapter import SmsIrAdapter
from src.application.use_cases.otp_auth import OtpAuthUseCase
from src.infrastructure.auth.otp_store import RedisOtpStore
from src.infrastructure.auth.tokens import AuthTokenService
from src.infrastructure.config import Settings, get_settings
from src.infrastructure.persistence.database import async_session_factory
from src.infrastructure.persistence.car_catalog_repositories import (
    SqlAlchemyCarBrandRepository,
    SqlAlchemyCarModelRepository,
    SqlAlchemyCarTrimRepository,
    SqlAlchemyCarYearRepository,
)
from src.infrastructure.persistence.repositories import (
    SqlAlchemyCrawlRunRepository,
    SqlAlchemyCrawlTargetRepository,
    SqlAlchemyDeliveryRepository,
    SqlAlchemyListingRepository,
    SqlAlchemyMarketPriceRepository,
    SqlAlchemyOpportunityRepository,
    SqlAlchemyPurchaseRequestRepository,
    SqlAlchemyUserRepository,
)

_redis_client: aioredis.Redis | None = None
_httpx_client: httpx.AsyncClient | None = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=False)
    return _redis_client


async def get_httpx_client() -> httpx.AsyncClient:
    global _httpx_client
    if _httpx_client is None:
        _httpx_client = httpx.AsyncClient(timeout=30.0)
    return _httpx_client


def get_divar_port(
    settings: Settings = Depends(get_settings),
) -> DivarListingPort:
    return DivarListingAdapter(settings)


def get_hamrah_port(
    settings: Settings = Depends(get_settings),
    redis: aioredis.Redis = Depends(get_redis),
) -> HamrahMechanicPricingPort:
    return HamrahMechanicPricingAdapter(settings, redis)


def get_notification_port(settings: Settings = Depends(get_settings)) -> NotificationPort:
    return SmsIrAdapter(settings)


def get_users_use_case(session: AsyncSession = Depends(get_db_session)) -> ManageUsersUseCase:
    return ManageUsersUseCase(SqlAlchemyUserRepository(session))


def get_crawl_targets_use_case(
    session: AsyncSession = Depends(get_db_session),
) -> ManageCrawlTargetsUseCase:
    return ManageCrawlTargetsUseCase(SqlAlchemyCrawlTargetRepository(session))


def get_purchase_requests_use_case(
    session: AsyncSession = Depends(get_db_session),
) -> ManagePurchaseRequestsUseCase:
    return ManagePurchaseRequestsUseCase(SqlAlchemyPurchaseRequestRepository(session))


def get_pricing_factory(
    settings: Settings = Depends(get_settings),
    redis: aioredis.Redis = Depends(get_redis),
) -> PricingServiceFactory:
    return PricingServiceFactory(settings, redis)


def get_crawl_evaluate_use_case(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    divar: DivarListingPort = Depends(get_divar_port),
    pricing_factory: PricingServiceFactory = Depends(get_pricing_factory),
) -> CrawlAndEvaluateUseCase:
    return CrawlAndEvaluateUseCase(
        crawl_target_repo=SqlAlchemyCrawlTargetRepository(session),
        listing_repo=SqlAlchemyListingRepository(session),
        market_price_repo=SqlAlchemyMarketPriceRepository(session),
        opportunity_repo=SqlAlchemyOpportunityRepository(session),
        crawl_run_repo=SqlAlchemyCrawlRunRepository(session),
        purchase_request_repo=SqlAlchemyPurchaseRequestRepository(session),
        platform_repo=SqlAlchemyPlatformRepository(session),
        car_trim_repo=SqlAlchemyCarTrimRepository(session),
        divar_port=divar,
        pricing_factory=pricing_factory,
        settings=settings,
        max_concurrent_details=settings.divar_max_concurrent_details,
    )


def get_match_notify_use_case(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    notification: NotificationPort = Depends(get_notification_port),
) -> MatchAndNotifyUseCase:
    return MatchAndNotifyUseCase(
        opportunity_repo=SqlAlchemyOpportunityRepository(session),
        purchase_request_repo=SqlAlchemyPurchaseRequestRepository(session),
        user_repo=SqlAlchemyUserRepository(session),
        listing_repo=SqlAlchemyListingRepository(session),
        delivery_repo=SqlAlchemyDeliveryRepository(session),
        notification_port=notification,
        settings=settings,
    )


def get_gateway_use_case(
    session: AsyncSession = Depends(get_db_session),
) -> GatewayRedirectUseCase:
    return GatewayRedirectUseCase(
        delivery_repo=SqlAlchemyDeliveryRepository(session),
        opportunity_repo=SqlAlchemyOpportunityRepository(session),
        listing_repo=SqlAlchemyListingRepository(session),
    )


def get_gateway_preview_use_case(
    session: AsyncSession = Depends(get_db_session),
) -> GatewayPreviewUseCase:
    return GatewayPreviewUseCase(
        delivery_repo=SqlAlchemyDeliveryRepository(session),
        opportunity_repo=SqlAlchemyOpportunityRepository(session),
        listing_repo=SqlAlchemyListingRepository(session),
    )


def get_metrics_use_case(session: AsyncSession = Depends(get_db_session)) -> MetricsUseCase:
    return MetricsUseCase(
        opportunity_repo=SqlAlchemyOpportunityRepository(session),
        delivery_repo=SqlAlchemyDeliveryRepository(session),
    )


def get_crawl_run_repo(session: AsyncSession = Depends(get_db_session)) -> CrawlRunRepository:
    return SqlAlchemyCrawlRunRepository(session)


def get_opportunity_repo(session: AsyncSession = Depends(get_db_session)) -> OpportunityRepository:
    return SqlAlchemyOpportunityRepository(session)


def get_car_brand_repo(session: AsyncSession = Depends(get_db_session)) -> CarBrandRepository:
    return SqlAlchemyCarBrandRepository(session)


def get_car_model_repo(session: AsyncSession = Depends(get_db_session)) -> CarModelRepository:
    return SqlAlchemyCarModelRepository(session)


def get_car_year_repo(session: AsyncSession = Depends(get_db_session)) -> CarYearRepository:
    return SqlAlchemyCarYearRepository(session)


def get_car_trim_repo(session: AsyncSession = Depends(get_db_session)) -> CarTrimRepository:
    return SqlAlchemyCarTrimRepository(session)


def get_evaluate_purchase_requests_use_case(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    pricing_factory: PricingServiceFactory = Depends(get_pricing_factory),
):
    from src.application.use_cases.evaluate_purchase_requests import EvaluatePurchaseRequestsUseCase

    return EvaluatePurchaseRequestsUseCase(
        crawl_target_repo=SqlAlchemyCrawlTargetRepository(session),
        purchase_request_repo=SqlAlchemyPurchaseRequestRepository(session),
        listing_repo=SqlAlchemyListingRepository(session),
        market_price_repo=SqlAlchemyMarketPriceRepository(session),
        opportunity_repo=SqlAlchemyOpportunityRepository(session),
        platform_repo=SqlAlchemyPlatformRepository(session),
        car_trim_repo=SqlAlchemyCarTrimRepository(session),
        pricing_factory=pricing_factory,
        settings=settings,
    )


def get_create_purchase_flow_use_case(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    pricing_factory: PricingServiceFactory = Depends(get_pricing_factory),
) -> CreatePurchaseFlowUseCase:
    return CreatePurchaseFlowUseCase(
        car_trim_repo=SqlAlchemyCarTrimRepository(session),
        car_model_repo=SqlAlchemyCarModelRepository(session),
        car_brand_repo=SqlAlchemyCarBrandRepository(session),
        crawl_target_repo=SqlAlchemyCrawlTargetRepository(session),
        purchase_request_repo=SqlAlchemyPurchaseRequestRepository(session),
        platform_repo=SqlAlchemyPlatformRepository(session),
        listing_repo=SqlAlchemyListingRepository(session),
        market_price_repo=SqlAlchemyMarketPriceRepository(session),
        opportunity_repo=SqlAlchemyOpportunityRepository(session),
        pricing_factory=pricing_factory,
        settings=settings,
    )


def get_run_purchase_crawl_use_case(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> RunPurchaseCrawlUseCase:
    return RunPurchaseCrawlUseCase(
        purchase_request_repo=SqlAlchemyPurchaseRequestRepository(session),
        car_trim_repo=SqlAlchemyCarTrimRepository(session),
        car_model_repo=SqlAlchemyCarModelRepository(session),
        car_brand_repo=SqlAlchemyCarBrandRepository(session),
        crawl_target_repo=SqlAlchemyCrawlTargetRepository(session),
        platform_repo=SqlAlchemyPlatformRepository(session),
        settings=settings,
    )


def get_platform_repo(session: AsyncSession = Depends(get_db_session)) -> SqlAlchemyPlatformRepository:
    return SqlAlchemyPlatformRepository(session)


def get_crawl_results_repo(
    session: AsyncSession = Depends(get_db_session),
) -> SqlAlchemyCrawlResultsRepository:
    return SqlAlchemyCrawlResultsRepository(session)


def get_share_batch_repo(session: AsyncSession = Depends(get_db_session)) -> SqlAlchemyShareBatchRepository:
    return SqlAlchemyShareBatchRepository(session)


def get_send_opportunity_sms_use_case(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    notification: NotificationPort = Depends(get_notification_port),
) -> SendOpportunitySmsUseCase:
    return SendOpportunitySmsUseCase(
        opportunity_repo=SqlAlchemyOpportunityRepository(session),
        purchase_request_repo=SqlAlchemyPurchaseRequestRepository(session),
        user_repo=SqlAlchemyUserRepository(session),
        listing_repo=SqlAlchemyListingRepository(session),
        delivery_repo=SqlAlchemyDeliveryRepository(session),
        notification_port=notification,
        settings=settings,
        share_batch_repo=SqlAlchemyShareBatchRepository(session),
    )


def get_preview_urls_use_case(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> PreviewUrlsUseCase:
    return PreviewUrlsUseCase(
        car_trim_repo=SqlAlchemyCarTrimRepository(session),
        car_model_repo=SqlAlchemyCarModelRepository(session),
        car_brand_repo=SqlAlchemyCarBrandRepository(session),
        platform_repo=SqlAlchemyPlatformRepository(session),
        settings=settings,
    )


def get_otp_store(
    settings: Settings = Depends(get_settings),
    redis: aioredis.Redis = Depends(get_redis),
):
    # Redis is required so OTP works across multiple Gunicorn workers (even in sandbox).
    return RedisOtpStore(redis)


def get_otp_auth_use_case(
    settings: Settings = Depends(get_settings),
    otp_store=Depends(get_otp_store),
    session: AsyncSession = Depends(get_db_session),
) -> OtpAuthUseCase:
    return OtpAuthUseCase(
        settings=settings,
        otp_store=otp_store,
        token_service=AuthTokenService(settings.auth_secret_key, settings.auth_token_max_age_sec),
        users=ManageUsersUseCase(SqlAlchemyUserRepository(session)),
        notification=SmsIrAdapter(settings),
    )
