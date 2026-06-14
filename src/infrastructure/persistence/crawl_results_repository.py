from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.domain.entities.car_catalog import CarTrim
from src.domain.entities.listing import Listing
from src.domain.entities.purchase_request import PurchaseRequest
from src.domain.services.listing_matcher import listing_matches_purchase_request
from src.domain.services.listing_retention import is_listing_crawl_valid
from src.domain.services.opportunity_scorer import evaluate_urgent_sale_opportunity
from src.domain.services.purchase_detail_filters import (
    effective_purchase_request,
    filter_diagnostics_for_purchase,
    latest_crawl_run_per_target,
)
from src.domain.compat import utc_now
from src.infrastructure.config import get_settings
from src.infrastructure.persistence.models import (
    CarModelModel,
    CarTrimModel,
    CarYearModel,
    CrawlRunModel,
    CrawlTargetModel,
    ListingMappingModel,
    ListingMappingTrimModel,
    ListingModel,
    ListingPlatformModel,
    MarketPriceModel,
    OpportunityDeliveryModel,
    OpportunityModel,
    PricingPlatformModel,
    PurchaseRequestCrawlTargetModel,
    PurchaseRequestModel,
    UserModel,
)


def _parse_dt(value):
    from datetime import datetime

    if value is None:
        return None
    if isinstance(value, str):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        dt = value
    now = utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=now.tzinfo)
    return dt


def _monitoring_status(
    is_active: bool,
    expires_at,
    latest_crawl_status: str | None,
    *,
    latest_crawl_started_at=None,
    purchase_created_at=None,
    opportunity_count: int = 0,
    has_crawl_targets: bool = True,
) -> str:
    now = utc_now()
    if not is_active:
        return "inactive"
    exp = _parse_dt(expires_at)
    if exp and exp <= now:
        return "inactive"
    if not has_crawl_targets:
        return "queued"
    if opportunity_count > 0:
        return "active"
    created = _parse_dt(purchase_created_at)
    started = _parse_dt(latest_crawl_started_at)
    crawl_for_this_request = (
        started is not None and created is not None and started >= created
    )
    if latest_crawl_status == "running":
        return "pending"
    if crawl_for_this_request:
        if latest_crawl_status == "completed":
            return "monitoring"
        if latest_crawl_status == "failed":
            return "failed"
    return "pending"


def _car_model_payload(pr: PurchaseRequestModel) -> dict:
    trim = pr.car_trim
    if trim and trim.year and trim.year.model:
        model = trim.year.model
        brand = model.brand
        name_parts = [p for p in (model.name, trim.year.title, trim.name) if p]
        return {
            "id": str(model.id),
            "name": " ".join(name_parts) if name_parts else model.name,
            "brand_name": brand.name if brand else None,
            "slug": model.slug,
            "trim_name": trim.name,
            "year_title": trim.year.title,
        }
    car = pr.car_model
    return {
        "id": str(pr.car_model_id) if pr.car_model_id else None,
        "name": car.name if car else None,
        "brand_name": car.brand.name if car and car.brand else None,
        "slug": car.slug if car else None,
        "trim_name": None,
        "year_title": None,
    }


class SqlAlchemyCrawlResultsRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def _target_ids_for_purchase(self, purchase_id: UUID) -> list[UUID]:
        links = await self._session.execute(
            select(PurchaseRequestCrawlTargetModel.crawl_target_id).where(
                PurchaseRequestCrawlTargetModel.purchase_request_id == purchase_id
            )
        )
        ids = [row[0] for row in links.all()]
        purchase = await self._session.get(PurchaseRequestModel, purchase_id)
        if purchase and purchase.crawl_target_id and purchase.crawl_target_id not in ids:
            ids.append(purchase.crawl_target_id)
        return ids

    async def _listing_mapping_ids_for_trim(
        self, trim_id: UUID, listing_platform_slug: str = "divar"
    ) -> set[UUID]:
        stmt = (
            select(ListingMappingModel.id)
            .join(ListingMappingTrimModel)
            .join(ListingPlatformModel)
            .where(
                ListingMappingTrimModel.trim_id == trim_id,
                ListingMappingModel.is_active.is_(True),
                ListingPlatformModel.slug == listing_platform_slug,
            )
        )
        result = await self._session.execute(stmt)
        return {row[0] for row in result.all()}

    async def _target_ids_for_trim(self, trim_id: UUID, purchase_id: UUID) -> list[UUID]:
        mapping_ids = await self._listing_mapping_ids_for_trim(trim_id)
        if not mapping_ids:
            return []
        target_ids = await self._target_ids_for_purchase(purchase_id)
        if not target_ids:
            return []
        result = await self._session.execute(
            select(CrawlTargetModel.id).where(
                CrawlTargetModel.id.in_(target_ids),
                CrawlTargetModel.listing_mapping_id.in_(mapping_ids),
            )
        )
        return [row[0] for row in result.all()]

    async def _purchase_request_domain(self, pr: PurchaseRequestModel) -> PurchaseRequest:
        return PurchaseRequest(
            id=pr.id,
            user_id=pr.user_id,
            car_trim_id=pr.car_trim_id,
            car_model_id=pr.car_model_id,
            crawl_target_id=pr.crawl_target_id,
            pricing_platform_id=pr.pricing_platform_id,
            city=pr.city or "tehran",
            color=pr.color,
            production_year_min=pr.production_year_min,
            production_year_max=pr.production_year_max,
            usage_min=pr.usage_min,
            usage_max=pr.usage_max,
            generated_divar_url=pr.generated_divar_url,
            is_active=pr.is_active,
            poll_interval_sec=pr.poll_interval_sec or 300,
            max_listings_per_check=pr.max_listings_per_check or 10,
            expires_at=pr.expires_at,
        )

    @staticmethod
    def _trim_entity(trim: CarTrimModel | None) -> CarTrim | None:
        if not trim:
            return None
        year = trim.year
        model = year.model if year else None
        brand = model.brand if model else None
        return CarTrim(
            id=trim.id,
            model_id=trim.model_id,
            year_id=trim.year_id,
            name=trim.name,
            seo_slug=trim.seo_slug,
            is_active=trim.is_active,
            year_title=year.title if year else None,
            model_name=model.name if model else None,
            brand_name=brand.name if brand else None,
        )

    async def _listings_for_target_ids(
        self,
        target_ids: list[UUID],
        purchase: PurchaseRequest | None = None,
        purchase_request_id: UUID | None = None,
        trim_id: UUID | None = None,
        require_trim_pricing: bool = False,
    ) -> list[dict]:
        if not target_ids:
            return []

        listings_result = await self._session.execute(
            select(ListingModel)
            .where(
                ListingModel.crawl_target_id.in_(target_ids),
                ListingModel.is_active.is_(True),
            )
            .order_by(ListingModel.last_seen_at.desc())
        )
        seen_tokens: set[str] = set()
        listings: list[ListingModel] = []
        for listing_model in listings_result.scalars().all():
            token = listing_model.external_token or str(listing_model.id)
            if token in seen_tokens:
                continue
            seen_tokens.add(token)
            listings.append(listing_model)
        if not listings:
            return []

        settings = get_settings()
        now = utc_now()
        valid_days = settings.crawl_result_valid_days

        listing_ids = [listing.id for listing in listings]
        mp_stmt = select(MarketPriceModel).where(MarketPriceModel.listing_id.in_(listing_ids))
        if trim_id:
            mp_stmt = mp_stmt.where(MarketPriceModel.trim_id == trim_id)
        mp_stmt = mp_stmt.order_by(MarketPriceModel.fetched_at.desc())
        market_prices_result = await self._session.execute(mp_stmt)
        latest_price_by_listing: dict[UUID, MarketPriceModel] = {}
        for mp in market_prices_result.scalars().all():
            if mp.listing_id not in latest_price_by_listing:
                latest_price_by_listing[mp.listing_id] = mp

        opp_stmt = select(OpportunityModel).where(OpportunityModel.listing_id.in_(listing_ids))
        if purchase_request_id:
            opp_stmt = opp_stmt.where(OpportunityModel.purchase_request_id == purchase_request_id)
        opps_result = await self._session.execute(opp_stmt)
        opportunities_by_listing: dict[UUID, list[OpportunityModel]] = {}
        for opp in opps_result.scalars().all():
            if opp.status == "expired":
                continue
            opportunities_by_listing.setdefault(opp.listing_id, []).append(opp)

        rows: list[dict] = []
        for listing_model in listings:
            listing = Listing(
                id=listing_model.id,
                crawl_target_id=listing_model.crawl_target_id,
                car_model_id=listing_model.car_model_id,
                external_token=listing_model.external_token,
                title=listing_model.title,
                price=listing_model.price,
                kilometer=listing_model.kilometer,
                production_year=listing_model.production_year,
                color=listing_model.color,
                body_condition=listing_model.body_condition,
                district=listing_model.district,
                divar_url=listing_model.divar_url,
            )
            if purchase and not listing_matches_purchase_request(listing, purchase):
                continue

            mp = latest_price_by_listing.get(listing_model.id)
            if require_trim_pricing and trim_id and not mp:
                continue

            opps = sorted(
                opportunities_by_listing.get(listing_model.id, []),
                key=lambda o: o.created_at or utc_now(),
                reverse=True,
            )
            best_opp = opps[0] if opps else None
            tier_matches = (
                evaluate_urgent_sale_opportunity(
                    listing_model.price,
                    mp.price_down,
                    mp.price_mid,
                    mp.price_up,
                )
                if mp
                else []
            )
            still_valid = bool(best_opp and best_opp.status != "expired") or (
                bool(tier_matches)
                and is_listing_crawl_valid(listing, valid_days=valid_days, now=now)
            )
            live_tag = (
                best_opp.deal_tag
                if best_opp and best_opp.status != "expired"
                else (tier_matches[0].deal_tag if tier_matches else None)
            )
            rows.append(
                {
                    "id": str(listing_model.id),
                    "crawl_target_id": str(listing_model.crawl_target_id),
                    "external_token": listing_model.external_token,
                    "title": listing_model.title,
                    "price": listing_model.price,
                    "kilometer": listing_model.kilometer,
                    "production_year": listing_model.production_year,
                    "color": listing_model.color,
                    "district": listing_model.district,
                    "divar_url": listing_model.divar_url,
                    "first_seen_at": listing_model.first_seen_at.isoformat()
                    if listing_model.first_seen_at
                    else None,
                    "last_seen_at": listing_model.last_seen_at.isoformat()
                    if listing_model.last_seen_at
                    else None,
                    "latest_market_price": {
                        "id": str(mp.id),
                        "price_up": mp.price_up,
                        "price_down": mp.price_down,
                        "price_mid": mp.price_mid,
                        "reference_url": mp.reference_url,
                        "pricing_provider": mp.pricing_provider,
                        "fetched_at": mp.fetched_at.isoformat() if mp.fetched_at else None,
                    }
                    if mp
                    else None,
                    "has_opportunity": bool(best_opp and best_opp.status != "expired"),
                    "opportunity_still_valid": still_valid,
                    "crawl_still_valid": is_listing_crawl_valid(
                        listing, valid_days=valid_days, now=now
                    ),
                    "opportunity_deal_tag": live_tag if still_valid else None,
                    "opportunity_status": best_opp.status if best_opp else None,
                }
            )
        return rows

    async def list_for_user(self, user_id: UUID) -> list[dict]:
        stmt = (
            select(PurchaseRequestModel)
            .options(
                selectinload(PurchaseRequestModel.car_trim)
                .selectinload(CarTrimModel.year)
                .selectinload(CarYearModel.model)
                .selectinload(CarModelModel.brand),
                selectinload(PurchaseRequestModel.pricing_platform),
            )
            .where(PurchaseRequestModel.user_id == user_id)
            .order_by(PurchaseRequestModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        purchases = result.scalars().all()
        rows: list[dict] = []

        for pr in purchases:
            target_ids = (
                await self._target_ids_for_trim(pr.car_trim_id, pr.id)
                if pr.car_trim_id
                else []
            )
            latest_run = None

            for target_id in target_ids:
                run_result = await self._session.execute(
                    select(CrawlRunModel)
                    .where(CrawlRunModel.crawl_target_id == target_id)
                    .order_by(CrawlRunModel.started_at.desc())
                    .limit(1)
                )
                run = run_result.scalar_one_or_none()
                if run and (latest_run is None or run.started_at > latest_run.started_at):
                    latest_run = run

            opp_count = await self._session.execute(
                select(func.count())
                .select_from(OpportunityModel)
                .where(
                    OpportunityModel.purchase_request_id == pr.id,
                    OpportunityModel.status != "expired",
                )
            )
            opportunity_count = opp_count.scalar() or 0

            trim = pr.car_trim
            year = trim.year if trim else None
            model = year.model if year else None
            brand = model.brand if model else None
            rows.append(
                {
                    "purchase_request_id": str(pr.id),
                    "car_brand_name": brand.name if brand else None,
                    "car_model_name": model.name if model else None,
                    "car_year_title": year.title if year else None,
                    "car_trim_name": trim.name if trim else None,
                    "city": pr.city,
                    "production_year_min": pr.production_year_min,
                    "usage_max": pr.usage_max,
                    "pricing_platform": pr.pricing_platform.slug if pr.pricing_platform else None,
                    "is_active": pr.is_active,
                    "expires_at": pr.expires_at.isoformat() if pr.expires_at else None,
                    "created_at": pr.created_at.isoformat() if pr.created_at else None,
                    "opportunity_count": opportunity_count,
                    "latest_crawl_status": latest_run.status if latest_run else None,
                    "monitoring_status": _monitoring_status(
                        pr.is_active,
                        pr.expires_at,
                        latest_run.status if latest_run else None,
                        latest_crawl_started_at=latest_run.started_at if latest_run else None,
                        purchase_created_at=pr.created_at,
                        opportunity_count=opportunity_count,
                        has_crawl_targets=bool(target_ids),
                    ),
                }
            )
        return rows

    async def get_detail_for_user(self, purchase_request_id: UUID, user_id: UUID) -> dict | None:
        detail = await self.get_detail(purchase_request_id)
        if not detail:
            return None
        if detail["user"]["id"] != str(user_id):
            return None
        latest_crawl_status = None
        latest_crawl_started_at = None
        crawl_runs = detail.get("crawl_runs") or []
        if crawl_runs:
            latest_crawl_status = crawl_runs[0].get("status")
            latest_crawl_started_at = crawl_runs[0].get("started_at")
        pr_data = detail["purchase_request"]
        opp_count_result = await self._session.execute(
            select(func.count())
            .select_from(OpportunityModel)
            .where(
                OpportunityModel.purchase_request_id == purchase_request_id,
                OpportunityModel.status != "expired",
            )
        )
        opp_count = opp_count_result.scalar() or 0
        return {
            "purchase_request": pr_data,
            "car_model": detail["car_model"],
            "pricing_platform": detail["pricing_platform"],
            "listings": detail["listings"],
            "opportunities": detail["opportunities"],
            "monitoring_status": _monitoring_status(
                pr_data.get("is_active", False),
                pr_data.get("expires_at"),
                latest_crawl_status,
                latest_crawl_started_at=latest_crawl_started_at,
                purchase_created_at=pr_data.get("created_at"),
                opportunity_count=opp_count,
                has_crawl_targets=bool(pr_data.get("listing_mapping_configured")),
            ),
        }

    async def list_overview(self, limit: int = 100) -> list[dict]:
        id_stmt = (
            select(PurchaseRequestModel.id)
            .order_by(PurchaseRequestModel.created_at.desc())
            .limit(limit)
        )
        id_result = await self._session.execute(id_stmt)
        purchase_ids = [row[0] for row in id_result.all()]
        if not purchase_ids:
            return []

        stmt = (
            select(PurchaseRequestModel)
            .where(PurchaseRequestModel.id.in_(purchase_ids))
            .options(
                selectinload(PurchaseRequestModel.user),
                selectinload(PurchaseRequestModel.car_trim)
                .selectinload(CarTrimModel.year)
                .selectinload(CarYearModel.model)
                .selectinload(CarModelModel.brand),
                selectinload(PurchaseRequestModel.pricing_platform),
            )
            .order_by(PurchaseRequestModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        purchases = result.scalars().all()
        rows: list[dict] = []

        for pr in purchases:
            target_ids = (
                await self._target_ids_for_trim(pr.car_trim_id, pr.id)
                if pr.car_trim_id
                else []
            )
            latest_run = None

            for target_id in target_ids:
                run_result = await self._session.execute(
                    select(CrawlRunModel)
                    .where(CrawlRunModel.crawl_target_id == target_id)
                    .order_by(CrawlRunModel.started_at.desc())
                    .limit(1)
                )
                run = run_result.scalar_one_or_none()
                if run and (latest_run is None or run.started_at > latest_run.started_at):
                    latest_run = run

            opp_count = await self._session.execute(
                select(func.count())
                .select_from(OpportunityModel)
                .where(
                    OpportunityModel.purchase_request_id == pr.id,
                    OpportunityModel.status != "expired",
                )
            )
            total_opportunities = opp_count.scalar() or 0

            sms_count = await self._session.execute(
                select(func.count())
                .select_from(OpportunityDeliveryModel)
                .where(
                    OpportunityDeliveryModel.purchase_request_id == pr.id,
                    OpportunityDeliveryModel.sms_status == "sent",
                )
            )

            trim = pr.car_trim
            year = trim.year if trim else None
            model = year.model if year else None
            brand = model.brand if model else None
            rows.append(
                {
                    "purchase_request_id": str(pr.id),
                    "user_id": str(pr.user_id),
                    "user_phone": pr.user.phone if pr.user else None,
                    "user_name": pr.user.first_name if pr.user else None,
                    "car_model_name": model.name if model else None,
                    "car_brand_name": brand.name if brand else None,
                    "car_year_title": year.title if year else None,
                    "car_trim_name": trim.name if trim else None,
                    "city": pr.city,
                    "color": pr.color,
                    "production_year_min": pr.production_year_min,
                    "production_year_max": pr.production_year_max,
                    "usage_max": pr.usage_max,
                    "pricing_platform": pr.pricing_platform.slug if pr.pricing_platform else None,
                    "is_active": pr.is_active,
                    "expires_at": pr.expires_at.isoformat() if pr.expires_at else None,
                    "created_at": pr.created_at.isoformat() if pr.created_at else None,
                    "crawl_target_count": len(target_ids),
                    "latest_crawl_status": latest_run.status if latest_run else None,
                    "latest_crawl_at": latest_run.started_at.isoformat() if latest_run else None,
                    "latest_posts_found": latest_run.posts_found if latest_run else 0,
                    "latest_opportunities_found": latest_run.opportunities_found if latest_run else 0,
                    "total_opportunities": total_opportunities,
                    "monitoring_status": _monitoring_status(
                        pr.is_active,
                        pr.expires_at,
                        latest_run.status if latest_run else None,
                        latest_crawl_started_at=latest_run.started_at if latest_run else None,
                        purchase_created_at=pr.created_at,
                        opportunity_count=total_opportunities,
                        has_crawl_targets=bool(target_ids),
                    ),
                    "sms_sent_count": sms_count.scalar() or 0,
                }
            )
        return rows

    async def get_detail(self, purchase_request_id: UUID) -> dict | None:
        stmt = (
            select(PurchaseRequestModel)
            .options(
                joinedload(PurchaseRequestModel.user),
                joinedload(PurchaseRequestModel.car_model).joinedload(CarModelModel.brand),
                joinedload(PurchaseRequestModel.car_trim)
                .joinedload(CarTrimModel.year)
                .joinedload(CarYearModel.model)
                .joinedload(CarModelModel.brand),
                joinedload(PurchaseRequestModel.pricing_platform),
                joinedload(PurchaseRequestModel.crawl_target),
                joinedload(PurchaseRequestModel.crawl_target_links).joinedload(
                    PurchaseRequestCrawlTargetModel.crawl_target
                ),
            )
            .where(PurchaseRequestModel.id == purchase_request_id)
        )
        result = await self._session.execute(stmt)
        pr = result.scalars().unique().one_or_none()
        if not pr:
            return None

        trim_targets = (
            await self._target_ids_for_trim(pr.car_trim_id, pr.id) if pr.car_trim_id else []
        )
        purchase_targets = await self._target_ids_for_purchase(pr.id)
        target_ids = list(dict.fromkeys([*trim_targets, *purchase_targets]))
        listing_mapping_configured = bool(
            await self._listing_mapping_ids_for_trim(pr.car_trim_id) if pr.car_trim_id else set()
        )
        purchase_domain = effective_purchase_request(
            await self._purchase_request_domain(pr),
            self._trim_entity(pr.car_trim),
        )
        crawl_targets = []
        crawl_runs = []
        opportunities = []

        if target_ids:
            for target_id in target_ids:
                target = await self._session.get(CrawlTargetModel, target_id)
                if target:
                    crawl_targets.append(
                        {
                            "id": str(target.id),
                            "source": target.source,
                            "listing_url": target.listing_url,
                            "is_active": target.is_active,
                            "is_shared_pool": target.is_shared_pool,
                            "poll_interval_sec": target.poll_interval_sec,
                        }
                    )

                runs_result = await self._session.execute(
                    select(CrawlRunModel)
                    .where(CrawlRunModel.crawl_target_id == target_id)
                    .order_by(CrawlRunModel.started_at.desc())
                    .limit(20)
                )
                for run in runs_result.scalars().all():
                    if pr.created_at and run.started_at and run.started_at < pr.created_at:
                        continue
                    crawl_runs.append(
                        {
                            "id": str(run.id),
                            "crawl_target_id": str(run.crawl_target_id),
                            "status": run.status,
                            "started_at": run.started_at.isoformat() if run.started_at else None,
                            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                            "posts_found": run.posts_found,
                            "opportunities_found": run.opportunities_found,
                            "error_message": run.error_message,
                            "diagnostics": filter_diagnostics_for_purchase(
                                run.diagnostics or [],
                                pr.id,
                                purchase_domain,
                            ),
                        }
                    )

            crawl_runs = latest_crawl_run_per_target(crawl_runs)

        opps_result = await self._session.execute(
            select(OpportunityModel)
            .options(joinedload(OpportunityModel.listing))
            .join(ListingModel, ListingModel.id == OpportunityModel.listing_id)
            .where(
                OpportunityModel.purchase_request_id == pr.id,
                OpportunityModel.status != "expired",
            )
            .order_by(OpportunityModel.created_at.desc())
        )
        seen_opp_listings: set[UUID] = set()
        for opp in opps_result.scalars().unique().all():
            listing = opp.listing
            if not listing or listing.id in seen_opp_listings:
                continue
            seen_opp_listings.add(listing.id)
            opportunities.append(
                {
                    "id": str(opp.id),
                    "listing_title": listing.title if listing else None,
                    "listing_price": listing.price,
                    "market_price_down": opp.market_price_down,
                    "market_price_up": opp.market_price_up,
                    "market_price_mid": opp.market_price_mid,
                    "price_basis": opp.price_basis,
                    "deal_tag": opp.deal_tag,
                    "reference_price": opp.reference_price,
                    "discount_pct": float(opp.discount_pct) if opp.discount_pct is not None else 0.0,
                    "discount_amount": opp.discount_amount,
                    "status": opp.status,
                    "is_below_floor": opp.is_below_floor,
                    "divar_url": listing.divar_url if listing else None,
                    "kilometer": listing.kilometer if listing else None,
                    "production_year": listing.production_year if listing else None,
                    "created_at": opp.created_at.isoformat() if opp.created_at else None,
                }
            )

        deliveries_result = await self._session.execute(
            select(OpportunityDeliveryModel)
            .options(joinedload(OpportunityDeliveryModel.opportunity).joinedload(OpportunityModel.listing))
            .where(OpportunityDeliveryModel.purchase_request_id == pr.id)
            .order_by(OpportunityDeliveryModel.created_at.desc())
        )
        deliveries = []
        for d in deliveries_result.scalars().unique().all():
            listing = d.opportunity.listing if d.opportunity else None
            deliveries.append(
                {
                    "id": str(d.id),
                    "opportunity_id": str(d.opportunity_id),
                    "listing_title": listing.title if listing else None,
                    "gateway_token": d.gateway_token,
                    "sms_status": d.sms_status,
                    "sms_sent_at": d.sms_sent_at.isoformat() if d.sms_sent_at else None,
                    "sms_error": d.sms_error,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
            )

        listings = await self._listings_for_target_ids(
            target_ids,
            purchase=purchase_domain,
            purchase_request_id=pr.id,
            trim_id=pr.car_trim_id,
            require_trim_pricing=True,
        )
        divar_url = pr.generated_divar_url if listing_mapping_configured else None
        return {
            "purchase_request": {
                "id": str(pr.id),
                "city": pr.city,
                "color": pr.color,
                "production_year_min": purchase_domain.production_year_min,
                "production_year_max": purchase_domain.production_year_max,
                "usage_min": pr.usage_min,
                "usage_max": pr.usage_max,
                "generated_divar_url": divar_url,
                "listing_mapping_configured": listing_mapping_configured,
                "is_active": pr.is_active,
                "poll_interval_sec": pr.poll_interval_sec,
                "max_listings_per_check": pr.max_listings_per_check,
                "expires_at": pr.expires_at.isoformat() if pr.expires_at else None,
                "created_at": pr.created_at.isoformat() if pr.created_at else None,
            },
            "user": {
                "id": str(pr.user_id),
                "phone": pr.user.phone if pr.user else None,
                "first_name": pr.user.first_name if pr.user else None,
                "last_name": pr.user.last_name if pr.user else None,
                "source_channel": pr.user.source_channel if pr.user else None,
            },
            "car_model": _car_model_payload(pr),
            "pricing_platform": pr.pricing_platform.slug if pr.pricing_platform else None,
            "crawl_targets": crawl_targets,
            "crawl_runs": crawl_runs,
            "listings": listings,
            "opportunities": opportunities,
            "deliveries": deliveries,
        }
