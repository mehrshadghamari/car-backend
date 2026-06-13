"""Decide when shared pools should be crawled (active purchase requests per listing mapping)."""

from datetime import datetime, timedelta
from uuid import UUID

from src.domain.entities.crawl_run import CrawlRun, CrawlRunStatus
from src.domain.entities.crawl_target import CrawlTarget
from src.domain.entities.purchase_request import PurchaseRequest


def active_trim_ids(purchases: list[PurchaseRequest]) -> set[UUID]:
    return {p.car_trim_id for p in purchases if p.car_trim_id}


def pool_needs_crawl(
    pool: CrawlTarget,
    *,
    active_listing_mapping_ids: set[UUID],
) -> bool:
    if not pool.is_active or not pool.is_shared_pool:
        return False
    if not pool.listing_mapping_id:
        return False
    return pool.listing_mapping_id in active_listing_mapping_ids


def pool_recently_crawled(
    last_run: CrawlRun | None,
    *,
    refresh_sec: int,
    now: datetime,
) -> bool:
    if not last_run or not last_run.started_at:
        return False
    if last_run.status == CrawlRunStatus.RUNNING:
        return True
    return last_run.started_at >= now - timedelta(seconds=refresh_sec)


def collect_pool_ids_for_active_purchases(
    purchases: list[PurchaseRequest],
) -> set[UUID]:
    pool_ids: set[UUID] = set()
    for purchase in purchases:
        if purchase.crawl_target_id:
            pool_ids.add(purchase.crawl_target_id)
        for target_id in purchase.crawl_target_ids or []:
            pool_ids.add(target_id)
    return pool_ids
