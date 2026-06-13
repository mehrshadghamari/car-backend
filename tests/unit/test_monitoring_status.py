from datetime import datetime, timedelta, timezone

from src.infrastructure.persistence.crawl_results_repository import _monitoring_status


def _dt(offset_hours: float = 0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=offset_hours)


def test_pending_when_no_crawl_run():
    assert (
        _monitoring_status(
            True,
            _dt(48),
            None,
            purchase_created_at=_dt(0),
        )
        == "pending"
    )


def test_pending_when_crawl_running():
    assert (
        _monitoring_status(
            True,
            _dt(48),
            "running",
            latest_crawl_started_at=_dt(-0.1),
            purchase_created_at=_dt(-1),
        )
        == "pending"
    )


def test_monitoring_after_completed_crawl_without_opportunities():
    created = _dt(-2)
    started = _dt(-1)
    assert (
        _monitoring_status(
            True,
            _dt(48),
            "completed",
            latest_crawl_started_at=started,
            purchase_created_at=created,
        )
        == "monitoring"
    )


def test_queued_when_no_crawl_targets():
    assert (
        _monitoring_status(
            True,
            _dt(48),
            None,
            purchase_created_at=_dt(0),
            has_crawl_targets=False,
        )
        == "queued"
    )


def test_pending_when_crawl_predates_purchase():
    assert (
        _monitoring_status(
            True,
            _dt(48),
            "completed",
            latest_crawl_started_at=_dt(-5),
            purchase_created_at=_dt(-1),
        )
        == "pending"
    )


def test_active_when_opportunities_exist():
    assert (
        _monitoring_status(
            True,
            _dt(48),
            None,
            purchase_created_at=_dt(0),
            opportunity_count=2,
        )
        == "active"
    )


def test_failed_after_failed_crawl_for_request():
    created = _dt(-2)
    started = _dt(-1)
    assert (
        _monitoring_status(
            True,
            _dt(48),
            "failed",
            latest_crawl_started_at=started,
            purchase_created_at=created,
        )
        == "failed"
    )


def test_inactive_when_expired():
    assert (
        _monitoring_status(
            True,
            _dt(-1),
            "completed",
            latest_crawl_started_at=_dt(-2),
            purchase_created_at=_dt(-3),
        )
        == "inactive"
    )


def test_inactive_when_deactivated():
    assert (
        _monitoring_status(
            False,
            _dt(48),
            "completed",
            latest_crawl_started_at=_dt(-1),
            purchase_created_at=_dt(-2),
        )
        == "inactive"
    )
