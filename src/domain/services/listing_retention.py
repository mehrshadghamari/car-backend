"""Crawl listing freshness and retention rules."""

from datetime import datetime, timedelta

from src.domain.compat import as_utc
from src.domain.entities.listing import Listing


def is_listing_crawl_valid(
    listing: Listing,
    *,
    valid_days: int,
    now: datetime,
) -> bool:
    """True when listing is active and last seen within the valid window."""
    if not listing.is_active:
        return False
    if not listing.last_seen_at:
        return False
    return as_utc(listing.last_seen_at) >= as_utc(now) - timedelta(days=valid_days)


def listing_deactivation_cutoff(*, deactivate_days: int, now: datetime) -> datetime:
    """Listings last seen before this time should be marked inactive."""
    return now - timedelta(days=deactivate_days)
