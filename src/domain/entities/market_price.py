from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class MarketPrice:
    id: UUID
    listing_id: UUID
    price_up: int
    price_down: int
    price_mid: int
    reference_url: str
    fetched_at: datetime
    trim_id: UUID | None = None
    pricing_provider: str = "hamrah_mechanic"

    @property
    def hamrah_url(self) -> str:
        return self.reference_url
