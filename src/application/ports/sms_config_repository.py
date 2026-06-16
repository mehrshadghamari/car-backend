from abc import ABC, abstractmethod

from src.domain.entities.sms_config import SmsProvider, SmsTemplate


class SmsConfigRepository(ABC):
    @abstractmethod
    async def get_active_template_by_action(self, action: str) -> SmsTemplate | None: ...

    @abstractmethod
    async def get_provider_by_id(self, provider_id) -> SmsProvider | None: ...
