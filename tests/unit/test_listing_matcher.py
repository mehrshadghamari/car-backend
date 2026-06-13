"""Tests for listing ↔ purchase request filter matching."""

from uuid import uuid4

from src.domain.entities.listing import Listing
from src.domain.entities.purchase_request import PurchaseRequest
from src.domain.services.listing_matcher import listing_matches_purchase_request


def _listing(**kwargs) -> Listing:
    defaults = {
        "id": uuid4(),
        "crawl_target_id": uuid4(),
        "external_token": "abc",
        "title": "Test car",
        "price": 1_000_000_000,
        "kilometer": 50_000,
        "production_year": 1402,
        "divar_url": "https://divar.ir/v/abc",
    }
    defaults.update(kwargs)
    return Listing(**defaults)


def _purchase(**kwargs) -> PurchaseRequest:
    defaults = {
        "id": uuid4(),
        "user_id": uuid4(),
        "car_trim_id": uuid4(),
        "car_model_id": uuid4(),
    }
    defaults.update(kwargs)
    return PurchaseRequest(**defaults)


def test_matches_when_no_filters():
    assert listing_matches_purchase_request(_listing(), _purchase()) is True


def test_year_min_filter():
    listing = _listing(production_year=1401)
    purchase = _purchase(production_year_min=1402)
    assert listing_matches_purchase_request(listing, purchase) is False


def test_year_max_filter():
    listing = _listing(production_year=1403)
    purchase = _purchase(production_year_max=1402)
    assert listing_matches_purchase_request(listing, purchase) is False


def test_usage_range_filter():
    listing = _listing(kilometer=120_000)
    purchase = _purchase(usage_min=0, usage_max=100_000)
    assert listing_matches_purchase_request(listing, purchase) is False


def test_color_filter():
    listing = _listing(color="سفید")
    purchase = _purchase(color="مشکی")
    assert listing_matches_purchase_request(listing, purchase) is False


def test_all_filters_match():
    listing = _listing(production_year=1402, kilometer=30_000, color="سفید")
    purchase = _purchase(
        production_year_min=1401,
        production_year_max=1403,
        usage_min=0,
        usage_max=50_000,
        color="سفید",
    )
    assert listing_matches_purchase_request(listing, purchase) is True
