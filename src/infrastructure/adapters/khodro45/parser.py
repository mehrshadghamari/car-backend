import re
from typing import Any

from src.domain.utils.persian_numbers import parse_price_toman

KHODRO45_PRICE_API_PATH = "v1/pricing/used-cars/defect-levels/price-estimation/"

URGENT_SALE_SECTION_TITLE = "قیمت فروش فوری"
PLATFORM_LISTINGS_SECTION_TITLE = "قیمت پلتفرم های آگهی"

_PRICE_TIER_CLASSES = (
    ("right-price", "up"),
    ("middle-price", "mid"),
    ("left-price", "down"),
)


def normalize_trim_seo_slug(slug: str) -> str:
    """Khodro45 API expects trim slug without the cpe- prefix."""
    trimmed = slug.strip()
    if trimmed.startswith("cpe-"):
        return trimmed[4:]
    return trimmed


def _extract_section_html(html: str, section_title: str) -> str:
    start = html.find(section_title)
    if start < 0:
        raise ValueError(f"Khodro45 section not found: {section_title}")

    end = html.find(PLATFORM_LISTINGS_SECTION_TITLE, start + len(section_title))
    if section_title == PLATFORM_LISTINGS_SECTION_TITLE:
        end = -1

    if end > start:
        return html[start:end]
    return html[start:]


def _parse_price_tiers_from_html(section_html: str) -> tuple[int, int, int]:
    prices: dict[str, int] = {}
    for css_class, key in _PRICE_TIER_CLASSES:
        pattern = rf'class="[^"]*\b{re.escape(css_class)}\b[^"]*"[^>]*>.*?<p>([^<]+)</p>'
        match = re.search(pattern, section_html, re.DOTALL)
        if not match:
            raise ValueError(f"Khodro45 price block not found: {css_class}")
        value = parse_price_toman(match.group(1))
        if value is None:
            raise ValueError(f"Khodro45 price parse failed for {css_class}")
        prices[key] = value

    if not (prices["up"] > prices["mid"] > prices["down"] > 0):
        raise ValueError("Khodro45 price values invalid")

    return prices["up"], prices["mid"], prices["down"]


def parse_khodro45_api_urgent_prices(data: dict[str, Any]) -> tuple[int, int, int]:
    """
    Parse Khodro45 price-estimation API JSON for urgent sale (قیمت فروش فوری).

    The website maps this block to ``k45_price`` (max / estimated_price / min),
    not ``market_price`` (platform listing prices).
    """
    urgent = data.get("k45_price")
    if not isinstance(urgent, dict):
        raise ValueError("Khodro45 API response missing k45_price")

    try:
        price_up = int(urgent["max"])
        price_mid = int(urgent["estimated_price"])
        price_down = int(urgent["min"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Khodro45 API k45_price fields invalid") from exc

    if not (price_up > price_mid > price_down > 0):
        raise ValueError("Khodro45 API k45_price values invalid")

    return price_up, price_mid, price_down


def parse_khodro45_api_prices(data: dict[str, Any]) -> tuple[int, int, int]:
    """
    Parse Khodro45 platform listing prices from market_price (قیمت پلتفرم های آگهی).
    """
    market = data.get("market_price")
    if not isinstance(market, dict):
        raise ValueError("Khodro45 API response missing market_price")

    try:
        price_up = int(market["max"])
        price_mid = int(market["fair_market_price"])
        price_down = int(market["min"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Khodro45 API market_price fields invalid") from exc

    if not (price_up > price_mid > price_down > 0):
        raise ValueError("Khodro45 API market_price values invalid")

    return price_up, price_mid, price_down


def parse_khodro45_prices(html: str) -> tuple[int, int, int]:
    """
    Parse Khodro45 car price page HTML.

    Returns (price_up, price_mid, price_down) from right/middle/left blocks
    under «قیمت فروش فوری» (urgent sale), not platform listing prices.
    """
    section_html = _extract_section_html(html, URGENT_SALE_SECTION_TITLE)
    return _parse_price_tiers_from_html(section_html)
