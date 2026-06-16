from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    phone: str
    source_channel: str
    first_name: str | None = None
    last_name: str | None = None


class UserUpdate(BaseModel):
    phone: str | None = None
    source_channel: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: UUID
    phone: str
    source_channel: str
    first_name: str | None
    last_name: str | None
    is_active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class VehicleContextSchema(BaseModel):
    hamrah_brand: str
    hamrah_model: str
    hamrah_type_id: str
    default_color: str = "ColorWhite"
    default_body_condition: str = "WithoutColor"
    color_map: dict[str, str] = Field(default_factory=dict)
    near_threshold_pct: float = 0.02
    max_pages_per_run: int = 5


class CrawlTargetCreate(BaseModel):
    listing_url: str
    vehicle_context: VehicleContextSchema
    source: str = "divar"
    poll_interval_sec: int = 300
    is_active: bool = True


class CrawlTargetUpdate(BaseModel):
    listing_url: str | None = None
    vehicle_context: VehicleContextSchema | None = None
    poll_interval_sec: int | None = None
    is_active: bool | None = None


class CrawlTargetResponse(BaseModel):
    id: UUID
    source: str
    listing_url: str
    vehicle_context: dict[str, Any]
    is_active: bool
    poll_interval_sec: int
    created_at: datetime | None = None


class CarBrandResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool


class CarModelResponse(BaseModel):
    id: UUID
    brand_id: UUID
    brand_name: str | None = None
    name: str
    slug: str
    is_active: bool


class CarYearResponse(BaseModel):
    id: UUID
    model_id: UUID
    title: str
    jalali_year: int | None = None
    model_name: str | None = None
    brand_name: str | None = None
    is_active: bool


class CarTrimResponse(BaseModel):
    id: UUID
    model_id: UUID
    year_id: UUID
    name: str
    seo_slug: str
    year_title: str | None = None
    model_name: str | None = None
    brand_name: str | None = None
    is_active: bool


class PlatformResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    fetch_strategy: str = "crawl"
    is_active: bool


class PreviewUrlsRequest(BaseModel):
    car_trim_id: UUID
    pricing_platform_slug: str = "hamrah_mechanic"
    city: str = "tehran"
    production_year_min: int | None = None
    production_year_max: int | None = None
    usage_min: int | None = None
    usage_max: int | None = None
    sample_production_year: int | None = None
    sample_kilometer: int | None = None
    color: str | None = None


class PreviewUrlsResponse(BaseModel):
    divar_url: str
    pricing_url: str
    pricing_platform_slug: str
    khodro45_url: str | None = None
    divar_path: str
    khodro45_slug: str | None = None
    trim_name: str | None = None
    year_title: str | None = None


class PurchaseFlowCreate(BaseModel):
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
    is_active: bool = True


class PurchaseFlowResponse(BaseModel):
    purchase_request_id: UUID
    crawl_target_id: UUID | None = None
    crawl_target_ids: list[UUID] = Field(default_factory=list)
    car_trim_id: UUID
    car_model_id: UUID | None = None
    divar_url: str = ""
    pricing_preview_url: str
    pricing_platform_slug: str
    expires_at: datetime | None = None
    hamrah_preview_url: str
    production_year_min: int | None = None
    usage_max: int | None = None
    listing_mapping_configured: bool = False


class ScenarioRunRequest(BaseModel):
    car_trim_id: UUID
    car_model_id: UUID | None = None
    user_id: UUID | None = None
    phone: str = "09120000000"
    source_channel: str = "landing"
    first_name: str | None = "Test"
    last_name: str | None = "User"
    pricing_platform_slug: str | None = None
    listing_platform_slugs: list[str] | None = None
    city: str = "tehran"
    color: str | None = None
    production_year_min: int | None = 1402
    production_year_max: int | None = None
    usage_min: int | None = None
    usage_max: int | None = 80000
    run_crawl: bool = False


class ScenarioRunResponse(BaseModel):
    user_id: UUID
    purchase_request_id: UUID
    crawl_target_id: UUID | None = None
    crawl_target_ids: list[UUID] = Field(default_factory=list)
    divar_url: str
    pricing_preview_url: str
    pricing_platform_slug: str
    expires_at: datetime | None = None
    hamrah_preview_url: str
    crawl_status: str | None = None


class PurchaseRequestCreate(BaseModel):
    car_trim_id: UUID
    car_model_id: UUID | None = None
    pricing_platform_slug: str | None = None
    city: str = "tehran"
    color: str | None = None
    production_year_min: int | None = None
    production_year_max: int | None = None
    usage_min: int | None = None
    usage_max: int | None = None
    near_threshold_pct: Decimal | None = None
    is_active: bool = True


class PurchaseRequestUpdate(BaseModel):
    is_active: bool | None = None
    near_threshold_pct: Decimal | None = None


class PurchaseRequestResponse(BaseModel):
    id: UUID
    user_id: UUID
    car_trim_id: UUID
    car_model_id: UUID | None = None
    crawl_target_id: UUID | None
    pricing_platform_id: UUID | None = None
    city: str
    color: str | None = None
    production_year_min: int | None
    production_year_max: int | None
    usage_min: int | None
    usage_max: int | None
    generated_divar_url: str | None
    is_active: bool
    near_threshold_pct: Decimal | None
    poll_interval_sec: int = 300
    max_listings_per_check: int = 10
    expires_at: datetime | None = None
    created_at: datetime | None = None


class OpportunityResponse(BaseModel):
    id: UUID
    listing_id: UUID
    crawl_target_id: UUID
    listing_price: int
    market_price_down: int
    market_price_up: int
    market_price_mid: int | None = None
    price_basis: str = "down"
    deal_tag: str = "best"
    reference_price: int
    discount_amount: int
    discount_pct: Decimal
    score: Decimal
    status: str
    is_below_floor: bool
    created_at: datetime | None = None


class CrawlRunResponse(BaseModel):
    id: UUID
    crawl_target_id: UUID
    status: str
    started_at: datetime
    finished_at: datetime | None
    posts_found: int
    opportunities_found: int
    error_message: str | None


class MetricsSummaryResponse(BaseModel):
    opportunities_detected: int
    opportunities_delivered: int
    sms_click_count: int
    click_rate_pct: float
    avg_time_to_click_sec: float | None


class CrawlResultOverviewItem(BaseModel):
    purchase_request_id: UUID
    user_id: UUID
    user_phone: str | None = None
    user_name: str | None = None
    car_model_name: str | None = None
    car_brand_name: str | None = None
    car_year_title: str | None = None
    car_trim_name: str | None = None
    city: str
    color: str | None = None
    production_year_min: int | None = None
    production_year_max: int | None = None
    usage_max: int | None = None
    pricing_platform: str | None = None
    is_active: bool
    expires_at: str | None = None
    created_at: str | None = None
    crawl_target_count: int = 0
    latest_crawl_status: str | None = None
    latest_crawl_at: str | None = None
    latest_posts_found: int = 0
    latest_opportunities_found: int = 0
    total_opportunities: int = 0
    monitoring_status: str = "pending"
    sms_sent_count: int = 0


class CrawlTargetSummary(BaseModel):
    id: UUID
    source: str
    listing_url: str
    is_active: bool
    poll_interval_sec: int


class CrawlRunSummary(BaseModel):
    id: UUID
    crawl_target_id: UUID
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    posts_found: int
    opportunities_found: int
    listings_count: int = 0
    error_message: str | None = None
    diagnostics: list[dict] = Field(default_factory=list)


class ListingsPagination(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    has_more: bool = False
    crawl_run_id: UUID | None = None


class ListingsMeta(BaseModel):
    matching_total: int = 0
    pool_priced_total: int = 0
    per_page: int = 20
    latest_crawl_posts: int = 0


class CrawlTaskStatusResponse(BaseModel):
    redis_ok: bool
    redis_error: str | None = None
    celery_broker: str
    scheduler_note: str
    active_purchases: int
    running_crawls: int
    completed_crawls: int
    failed_crawls: int
    stale_runs_recovered: int
    hints: list[str] = Field(default_factory=list)


class OpportunitySummary(BaseModel):
    id: UUID
    listing_title: str | None = None
    listing_price: int
    market_price_down: int
    market_price_up: int
    market_price_mid: int | None = None
    price_basis: str = "down"
    deal_tag: str = "best"
    reference_price: int | None = None
    discount_pct: float
    discount_amount: int
    status: str
    is_below_floor: bool
    divar_url: str | None = None
    reference_url: str | None = None
    pricing_provider: str | None = None
    kilometer: int | None = None
    production_year: int | None = None
    created_at: str | None = None


class DeliverySummary(BaseModel):
    id: UUID
    opportunity_id: UUID
    listing_title: str | None = None
    gateway_token: str
    sms_status: str
    sms_sent_at: str | None = None
    sms_error: str | None = None
    created_at: str | None = None


class MarketPriceSummary(BaseModel):
    id: UUID
    price_up: int
    price_down: int
    price_mid: int
    reference_url: str
    pricing_provider: str
    fetched_at: str | None = None


class ListingSummary(BaseModel):
    id: UUID
    crawl_target_id: UUID
    external_token: str
    title: str
    price: int
    kilometer: int | None = None
    production_year: int | None = None
    color: str | None = None
    district: str | None = None
    divar_url: str
    first_seen_at: str | None = None
    last_seen_at: str | None = None
    latest_market_price: MarketPriceSummary | None = None
    has_opportunity: bool = False
    opportunity_deal_tag: str | None = None
    opportunity_status: str | None = None


class CrawlResultDetailResponse(BaseModel):
    purchase_request: dict
    user: dict
    car_model: dict
    pricing_platform: str | None = None
    crawl_targets: list[CrawlTargetSummary]
    crawl_runs: list[CrawlRunSummary]
    listings: list[ListingSummary] = Field(default_factory=list)
    listings_pagination: ListingsPagination | None = None
    listings_meta: ListingsMeta | None = None
    opportunities: list[OpportunitySummary]
    deliveries: list[DeliverySummary]


class OtpCreateRequest(BaseModel):
    phone: str


class OtpCreateResponse(BaseModel):
    phone: str
    expires_in_sec: int
    sandbox: bool
    sandbox_code: str | None = None
    message: str


class OtpVerifyRequest(BaseModel):
    phone: str
    code: str
    first_name: str | None = None


class OtpVerifyResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserPurchaseCreate(BaseModel):
    car_trim_id: UUID
    car_model_id: UUID | None = None
    pricing_platform_slug: str | None = "hamrah_mechanic"
    city: str = "tehran"
    color: str | None = None
    production_year_min: int | None = None
    production_year_max: int | None = None
    usage_min: int | None = None
    usage_max: int | None = None
    run_crawl: bool = False


class MyPurchaseSummary(BaseModel):
    purchase_request_id: UUID
    car_brand_name: str | None = None
    car_model_name: str | None = None
    car_year_title: str | None = None
    car_trim_name: str | None = None
    city: str
    production_year_min: int | None = None
    usage_max: int | None = None
    pricing_platform: str | None = None
    is_active: bool
    expires_at: str | None = None
    created_at: str | None = None
    opportunity_count: int = 0
    latest_crawl_status: str | None = None
    monitoring_status: str = "pending"


class MyPurchaseDetailResponse(BaseModel):
    purchase_request: dict
    car_model: dict
    pricing_platform: str | None = None
    listings: list[ListingSummary] = Field(default_factory=list)
    opportunities: list[OpportunitySummary]
    monitoring_status: str = "pending"


class ListingMappingCreate(BaseModel):
    listing_platform_slug: str = "divar"
    divar_car_model_id: UUID
    path: str
    config: dict[str, Any] = Field(default_factory=dict)
    trim_ids: list[UUID] = Field(default_factory=list)


class ListingMappingLinkTrims(BaseModel):
    trim_ids: list[UUID]


class ListingMappingResponse(BaseModel):
    id: UUID
    listing_platform_slug: str | None = None
    path: str
    divar_car_model_id: UUID
    divar_car_model_slug: str = ""
    divar_car_model_display: str = ""
    is_active: bool
    trim_count: int = 0
    trims: list[dict] = Field(default_factory=list)


class DivarCityResponse(BaseModel):
    id: UUID
    slug: str
    display: str


class DivarCarModelResponse(BaseModel):
    id: UUID
    slug: str
    display: str


class SendOpportunitySmsRequest(BaseModel):
    opportunity_ids: list[UUID]
    mode: str = "gateway"  # gateway | portal


class SendOpportunitySmsResponse(BaseModel):
    sms_sent: int
    deliveries_created: int
    share_token: str | None = None
    share_url: str | None = None


class ReviewOpportunitiesRequest(BaseModel):
    opportunity_ids: list[UUID]
    action: str  # approve | reject


class ReviewOpportunitiesResponse(BaseModel):
    updated: int
    action: str


class ShareBatchDetailResponse(BaseModel):
    purchase_request: dict
    car_model: dict
    opportunities: list[OpportunitySummary]
