from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class VehicleContext:
    pricing_platform: str = "khodro45"
    pricing_config: dict[str, Any] | None = None
    hamrah_brand: str = ""
    hamrah_model: str = ""
    hamrah_type_id: str = ""
    default_color: str = "ColorWhite"
    default_body_condition: str = "WithoutColor"
    color_map: dict[str, str] | None = None
    near_threshold_pct: float = 0.02
    max_pages_per_run: int = 5
    max_listings_per_check: int = 10
    divar_brand_model: str | None = None
    listing_platform: str = "divar"
    listing_fetch_strategy: str = "crawl"
    pricing_fetch_strategy: str = "crawl"
    listing_category: str = "light"
    production_year_min: int | None = None
    production_year_max: int | None = None
    usage_min: int | None = None
    usage_max: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VehicleContext":
        return cls(
            pricing_platform=data.get("pricing_platform", "hamrah_mechanic"),
            pricing_config=data.get("pricing_config"),
            hamrah_brand=data.get("hamrah_brand", ""),
            hamrah_model=data.get("hamrah_model", ""),
            hamrah_type_id=str(data.get("hamrah_type_id", "")),
            default_color=data.get("default_color", "ColorWhite"),
            default_body_condition=data.get("default_body_condition", "WithoutColor"),
            color_map=data.get("color_map"),
            near_threshold_pct=float(data.get("near_threshold_pct", 0.02)),
            max_pages_per_run=int(data.get("max_pages_per_run", 5)),
            max_listings_per_check=int(data.get("max_listings_per_check", 10)),
            divar_brand_model=data.get("divar_brand_model"),
            listing_platform=data.get("listing_platform", "divar"),
            listing_fetch_strategy=data.get("listing_fetch_strategy", "crawl"),
            pricing_fetch_strategy=data.get("pricing_fetch_strategy", "crawl"),
            listing_category=data.get("listing_category", "light"),
            production_year_min=data.get("production_year_min"),
            production_year_max=data.get("production_year_max"),
            usage_min=data.get("usage_min"),
            usage_max=data.get("usage_max"),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "pricing_platform": self.pricing_platform,
            "pricing_config": self.pricing_config or {},
            "hamrah_brand": self.hamrah_brand,
            "hamrah_model": self.hamrah_model,
            "hamrah_type_id": self.hamrah_type_id,
            "default_color": self.default_color,
            "default_body_condition": self.default_body_condition,
            "color_map": self.color_map or {},
            "near_threshold_pct": self.near_threshold_pct,
            "max_pages_per_run": self.max_pages_per_run,
            "max_listings_per_check": self.max_listings_per_check,
            "listing_platform": self.listing_platform,
        }
        if self.divar_brand_model:
            result["divar_brand_model"] = self.divar_brand_model
        result["listing_fetch_strategy"] = self.listing_fetch_strategy
        result["pricing_fetch_strategy"] = self.pricing_fetch_strategy
        result["listing_category"] = self.listing_category
        if self.production_year_min is not None:
            result["production_year_min"] = self.production_year_min
        if self.production_year_max is not None:
            result["production_year_max"] = self.production_year_max
        if self.usage_min is not None:
            result["usage_min"] = self.usage_min
        if self.usage_max is not None:
            result["usage_max"] = self.usage_max
        return result


@dataclass
class CrawlTarget:
    id: UUID
    source: str
    listing_url: str
    vehicle_context: VehicleContext
    is_active: bool = True
    poll_interval_sec: int = 300
    listing_mapping_id: UUID | None = None
    car_model_id: UUID | None = None
    city: str = "tehran"
    is_shared_pool: bool = False
    pool_production_year: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
