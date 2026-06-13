from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from src.domain.compat import StrEnum
from uuid import UUID


class OpportunityStatus(StrEnum):
    NEW = "new"
    MATCHED = "matched"
    NOTIFIED = "notified"
    EXPIRED = "expired"


class DealTag(StrEnum):
    """Quality tag vs market reference tiers."""

    BEST = "best"  # near left (floor) urgent-sale price
    GOOD = "good"  # near middle urgent-sale price
    NORMAL = "normal"  # near right (ceiling) urgent-sale price
    FAIR = "fair"  # legacy Hamrah near-mid tag


DEAL_TAG_LABELS: dict[str, dict[str, str]] = {
    DealTag.BEST.value: {"en": "Best", "fa": "بهترین"},
    DealTag.GOOD.value: {"en": "Good", "fa": "خوب"},
    DealTag.NORMAL.value: {"en": "Normal", "fa": "عادی"},
    DealTag.FAIR.value: {"en": "Fair", "fa": "مناسب"},
}


@dataclass
class Opportunity:
    id: UUID
    listing_id: UUID
    crawl_target_id: UUID
    listing_price: int
    market_price_down: int
    market_price_up: int
    discount_amount: int
    discount_pct: Decimal
    score: Decimal
    status: OpportunityStatus
    is_below_floor: bool
    purchase_request_id: UUID | None = None
    price_basis: str = "down"
    reference_price: int | None = None
    market_price_mid: int | None = None
    deal_tag: str = DealTag.BEST.value
    created_at: datetime | None = None
