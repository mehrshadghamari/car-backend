import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from src.application.services.sms_service import SmsService
from src.application.ports.repositories import (
    DeliveryRepository,
    ListingRepository,
    OpportunityRepository,
    PurchaseRequestRepository,
    UserRepository,
)
from src.domain.compat import utc_now
from src.domain.entities.delivery import OpportunityDelivery, SmsStatus
from src.domain.constants.opportunity_visibility import STAFF_SMS_ELIGIBLE_OPPORTUNITY_STATUSES
from src.domain.entities.opportunity import OpportunityStatus
from src.domain.constants.sms_actions import SmsAction
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.domain.services.sms_param_builder import gateway_link_params, portal_link_params
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
        sms_service: SmsService,
        settings: Settings,
        share_batch_repo=None,
    ):
        self._opportunity_repo = opportunity_repo
        self._purchase_request_repo = purchase_request_repo
        self._user_repo = user_repo
        self._listing_repo = listing_repo
        self._delivery_repo = delivery_repo
        self._sms_service = sms_service
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
            if opp.status == OpportunityStatus.REJECTED:
                raise ValidationError("فرصت رد‌شده قابل ارسال نیست")
            if opp.status == OpportunityStatus.NEW:
                raise ValidationError("فرصت در وضعیت اولیه است — ابتدا توسط کارشناس تایید شود")
            if opp.status not in STAFF_SMS_ELIGIBLE_OPPORTUNITY_STATUSES:
                raise ValidationError("فقط فرصت‌های تایید‌شده قابل ارسال پیامک هستند")
            opportunities.append(opp)

        if input_dto.mode == "portal":
            return await self._send_portal_link(purchase, user, opportunities)
        return await self._send_gateway_links(purchase, user, opportunities)

    async def _send_gateway_links(self, purchase, user, opportunities) -> SendOpportunitySmsResult:
        deliveries = 0
        sent = 0
        pending: list[tuple[OpportunityDelivery, dict[str, str]]] = []

        for opp in opportunities:
            listing = await self._listing_repo.get_by_id(opp.listing_id)
            if not listing:
                continue
            gateway_token = secrets.token_urlsafe(16)
            params = gateway_link_params(opp, listing, gateway_token, self._settings.app_host)

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
            pending.append((delivery, params))
            opp.status = OpportunityStatus.NOTIFIED
            await self._opportunity_repo.save(opp)

        if not pending:
            raise ValidationError("آگهی معتبری برای ارسال یافت نشد")

        for delivery, params in pending:
            try:
                provider_id = await self._sms_service.send(SmsAction.GATEWAY_LINK, user.phone, params)
                delivery.sms_status = SmsStatus.SENT
                delivery.sms_sent_at = utc_now()
                delivery.sms_provider_id = provider_id
                sent += 1
            except Exception as exc:
                logger.warning("SMS failed for delivery %s: %s", delivery.id, exc)
                delivery.sms_status = SmsStatus.FAILED
                delivery.sms_error = str(exc)
            await self._delivery_repo.save(delivery)

        if sent == 0:
            raise ValidationError("ارسال پیامک ناموفق بود")

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
        share_url = f"{self._settings.app_host}/shared-opportunities.html?token={token}"

        sent = 0
        try:
            await self._sms_service.send(
                SmsAction.PORTAL_LINK,
                user.phone,
                portal_link_params(share_url),
            )
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
