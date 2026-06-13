from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass
class PurchaseRequest:
    id: UUID
    user_id: UUID
    car_trim_id: UUID
    car_model_id: UUID | None = None
    crawl_target_id: UUID | None = None
    pricing_platform_id: UUID | None = None
    city: str = "tehran"
    color: str | None = None
    production_year_min: int | None = None
    production_year_max: int | None = None
    usage_min: int | None = None
    usage_max: int | None = None
    generated_divar_url: str | None = None
    is_active: bool = True
    near_threshold_pct: Decimal | None = None
    poll_interval_sec: int = 300
    max_listings_per_check: int = 10
    expires_at: datetime | None = None
    crawl_target_ids: list[UUID] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and self.expires_at <= now
