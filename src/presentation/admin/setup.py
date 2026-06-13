from pathlib import Path

from sqlalchemy import create_engine
from starlette.middleware.sessions import SessionMiddleware
from starlette_admin.views import DropDown, Link
from starlette_admin.auth import AdminConfig, AdminUser, AuthProvider, LoginFailed
from starlette_admin.contrib.sqla import Admin, ModelView
from starlette.requests import Request
from starlette.responses import Response

from src.infrastructure.config import get_settings
from src.presentation.routing_paths import portal_results_path, portal_user_prefix
from src.infrastructure.persistence.models import (
    CarBrandModel,
    CarModelModel,
    CarTrimModel,
    CarYearModel,
    CrawlRunModel,
    CrawlTargetModel,
    DivarCarModelModel,
    DivarCityModel,
    GatewayClickModel,
    ListingMappingModel,
    ListingMappingTrimModel,
    ListingModel,
    ListingPlatformModel,
    MarketPriceModel,
    OpportunityDeliveryModel,
    OpportunityModel,
    OpportunityPageViewModel,
    PricingPlatformModel,
    PurchaseRequestCrawlTargetModel,
    PurchaseRequestModel,
    TrimPricingMappingModel,
    UserModel,
)

_ADMIN_TEMPLATES = Path(__file__).resolve().parent / "templates"


class PurchaseRequestAdmin(ModelView):
    label = "Purchase Requests"
    name = "Purchase"
    icon = "fa fa-shopping-cart"
    fields = [
        "id",
        "user",
        "car_trim",
        "car_model",
        "pricing_platform",
        "crawl_target",
        "city",
        "color",
        "production_year_min",
        "production_year_max",
        "usage_min",
        "usage_max",
        "generated_divar_url",
        "is_active",
        "near_threshold_pct",
        "poll_interval_sec",
        "max_listings_per_check",
        "expires_at",
        "created_at",
        "updated_at",
    ]
    exclude_fields_from_list = ["generated_divar_url"]


class CrawlTargetAdmin(ModelView):
    label = "Crawl Targets"
    name = "Crawl Target"
    icon = "fa fa-search"
    fields = [
        "id",
        "source",
        "listing_url",
        "vehicle_context",
        "is_active",
        "poll_interval_sec",
        "created_at",
        "updated_at",
    ]


class ListingAdmin(ModelView):
    label = "Listings"
    name = "Listing"
    icon = "fa fa-list"
    fields = [
        "id",
        "crawl_target",
        "external_token",
        "title",
        "price",
        "kilometer",
        "production_year",
        "color",
        "district",
        "divar_url",
        "first_seen_at",
        "last_seen_at",
    ]
    exclude_fields_from_list = ["title", "divar_url"]


class OpportunityAdmin(ModelView):
    label = "Opportunities"
    name = "Opportunity"
    icon = "fa fa-star"
    fields = [
        "id",
        "listing",
        "crawl_target_id",
        "listing_price",
        "price_basis",
        "deal_tag",
        "reference_price",
        "market_price_down",
        "market_price_mid",
        "market_price_up",
        "discount_amount",
        "discount_pct",
        "score",
        "status",
        "is_below_floor",
        "created_at",
    ]
    exclude_fields_from_list = ["listing"]


class UserAdmin(ModelView):
    label = "Users"
    name = "User"
    icon = "fa fa-user"
    exclude_fields_from_list = ["purchase_requests"]
    exclude_fields_from_detail = ["purchase_requests"]


class AdminAuth(AuthProvider):
    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> Response:
        if username == "admin" and password == "admin":
            request.session.update({"username": username})
            return response
        raise LoginFailed("Invalid username or password")

    async def is_authenticated(self, request: Request) -> bool:
        return request.session.get("username") == "admin"

    def get_admin_config(self, request: Request) -> AdminConfig:
        return AdminConfig(app_title="Car Opportunity Admin")

    def get_admin_user(self, request: Request) -> AdminUser | None:
        if request.session.get("username") == "admin":
            return AdminUser(username="admin")
        return None

    async def logout(self, request: Request, response: Response) -> Response:
        request.session.clear()
        return response


def setup_admin(app, admin_base_url: str = "/admin") -> Admin:
    settings = get_settings()
    url = settings.database_url
    if "sqlite" in url:
        sync_url = url.replace("+aiosqlite", "")
    else:
        sync_url = url.replace("+asyncpg", "+psycopg2")
    connect_args = {"check_same_thread": False} if "sqlite" in sync_url else {}
    engine = create_engine(sync_url, connect_args=connect_args)

    https_only = settings.app_env == "production"
    app.add_middleware(
        SessionMiddleware,
        secret_key="car-admin-secret-change-in-prod",
        https_only=https_only,
        same_site="lax",
    )

    templates_dir = str(_ADMIN_TEMPLATES) if _ADMIN_TEMPLATES.exists() else "templates"
    admin = Admin(
        engine,
        title="Car Opportunity Admin",
        base_url=admin_base_url,
        auth_provider=AdminAuth(),
        middlewares=[],
        templates_dir=templates_dir,
    )

    admin.add_view(Link(label="User Portal", icon="fa fa-home", url=f"{portal_user_prefix()}/"))
    admin.add_view(Link(label="Crawl Results", icon="fa fa-table", url=portal_results_path()))
    admin.add_view(
        DropDown(
            "Catalog",
            icon="fa fa-book",
            always_open=False,
            views=[
                ModelView(CarBrandModel, label="Brands", icon="fa fa-car"),
                ModelView(CarModelModel, label="Models", icon="fa fa-cogs"),
                ModelView(CarYearModel, label="Years", icon="fa fa-calendar"),
                ModelView(CarTrimModel, label="Trims", icon="fa fa-wrench"),
                ModelView(ListingPlatformModel, label="Listing Platforms", icon="fa fa-store"),
                ModelView(PricingPlatformModel, label="Pricing Platforms", icon="fa fa-tags"),
                ModelView(DivarCityModel, label="Divar Cities", icon="fa fa-map-marker"),
                ModelView(DivarCarModelModel, label="Divar Car Models", icon="fa fa-car"),
                ModelView(ListingMappingModel, label="Listing Mappings", icon="fa fa-link"),
                ModelView(ListingMappingTrimModel, label="Listing ↔ Trim", icon="fa fa-random"),
                ModelView(TrimPricingMappingModel, label="Trim Pricing", icon="fa fa-money"),
            ],
        )
    )
    admin.add_view(
        DropDown(
            "Users & Purchases",
            icon="fa fa-users",
            always_open=False,
            views=[
                UserAdmin(UserModel),
                PurchaseRequestAdmin(PurchaseRequestModel),
                ModelView(
                    PurchaseRequestCrawlTargetModel,
                    label="Purchase ↔ Crawl Links",
                    icon="fa fa-link",
                ),
            ],
        )
    )
    admin.add_view(
        DropDown(
            "Crawl Pipeline",
            icon="fa fa-spider",
            always_open=False,
            views=[
                CrawlTargetAdmin(CrawlTargetModel),
                ModelView(CrawlRunModel, label="Crawl Runs", icon="fa fa-history"),
                ListingAdmin(ListingModel),
                ModelView(MarketPriceModel, label="Market Prices", icon="fa fa-chart-line"),
            ],
        )
    )
    admin.add_view(
        DropDown(
            "Opportunities & SMS",
            icon="fa fa-bell",
            always_open=False,
            views=[
                OpportunityAdmin(OpportunityModel),
                ModelView(OpportunityDeliveryModel, label="SMS Deliveries", icon="fa fa-paper-plane"),
                ModelView(OpportunityPageViewModel, label="Page Views", icon="fa fa-eye"),
                ModelView(GatewayClickModel, label="Gateway Clicks", icon="fa fa-mouse-pointer"),
            ],
        )
    )

    admin.mount_to(app)
    return admin
