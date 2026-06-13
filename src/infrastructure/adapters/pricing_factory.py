from typing import Any

import redis.asyncio as aioredis

from src.application.ports.external import MarketPricingPort
from src.domain.entities.crawl_target import VehicleContext
from src.domain.exceptions import ValidationError
from src.domain.value_objects.market_reference import MarketReferencePrice
from src.infrastructure.adapters.hamrah_mechanic.hamrah_adapter import HamrahMechanicPricingAdapter
from src.infrastructure.adapters.khodro45.khodro45_adapter import Khodro45PricingAdapter
from src.infrastructure.config import Settings


class HamrahConfigPricingAdapter(MarketPricingPort):
    """Wraps Hamrah adapter to satisfy MarketPricingPort with config dict."""

    def __init__(self, hamrah: HamrahMechanicPricingAdapter):
        self._hamrah = hamrah

    async def get_market_price(
        self,
        pricing_config: dict[str, Any],
        production_year: int,
        kilometer: int,
        color: str | None = None,
        body_condition: str | None = None,
    ) -> MarketReferencePrice:
        vehicle_context = VehicleContext(
            hamrah_brand=pricing_config["brand"],
            hamrah_model=pricing_config["model"],
            hamrah_type_id=str(pricing_config["type_id"]),
            default_color=pricing_config.get("default_color", "ColorWhite"),
            default_body_condition=pricing_config.get("default_body_condition", "WithoutColor"),
            color_map=pricing_config.get("color_map"),
        )
        result = await self._hamrah.get_market_price(
            vehicle_context=vehicle_context,
            production_year=production_year,
            kilometer=kilometer,
            color=color,
            body_condition=body_condition,
        )
        return MarketReferencePrice(
            price_up=result.price_up,
            price_down=result.price_down,
            price_mid=result.price_mid,
            reference_url=result.reference_url,
            provider="hamrah_mechanic",
            brand=result.brand,
            model=result.model,
            year=result.year,
            type_id=result.type_id,
        )

    async def close(self) -> None:
        await self._hamrah.close()


class PricingServiceFactory:
    def __init__(self, settings: Settings, redis_client: aioredis.Redis):
        self._settings = settings
        self._redis = redis_client
        self._hamrah = HamrahMechanicPricingAdapter(settings, redis_client)
        self._khodro45 = Khodro45PricingAdapter(settings)
        self._hamrah_config = HamrahConfigPricingAdapter(self._hamrah)

    def get(self, slug: str) -> MarketPricingPort:
        if slug == "hamrah_mechanic":
            return self._hamrah_config
        if slug == "khodro45":
            return self._khodro45
        raise ValidationError(f"Unknown pricing platform: {slug}")

    async def close(self) -> None:
        await self._hamrah.close()
        await self._khodro45.close()
