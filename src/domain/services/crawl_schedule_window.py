"""Tehran business hours for scheduled/manual Divar crawls (8:00–21:59)."""

from datetime import datetime
from zoneinfo import ZoneInfo

TEHRAN_TZ = ZoneInfo("Asia/Tehran")
CRAWL_ALLOWED_START_HOUR = 8
CRAWL_ALLOWED_END_HOUR = 22  # exclusive — 22:00+ is quiet


def tehran_now(now: datetime | None = None) -> datetime:
    current = now or datetime.now(TEHRAN_TZ)
    if current.tzinfo is None:
        return current.replace(tzinfo=TEHRAN_TZ)
    return current.astimezone(TEHRAN_TZ)


def is_crawl_allowed_in_tehran(now: datetime | None = None) -> bool:
    """True between 08:00 and 21:59 Asia/Tehran (no crawl 22:00–07:59)."""
    local = tehran_now(now)
    return CRAWL_ALLOWED_START_HOUR <= local.hour < CRAWL_ALLOWED_END_HOUR


def crawl_quiet_hours_message() -> str:
    return (
        "Crawl paused outside business hours (08:00–22:00 Asia/Tehran). "
        "No fetch between 22:00 and 07:59."
    )
