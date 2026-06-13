"""Deactivate stale crawl listings and bulk-purge inactive pool data."""

import logging

from src.application.ports.repositories import ListingRepository, PurchaseRequestRepository
from src.domain.compat import utc_now
from src.domain.services.listing_retention import listing_deactivation_cutoff
from src.infrastructure.config import Settings

logger = logging.getLogger(__name__)


class CrawlRetentionUseCase:
    """
    1. Mark listings inactive when last_seen_at exceeds deactivate_days (default 5).
    2. Bulk-delete inactive listings and related market prices / opportunities.
    3. Deactivate purchase requests older than deactivate_days.
    """

    def __init__(
        self,
        listing_repo: ListingRepository,
        purchase_request_repo: PurchaseRequestRepository,
        settings: Settings,
    ):
        self._listing_repo = listing_repo
        self._purchase_request_repo = purchase_request_repo
        self._settings = settings

    async def execute(self) -> dict[str, int]:
        now = utc_now()
        deactivate_days = self._settings.crawl_result_deactivate_days
        cutoff = listing_deactivation_cutoff(deactivate_days=deactivate_days, now=now)

        listings_deactivated = await self._listing_repo.deactivate_stale(cutoff)
        purchases_deactivated = await self._purchase_request_repo.deactivate_older_than(cutoff)
        purge_counts = await self._listing_repo.bulk_purge_inactive()

        logger.info(
            "Crawl retention: deactivated %s listing(s), %s purchase(s); purged %s",
            listings_deactivated,
            purchases_deactivated,
            purge_counts,
        )
        return {
            "listings_deactivated": listings_deactivated,
            "purchases_deactivated": purchases_deactivated,
            **purge_counts,
        }
