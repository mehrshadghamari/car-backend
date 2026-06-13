from dataclasses import dataclass


@dataclass(frozen=True)
class MarketReferencePrice:
    price_up: int
    price_down: int
    price_mid: int
    reference_url: str
    provider: str = "hamrah_mechanic"
    brand: str = ""
    model: str = ""
    year: int = 0
    type_id: str = ""

    @property
    def hamrah_url(self) -> str:
        """Backward-compatible alias for reference_url."""
        return self.reference_url
