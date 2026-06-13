"""Tests for listing mapping lookup (no auto-create)."""

from uuid import uuid4

import pytest

from src.application.services.ensure_trim_mappings import ensure_listing_mappings_for_trim
from src.domain.entities.car_catalog import CarTrim
from src.domain.entities.platform import ListingMapping


class FakePlatformRepo:
    def __init__(self, mappings: list[ListingMapping] | None = None):
        self._mappings = mappings or []

    async def get_listing_mappings_for_trim(self, trim_id, listing_platform_slug=None):
        return [m for m in self._mappings if trim_id in (m.trim_ids or [])]


@pytest.mark.asyncio
async def test_ensure_listing_mappings_returns_existing_only():
    trim_id = uuid4()
    mapping = ListingMapping(
        id=uuid4(),
        listing_platform_id=uuid4(),
        divar_car_model_id=uuid4(),
        path="car/peugeot/207i/manual-p",
        divar_brand_model="Peugeot 207i Manual P",
        trim_ids=[trim_id],
    )
    repo = FakePlatformRepo([mapping])
    trim = CarTrim(
        id=trim_id,
        model_id=uuid4(),
        year_id=uuid4(),
        name="پانا",
        seo_slug="peugeot-207pana-mt",
    )
    result = await ensure_listing_mappings_for_trim(repo, trim=trim, listing_platform_slug="divar")
    assert result == [mapping]


@pytest.mark.asyncio
async def test_ensure_listing_mappings_does_not_auto_create():
    trim = CarTrim(
        id=uuid4(),
        model_id=uuid4(),
        year_id=uuid4(),
        name="پانا",
        seo_slug="peugeot-207pana-mt",
    )
    result = await ensure_listing_mappings_for_trim(FakePlatformRepo(), trim=trim, listing_platform_slug="divar")
    assert result == []
