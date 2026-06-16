"""Cancel a purchase request and stop crawling when no active requests remain."""

from uuid import UUID

from src.application.ports.repositories import (
    CrawlTargetRepository,
    OpportunityRepository,
    PurchaseRequestRepository,
)
from src.domain.entities.opportunity import OpportunityStatus
from src.domain.entities.purchase_request import PurchaseRequest
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.infrastructure.persistence.platform_repositories import SqlAlchemyPlatformRepository


class CancelPurchaseRequestUseCase:
    def __init__(
        self,
        purchase_request_repo: PurchaseRequestRepository,
        crawl_target_repo: CrawlTargetRepository,
        opportunity_repo: OpportunityRepository,
        platform_repo: SqlAlchemyPlatformRepository,
    ):
        self._purchase_request_repo = purchase_request_repo
        self._crawl_target_repo = crawl_target_repo
        self._opportunity_repo = opportunity_repo
        self._platform_repo = platform_repo

    async def execute(
        self,
        purchase_request_id: UUID,
        *,
        user_id: UUID | None = None,
    ) -> PurchaseRequest:
        purchase = await self._purchase_request_repo.get_by_id(purchase_request_id)
        if not purchase:
            raise EntityNotFoundError("درخواست خرید پیدا نشد")
        if user_id is not None and purchase.user_id != user_id:
            raise ValidationError("دسترسی به این درخواست مجاز نیست")
        if not purchase.is_active:
            return purchase

        pool_ids = list(purchase.crawl_target_ids or [])
        if purchase.crawl_target_id and purchase.crawl_target_id not in pool_ids:
            pool_ids.append(purchase.crawl_target_id)

        purchase.is_active = False
        purchase = await self._purchase_request_repo.save(purchase)

        await self._expire_pending_opportunities(purchase_request_id)
        await self._deactivate_orphan_pools(pool_ids)

        return purchase

    async def _expire_pending_opportunities(self, purchase_request_id: UUID) -> None:
        opportunities = await self._opportunity_repo.list_by_purchase_request(purchase_request_id)
        for opp in opportunities:
            if opp.status in (
                OpportunityStatus.NEW,
                OpportunityStatus.APPROVED,
                OpportunityStatus.MATCHED,
                OpportunityStatus.NOTIFIED,
            ):
                opp.status = OpportunityStatus.EXPIRED
                await self._opportunity_repo.save(opp)

    async def _deactivate_orphan_pools(self, pool_ids: list[UUID]) -> None:
        active_purchases = await self._purchase_request_repo.list_active_non_expired()
        active_trim_ids = {p.car_trim_id for p in active_purchases if p.car_trim_id}
        active_mapping_ids = await self._platform_repo.list_active_listing_mapping_ids_for_trims(
            active_trim_ids
        )

        seen_mapping_ids: set[UUID] = set()
        for pool_id in pool_ids:
            pool = await self._crawl_target_repo.get_by_id(pool_id)
            if not pool or not pool.is_shared_pool or not pool.listing_mapping_id:
                continue
            mapping_id = pool.listing_mapping_id
            if mapping_id in seen_mapping_ids:
                continue
            seen_mapping_ids.add(mapping_id)
            if mapping_id not in active_mapping_ids:
                pool.is_active = False
                await self._crawl_target_repo.save(pool)
