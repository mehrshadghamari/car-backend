from dataclasses import dataclass
from uuid import UUID


@dataclass
class SmsProvider:
    id: UUID
    slug: str
    name: str
    driver: str
    is_active: bool
    config: dict


@dataclass
class SmsTemplate:
    id: UUID
    action: str
    name: str
    send_mode: str
    text_body: str | None
    pattern_key: str | None
    pattern_slots: list[str] | None
    pattern_params: list[str] | None
    provider_id: UUID
    is_active: bool
    provider: SmsProvider | None = None
