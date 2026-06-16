from datetime import datetime
from zoneinfo import ZoneInfo

from src.domain.services.crawl_schedule_window import (
    CRAWL_ALLOWED_END_HOUR,
    CRAWL_ALLOWED_START_HOUR,
    is_crawl_allowed_in_tehran,
)

TEHRAN = ZoneInfo("Asia/Tehran")


def _tehran(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 6, 14, hour, minute, tzinfo=TEHRAN)


def test_allowed_at_8am():
    assert is_crawl_allowed_in_tehran(_tehran(8, 0)) is True


def test_allowed_at_9pm():
    assert is_crawl_allowed_in_tehran(_tehran(21, 59)) is True


def test_blocked_at_10pm():
    assert is_crawl_allowed_in_tehran(_tehran(22, 0)) is False


def test_blocked_at_7am():
    assert is_crawl_allowed_in_tehran(_tehran(7, 59)) is False


def test_constants():
    assert CRAWL_ALLOWED_START_HOUR == 8
    assert CRAWL_ALLOWED_END_HOUR == 22
