from decimal import Decimal

from src.domain.entities.crawl_run import CrawlRun
from src.domain.entities.crawl_target import CrawlTarget, VehicleContext
from src.domain.entities.delivery import GatewayClick, OpportunityDelivery, SmsStatus
from src.domain.entities.listing import Listing
from src.domain.entities.market_price import MarketPrice
from src.domain.entities.opportunity import Opportunity, OpportunityStatus
from src.domain.entities.purchase_request import PurchaseRequest
from src.domain.entities.user import User
from src.infrastructure.persistence.models import (
    CrawlRunModel,
    CrawlTargetModel,
    GatewayClickModel,
    ListingModel,
    MarketPriceModel,
    OpportunityDeliveryModel,
    OpportunityModel,
    PurchaseRequestModel,
    UserModel,
)


def user_to_domain(model: UserModel) -> User:
    return User(
        id=model.id,
        phone=model.phone,
        first_name=model.first_name,
        last_name=model.last_name,
        source_channel=model.source_channel,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def crawl_target_to_domain(model: CrawlTargetModel) -> CrawlTarget:
    return CrawlTarget(
        id=model.id,
        source=model.source,
        listing_url=model.listing_url,
        vehicle_context=VehicleContext.from_dict(model.vehicle_context),
        is_active=model.is_active,
        poll_interval_sec=model.poll_interval_sec,
        listing_mapping_id=model.listing_mapping_id,
        car_model_id=model.car_model_id,
        city=model.city or "tehran",
        is_shared_pool=bool(model.is_shared_pool),
        pool_production_year=model.pool_production_year,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def purchase_request_to_domain(model: PurchaseRequestModel) -> PurchaseRequest:
    return PurchaseRequest(
        id=model.id,
        user_id=model.user_id,
        car_trim_id=model.car_trim_id,
        car_model_id=model.car_model_id,
        crawl_target_id=model.crawl_target_id,
        pricing_platform_id=model.pricing_platform_id,
        city=model.city or "tehran",
        color=model.color,
        production_year_min=model.production_year_min,
        production_year_max=model.production_year_max,
        usage_min=model.usage_min,
        usage_max=model.usage_max,
        generated_divar_url=model.generated_divar_url,
        is_active=model.is_active,
        near_threshold_pct=Decimal(str(model.near_threshold_pct)) if model.near_threshold_pct else None,
        poll_interval_sec=model.poll_interval_sec or 300,
        max_listings_per_check=model.max_listings_per_check or 10,
        expires_at=model.expires_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def listing_to_domain(model: ListingModel) -> Listing:
    return Listing(
        id=model.id,
        crawl_target_id=model.crawl_target_id,
        car_model_id=model.car_model_id,
        external_token=model.external_token,
        title=model.title,
        price=model.price,
        kilometer=model.kilometer,
        production_year=model.production_year,
        color=model.color,
        body_condition=model.body_condition,
        district=model.district,
        divar_url=model.divar_url,
        first_seen_at=model.first_seen_at,
        last_seen_at=model.last_seen_at,
        is_active=bool(model.is_active),
    )


def market_price_to_domain(model: MarketPriceModel) -> MarketPrice:
    return MarketPrice(
        id=model.id,
        listing_id=model.listing_id,
        price_up=model.price_up,
        price_down=model.price_down,
        price_mid=model.price_mid,
        reference_url=model.reference_url,
        fetched_at=model.fetched_at,
        pricing_provider=model.pricing_provider or "hamrah_mechanic",
        trim_id=model.trim_id,
    )


def opportunity_to_domain(model: OpportunityModel) -> Opportunity:
    return Opportunity(
        id=model.id,
        listing_id=model.listing_id,
        crawl_target_id=model.crawl_target_id,
        purchase_request_id=model.purchase_request_id,
        listing_price=model.listing_price,
        market_price_down=model.market_price_down,
        market_price_up=model.market_price_up,
        market_price_mid=model.market_price_mid,
        price_basis=model.price_basis or "down",
        deal_tag=model.deal_tag or "best",
        reference_price=model.reference_price or model.market_price_down,
        discount_amount=model.discount_amount,
        discount_pct=Decimal(str(model.discount_pct)),
        score=Decimal(str(model.score)),
        status=OpportunityStatus(model.status),
        is_below_floor=model.is_below_floor,
        created_at=model.created_at,
    )


def crawl_run_to_domain(model: CrawlRunModel) -> CrawlRun:
    from src.domain.entities.crawl_run import CrawlRunStatus

    return CrawlRun(
        id=model.id,
        crawl_target_id=model.crawl_target_id,
        status=CrawlRunStatus(model.status),
        started_at=model.started_at,
        posts_found=model.posts_found,
        opportunities_found=model.opportunities_found,
        finished_at=model.finished_at,
        error_message=model.error_message,
        diagnostics=model.diagnostics or [],
    )


def delivery_to_domain(model: OpportunityDeliveryModel) -> OpportunityDelivery:
    return OpportunityDelivery(
        id=model.id,
        opportunity_id=model.opportunity_id,
        purchase_request_id=model.purchase_request_id,
        user_id=model.user_id,
        gateway_token=model.gateway_token,
        sms_status=SmsStatus(model.sms_status),
        sms_sent_at=model.sms_sent_at,
        sms_provider_id=model.sms_provider_id,
        sms_error=model.sms_error,
        created_at=model.created_at,
    )


def click_to_domain(model: GatewayClickModel) -> GatewayClick:
    return GatewayClick(
        id=model.id,
        delivery_id=model.delivery_id,
        clicked_at=model.clicked_at,
        time_to_click_sec=model.time_to_click_sec,
    )
