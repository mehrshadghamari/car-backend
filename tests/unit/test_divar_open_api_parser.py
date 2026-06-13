"""Tests for Divar open-platform finder response parsing."""

from src.infrastructure.adapters.divar.open_api_parser import parse_open_finder_response


SAMPLE_RESPONSE = {
    "posts": [
        {
            "token": "gaigKMO-",
            "title": "پژو 207i دنده ای",
            "price": {"mode": "مقطوع", "value": "2050000000"},
            "vehicles_fields": {"usage": "0"},
        },
        {
            "token": "AaPsW7Ir",
            "title": "پژو 207i پانوراما",
            "price": {"mode": "مقطoع", "value": "1700000000"},
            "vehicles_fields": {"usage": "10000"},
        },
    ]
}


def test_parse_open_finder_response():
    cards = parse_open_finder_response(SAMPLE_RESPONSE)
    assert len(cards) == 2
    assert cards[0].token == "gaigKMO-"
    assert cards[0].price == 2_050_000_000
    assert cards[0].kilometer == 0
    assert cards[1].kilometer == 10000
    assert "divar.ir" in cards[0].divar_url


def test_parse_empty_response():
    assert parse_open_finder_response({}) == []
