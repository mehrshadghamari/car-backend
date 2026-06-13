from typing import Any

import httpx

from src.application.ports.external import MarketPricingPort
from src.domain.exceptions import ExternalServiceError
from src.domain.value_objects.market_reference import MarketReferencePrice
from src.infrastructure.adapters.khodro45.parser import (
    KHODRO45_PRICE_API_PATH,
    normalize_trim_seo_slug,
    parse_khodro45_api_urgent_prices,
    parse_khodro45_prices,
)
from src.infrastructure.config import Settings


class Khodro45PricingAdapter(MarketPricingPort):
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
    ):
        self._settings = settings
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _map_color(self, pricing_config: dict[str, Any], color: str | None) -> str:
        default = pricing_config.get("default_color", "Black")
        if not color:
            return default
        color_map = pricing_config.get("color_map") or {}
        if color in color_map:
            return color_map[color]
        defaults = {
            "سفید": "White",
            "مشکی": "Black",
            "قرمز": "Red",
            "نقره‌ای": "Silver",
            "نوک مدادی": "Gray",
            "تیتانیوم": "Others",
        }
        return defaults.get(color.strip(), default)

    def _carprice_slug(self, slug: str) -> str:
        """Public carprice URLs require the cpe- prefix when configured that way."""
        trimmed = slug.strip()
        if trimmed.startswith("cpe-"):
            return trimmed
        if trimmed.startswith("peugeot-") or trimmed.startswith("iran-"):
            return f"cpe-{trimmed}"
        return trimmed

    def build_price_url(
        self,
        slug: str,
        production_year: int,
        kilometer: int,
        color_id: str,
    ) -> str:
        base = self._settings.khodro45_base_url.rstrip("/")
        carprice_slug = self._carprice_slug(slug)
        return (
            f"{base}/carprice/{carprice_slug}/"
            f"?year={production_year}&color_id={color_id}&kilometer={kilometer}"
        )

    async def get_market_price(
        self,
        pricing_config: dict[str, Any],
        production_year: int,
        kilometer: int,
        color: str | None = None,
        body_condition: str | None = None,
    ) -> MarketReferencePrice:
        slug = pricing_config.get("slug") or pricing_config.get("model_slug")
        if not slug:
            raise ExternalServiceError("Khodro45 mapping missing slug")

        color_id = self._map_color(pricing_config, color)
        km = max(kilometer, 0)
        reference_url = self.build_price_url(slug, production_year, km, color_id)
        client = await self._get_client()
        api_base = self._settings.khodro45_base_url.rstrip("/") + "/api/"
        api_params = {
            "slug": color_id,
            "trim_seo_slug": normalize_trim_seo_slug(slug),
            "year_title": str(production_year),
            "kilometer": str(km),
        }
        response = await client.get(
            api_base + KHODRO45_PRICE_API_PATH,
            params=api_params,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if response.status_code == 200:
            try:
                data = response.json()
                if not data.get("k45_price"):
                    raise ExternalServiceError(
                        f"Khodro45 has no urgent-sale price for year {production_year}"
                    )
                price_up, price_mid, price_down = parse_khodro45_api_urgent_prices(data)
            except ValueError as exc:
                raise ExternalServiceError(str(exc)) from exc
        else:
            page_response = await client.get(
                reference_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "fa-IR,fa;q=0.9",
                },
            )
            if page_response.status_code != 200:
                raise ExternalServiceError(
                    f"Khodro45 pricing failed: API {response.status_code}, "
                    f"page {page_response.status_code}"
                )
            try:
                price_up, price_mid, price_down = parse_khodro45_prices(page_response.text)
            except ValueError as exc:
                raise ExternalServiceError(str(exc)) from exc

        return MarketReferencePrice(
            price_up=price_up,
            price_down=price_down,
            price_mid=price_mid,
            reference_url=reference_url,
            provider="khodro45",
            brand=pricing_config.get("brand", slug),
            model=slug,
            year=production_year,
            type_id=slug,
        )

    async def close(self) -> None:
        if self._owns_client and self._client:
            await self._client.aclose()
            self._client = None
