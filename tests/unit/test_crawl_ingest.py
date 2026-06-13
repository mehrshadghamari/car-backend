"""Tests for shared pool listing ingest (API vs crawl detail fetch)."""

from uuid import uuid4

import pytest

from src.application.use_cases.crawl_and_evaluate import CrawlAndEvaluateUseCase
from src.domain.entities.crawl_target import CrawlTarget, VehicleContext
from src.domain.entities.listing import Listing
from src.domain.enums.platform_fetch_strategy import PlatformFetchStrategy
from src.domain.exceptions import ExternalServiceError
from src.domain.services.crawl_diagnostics import CrawlDiagnostics
from src.domain.value_objects.divar_listing import DivarListingCard, DivarListingDetail


class FakeListingRepo:
    async def upsert(self, listing: Listing):
        return listing, True


class FakeDivarPort:
    def __init__(self):
        self.detail_tokens: list[str] = []

    def build_listing_url(self, token: str) -> str:
        return f"https://divar.ir/v/{token}"

    async def fetch_listing_detail(self, token: str) -> DivarListingDetail:
        self.detail_tokens.append(token)
        raise ExternalServiceError("Divar detail fetch failed: 429")


def _use_case(divar_port: FakeDivarPort) -> CrawlAndEvaluateUseCase:
    return CrawlAndEvaluateUseCase(
        crawl_target_repo=None,
        listing_repo=FakeListingRepo(),
        market_price_repo=None,
        opportunity_repo=None,
        crawl_run_repo=None,
        purchase_request_repo=None,
        platform_repo=None,
        car_trim_repo=None,
        divar_port=divar_port,
        pricing_factory=None,
        settings=None,
    )


def _target(strategy: str) -> CrawlTarget:
    return CrawlTarget(
        id=uuid4(),
        source="divar",
        listing_url="https://divar.ir/s/tehran/car/peugeot/207i/manual-p",
        vehicle_context=VehicleContext(
            divar_brand_model="Peugeot 207i Manual P",
            listing_fetch_strategy=strategy,
            listing_category="light",
        ),
        city="tehran",
        listing_mapping_id=uuid4(),
        is_shared_pool=True,
    )


def _card(title: str = "پژو 207i ۱۴۰۳", km: int = 50_000) -> DivarListingCard:
    return DivarListingCard(
        token="tok1",
        title=title,
        price=1_900_000_000,
        kilometer=km,
        district="tehran",
        divar_url="https://divar.ir/v/tok1",
    )


@pytest.mark.asyncio
async def test_api_mode_skips_detail_when_year_and_km_present():
    port = FakeDivarPort()
    uc = _use_case(port)
    target = _target(PlatformFetchStrategy.API.value)
    diag = CrawlDiagnostics()

    ingested = await uc._ingest_listing(target, "tok1", _card(), diag)

    assert ingested is True
    assert port.detail_tokens == []


@pytest.mark.asyncio
async def test_api_mode_fetches_detail_when_year_missing():
    port = FakeDivarPort()
    uc = _use_case(port)
    target = _target(PlatformFetchStrategy.API.value)
    diag = CrawlDiagnostics()

    with pytest.raises(ExternalServiceError):
        await uc._ingest_listing(
            target,
            "tok1",
            _card(title="پژو 207i بدون سال"),
            diag,
        )

    assert port.detail_tokens == ["tok1"]


@pytest.mark.asyncio
async def test_crawl_mode_always_fetches_detail():
    port = FakeDivarPort()
    uc = _use_case(port)
    target = _target(PlatformFetchStrategy.CRAWL.value)
    diag = CrawlDiagnostics()

    with pytest.raises(ExternalServiceError):
        await uc._ingest_listing(target, "tok1", _card(), diag)

    assert port.detail_tokens == ["tok1"]
