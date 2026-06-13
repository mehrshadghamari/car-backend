"""Tests for crawl listing retention rules."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.domain.entities.listing import Listing
from src.domain.services.listing_retention import (
    is_listing_crawl_valid,
    listing_deactivation_cutoff,
)


def _listing(**kwargs) -> Listing:
    defaults = {
        "id": uuid4(),
        "crawl_target_id": uuid4(),
        "external_token": "tok",
        "title": "Car",
        "price": 1_000_000_000,
        "divar_url": "https://divar.ir/v/1",
        "last_seen_at": datetime.now(timezone.utc),
        "is_active": True,
    }
    defaults.update(kwargs)
    return Listing(**defaults)


def test_listing_valid_within_window():
    now = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)
    listing = _listing(last_seen_at=now - timedelta(days=1))
    assert is_listing_crawl_valid(listing, valid_days=2, now=now) is True


def test_listing_invalid_after_valid_window():
    now = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)
    listing = _listing(last_seen_at=now - timedelta(days=3))
    assert is_listing_crawl_valid(listing, valid_days=2, now=now) is False


def test_inactive_listing_never_valid():
    now = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)
    listing = _listing(is_active=False, last_seen_at=now)
    assert is_listing_crawl_valid(listing, valid_days=2, now=now) is False


def test_deactivation_cutoff():
    now = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)
    cutoff = listing_deactivation_cutoff(deactivate_days=5, now=now)
    assert cutoff == now - timedelta(days=5)
