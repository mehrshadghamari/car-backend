"""Match listings discovered during a specific crawl run."""

from __future__ import annotations

from datetime import datetime, timedelta


def tokens_from_run_diagnostics(diagnostics: list[dict] | None) -> set[str]:
    tokens: set[str] = set()
    for event in diagnostics or []:
        if event.get("level") == "ingested" and event.get("token"):
            tokens.add(str(event["token"]))
    return tokens


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def listings_for_crawl_run(run: dict, listings: list[dict]) -> list[dict]:
    """Listings ingested in this run (diagnostic tokens, else first_seen window)."""
    tokens = tokens_from_run_diagnostics(run.get("diagnostics"))
    if tokens:
        return [listing for listing in listings if listing.get("external_token") in tokens]

    started = _parse_iso(run.get("started_at"))
    finished = _parse_iso(run.get("finished_at")) or started
    if not started:
        return []

    if finished and finished < started:
        finished = started
    window_end = finished + timedelta(minutes=5) if finished else started + timedelta(hours=2)

    matched: list[dict] = []
    for listing in listings:
        first_seen = _parse_iso(listing.get("first_seen_at"))
        if not first_seen:
            continue
        if started <= first_seen <= window_end:
            matched.append(listing)
    return matched
