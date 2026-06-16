from abc import ABC, abstractmethod

from src.domain.value_objects.sms import SmsPayload

from src.domain.entities.crawl_target import VehicleContext
from src.domain.value_objects.divar_listing import DivarListingCard, DivarListingDetail, DivarSearchPage
from src.domain.value_objects.market_reference import MarketReferencePrice


class DivarListingPort(ABC):
    @abstractmethod
    async def fetch_search_page(
        self,
        listing_url: str,
        last_post_date_epoch: int | None = None,
    ) -> DivarSearchPage: ...

    @abstractmethod
    async def fetch_listing_detail(self, token: str) -> DivarListingDetail: ...

    @abstractmethod
    def build_listing_url(self, token: str) -> str: ...

    @abstractmethod
    async def fetch_all_pages(
        self,
        listing_url: str,
        max_pages: int = 5,
    ) -> list[DivarListingCard]: ...

    @abstractmethod
    async def fetch_finder_posts(
        self,
        *,
        brand_model: str,
        city: str,
        category: str = "light",
        production_year_min: int | None = None,
        production_year_max: int | None = None,
        usage_min: int | None = None,
        usage_max: int | None = None,
        max_results: int = 150,
    ) -> list[DivarListingCard]: ...


class MarketPricingPort(ABC):
    @abstractmethod
    async def get_market_price(
        self,
        pricing_config: dict,
        production_year: int,
        kilometer: int,
        color: str | None = None,
        body_condition: str | None = None,
    ) -> MarketReferencePrice: ...


class HamrahMechanicPricingPort(ABC):
    @abstractmethod
    async def get_market_price(
        self,
        vehicle_context: VehicleContext,
        production_year: int,
        kilometer: int,
        color: str | None = None,
        body_condition: str | None = None,
    ) -> MarketReferencePrice: ...

    @abstractmethod
    async def refresh_build_id(self) -> str: ...


class NotificationPort(ABC):
    @abstractmethod
    async def send_sms(self, phone: str, payload: SmsPayload) -> str: ...

    async def send_opportunity_sms(self, phone: str, message: str) -> str:
        return await self.send_sms(phone, SmsPayload(mode="text", text=message))
