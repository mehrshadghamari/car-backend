from pathlib import Path

from src.infrastructure.adapters.khodro45.parser import (
    normalize_trim_seo_slug,
    parse_khodro45_api_prices,
    parse_khodro45_api_urgent_prices,
    parse_khodro45_prices,
)

ROOT = Path(__file__).resolve().parents[2]


def test_normalize_trim_seo_slug_strips_cpe_prefix():
    assert normalize_trim_seo_slug("cpe-peugeot-207pana-at") == "peugeot-207pana-at"
    assert normalize_trim_seo_slug("peugeot-207pana-at") == "peugeot-207pana-at"


def test_parse_khodro45_api_urgent_prices():
    data = {
        "k45_price": {
            "min": 2_177_000_000,
            "estimated_price": 2_316_000_000,
            "max": 2_363_000_000,
        }
    }
    price_up, price_mid, price_down = parse_khodro45_api_urgent_prices(data)
    assert price_up == 2_363_000_000
    assert price_mid == 2_316_000_000
    assert price_down == 2_177_000_000


def test_parse_khodro45_api_prices():
    data = {
        "market_price": {
            "min": 2_149_000_000,
            "fair_market_price": 2_286_000_000,
            "max": 2_332_000_000,
        }
    }
    price_up, price_mid, price_down = parse_khodro45_api_prices(data)
    assert price_up == 2_332_000_000
    assert price_mid == 2_286_000_000
    assert price_down == 2_149_000_000


def test_parse_khodro45_prices_from_urgent_sale_section():
    html = ROOT.joinpath("smaple-khodro45.html").read_text(encoding="utf-8")
    price_up, price_mid, price_down = parse_khodro45_prices(html)
    assert price_up == 2_074_000_000
    assert price_mid == 2_033_000_000
    assert price_down == 1_911_000_000
    assert price_up > price_mid > price_down


def test_parse_khodro45_prices_from_khodro45_html_sample():
    html = ROOT.joinpath("khodro45.html").read_text(encoding="utf-8")
    price_up, price_mid, price_down = parse_khodro45_prices(html)
    assert price_up == 2_174_000_000
    assert price_mid == 2_132_000_000
    assert price_down == 2_004_000_000
    assert price_up > price_mid > price_down
