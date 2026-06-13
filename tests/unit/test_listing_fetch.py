"""Tests for shared pool listing fetch strategy routing."""

from uuid import uuid4

import pytest

from src.application.services.listing_fetch import fetch_shared_pool_listings
from src.domain.entities.crawl_target import CrawlTarget, VehicleContext
from src.domain.enums.platform_fetch_strategy import PlatformFetchStrategy


class FakeDivarPort:
    def __init__(self):
        self.finder_called = False
        self.crawl_called = False

    async def fetch_finder_posts(self, **kwargs):
        self.finder_called = True
        self.finder_kwargs = kwargs
        from src.domain.value_objects.divar_listing import DivarListingCard

        return [
            DivarListingCard(
                token="abc",
                title="Test",
                price=1_000_000,
                kilometer=0,
                district=None,
                divar_url="https://divar.ir/v/abc",
            )
        ]

    async def fetch_all_pages(self, listing_url, max_pages=5):
        self.crawl_called = True
        return []


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
        car_model_id=uuid4(),
        is_shared_pool=True,
    )


@pytest.mark.asyncio
async def test_api_strategy_uses_finder():
    port = FakeDivarPort()
    target = _target(PlatformFetchStrategy.API.value)
    target.vehicle_context.production_year_min = 1403
    target.vehicle_context.production_year_max = 1403
    cards = await fetch_shared_pool_listings(port, target, max_listings=50, max_pages=5)
    assert port.finder_called is True
    assert port.crawl_called is False
    assert len(cards) == 1
    assert port.finder_kwargs["brand_model"] == "Peugeot 207i Manual P"
    assert port.finder_kwargs["production_year_min"] == 1403
    assert port.finder_kwargs["production_year_max"] == 1403


@pytest.mark.asyncio
async def test_crawl_strategy_uses_pages():
    port = FakeDivarPort()
    target = _target(PlatformFetchStrategy.CRAWL.value)
    await fetch_shared_pool_listings(port, target, max_listings=50, max_pages=3)
    assert port.crawl_called is True
    assert port.finder_called is False
