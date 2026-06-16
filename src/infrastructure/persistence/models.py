import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CarBrandModel(Base):
    __tablename__ = "car_brands"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    khodro45_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    title_en: Mapped[str | None] = mapped_column(String(100), nullable=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    models: Mapped[list["CarModelModel"]] = relationship(back_populates="brand")


class CarModelModel(Base):
    __tablename__ = "car_models"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    khodro45_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("car_brands.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    title_en: Mapped[str | None] = mapped_column(String(150), nullable=True)
    slug: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    near_threshold_pct: Mapped[float] = mapped_column(Numeric(5, 4), default=0.02)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    brand: Mapped[CarBrandModel] = relationship(back_populates="models")
    years: Mapped[list["CarYearModel"]] = relationship(back_populates="model")
    trims: Mapped[list["CarTrimModel"]] = relationship(back_populates="model")
    purchase_requests: Mapped[list["PurchaseRequestModel"]] = relationship(back_populates="car_model")


class CarYearModel(Base):
    __tablename__ = "car_years"
    __table_args__ = (UniqueConstraint("model_id", "khodro45_id", name="uq_car_year_model_k45"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    khodro45_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("car_models.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(10), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    model: Mapped[CarModelModel] = relationship(back_populates="years")
    trims: Mapped[list["CarTrimModel"]] = relationship(back_populates="year")


class CarTrimModel(Base):
    __tablename__ = "car_trims"
    __table_args__ = (UniqueConstraint("year_id", "seo_slug", name="uq_car_trim_year_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    khodro45_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("car_models.id"), nullable=False, index=True)
    year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("car_years.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    title_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    seo_slug: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    model: Mapped[CarModelModel] = relationship(back_populates="trims")
    year: Mapped[CarYearModel] = relationship(back_populates="trims")
    pricing_mappings: Mapped[list["TrimPricingMappingModel"]] = relationship(back_populates="trim")
    listing_links: Mapped[list["ListingMappingTrimModel"]] = relationship(back_populates="trim")
    purchase_requests: Mapped[list["PurchaseRequestModel"]] = relationship(back_populates="car_trim")


class ListingPlatformModel(Base):
    __tablename__ = "listing_platforms"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    fetch_strategy: Mapped[str] = mapped_column(String(10), default="crawl", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DivarCityModel(Base):
    __tablename__ = "divar_cities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    display: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DivarCarModelModel(Base):
    __tablename__ = "divar_car_models"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    display: Mapped[str] = mapped_column(String(300), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    listing_mappings: Mapped[list["ListingMappingModel"]] = relationship(back_populates="divar_car_model")


class PricingPlatformModel(Base):
    __tablename__ = "pricing_platforms"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    fetch_strategy: Mapped[str] = mapped_column(String(10), default="crawl", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ListingMappingModel(Base):
    __tablename__ = "listing_mappings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    listing_platform_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("listing_platforms.id"), nullable=False, index=True
    )
    divar_car_model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("divar_car_models.id"), nullable=False, index=True
    )
    path: Mapped[str] = mapped_column(String(300), nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    listing_platform: Mapped[ListingPlatformModel] = relationship()
    divar_car_model: Mapped[DivarCarModelModel] = relationship(back_populates="listing_mappings")
    trim_links: Mapped[list["ListingMappingTrimModel"]] = relationship(back_populates="listing_mapping")
    crawl_targets: Mapped[list["CrawlTargetModel"]] = relationship(back_populates="listing_mapping")


class ListingMappingTrimModel(Base):
    __tablename__ = "listing_mapping_trims"
    __table_args__ = (
        UniqueConstraint("listing_mapping_id", "trim_id", name="uq_listing_mapping_trim"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    listing_mapping_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("listing_mappings.id"), nullable=False, index=True
    )
    trim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("car_trims.id"), nullable=False, index=True)

    listing_mapping: Mapped[ListingMappingModel] = relationship(back_populates="trim_links")
    trim: Mapped[CarTrimModel] = relationship(back_populates="listing_links")


class TrimPricingMappingModel(Base):
    __tablename__ = "trim_pricing_mappings"
    __table_args__ = (UniqueConstraint("trim_id", "pricing_platform_id", name="uq_trim_pricing_platform"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    trim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("car_trims.id"), nullable=False, index=True)
    pricing_platform_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pricing_platforms.id"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    trim: Mapped[CarTrimModel] = relationship(back_populates="pricing_mappings")
    pricing_platform: Mapped[PricingPlatformModel] = relationship()


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    source_channel: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    purchase_requests: Mapped[list["PurchaseRequestModel"]] = relationship(back_populates="user")


class CrawlTargetModel(Base):
    __tablename__ = "crawl_targets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    listing_mapping_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("listing_mappings.id"), nullable=True, index=True
    )
    car_model_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("car_models.id"), nullable=True, index=True
    )
    city: Mapped[str] = mapped_column(String(50), default="tehran")
    is_shared_pool: Mapped[bool] = mapped_column(Boolean, default=False)
    pool_production_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="divar")
    listing_url: Mapped[str] = mapped_column(Text, nullable=False)
    vehicle_context: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    poll_interval_sec: Mapped[int] = mapped_column(Integer, default=300)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    purchase_requests: Mapped[list["PurchaseRequestModel"]] = relationship(back_populates="crawl_target")
    listings: Mapped[list["ListingModel"]] = relationship(back_populates="crawl_target")
    crawl_runs: Mapped[list["CrawlRunModel"]] = relationship(back_populates="crawl_target")
    listing_mapping: Mapped["ListingMappingModel | None"] = relationship(back_populates="crawl_targets")


class PurchaseRequestModel(Base):
    __tablename__ = "purchase_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    car_trim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("car_trims.id"), nullable=False, index=True
    )
    car_model_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("car_models.id"), nullable=True, index=True
    )
    crawl_target_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("crawl_targets.id"), nullable=True, index=True
    )
    pricing_platform_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pricing_platforms.id"), nullable=True, index=True
    )
    city: Mapped[str] = mapped_column(String(50), default="tehran")
    color: Mapped[str | None] = mapped_column(String(100))
    production_year_min: Mapped[int | None] = mapped_column(Integer)
    production_year_max: Mapped[int | None] = mapped_column(Integer)
    usage_min: Mapped[int | None] = mapped_column(Integer)
    usage_max: Mapped[int | None] = mapped_column(Integer)
    generated_divar_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    near_threshold_pct: Mapped[float | None] = mapped_column(Numeric(5, 4))
    poll_interval_sec: Mapped[int] = mapped_column(Integer, default=300)
    max_listings_per_check: Mapped[int] = mapped_column(Integer, default=10)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[UserModel] = relationship(back_populates="purchase_requests")
    car_trim: Mapped[CarTrimModel] = relationship(back_populates="purchase_requests")
    car_model: Mapped[CarModelModel | None] = relationship(back_populates="purchase_requests")
    crawl_target: Mapped[CrawlTargetModel | None] = relationship(back_populates="purchase_requests")
    pricing_platform: Mapped["PricingPlatformModel | None"] = relationship()
    crawl_target_links: Mapped[list["PurchaseRequestCrawlTargetModel"]] = relationship(
        back_populates="purchase_request"
    )


class PurchaseRequestCrawlTargetModel(Base):
    __tablename__ = "purchase_request_crawl_targets"
    __table_args__ = (
        UniqueConstraint("purchase_request_id", "crawl_target_id", name="uq_purchase_crawl_target"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    purchase_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchase_requests.id"), nullable=False, index=True
    )
    crawl_target_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crawl_targets.id"), nullable=False, index=True
    )

    purchase_request: Mapped[PurchaseRequestModel] = relationship(back_populates="crawl_target_links")
    crawl_target: Mapped[CrawlTargetModel] = relationship()


class CrawlRunModel(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    crawl_target_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crawl_targets.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posts_found: Mapped[int] = mapped_column(Integer, default=0)
    opportunities_found: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    diagnostics: Mapped[list | None] = mapped_column(JSON)

    crawl_target: Mapped[CrawlTargetModel] = relationship(back_populates="crawl_runs")


class ListingModel(Base):
    __tablename__ = "listings"
    __table_args__ = (UniqueConstraint("external_token", name="uq_listings_external_token"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    crawl_target_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crawl_targets.id"), nullable=False, index=True
    )
    car_model_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("car_models.id"), nullable=True, index=True
    )
    external_token: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kilometer: Mapped[int | None] = mapped_column(Integer)
    production_year: Mapped[int | None] = mapped_column(Integer)
    color: Mapped[str | None] = mapped_column(String(100))
    body_condition: Mapped[str | None] = mapped_column(String(100))
    district: Mapped[str | None] = mapped_column(String(200))
    divar_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    crawl_target: Mapped[CrawlTargetModel] = relationship(back_populates="listings")
    market_prices: Mapped[list["MarketPriceModel"]] = relationship(back_populates="listing")
    opportunities: Mapped[list["OpportunityModel"]] = relationship(back_populates="listing")


class MarketPriceModel(Base):
    __tablename__ = "market_prices"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"), nullable=False, index=True)
    trim_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("car_trims.id"), nullable=True, index=True
    )
    price_up: Mapped[int] = mapped_column(BigInteger, nullable=False)
    price_down: Mapped[int] = mapped_column(BigInteger, nullable=False)
    price_mid: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reference_url: Mapped[str] = mapped_column(Text, nullable=False)
    pricing_provider: Mapped[str] = mapped_column(String(50), default="hamrah_mechanic")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listing: Mapped[ListingModel] = relationship(back_populates="market_prices")


class OpportunityModel(Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        UniqueConstraint(
            "listing_id",
            "purchase_request_id",
            name="uq_opportunity_listing_purchase",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"), nullable=False, index=True)
    purchase_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("purchase_requests.id"), nullable=True, index=True
    )
    crawl_target_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crawl_targets.id"), nullable=False, index=True
    )
    listing_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    market_price_down: Mapped[int] = mapped_column(BigInteger, nullable=False)
    market_price_up: Mapped[int] = mapped_column(BigInteger, nullable=False)
    market_price_mid: Mapped[int | None] = mapped_column(BigInteger)
    price_basis: Mapped[str] = mapped_column(String(10), nullable=False, default="down")
    deal_tag: Mapped[str] = mapped_column(String(10), nullable=False, default="best")
    reference_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_pct: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")
    is_below_floor: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listing: Mapped[ListingModel] = relationship(back_populates="opportunities")
    deliveries: Mapped[list["OpportunityDeliveryModel"]] = relationship(back_populates="opportunity")


class OpportunityDeliveryModel(Base):
    __tablename__ = "opportunity_deliveries"
    __table_args__ = (
        UniqueConstraint("gateway_token", name="uq_deliveries_gateway_token"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunities.id"), nullable=False, index=True
    )
    purchase_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchase_requests.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    gateway_token: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sms_status: Mapped[str] = mapped_column(String(20), default="pending")
    sms_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sms_provider_id: Mapped[str | None] = mapped_column(String(100))
    sms_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    opportunity: Mapped[OpportunityModel] = relationship(back_populates="deliveries")
    clicks: Mapped[list["GatewayClickModel"]] = relationship(back_populates="delivery")
    page_views: Mapped[list["OpportunityPageViewModel"]] = relationship(back_populates="delivery")


class GatewayClickModel(Base):
    __tablename__ = "gateway_clicks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_deliveries.id"), nullable=False, index=True
    )
    clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    time_to_click_sec: Mapped[int | None] = mapped_column(Integer)

    delivery: Mapped[OpportunityDeliveryModel] = relationship(back_populates="clicks")


class OpportunityPageViewModel(Base):
    __tablename__ = "opportunity_page_views"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_deliveries.id"), nullable=False, index=True
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    is_unique_view: Mapped[bool] = mapped_column(Boolean, default=True)
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    delivery: Mapped[OpportunityDeliveryModel] = relationship(back_populates="page_views")


class OpportunityShareBatchModel(Base):
    __tablename__ = "opportunity_share_batches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    purchase_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchase_requests.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    opportunity_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SmsProviderModel(Base):
    __tablename__ = "sms_providers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    driver: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    templates: Mapped[list["SmsTemplateModel"]] = relationship(back_populates="provider")


class SmsTemplateModel(Base):
    __tablename__ = "sms_templates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    send_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="text")
    text_body: Mapped[str | None] = mapped_column(Text)
    pattern_key: Mapped[str | None] = mapped_column(String(120))
    pattern_slots: Mapped[list | None] = mapped_column(JSON)
    pattern_params: Mapped[list | None] = mapped_column(JSON)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sms_providers.id"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    provider: Mapped[SmsProviderModel] = relationship(back_populates="templates")
