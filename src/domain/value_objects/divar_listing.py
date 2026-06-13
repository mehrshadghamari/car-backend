from dataclasses import dataclass


@dataclass(frozen=True)
class DivarListingCard:
    token: str
    title: str
    price: int
    kilometer: int | None
    district: str | None
    divar_url: str


@dataclass(frozen=True)
class DivarListingDetail:
    token: str
    title: str
    price: int
    kilometer: int | None
    production_year: int | None
    color: str | None
    brand_model: str | None
    district: str | None


@dataclass(frozen=True)
class DivarSearchPage:
    listings: list[DivarListingCard]
    last_post_date_epoch: int | None
    has_more: bool
