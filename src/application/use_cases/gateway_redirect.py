from dataclasses import dataclass
from src.domain.compat import as_utc, utc_now
from uuid import uuid4

from src.application.ports.repositories import DeliveryRepository, ListingRepository, OpportunityRepository
from src.domain.entities.delivery import GatewayClick
from src.domain.exceptions import EntityNotFoundError


@dataclass
class GatewayRedirectResult:
    redirect_url: str
    delivery_id: str


class GatewayRedirectUseCase:
    def __init__(
        self,
        delivery_repo: DeliveryRepository,
        opportunity_repo: OpportunityRepository,
        listing_repo: ListingRepository,
    ):
        self._delivery_repo = delivery_repo
        self._opportunity_repo = opportunity_repo
        self._listing_repo = listing_repo

    async def execute(self, gateway_token: str) -> GatewayRedirectResult:
        delivery = await self._delivery_repo.get_by_gateway_token(gateway_token)
        if not delivery:
            raise EntityNotFoundError(f"Gateway token not found: {gateway_token}")

        opportunity = await self._opportunity_repo.get_by_id(delivery.opportunity_id)
        if not opportunity:
            raise EntityNotFoundError("Opportunity not found for delivery")

        listing = await self._listing_repo.get_by_id(opportunity.listing_id)
        if not listing:
            raise EntityNotFoundError("Listing not found for opportunity")

        clicked_at = utc_now()
        time_to_click = None
        if delivery.sms_sent_at:
            time_to_click = int((clicked_at - as_utc(delivery.sms_sent_at)).total_seconds())

        await self._delivery_repo.save_click(
            GatewayClick(
                id=uuid4(),
                delivery_id=delivery.id,
                clicked_at=clicked_at,
                time_to_click_sec=time_to_click,
            )
        )

        return GatewayRedirectResult(
            redirect_url=listing.divar_url,
            delivery_id=str(delivery.id),
        )
