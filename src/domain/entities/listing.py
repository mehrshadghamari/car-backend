from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Listing:
    id: UUID
    crawl_target_id: UUID
    external_token: str
    title: str
    price: int
    divar_url: str
    car_model_id: UUID | None = None
    kilometer: int | None = None
    production_year: int | None = None
    color: str | None = None
    body_condition: str | None = None
    district: str | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    is_active: bool = True
