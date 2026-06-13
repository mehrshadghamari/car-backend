"""Match Divar listings against purchase-request filters."""

from src.domain.entities.listing import Listing
from src.domain.entities.purchase_request import PurchaseRequest
from src.domain.utils.persian_numbers import catalog_year_to_jalali, parse_jalali_year


def _listing_year_jalali(listing: Listing) -> int | None:
    if listing.production_year is None:
        return None
    year = listing.production_year
    if 1300 <= year <= 1499:
        return year
    if 1900 <= year <= 2100:
        from src.domain.utils.persian_numbers import gregorian_to_jalali

        jy, _, _ = gregorian_to_jalali(year, 7, 1)
        return jy
    return parse_jalali_year(str(year))


def _request_year_jalali(value: int | None) -> int | None:
    if value is None:
        return None
    if 1300 <= value <= 1499:
        return value
    if 1900 <= value <= 2100:
        from src.domain.utils.persian_numbers import gregorian_to_jalali

        jy, _, _ = gregorian_to_jalali(value, 7, 1)
        return jy
    return catalog_year_to_jalali(str(value))


def listing_matches_purchase_request(listing: Listing, request: PurchaseRequest) -> bool:
    """True when listing year/km/color satisfy the purchase request criteria."""
    listing_year = _listing_year_jalali(listing)
    year_min = _request_year_jalali(request.production_year_min)
    year_max = _request_year_jalali(request.production_year_max)

    if year_min is not None:
        if listing_year is None or listing_year < year_min:
            return False
    if year_max is not None:
        if listing_year is None or listing_year > year_max:
            return False
    if request.usage_min is not None:
        if listing.kilometer is None or listing.kilometer < request.usage_min:
            return False
    if request.usage_max is not None:
        if listing.kilometer is None or listing.kilometer > request.usage_max:
            return False
    if request.color and listing.color:
        if listing.color.strip() != request.color.strip():
            return False
    return True
