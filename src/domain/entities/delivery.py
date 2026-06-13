from dataclasses import dataclass
from datetime import datetime
from src.domain.compat import StrEnum
from uuid import UUID


class SmsStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


@dataclass
class OpportunityDelivery:
    id: UUID
    opportunity_id: UUID
    purchase_request_id: UUID
    user_id: UUID
    gateway_token: str
    sms_status: SmsStatus = SmsStatus.PENDING
    sms_sent_at: datetime | None = None
    sms_provider_id: str | None = None
    sms_error: str | None = None
    created_at: datetime | None = None


@dataclass
class GatewayClick:
    id: UUID
    delivery_id: UUID
    clicked_at: datetime
    time_to_click_sec: int | None = None
