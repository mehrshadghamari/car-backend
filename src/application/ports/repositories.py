from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities.crawl_run import CrawlRun
from src.domain.entities.crawl_target import CrawlTarget
from src.domain.entities.delivery import GatewayClick, OpportunityDelivery
from src.domain.entities.listing import Listing
from src.domain.entities.market_price import MarketPrice
from src.domain.entities.opportunity import Opportunity
from src.domain.entities.purchase_request import PurchaseRequest
from src.domain.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    async def save(self, user: User) -> User: ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def get_by_phone(self, phone: str) -> User | None: ...

    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> list[User]: ...

    @abstractmethod
    async def delete(self, user_id: UUID) -> bool: ...


class CrawlTargetRepository(ABC):
    @abstractmethod
    async def save(self, target: CrawlTarget) -> CrawlTarget: ...

    @abstractmethod
    async def get_by_id(self, target_id: UUID) -> CrawlTarget | None: ...

    @abstractmethod
    async def list_all(self, active_only: bool = False) -> list[CrawlTarget]: ...

    @abstractmethod
    async def get_shared_pool(
        self,
        listing_mapping_id: UUID,
        city: str,
        source: str,
        pool_production_year: int | None = None,
    ) -> CrawlTarget | None: ...

    @abstractmethod
    async def deactivate_duplicate_shared_pools(
        self,
        listing_mapping_id: UUID,
        city: str,
        source: str,
        keep_id: UUID,
        pool_production_year: int | None = None,
    ) -> int: ...

    @abstractmethod
    async def list_active_shared_pools(self) -> list[CrawlTarget]: ...

    @abstractmethod
    async def delete(self, target_id: UUID) -> bool: ...


class PurchaseRequestRepository(ABC):
    @abstractmethod
    async def save(self, request: PurchaseRequest) -> PurchaseRequest: ...

    @abstractmethod
    async def get_by_id(self, request_id: UUID) -> PurchaseRequest | None: ...

    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[PurchaseRequest]: ...

    @abstractmethod
    async def list_active_by_crawl_target(self, crawl_target_id: UUID) -> list[PurchaseRequest]: ...

    @abstractmethod
    async def list_active_non_expired(self) -> list[PurchaseRequest]: ...

    @abstractmethod
    async def list_active_trim_ids(self) -> set[UUID]: ...

    @abstractmethod
    async def deactivate_older_than(self, cutoff: datetime) -> int: ...


class ListingRepository(ABC):
    @abstractmethod
    async def get_by_id(self, listing_id: UUID) -> Listing | None: ...

    @abstractmethod
    async def get_by_token(self, external_token: str) -> Listing | None: ...

    @abstractmethod
    async def save(self, listing: Listing) -> Listing: ...

    @abstractmethod
    async def upsert(self, listing: Listing) -> tuple[Listing, bool]: ...

    @abstractmethod
    async def list_by_crawl_target(
        self, crawl_target_id: UUID, *, active_only: bool = False
    ) -> list[Listing]: ...

    @abstractmethod
    async def deactivate_stale(self, cutoff: datetime) -> int: ...

    @abstractmethod
    async def bulk_purge_inactive(self) -> dict[str, int]: ...


class MarketPriceRepository(ABC):
    @abstractmethod
    async def save(self, market_price: MarketPrice) -> MarketPrice: ...

    @abstractmethod
    async def get_latest_for_listing(self, listing_id: UUID) -> MarketPrice | None: ...

    @abstractmethod
    async def get_latest_for_listing_and_trim(
        self, listing_id: UUID, trim_id: UUID
    ) -> MarketPrice | None: ...

    @abstractmethod
    async def get_fresh_for_trim(
        self, trim_id: UUID, pricing_provider: str, ttl_hours: int
    ) -> MarketPrice | None: ...

    @abstractmethod
    async def get_fresh_for_trim_at_specs(
        self,
        trim_id: UUID,
        production_year: int,
        kilometer: int,
        pricing_provider: str,
        ttl_hours: int,
    ) -> MarketPrice | None: ...


class OpportunityRepository(ABC):
    @abstractmethod
    async def save(self, opportunity: Opportunity) -> Opportunity: ...

    @abstractmethod
    async def get_by_id(self, opportunity_id: UUID) -> Opportunity | None: ...

    @abstractmethod
    async def get_by_listing(self, listing_id: UUID) -> Opportunity | None: ...

    @abstractmethod
    async def get_by_listing_and_basis(self, listing_id: UUID, price_basis: str) -> Opportunity | None: ...

    @abstractmethod
    async def get_by_listing_and_purchase(
        self, listing_id: UUID, purchase_request_id: UUID
    ) -> Opportunity | None: ...

    @abstractmethod
    async def list_by_listing(self, listing_id: UUID) -> list[Opportunity]: ...

    @abstractmethod
    async def list_by_purchase_request(
        self, purchase_request_id: UUID, status: str | None = None
    ) -> list[Opportunity]: ...

    @abstractmethod
    async def list_all(
        self,
        crawl_target_id: UUID | None = None,
        purchase_request_id: UUID | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Opportunity]: ...


class CrawlRunRepository(ABC):
    @abstractmethod
    async def save(self, crawl_run: CrawlRun) -> CrawlRun: ...

    @abstractmethod
    async def recover_stale_runs(self, max_age_minutes: int = 15) -> int: ...

    @abstractmethod
    async def count_by_status(self, status: str) -> int: ...

    @abstractmethod
    async def list_by_target(self, crawl_target_id: UUID, limit: int = 20) -> list[CrawlRun]: ...

    @abstractmethod
    async def get_latest_for_target(self, crawl_target_id: UUID) -> CrawlRun | None: ...


class DeliveryRepository(ABC):
    @abstractmethod
    async def save(self, delivery: OpportunityDelivery) -> OpportunityDelivery: ...

    @abstractmethod
    async def get_by_gateway_token(self, token: str) -> OpportunityDelivery | None: ...

    @abstractmethod
    async def exists_for_user_and_token(self, user_id: UUID, external_token: str) -> bool: ...

    @abstractmethod
    async def save_click(self, click: GatewayClick) -> GatewayClick: ...

    @abstractmethod
    async def count_deliveries(self, since: datetime | None = None) -> int: ...

    @abstractmethod
    async def count_clicks(self, since: datetime | None = None) -> int: ...

    @abstractmethod
    async def save_page_view(
        self,
        delivery_id: UUID,
        ip_address: str,
        is_unique_view: bool,
        viewed_at: datetime,
        view_id: UUID,
    ) -> None: ...

    @abstractmethod
    async def has_page_view_from_ip(self, delivery_id: UUID, ip_address: str) -> bool: ...

    @abstractmethod
    async def count_page_views(self, delivery_id: UUID) -> tuple[int, int]: ...
