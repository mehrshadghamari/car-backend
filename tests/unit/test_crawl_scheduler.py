"""Tests for listing-mapping-gated crawl scheduling."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.application.services.crawl_scheduler import (
    active_trim_ids,
    pool_needs_crawl,
    pool_recently_crawled,
)
from src.domain.entities.crawl_run import CrawlRun, CrawlRunStatus
from src.domain.entities.crawl_target import CrawlTarget, VehicleContext
from src.domain.entities.purchase_request import PurchaseRequest


def _purchase(trim_id) -> PurchaseRequest:
    return PurchaseRequest(
        id=uuid4(),
        user_id=uuid4(),
        car_trim_id=trim_id,
    )


def _pool(listing_mapping_id, is_active=True) -> CrawlTarget:
    return CrawlTarget(
        id=uuid4(),
        source="divar",
        listing_url="https://divar.ir/...",
        vehicle_context=VehicleContext(),
        listing_mapping_id=listing_mapping_id,
        is_shared_pool=True,
        is_active=is_active,
    )


def test_active_trim_ids_from_purchases():
    trim_a = uuid4()
    trim_b = uuid4()
    ids = active_trim_ids([_purchase(trim_a), _purchase(trim_a), _purchase(trim_b)])
    assert ids == {trim_a, trim_b}


def test_pool_needs_crawl_when_mapping_has_open_purchase():
    mapping_id = uuid4()
    pool = _pool(mapping_id)
    assert pool_needs_crawl(pool, active_listing_mapping_ids={mapping_id}) is True


def test_pool_skipped_when_no_open_purchase_for_mapping():
    pool = _pool(uuid4())
    assert pool_needs_crawl(pool, active_listing_mapping_ids=set()) is False


def test_pool_skipped_without_listing_mapping_id():
    pool = _pool(uuid4())
    pool.listing_mapping_id = None
    assert pool_needs_crawl(pool, active_listing_mapping_ids={uuid4()}) is False


def test_pool_recently_crawled_within_refresh_window():
    now = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)
    run = CrawlRun(
        id=uuid4(),
        crawl_target_id=uuid4(),
        status=CrawlRunStatus.COMPLETED,
        started_at=now - timedelta(minutes=10),
    )
    assert pool_recently_crawled(run, refresh_sec=1800, now=now) is True


def test_pool_not_recent_when_outside_refresh_window():
    now = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)
    run = CrawlRun(
        id=uuid4(),
        crawl_target_id=uuid4(),
        status=CrawlRunStatus.COMPLETED,
        started_at=now - timedelta(minutes=45),
    )
    assert pool_recently_crawled(run, refresh_sec=1800, now=now) is False
