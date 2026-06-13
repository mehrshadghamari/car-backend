from dataclasses import dataclass
from src.domain.compat import utc_now
from uuid import uuid4

from src.application.ports.repositories import DeliveryRepository, ListingRepository, OpportunityRepository
from src.domain.exceptions import EntityNotFoundError


@dataclass
class GatewayPreviewResult:
    delivery_id: str
    title: str
    listing_price: int
    market_price_down: int
    market_price_up: int
    discount_pct: float
    production_year: int | None
    kilometer: int | None
    district: str | None
    redirect_path: str
    total_views: int
    unique_views: int
    is_unique_view: bool


class GatewayPreviewUseCase:
    def __init__(
        self,
        delivery_repo: DeliveryRepository,
        opportunity_repo: OpportunityRepository,
        listing_repo: ListingRepository,
    ):
        self._delivery_repo = delivery_repo
        self._opportunity_repo = opportunity_repo
        self._listing_repo = listing_repo

    async def execute(self, gateway_token: str, client_ip: str) -> GatewayPreviewResult:
        delivery = await self._delivery_repo.get_by_gateway_token(gateway_token)
        if not delivery:
            raise EntityNotFoundError(f"Gateway token not found: {gateway_token}")

        opportunity = await self._opportunity_repo.get_by_id(delivery.opportunity_id)
        if not opportunity:
            raise EntityNotFoundError("Opportunity not found for delivery")

        listing = await self._listing_repo.get_by_id(opportunity.listing_id)
        if not listing:
            raise EntityNotFoundError("Listing not found for opportunity")

        is_unique = not await self._delivery_repo.has_page_view_from_ip(delivery.id, client_ip)
        await self._delivery_repo.save_page_view(
            delivery_id=delivery.id,
            ip_address=client_ip,
            is_unique_view=is_unique,
            viewed_at=utc_now(),
            view_id=uuid4(),
        )
        total_views, unique_views = await self._delivery_repo.count_page_views(delivery.id)

        return GatewayPreviewResult(
            delivery_id=str(delivery.id),
            title=listing.title,
            listing_price=opportunity.listing_price,
            market_price_down=opportunity.market_price_down,
            market_price_up=opportunity.market_price_up,
            discount_pct=float(opportunity.discount_pct),
            production_year=listing.production_year,
            kilometer=listing.kilometer,
            district=listing.district,
            redirect_path=f"/g/{gateway_token}/go",
            total_views=total_views,
            unique_views=unique_views,
            is_unique_view=is_unique,
        )
