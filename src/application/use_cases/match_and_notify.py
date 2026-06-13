import logging
import secrets
from uuid import UUID, uuid4

from src.application.ports.external import NotificationPort
from src.application.ports.repositories import (
    DeliveryRepository,
    ListingRepository,
    OpportunityRepository,
    PurchaseRequestRepository,
    UserRepository,
)
from src.domain.compat import utc_now
from src.domain.entities.delivery import OpportunityDelivery, SmsStatus
from src.domain.entities.opportunity import DEAL_TAG_LABELS, OpportunityStatus
from src.infrastructure.config import Settings

logger = logging.getLogger(__name__)


class MatchAndNotifyUseCase:
    def __init__(
        self,
        opportunity_repo: OpportunityRepository,
        purchase_request_repo: PurchaseRequestRepository,
        user_repo: UserRepository,
        listing_repo: ListingRepository,
        delivery_repo: DeliveryRepository,
        notification_port: NotificationPort,
        settings: Settings,
    ):
        self._opportunity_repo = opportunity_repo
        self._purchase_request_repo = purchase_request_repo
        self._user_repo = user_repo
        self._listing_repo = listing_repo
        self._delivery_repo = delivery_repo
        self._notification_port = notification_port
        self._settings = settings

    async def execute(self, opportunity_ids: list[str]) -> int:
        sent_count = 0
        for opp_id_str in opportunity_ids:
            opportunity = await self._opportunity_repo.get_by_id(UUID(opp_id_str))
            if not opportunity or opportunity.status != OpportunityStatus.NEW:
                continue

            if not opportunity.purchase_request_id:
                logger.warning("Opportunity %s has no purchase_request_id — skip notify", opp_id_str)
                continue

            listing = await self._listing_repo.get_by_id(opportunity.listing_id)
            if not listing:
                continue

            request = await self._purchase_request_repo.get_by_id(opportunity.purchase_request_id)
            if not request or not request.is_active:
                continue

            user = await self._user_repo.get_by_id(request.user_id)
            if not user or not user.is_active:
                continue

            already_sent = await self._delivery_repo.exists_for_user_and_token(
                user.id, listing.external_token
            )
            if already_sent:
                opportunity.status = OpportunityStatus.NOTIFIED
                await self._opportunity_repo.save(opportunity)
                continue

            gateway_token = secrets.token_urlsafe(16)
            gateway_url = f"{self._settings.app_host}/g/{gateway_token}"

            km_text = f"{listing.kilometer:,}" if listing.kilometer else "N/A"
            basis_labels = {
                "down": "کف فروش فوری",
                "mid": "قیمت میانه فروش فوری",
                "up": "سقف فروش فوری",
            }
            basis_label = basis_labels.get(opportunity.price_basis, "قیمت مرجع")
            ref_price = opportunity.reference_price or opportunity.market_price_down
            tag_label = DEAL_TAG_LABELS.get(opportunity.deal_tag, {}).get("fa", opportunity.deal_tag)
            message = (
                f"فرصت خرید خودرو [{tag_label}]\n"
                f"{listing.title}\n"
                f"سال: {listing.production_year} | کارکرد: {km_text} km\n"
                f"قیمت آگهی: {listing.price:,} تومان\n"
                f"{basis_label}: {ref_price:,} تومان\n"
                f"تخفیف: {opportunity.discount_pct}%\n"
                f"لینک: {gateway_url}"
            )

            delivery = OpportunityDelivery(
                id=uuid4(),
                opportunity_id=opportunity.id,
                purchase_request_id=request.id,
                user_id=user.id,
                gateway_token=gateway_token,
                sms_status=SmsStatus.PENDING,
            )

            try:
                provider_id = await self._notification_port.send_opportunity_sms(
                    user.phone, message
                )
                delivery.sms_status = SmsStatus.SENT
                delivery.sms_sent_at = utc_now()
                delivery.sms_provider_id = provider_id
                sent_count += 1
            except Exception as exc:
                logger.warning("SMS failed for user %s: %s", user.id, exc)
                delivery.sms_status = SmsStatus.FAILED
                delivery.sms_error = str(exc)

            await self._delivery_repo.save(delivery)

            opportunity.status = OpportunityStatus.NOTIFIED
            await self._opportunity_repo.save(opportunity)

        return sent_count
