"""Scope crawl results and diagnostics to a single purchase request."""

from uuid import UUID

from src.domain.entities.car_catalog import CarTrim
from src.domain.entities.purchase_request import PurchaseRequest
from src.domain.services.trim_production_year import resolve_production_year_range

_BRIEF_CRAWL_MESSAGES = frozenset(
    {
        "Shared pool fetch started",
        "Listing platform mapping validated for active purchase trim(s)",
        "No active purchase request for this listing pool — skipping Divar fetch",
    }
)


def effective_purchase_request(
    purchase: PurchaseRequest,
    trim: CarTrim | None = None,
) -> PurchaseRequest:
    """Apply catalog trim year defaults when purchase year range was not stored."""
    if not trim:
        return purchase
    year_min, year_max = resolve_production_year_range(
        trim,
        production_year_min=purchase.production_year_min,
        production_year_max=purchase.production_year_max,
    )
    return PurchaseRequest(
        id=purchase.id,
        user_id=purchase.user_id,
        car_trim_id=purchase.car_trim_id,
        car_model_id=purchase.car_model_id,
        crawl_target_id=purchase.crawl_target_id,
        pricing_platform_id=purchase.pricing_platform_id,
        city=purchase.city,
        color=purchase.color,
        production_year_min=year_min,
        production_year_max=year_max,
        usage_min=purchase.usage_min,
        usage_max=purchase.usage_max,
        generated_divar_url=purchase.generated_divar_url,
        is_active=purchase.is_active,
        near_threshold_pct=purchase.near_threshold_pct,
        poll_interval_sec=purchase.poll_interval_sec,
        max_listings_per_check=purchase.max_listings_per_check,
        expires_at=purchase.expires_at,
        crawl_target_ids=list(purchase.crawl_target_ids or []),
    )


def _dedupe_key(event: dict) -> tuple:
    return (
        event.get("level"),
        event.get("message"),
        event.get("year"),
        event.get("km"),
        event.get("token"),
        event.get("purchase_request_id"),
    )


def filter_diagnostics_for_purchase(
    events: list[dict],
    purchase_id: UUID,
    purchase: PurchaseRequest,
) -> list[dict]:
    """
    Purchase detail diagnostics must be scoped to this request only.

    Shared pool runs log every ingested listing (Shahin, Changan, …) — those are
    not shown here. Only events tagged with this purchase_request_id plus brief
    crawl summary lines (fetch started, N posts returned, completed).
    """
    del purchase  # reserved for future title/brand scoping
    purchase_id_str = str(purchase_id)
    filtered: list[dict] = []
    seen: set[tuple] = set()

    for event in events:
        event_pr = event.get("purchase_request_id")
        if event_pr:
            if event_pr != purchase_id_str:
                continue
            key = _dedupe_key(event)
            if key in seen:
                continue
            seen.add(key)
            filtered.append(event)
            continue

        message = event.get("message") or ""
        if message in _BRIEF_CRAWL_MESSAGES:
            filtered.append(event)
            continue
        if message.startswith("Listing platform returned"):
            filtered.append(event)
            continue
        if message.startswith("Crawl completed"):
            filtered.append(event)
            continue

    return filtered


def latest_crawl_run_per_target(runs: list[dict]) -> list[dict]:
    """One newest run per crawl target for purchase detail."""
    by_target: dict[str, dict] = {}
    for run in runs:
        tid = run.get("crawl_target_id")
        if not tid:
            continue
        existing = by_target.get(tid)
        if not existing or (run.get("started_at") or "") > (existing.get("started_at") or ""):
            by_target[tid] = run
    return sorted(by_target.values(), key=lambda r: r.get("started_at") or "", reverse=True)
