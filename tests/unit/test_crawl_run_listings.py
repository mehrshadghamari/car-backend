from src.domain.services.crawl_run_listings import (
    listings_for_crawl_run,
    tokens_from_run_diagnostics,
)


def test_tokens_from_run_diagnostics():
    diagnostics = [
        {"level": "ingested", "token": "abc"},
        {"level": "info", "token": "ignored"},
        {"level": "ingested", "token": "xyz"},
    ]
    assert tokens_from_run_diagnostics(diagnostics) == {"abc", "xyz"}


def test_listings_for_crawl_run_by_token():
    run = {
        "started_at": "2026-01-01T10:00:00+00:00",
        "diagnostics": [{"level": "ingested", "token": "tok1"}],
    }
    listings = [
        {"external_token": "tok1", "first_seen_at": "2026-01-01T09:00:00+00:00"},
        {"external_token": "other", "first_seen_at": "2026-01-01T11:00:00+00:00"},
    ]
    matched = listings_for_crawl_run(run, listings)
    assert [l["external_token"] for l in matched] == ["tok1"]


def test_listings_for_crawl_run_by_first_seen_window():
    run = {
        "started_at": "2026-01-01T10:00:00+00:00",
        "finished_at": "2026-01-01T11:00:00+00:00",
        "diagnostics": [],
    }
    listings = [
        {"external_token": "a", "first_seen_at": "2026-01-01T10:30:00+00:00"},
        {"external_token": "b", "first_seen_at": "2026-01-01T11:30:00+00:00"},
        {"external_token": "c", "first_seen_at": "2026-01-01T09:00:00+00:00"},
    ]
    matched = listings_for_crawl_run(run, listings)
    assert [l["external_token"] for l in matched] == ["a"]
