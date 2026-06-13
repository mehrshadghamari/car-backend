import json
import re

import httpx
import redis.asyncio as aioredis

from src.application.ports.external import HamrahMechanicPricingPort
from src.domain.entities.crawl_target import VehicleContext
from src.domain.exceptions import ExternalServiceError
from src.domain.value_objects.market_reference import MarketReferencePrice
from src.domain.services.url_builder import build_hamrah_price_url, normalize_hamrah_base_url
from src.infrastructure.config import Settings


class HamrahMechanicPricingAdapter(HamrahMechanicPricingPort):
    BUILD_ID_CACHE_KEY = "hamrah:build_id"

    def __init__(
        self,
        settings: Settings,
        redis_client: aioredis.Redis,
        client: httpx.AsyncClient | None = None,
    ):
        self._settings = settings
        self._redis = redis_client
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _get_build_id(self) -> str:
        cached = await self._redis.get(self.BUILD_ID_CACHE_KEY)
        if cached:
            return cached.decode() if isinstance(cached, bytes) else cached
        return await self.refresh_build_id()

    async def refresh_build_id(self) -> str:
        client = await self._get_client()
        base = normalize_hamrah_base_url(self._settings.hamrah_mechanic_base_url)
        response = await client.get(f"{base}/carprice/")
        if response.status_code != 200:
            raise ExternalServiceError("Failed to fetch Hamrah Mechanic carprice page")
        match = re.search(r'"buildId":"([^"]+)"', response.text)
        if not match:
            match = re.search(r'/_next/data/([^/]+)/carprice', response.text)
        if not match:
            raise ExternalServiceError("Could not extract Hamrah Mechanic buildId")
        build_id = match.group(1)
        await self._redis.set(
            self.BUILD_ID_CACHE_KEY,
            build_id,
            ex=self._settings.hamrah_catalog_cache_ttl_sec,
        )
        return build_id

    def _map_color(self, vehicle_context: VehicleContext, color: str | None) -> str:
        if not color:
            return vehicle_context.default_color
        if vehicle_context.color_map and color in vehicle_context.color_map:
            return vehicle_context.color_map[color]
        color_lower = color.strip()
        defaults = {
            "سفید": "ColorWhite",
            "مشکی": "ColorBlack",
            "قرمز": "ColorRed",
            "نقره‌ای": "ColorSilver",
            "نوک مدادی": "ColorGray",
        }
        return defaults.get(color_lower, vehicle_context.default_color)

    def _km_bucket(self, kilometer: int) -> int:
        return round(kilometer / 1000) * 1000

    def _build_price_url(
        self,
        build_id: str,
        vehicle_context: VehicleContext,
        year: int,
        kilometer: int,
        color: str,
        body_condition: str,
    ) -> str:
        base = normalize_hamrah_base_url(self._settings.hamrah_mechanic_base_url)
        path = (
            f"/_next/data/{build_id}/carprice/"
            f"{vehicle_context.hamrah_brand}/{vehicle_context.hamrah_model}/"
            f"{year}/{vehicle_context.hamrah_type_id}.json"
        )
        from urllib.parse import urlencode

        query = urlencode(
            {
                "kilometer": kilometer,
                "clr": color,
                "bodycondition": body_condition,
            }
        )
        return f"{base}{path}?{query}"

    def _build_frontend_url(
        self,
        vehicle_context: VehicleContext,
        year: int,
        kilometer: int,
        color: str,
        body_condition: str,
    ) -> str:
        return build_hamrah_price_url(
            hamrah_brand=vehicle_context.hamrah_brand,
            hamrah_model=vehicle_context.hamrah_model,
            hamrah_type_id=vehicle_context.hamrah_type_id,
            production_year=year,
            kilometer=kilometer,
            color=color,
            body_condition=body_condition,
            base_url=self._settings.hamrah_mechanic_base_url,
        )

    async def get_market_price(
        self,
        vehicle_context: VehicleContext,
        production_year: int,
        kilometer: int,
        color: str | None = None,
        body_condition: str | None = None,
    ) -> MarketReferencePrice:
        mapped_color = self._map_color(vehicle_context, color)
        mapped_body = body_condition or vehicle_context.default_body_condition
        km = max(kilometer, 0)
        km_bucket = self._km_bucket(km)

        cache_key = (
            f"hamrah:price:{vehicle_context.hamrah_brand}:"
            f"{vehicle_context.hamrah_model}:{production_year}:"
            f"{vehicle_context.hamrah_type_id}:{km_bucket}:{mapped_color}:{mapped_body}"
        )
        cached = await self._redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            return MarketReferencePrice(**data)

        build_id = await self._get_build_id()
        url = self._build_price_url(
            build_id, vehicle_context, production_year, km, mapped_color, mapped_body
        )
        client = await self._get_client()
        response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 404:
            build_id = await self.refresh_build_id()
            url = self._build_price_url(
                build_id, vehicle_context, production_year, km, mapped_color, mapped_body
            )
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            raise ExternalServiceError(f"Hamrah price fetch failed: {response.status_code}")

        page_props = response.json().get("pageProps", {})
        price_data = page_props.get("price", {})
        if not price_data.get("priceDown"):
            raise ExternalServiceError("Hamrah Mechanic returned no price data")

        result = MarketReferencePrice(
            price_up=int(price_data["priceUp"]),
            price_down=int(price_data["priceDown"]),
            price_mid=int(price_data.get("price", price_data["priceDown"])),
            reference_url=self._build_frontend_url(
                vehicle_context, production_year, km, mapped_color, mapped_body
            ),
            provider="hamrah_mechanic",
            brand=vehicle_context.hamrah_brand,
            model=vehicle_context.hamrah_model,
            year=production_year,
            type_id=vehicle_context.hamrah_type_id,
        )
        await self._redis.set(
            cache_key,
            json.dumps(result.__dict__),
            ex=self._settings.hamrah_price_cache_ttl_sec,
        )
        return result

    async def close(self) -> None:
        if self._owns_client and self._client:
            await self._client.aclose()
            self._client = None
