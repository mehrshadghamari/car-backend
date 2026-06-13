from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class CarBrand:
    id: UUID
    name: str
    slug: str
    khodro45_id: int | None = None
    title_en: str | None = None
    is_active: bool = True
    created_at: datetime | None = None


@dataclass
class CarModel:
    id: UUID
    brand_id: UUID
    name: str
    slug: str
    khodro45_id: int | None = None
    title_en: str | None = None
    near_threshold_pct: float = 0.02
    is_active: bool = True
    created_at: datetime | None = None
    brand_name: str | None = None


@dataclass
class CarYear:
    id: UUID
    model_id: UUID
    title: str
    khodro45_id: int | None = None
    is_active: bool = True
    created_at: datetime | None = None
    model_name: str | None = None
    brand_name: str | None = None


@dataclass
class CarTrim:
    id: UUID
    model_id: UUID
    year_id: UUID
    name: str
    seo_slug: str
    khodro45_id: int | None = None
    title_en: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    year_title: str | None = None
    model_name: str | None = None
    brand_name: str | None = None
    brand_id: UUID | None = None

    @property
    def khodro45_price_slug(self) -> str:
        slug = self.seo_slug.strip()
        return slug if slug.startswith("cpe-") else f"cpe-{slug}"
