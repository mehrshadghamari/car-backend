from datetime import datetime, timedelta

from src.domain.compat import utc_now
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.mappers.entity_mappers import (
    click_to_domain,
    crawl_run_to_domain,
    crawl_target_to_domain,
    delivery_to_domain,
    listing_to_domain,
    market_price_to_domain,
    opportunity_to_domain,
    purchase_request_to_domain,
    user_to_domain,
)
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
from src.domain.entities.crawl_run import CrawlRun
from src.domain.entities.crawl_target import CrawlTarget
from src.domain.entities.delivery import GatewayClick, OpportunityDelivery
from src.domain.entities.listing import Listing
from src.domain.entities.market_price import MarketPrice
from src.domain.entities.opportunity import Opportunity
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
    OpportunityPageViewModel,
    PurchaseRequestCrawlTargetModel,
    PurchaseRequestModel,
    UserModel,
)


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def rollback(self) -> None:
        await self._session.rollback()

    async def save(self, user: User) -> User:
        model = await self._session.get(UserModel, user.id)
        if model is None:
            model = UserModel(
                id=user.id or uuid4(),
                phone=user.phone,
                first_name=user.first_name,
                last_name=user.last_name,
                source_channel=user.source_channel,
                is_active=user.is_active,
            )
            self._session.add(model)
        else:
            model.phone = user.phone
            model.first_name = user.first_name
            model.last_name = user.last_name
            model.source_channel = user.source_channel
            model.is_active = user.is_active
        await self._session.commit()
        await self._session.refresh(model)
        return user_to_domain(model)

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return user_to_domain(model) if model else None

    async def get_by_phone(self, phone: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.phone == phone).limit(1)
        )
        model = result.scalars().first()
        return user_to_domain(model) if model else None

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        result = await self._session.execute(select(UserModel).offset(skip).limit(limit))
        return [user_to_domain(m) for m in result.scalars().all()]

    async def delete(self, user_id: UUID) -> bool:
        model = await self._session.get(UserModel, user_id)
        if not model:
            return False
        await self._session.delete(model)
        await self._session.commit()
        return True


class SqlAlchemyCrawlTargetRepository(CrawlTargetRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, target: CrawlTarget) -> CrawlTarget:
        model = await self._session.get(CrawlTargetModel, target.id)
        if model is None:
            model = CrawlTargetModel(
                id=target.id or uuid4(),
                listing_mapping_id=target.listing_mapping_id,
                car_model_id=target.car_model_id,
                city=target.city,
                is_shared_pool=target.is_shared_pool,
                pool_production_year=target.pool_production_year,
                source=target.source,
                listing_url=target.listing_url,
                vehicle_context=target.vehicle_context.to_dict(),
                is_active=target.is_active,
                poll_interval_sec=target.poll_interval_sec,
            )
            self._session.add(model)
        else:
            model.listing_mapping_id = target.listing_mapping_id
            model.car_model_id = target.car_model_id
            model.city = target.city
            model.is_shared_pool = target.is_shared_pool
            model.pool_production_year = target.pool_production_year
            model.source = target.source
            model.listing_url = target.listing_url
            model.vehicle_context = target.vehicle_context.to_dict()
            model.is_active = target.is_active
            model.poll_interval_sec = target.poll_interval_sec
        await self._session.commit()
        await self._session.refresh(model)
        return crawl_target_to_domain(model)

    async def get_by_id(self, target_id: UUID) -> CrawlTarget | None:
        model = await self._session.get(CrawlTargetModel, target_id)
        return crawl_target_to_domain(model) if model else None

    async def list_all(self, active_only: bool = False) -> list[CrawlTarget]:
        stmt = select(CrawlTargetModel)
        if active_only:
            stmt = stmt.where(CrawlTargetModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return [crawl_target_to_domain(m) for m in result.scalars().all()]

    async def get_shared_pool(
        self,
        listing_mapping_id: UUID,
        city: str,
        source: str,
        pool_production_year: int | None = None,
    ) -> CrawlTarget | None:
        stmt = select(CrawlTargetModel).where(
            CrawlTargetModel.listing_mapping_id == listing_mapping_id,
            CrawlTargetModel.city == city,
            CrawlTargetModel.source == source,
            CrawlTargetModel.is_shared_pool.is_(True),
        )
        if pool_production_year is None:
            stmt = stmt.where(CrawlTargetModel.pool_production_year.is_(None))
        else:
            stmt = stmt.where(CrawlTargetModel.pool_production_year == pool_production_year)
        result = await self._session.execute(
            stmt.order_by(
                CrawlTargetModel.is_active.desc(),
                CrawlTargetModel.updated_at.desc(),
                CrawlTargetModel.created_at.desc(),
            ).limit(1)
        )
        model = result.scalar_one_or_none()
        return crawl_target_to_domain(model) if model else None

    async def deactivate_duplicate_shared_pools(
        self,
        listing_mapping_id: UUID,
        city: str,
        source: str,
        keep_id: UUID,
        pool_production_year: int | None = None,
    ) -> int:
        from sqlalchemy import update

        stmt = update(CrawlTargetModel).where(
            CrawlTargetModel.listing_mapping_id == listing_mapping_id,
            CrawlTargetModel.city == city,
            CrawlTargetModel.source == source,
            CrawlTargetModel.is_shared_pool.is_(True),
            CrawlTargetModel.id != keep_id,
        )
        if pool_production_year is None:
            stmt = stmt.where(CrawlTargetModel.pool_production_year.is_(None))
        else:
            stmt = stmt.where(CrawlTargetModel.pool_production_year == pool_production_year)
        result = await self._session.execute(stmt.values(is_active=False))
        await self._session.commit()
        return result.rowcount or 0

    async def list_active_shared_pools(self) -> list[CrawlTarget]:
        result = await self._session.execute(
            select(CrawlTargetModel).where(
                CrawlTargetModel.is_shared_pool.is_(True),
                CrawlTargetModel.is_active.is_(True),
                CrawlTargetModel.listing_mapping_id.is_not(None),
            )
        )
        return [crawl_target_to_domain(m) for m in result.scalars().all()]

    async def delete(self, target_id: UUID) -> bool:
        model = await self._session.get(CrawlTargetModel, target_id)
        if not model:
            return False
        await self._session.delete(model)
        await self._session.commit()
        return True


class SqlAlchemyPurchaseRequestRepository(PurchaseRequestRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, request: PurchaseRequest) -> PurchaseRequest:
        model = await self._session.get(PurchaseRequestModel, request.id)
        if model is None:
            model = PurchaseRequestModel(
                id=request.id or uuid4(),
                user_id=request.user_id,
                car_trim_id=request.car_trim_id,
                car_model_id=request.car_model_id,
                crawl_target_id=request.crawl_target_id,
                pricing_platform_id=request.pricing_platform_id,
                city=request.city,
                color=request.color,
                production_year_min=request.production_year_min,
                production_year_max=request.production_year_max,
                usage_min=request.usage_min,
                usage_max=request.usage_max,
                generated_divar_url=request.generated_divar_url,
                is_active=request.is_active,
                near_threshold_pct=float(request.near_threshold_pct) if request.near_threshold_pct else None,
                poll_interval_sec=request.poll_interval_sec,
                max_listings_per_check=request.max_listings_per_check,
                expires_at=request.expires_at,
            )
            self._session.add(model)
        else:
            model.is_active = request.is_active
            model.crawl_target_id = request.crawl_target_id
            model.near_threshold_pct = (
                float(request.near_threshold_pct) if request.near_threshold_pct else None
            )
            model.expires_at = request.expires_at

        await self._session.flush()
        if request.crawl_target_ids:
            existing = await self._session.execute(
                select(PurchaseRequestCrawlTargetModel).where(
                    PurchaseRequestCrawlTargetModel.purchase_request_id == model.id
                )
            )
            for link in existing.scalars().all():
                await self._session.delete(link)
            for target_id in request.crawl_target_ids:
                self._session.add(
                    PurchaseRequestCrawlTargetModel(
                        id=uuid4(),
                        purchase_request_id=model.id,
                        crawl_target_id=target_id,
                    )
                )

        await self._session.commit()
        await self._session.refresh(model)
        return await self._to_domain_with_targets(model)

    async def _to_domain_with_targets(self, model: PurchaseRequestModel) -> PurchaseRequest:
        links = await self._session.execute(
            select(PurchaseRequestCrawlTargetModel.crawl_target_id).where(
                PurchaseRequestCrawlTargetModel.purchase_request_id == model.id
            )
        )
        target_ids = [row[0] for row in links.all()]
        domain = purchase_request_to_domain(model)
        domain.crawl_target_ids = target_ids or None
        return domain

    async def get_by_id(self, request_id: UUID) -> PurchaseRequest | None:
        model = await self._session.get(PurchaseRequestModel, request_id)
        return await self._to_domain_with_targets(model) if model else None

    async def list_by_user(self, user_id: UUID) -> list[PurchaseRequest]:
        result = await self._session.execute(
            select(PurchaseRequestModel).where(PurchaseRequestModel.user_id == user_id)
        )
        return [await self._to_domain_with_targets(m) for m in result.scalars().all()]

    async def list_active_by_crawl_target(self, crawl_target_id: UUID) -> list[PurchaseRequest]:
        now = utc_now()
        stmt = (
            select(PurchaseRequestModel)
            .outerjoin(
                PurchaseRequestCrawlTargetModel,
                PurchaseRequestCrawlTargetModel.purchase_request_id == PurchaseRequestModel.id,
            )
            .where(
                PurchaseRequestModel.is_active.is_(True),
                (PurchaseRequestModel.expires_at.is_(None)) | (PurchaseRequestModel.expires_at > now),
                (PurchaseRequestModel.crawl_target_id == crawl_target_id)
                | (PurchaseRequestCrawlTargetModel.crawl_target_id == crawl_target_id),
            )
            .distinct()
        )
        result = await self._session.execute(stmt)
        return [await self._to_domain_with_targets(m) for m in result.scalars().all()]

    async def list_active_non_expired(self) -> list[PurchaseRequest]:
        now = utc_now()
        result = await self._session.execute(
            select(PurchaseRequestModel).where(
                PurchaseRequestModel.is_active.is_(True),
                (PurchaseRequestModel.expires_at.is_(None)) | (PurchaseRequestModel.expires_at > now),
            )
        )
        return [await self._to_domain_with_targets(m) for m in result.scalars().all()]

    async def list_active_trim_ids(self) -> set[UUID]:
        purchases = await self.list_active_non_expired()
        return {p.car_trim_id for p in purchases if p.car_trim_id}

    async def deactivate_older_than(self, cutoff) -> int:
        from sqlalchemy import update

        from src.infrastructure.persistence.models import PurchaseRequestModel

        result = await self._session.execute(
            update(PurchaseRequestModel)
            .where(PurchaseRequestModel.is_active.is_(True))
            .where(PurchaseRequestModel.created_at < cutoff)
            .values(is_active=False)
        )
        await self._session.commit()
        return result.rowcount or 0


class SqlAlchemyListingRepository(ListingRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, listing_id: UUID) -> Listing | None:
        model = await self._session.get(ListingModel, listing_id)
        return listing_to_domain(model) if model else None

    async def get_by_token(self, external_token: str) -> Listing | None:
        result = await self._session.execute(
            select(ListingModel).where(ListingModel.external_token == external_token)
        )
        model = result.scalar_one_or_none()
        return listing_to_domain(model) if model else None

    async def save(self, listing: Listing) -> Listing:
        model = await self._session.get(ListingModel, listing.id)
        if model is None:
            model = ListingModel(
                id=listing.id or uuid4(),
                crawl_target_id=listing.crawl_target_id,
                car_model_id=listing.car_model_id,
                external_token=listing.external_token,
                title=listing.title,
                price=listing.price,
                kilometer=listing.kilometer,
                production_year=listing.production_year,
                color=listing.color,
                body_condition=listing.body_condition,
                district=listing.district,
                divar_url=listing.divar_url,
                is_active=listing.is_active,
            )
            self._session.add(model)
        else:
            model.title = listing.title
            model.price = listing.price
            model.kilometer = listing.kilometer
            model.production_year = listing.production_year
            model.color = listing.color
            model.body_condition = listing.body_condition
            model.district = listing.district
            model.divar_url = listing.divar_url
            model.crawl_target_id = listing.crawl_target_id
            model.car_model_id = listing.car_model_id
            model.is_active = listing.is_active
            model.last_seen_at = utc_now()
        await self._session.commit()
        await self._session.refresh(model)
        return listing_to_domain(model)

    async def upsert(self, listing: Listing) -> tuple[Listing, bool]:
        from sqlalchemy.exc import IntegrityError

        existing = await self.get_by_token(listing.external_token)
        if existing:
            listing.id = existing.id
            listing.first_seen_at = existing.first_seen_at
            listing.is_active = True
            changed = (
                existing.price != listing.price
                or existing.kilometer != listing.kilometer
                or existing.production_year != listing.production_year
                or existing.crawl_target_id != listing.crawl_target_id
            )
            saved = await self.save(listing)
            return saved, changed
        listing.id = listing.id or uuid4()
        try:
            saved = await self.save(listing)
            return saved, True
        except IntegrityError:
            await self._session.rollback()
            existing = await self.get_by_token(listing.external_token)
            if not existing:
                raise
            listing.id = existing.id
            saved = await self.save(listing)
            return saved, False

    async def list_by_crawl_target(
        self, crawl_target_id: UUID, *, active_only: bool = False
    ) -> list[Listing]:
        stmt = select(ListingModel).where(ListingModel.crawl_target_id == crawl_target_id)
        if active_only:
            stmt = stmt.where(ListingModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return [listing_to_domain(m) for m in result.scalars().all()]

    async def deactivate_stale(self, cutoff) -> int:
        from sqlalchemy import update

        from src.infrastructure.persistence.models import ListingModel

        result = await self._session.execute(
            update(ListingModel)
            .where(ListingModel.is_active.is_(True))
            .where(ListingModel.last_seen_at < cutoff)
            .values(is_active=False)
        )
        await self._session.commit()
        return result.rowcount or 0

    async def bulk_purge_inactive(self) -> dict[str, int]:
        from sqlalchemy import delete, select

        from src.infrastructure.persistence.models import (
            GatewayClickModel,
            ListingModel,
            MarketPriceModel,
            OpportunityDeliveryModel,
            OpportunityModel,
            OpportunityPageViewModel,
        )

        result = await self._session.execute(
            select(ListingModel.id).where(ListingModel.is_active.is_(False))
        )
        listing_ids = [row[0] for row in result.all()]
        if not listing_ids:
            return {
                "listings_purged": 0,
                "market_prices_purged": 0,
                "opportunities_purged": 0,
                "deliveries_purged": 0,
            }

        opp_result = await self._session.execute(
            select(OpportunityModel.id).where(OpportunityModel.listing_id.in_(listing_ids))
        )
        opp_ids = [row[0] for row in opp_result.all()]

        deliveries_purged = 0
        opportunities_purged = 0
        if opp_ids:
            delivery_result = await self._session.execute(
                select(OpportunityDeliveryModel.id).where(
                    OpportunityDeliveryModel.opportunity_id.in_(opp_ids)
                )
            )
            delivery_ids = [row[0] for row in delivery_result.all()]
            if delivery_ids:
                await self._session.execute(
                    delete(GatewayClickModel).where(
                        GatewayClickModel.delivery_id.in_(delivery_ids)
                    )
                )
                await self._session.execute(
                    delete(OpportunityPageViewModel).where(
                        OpportunityPageViewModel.delivery_id.in_(delivery_ids)
                    )
                )
                del_result = await self._session.execute(
                    delete(OpportunityDeliveryModel).where(
                        OpportunityDeliveryModel.id.in_(delivery_ids)
                    )
                )
                deliveries_purged = del_result.rowcount or 0

            opp_del = await self._session.execute(
                delete(OpportunityModel).where(OpportunityModel.id.in_(opp_ids))
            )
            opportunities_purged = opp_del.rowcount or 0

        mp_result = await self._session.execute(
            delete(MarketPriceModel).where(MarketPriceModel.listing_id.in_(listing_ids))
        )
        market_prices_purged = mp_result.rowcount or 0

        listing_result = await self._session.execute(
            delete(ListingModel).where(ListingModel.id.in_(listing_ids))
        )
        listings_purged = listing_result.rowcount or 0

        await self._session.commit()
        return {
            "listings_purged": listings_purged,
            "market_prices_purged": market_prices_purged,
            "opportunities_purged": opportunities_purged,
            "deliveries_purged": deliveries_purged,
        }


class SqlAlchemyMarketPriceRepository(MarketPriceRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_latest_for_listing(self, listing_id: UUID) -> MarketPrice | None:
        result = await self._session.execute(
            select(MarketPriceModel)
            .where(MarketPriceModel.listing_id == listing_id)
            .order_by(MarketPriceModel.fetched_at.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return market_price_to_domain(model) if model else None

    async def get_latest_for_listing_and_trim(
        self, listing_id: UUID, trim_id: UUID
    ) -> MarketPrice | None:
        result = await self._session.execute(
            select(MarketPriceModel)
            .where(
                MarketPriceModel.listing_id == listing_id,
                MarketPriceModel.trim_id == trim_id,
            )
            .order_by(MarketPriceModel.fetched_at.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return market_price_to_domain(model) if model else None

    async def get_fresh_for_trim(
        self, trim_id: UUID, pricing_provider: str, ttl_hours: int
    ) -> MarketPrice | None:
        cutoff = utc_now() - timedelta(hours=ttl_hours)
        result = await self._session.execute(
            select(MarketPriceModel)
            .where(
                MarketPriceModel.trim_id == trim_id,
                MarketPriceModel.pricing_provider == pricing_provider,
                MarketPriceModel.fetched_at >= cutoff,
            )
            .order_by(MarketPriceModel.fetched_at.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return market_price_to_domain(model) if model else None

    async def get_fresh_for_trim_at_specs(
        self,
        trim_id: UUID,
        production_year: int,
        kilometer: int,
        pricing_provider: str,
        ttl_hours: int,
    ) -> MarketPrice | None:
        cutoff = utc_now() - timedelta(hours=ttl_hours)
        result = await self._session.execute(
            select(MarketPriceModel)
            .join(ListingModel, ListingModel.id == MarketPriceModel.listing_id)
            .where(
                MarketPriceModel.trim_id == trim_id,
                MarketPriceModel.pricing_provider == pricing_provider,
                MarketPriceModel.fetched_at >= cutoff,
                ListingModel.production_year == production_year,
                ListingModel.kilometer == kilometer,
            )
            .order_by(MarketPriceModel.fetched_at.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return market_price_to_domain(model) if model else None

    async def save(self, market_price: MarketPrice) -> MarketPrice:
        model = MarketPriceModel(
            id=market_price.id or uuid4(),
            listing_id=market_price.listing_id,
            trim_id=market_price.trim_id,
            price_up=market_price.price_up,
            price_down=market_price.price_down,
            price_mid=market_price.price_mid,
            reference_url=market_price.reference_url,
            pricing_provider=market_price.pricing_provider,
            fetched_at=market_price.fetched_at,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return market_price_to_domain(model)


class SqlAlchemyOpportunityRepository(OpportunityRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, opportunity: Opportunity) -> Opportunity:
        model = await self._session.get(OpportunityModel, opportunity.id)
        if model is None:
            model = OpportunityModel(
                id=opportunity.id or uuid4(),
                listing_id=opportunity.listing_id,
                purchase_request_id=opportunity.purchase_request_id,
                crawl_target_id=opportunity.crawl_target_id,
                listing_price=opportunity.listing_price,
                market_price_down=opportunity.market_price_down,
                market_price_up=opportunity.market_price_up,
                market_price_mid=opportunity.market_price_mid,
                price_basis=opportunity.price_basis,
                deal_tag=opportunity.deal_tag,
                reference_price=opportunity.reference_price or opportunity.market_price_down,
                discount_amount=opportunity.discount_amount,
                discount_pct=float(opportunity.discount_pct),
                score=float(opportunity.score),
                status=opportunity.status.value,
                is_below_floor=opportunity.is_below_floor,
            )
            self._session.add(model)
        else:
            model.listing_id = opportunity.listing_id
            model.purchase_request_id = opportunity.purchase_request_id
            model.crawl_target_id = opportunity.crawl_target_id
            model.listing_price = opportunity.listing_price
            model.market_price_down = opportunity.market_price_down
            model.market_price_up = opportunity.market_price_up
            model.market_price_mid = opportunity.market_price_mid
            model.price_basis = opportunity.price_basis
            model.deal_tag = opportunity.deal_tag
            model.reference_price = opportunity.reference_price or opportunity.market_price_down
            model.discount_amount = opportunity.discount_amount
            model.discount_pct = float(opportunity.discount_pct)
            model.score = float(opportunity.score)
            model.status = opportunity.status.value
            model.is_below_floor = opportunity.is_below_floor
        await self._session.commit()
        await self._session.refresh(model)
        return opportunity_to_domain(model)

    async def get_by_id(self, opportunity_id: UUID) -> Opportunity | None:
        model = await self._session.get(OpportunityModel, opportunity_id)
        return opportunity_to_domain(model) if model else None

    async def get_by_listing(self, listing_id: UUID) -> Opportunity | None:
        result = await self._session.execute(
            select(OpportunityModel).where(OpportunityModel.listing_id == listing_id)
        )
        model = result.scalar_one_or_none()
        return opportunity_to_domain(model) if model else None

    async def get_by_listing_and_basis(self, listing_id: UUID, price_basis: str) -> Opportunity | None:
        result = await self._session.execute(
            select(OpportunityModel).where(
                OpportunityModel.listing_id == listing_id,
                OpportunityModel.price_basis == price_basis,
            )
        )
        model = result.scalar_one_or_none()
        return opportunity_to_domain(model) if model else None

    async def get_by_listing_and_purchase(
        self, listing_id: UUID, purchase_request_id: UUID
    ) -> Opportunity | None:
        result = await self._session.execute(
            select(OpportunityModel).where(
                OpportunityModel.listing_id == listing_id,
                OpportunityModel.purchase_request_id == purchase_request_id,
            )
        )
        model = result.scalar_one_or_none()
        return opportunity_to_domain(model) if model else None

    async def list_by_listing(self, listing_id: UUID) -> list[Opportunity]:
        result = await self._session.execute(
            select(OpportunityModel).where(OpportunityModel.listing_id == listing_id)
        )
        return [opportunity_to_domain(m) for m in result.scalars().all()]

    async def list_by_purchase_request(
        self, purchase_request_id: UUID, status: str | None = None
    ) -> list[Opportunity]:
        stmt = select(OpportunityModel).where(
            OpportunityModel.purchase_request_id == purchase_request_id
        )
        if status:
            stmt = stmt.where(OpportunityModel.status == status)
        result = await self._session.execute(stmt.order_by(OpportunityModel.created_at.desc()))
        return [opportunity_to_domain(m) for m in result.scalars().all()]

    async def list_all(
        self,
        crawl_target_id: UUID | None = None,
        purchase_request_id: UUID | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Opportunity]:
        stmt = select(OpportunityModel)
        if crawl_target_id:
            stmt = stmt.where(OpportunityModel.crawl_target_id == crawl_target_id)
        if purchase_request_id:
            stmt = stmt.where(OpportunityModel.purchase_request_id == purchase_request_id)
        if status:
            stmt = stmt.where(OpportunityModel.status == status)
        stmt = stmt.order_by(OpportunityModel.created_at.desc()).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return [opportunity_to_domain(m) for m in result.scalars().all()]


class SqlAlchemyCrawlRunRepository(CrawlRunRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, crawl_run: CrawlRun) -> CrawlRun:
        model = await self._session.get(CrawlRunModel, crawl_run.id)
        if model is None:
            model = CrawlRunModel(
                id=crawl_run.id or uuid4(),
                crawl_target_id=crawl_run.crawl_target_id,
                status=crawl_run.status.value,
                started_at=crawl_run.started_at,
                posts_found=crawl_run.posts_found,
                opportunities_found=crawl_run.opportunities_found,
                finished_at=crawl_run.finished_at,
                error_message=crawl_run.error_message,
                diagnostics=crawl_run.diagnostics,
            )
            self._session.add(model)
        else:
            model.status = crawl_run.status.value
            model.posts_found = crawl_run.posts_found
            model.opportunities_found = crawl_run.opportunities_found
            model.finished_at = crawl_run.finished_at
            model.error_message = crawl_run.error_message
            model.diagnostics = crawl_run.diagnostics
        await self._session.commit()
        await self._session.refresh(model)
        return crawl_run_to_domain(model)

    async def recover_stale_runs(self, max_age_minutes: int = 15) -> int:
        from datetime import timedelta

        from sqlalchemy import update

        from src.domain.entities.crawl_run import CrawlRunStatus

        cutoff = utc_now() - timedelta(minutes=max_age_minutes)
        result = await self._session.execute(
            update(CrawlRunModel)
            .where(
                CrawlRunModel.status == CrawlRunStatus.RUNNING.value,
                CrawlRunModel.started_at < cutoff,
            )
            .values(
                status=CrawlRunStatus.FAILED.value,
                finished_at=utc_now(),
                error_message="Crawl interrupted (stale running state — server reload or crash)",
            )
        )
        await self._session.commit()
        return result.rowcount or 0

    async def count_by_status(self, status: str) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(CrawlRunModel)
            .where(CrawlRunModel.status == status)
        )
        return result.scalar() or 0

    async def list_by_target(self, crawl_target_id: UUID, limit: int = 20) -> list[CrawlRun]:
        result = await self._session.execute(
            select(CrawlRunModel)
            .where(CrawlRunModel.crawl_target_id == crawl_target_id)
            .order_by(CrawlRunModel.started_at.desc())
            .limit(limit)
        )
        return [crawl_run_to_domain(m) for m in result.scalars().all()]

    async def get_latest_for_target(self, crawl_target_id: UUID) -> CrawlRun | None:
        result = await self._session.execute(
            select(CrawlRunModel)
            .where(CrawlRunModel.crawl_target_id == crawl_target_id)
            .order_by(CrawlRunModel.started_at.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return crawl_run_to_domain(model) if model else None


class SqlAlchemyDeliveryRepository(DeliveryRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, delivery: OpportunityDelivery) -> OpportunityDelivery:
        model = await self._session.get(OpportunityDeliveryModel, delivery.id)
        if model is None:
            model = OpportunityDeliveryModel(
                id=delivery.id or uuid4(),
                opportunity_id=delivery.opportunity_id,
                purchase_request_id=delivery.purchase_request_id,
                user_id=delivery.user_id,
                gateway_token=delivery.gateway_token,
                sms_status=delivery.sms_status.value,
                sms_sent_at=delivery.sms_sent_at,
                sms_provider_id=delivery.sms_provider_id,
                sms_error=delivery.sms_error,
            )
            self._session.add(model)
        else:
            model.sms_status = delivery.sms_status.value
            model.sms_sent_at = delivery.sms_sent_at
            model.sms_provider_id = delivery.sms_provider_id
            model.sms_error = delivery.sms_error
        await self._session.commit()
        await self._session.refresh(model)
        return delivery_to_domain(model)

    async def get_by_gateway_token(self, token: str) -> OpportunityDelivery | None:
        result = await self._session.execute(
            select(OpportunityDeliveryModel).where(OpportunityDeliveryModel.gateway_token == token)
        )
        model = result.scalar_one_or_none()
        return delivery_to_domain(model) if model else None

    async def exists_for_user_and_token(self, user_id: UUID, external_token: str) -> bool:
        stmt = (
            select(func.count())
            .select_from(OpportunityDeliveryModel)
            .join(OpportunityModel, OpportunityDeliveryModel.opportunity_id == OpportunityModel.id)
            .join(ListingModel, OpportunityModel.listing_id == ListingModel.id)
            .where(
                OpportunityDeliveryModel.user_id == user_id,
                ListingModel.external_token == external_token,
            )
        )
        result = await self._session.execute(stmt)
        return (result.scalar() or 0) > 0

    async def save_click(self, click: GatewayClick) -> GatewayClick:
        model = GatewayClickModel(
            id=click.id or uuid4(),
            delivery_id=click.delivery_id,
            clicked_at=click.clicked_at,
            time_to_click_sec=click.time_to_click_sec,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return click_to_domain(model)

    async def count_deliveries(self, since: datetime | None = None) -> int:
        stmt = select(func.count()).select_from(OpportunityDeliveryModel)
        if since:
            stmt = stmt.where(OpportunityDeliveryModel.created_at >= since)
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def count_clicks(self, since: datetime | None = None) -> int:
        stmt = select(func.count()).select_from(GatewayClickModel)
        if since:
            stmt = stmt.where(GatewayClickModel.clicked_at >= since)
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def save_page_view(
        self,
        delivery_id: UUID,
        ip_address: str,
        is_unique_view: bool,
        viewed_at: datetime,
        view_id: UUID,
    ) -> None:
        self._session.add(
            OpportunityPageViewModel(
                id=view_id,
                delivery_id=delivery_id,
                ip_address=ip_address,
                is_unique_view=is_unique_view,
                viewed_at=viewed_at,
            )
        )
        await self._session.commit()

    async def has_page_view_from_ip(self, delivery_id: UUID, ip_address: str) -> bool:
        stmt = (
            select(func.count())
            .select_from(OpportunityPageViewModel)
            .where(
                OpportunityPageViewModel.delivery_id == delivery_id,
                OpportunityPageViewModel.ip_address == ip_address,
            )
        )
        result = await self._session.execute(stmt)
        return (result.scalar() or 0) > 0

    async def count_page_views(self, delivery_id: UUID) -> tuple[int, int]:
        total_stmt = (
            select(func.count())
            .select_from(OpportunityPageViewModel)
            .where(OpportunityPageViewModel.delivery_id == delivery_id)
        )
        unique_stmt = (
            select(func.count())
            .select_from(OpportunityPageViewModel)
            .where(
                OpportunityPageViewModel.delivery_id == delivery_id,
                OpportunityPageViewModel.is_unique_view.is_(True),
            )
        )
        total = (await self._session.execute(total_stmt)).scalar() or 0
        unique = (await self._session.execute(unique_stmt)).scalar() or 0
        return total, unique
