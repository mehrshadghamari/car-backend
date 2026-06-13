from uuid import uuid4

from src.domain.entities.purchase_request import PurchaseRequest
from src.domain.services.purchase_detail_filters import (
    filter_diagnostics_for_purchase,
    latest_crawl_run_per_target,
)


def _purchase(**kwargs) -> PurchaseRequest:
    defaults = dict(
        id=uuid4(),
        user_id=uuid4(),
        car_trim_id=uuid4(),
        car_model_id=uuid4(),
        crawl_target_id=None,
        pricing_platform_id=uuid4(),
        city="tehran",
        color=None,
        production_year_min=1403,
        production_year_max=1403,
        usage_min=None,
        usage_max=80000,
        generated_divar_url=None,
        is_active=True,
        poll_interval_sec=300,
        max_listings_per_check=10,
        expires_at=None,
    )
    defaults.update(kwargs)
    return PurchaseRequest(**defaults)


def test_filter_diagnostics_excludes_unrelated_pool_listings():
    purchase = _purchase(production_year_min=1403, production_year_max=1403)
    other_id = str(uuid4())
    events = [
        {"level": "info", "message": "Shared pool fetch started"},
        {"level": "ingested", "message": "Pool listing ingested", "title": "پژو 207", "year": 1401, "km": 50000},
        {
            "level": "ingested",
            "message": "Pool listing ingested",
            "title": "شاهین",
            "year": 1403,
            "km": 2600,
        },
        {
            "level": "skip",
            "message": "Khodro45 price unavailable: test",
            "year": 1403,
            "km": 2600,
            "purchase_request_id": other_id,
        },
        {
            "level": "info",
            "message": "Purchase evaluation summary",
            "purchase_request_id": str(purchase.id),
            "evaluated": 0,
        },
    ]
    filtered = filter_diagnostics_for_purchase(events, purchase.id, purchase)
    messages = [e["message"] for e in filtered]
    assert "Shared pool fetch started" in messages
    assert "Purchase evaluation summary" in messages
    assert "Pool listing ingested" not in messages
    assert not any("Khodro45" in m for m in messages)


def test_filter_diagnostics_includes_purchase_scoped_pricing_skip():
    purchase = _purchase()
    events = [
        {
            "level": "skip",
            "message": "Khodro45 price unavailable: test",
            "year": 1404,
            "km": 2600,
            "purchase_request_id": str(purchase.id),
        }
    ]
    filtered = filter_diagnostics_for_purchase(events, purchase.id, purchase)
    assert len(filtered) == 1


def test_filter_diagnostics_dedupes_repeated_pricing_skip():
    purchase = _purchase()
    event = {
        "level": "skip",
        "message": "Khodro45 price unavailable: test",
        "year": 1404,
        "km": 2600,
        "purchase_request_id": str(purchase.id),
    }
    filtered = filter_diagnostics_for_purchase([event, event], purchase.id, purchase)
    assert len(filtered) == 1


def test_latest_crawl_run_per_target():
    runs = [
        {"crawl_target_id": "a", "started_at": "2026-06-09T10:00:00+00:00"},
        {"crawl_target_id": "a", "started_at": "2026-06-09T11:00:00+00:00"},
        {"crawl_target_id": "b", "started_at": "2026-06-09T09:00:00+00:00"},
    ]
    latest = latest_crawl_run_per_target(runs)
    assert len(latest) == 2
    by_target = {r["crawl_target_id"]: r for r in latest}
    assert by_target["a"]["started_at"].endswith("11:00:00+00:00")
