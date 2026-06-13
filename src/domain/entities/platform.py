from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.enums.platform_fetch_strategy import PlatformFetchStrategy


@dataclass
class ListingPlatform:
    id: UUID
    slug: str
    name: str
    fetch_strategy: str = PlatformFetchStrategy.CRAWL.value
    is_active: bool = True
    created_at: datetime | None = None


@dataclass
class PricingPlatform:
    id: UUID
    slug: str
    name: str
    fetch_strategy: str = PlatformFetchStrategy.CRAWL.value
    is_active: bool = True
    created_at: datetime | None = None


@dataclass
class DivarCity:
    id: UUID
    slug: str
    display: str
    is_active: bool = True


@dataclass
class DivarCarModel:
    id: UUID
    slug: str
    display: str
    is_active: bool = True


@dataclass
class ListingMapping:
    """Divar (or other listing platform) search pool — can serve multiple trims."""

    id: UUID
    listing_platform_id: UUID
    divar_car_model_id: UUID
    path: str
    divar_brand_model: str = ""
    config: dict[str, Any] | None = None
    is_active: bool = True
    trim_ids: list[UUID] | None = None


@dataclass
class TrimPricingMapping:
    id: UUID
    trim_id: UUID
    pricing_platform_id: UUID
    slug: str
    config: dict[str, Any] | None = None
    is_active: bool = True
