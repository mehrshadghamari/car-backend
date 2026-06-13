import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta
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
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.infrastructure.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class SendOpportunitySmsInput:
    purchase_request_id: UUID
    opportunity_ids: list[UUID]
    mode: str  # "gateway" | "portal"


@dataclass
class SendOpportunitySmsResult:
    sms_sent: int
    deliveries_created: int
    share_token: str | None = None
    share_url: str | None = None


class SendOpportunitySmsUseCase:
    def __init__(
        self,
        opportunity_repo: OpportunityRepository,
        purchase_request_repo: PurchaseRequestRepository,
        user_repo: UserRepository,
        listing_repo: ListingRepository,
        delivery_repo: DeliveryRepository,
        notification_port: NotificationPort,
        settings: Settings,
        share_batch_repo=None,
    ):
        self._opportunity_repo = opportunity_repo
        self._purchase_request_repo = purchase_request_repo
        self._user_repo = user_repo
        self._listing_repo = listing_repo
        self._delivery_repo = delivery_repo
        self._notification_port = notification_port
        self._settings = settings
        self._share_batch_repo = share_batch_repo

    async def execute(self, input_dto: SendOpportunitySmsInput) -> SendOpportunitySmsResult:
        if not input_dto.opportunity_ids:
            raise ValidationError("حداقل یک فرصت را انتخاب کنید")
        if input_dto.mode not in ("gateway", "portal"):
            raise ValidationError("mode باید gateway یا portal باشد")

        purchase = await self._purchase_request_repo.get_by_id(input_dto.purchase_request_id)
        if not purchase:
            raise EntityNotFoundError("درخواست خرید پیدا نشد")
        user = await self._user_repo.get_by_id(purchase.user_id)
        if not user or not user.phone:
            raise ValidationError("کاربر یا شماره موبایل یافت نشد")

        opportunities = []
        for opp_id in input_dto.opportunity_ids:
            opp = await self._opportunity_repo.get_by_id(opp_id)
            if not opp or opp.purchase_request_id != purchase.id:
                raise ValidationError(f"فرصت {opp_id} برای این درخواست معتبر نیست")
            if opp.status == OpportunityStatus.EXPIRED:
                raise ValidationError("فرصت منقضی‌شده قابل ارسال نیست")
            opportunities.append(opp)

        if input_dto.mode == "portal":
            return await self._send_portal_link(purchase, user, opportunities)
        return await self._send_gateway_links(purchase, user, opportunities)

    async def _send_gateway_links(self, purchase, user, opportunities) -> SendOpportunitySmsResult:
        deliveries = 0
        gateway_lines: list[str] = ["فرصت‌های خرید خودرو:"]

        for opp in opportunities:
            listing = await self._listing_repo.get_by_id(opp.listing_id)
            if not listing:
                continue
            gateway_token = secrets.token_urlsafe(16)
            gateway_url = f"{self._settings.app_host}/g/{gateway_token}"
            tag_label = DEAL_TAG_LABELS.get(opp.deal_tag, {}).get("fa", opp.deal_tag)
            gateway_lines.append(f"• [{tag_label}] {listing.title} — {gateway_url}")

            delivery = OpportunityDelivery(
                id=uuid4(),
                opportunity_id=opp.id,
                purchase_request_id=purchase.id,
                user_id=user.id,
                gateway_token=gateway_token,
                sms_status=SmsStatus.PENDING,
            )
            await self._delivery_repo.save(delivery)
            deliveries += 1
            opp.status = OpportunityStatus.NOTIFIED
            await self._opportunity_repo.save(opp)

        if len(gateway_lines) <= 1:
            raise ValidationError("آگهی معتبری برای ارسال یافت نشد")

        sent = 0
        try:
            await self._notification_port.send_opportunity_sms(user.phone, "\n".join(gateway_lines))
            sent = 1
        except Exception as exc:
            logger.warning("SMS failed: %s", exc)
            raise ValidationError(f"ارسال پیامک ناموفق: {exc}") from exc

        return SendOpportunitySmsResult(sms_sent=sent, deliveries_created=deliveries)

    async def _send_portal_link(self, purchase, user, opportunities) -> SendOpportunitySmsResult:
        if not self._share_batch_repo:
            raise ValidationError("ارسال لینک پورتال پشتیبانی نمی‌شود")

        token = secrets.token_urlsafe(16)
        expires_at = utc_now() + timedelta(hours=48)
        await self._share_batch_repo.save(
            token=token,
            purchase_request_id=purchase.id,
            user_id=user.id,
            opportunity_ids=[str(o.id) for o in opportunities],
            expires_at=expires_at,
        )
        share_url = f"{self._settings.app_host}/portal/shared-opportunities.html?token={token}"
        message = f"فرصت‌های خرید خودرو برای شما:\n{share_url}"

        sent = 0
        try:
            await self._notification_port.send_opportunity_sms(user.phone, message)
            sent = 1
        except Exception as exc:
            logger.warning("Portal SMS failed: %s", exc)
            raise ValidationError(f"ارسال پیامک ناموفق: {exc}") from exc

        for opp in opportunities:
            opp.status = OpportunityStatus.NOTIFIED
            await self._opportunity_repo.save(opp)

        return SendOpportunitySmsResult(
            sms_sent=sent,
            deliveries_created=0,
            share_token=token,
            share_url=share_url,
        )
