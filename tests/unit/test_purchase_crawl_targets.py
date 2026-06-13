"""Tests for listing mapping validation at crawl time."""

from uuid import uuid4

import pytest

from src.application.services.purchase_crawl_targets import validate_trim_listing_mapping
from src.domain.entities.car_catalog import CarTrim
from src.domain.exceptions import ValidationError


class FakePlatformRepo:
    def __init__(self, mappings: list | None = None):
        self.mappings = mappings or []

    async def get_listing_mappings_for_trim(self, trim_id, listing_platform_slug=None):
        return self.mappings


class FakeTrimRepo:
    def __init__(self, trim: CarTrim | None):
        self.trim = trim

    async def get_by_id(self, trim_id):
        return self.trim


@pytest.mark.asyncio
async def test_validate_passes_when_mapping_exists():
    trim_id = uuid4()
    await validate_trim_listing_mapping(
        FakePlatformRepo([object()]),
        FakeTrimRepo(CarTrim(id=trim_id, model_id=uuid4(), year_id=uuid4(), name="Manual", seo_slug="x")),
        trim_id,
    )


@pytest.mark.asyncio
async def test_validate_raises_when_mapping_missing():
    trim_id = uuid4()
    with pytest.raises(ValidationError, match="نگاشت پلتفرم آگهی"):
        await validate_trim_listing_mapping(
            FakePlatformRepo([]),
            FakeTrimRepo(
                CarTrim(
                    id=trim_id,
                    model_id=uuid4(),
                    year_id=uuid4(),
                    name="دنا پلاس",
                    seo_slug="dena-plus",
                    year_title="1403",
                )
            ),
            trim_id,
        )
