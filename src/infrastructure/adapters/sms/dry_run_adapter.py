import httpx

from src.domain.exceptions import ExternalServiceError
from src.domain.value_objects.sms import SmsPayload
from src.infrastructure.adapters.sms.base import BaseSmsAdapter
from src.infrastructure.adapters.sms.provider_config import SmsProviderCredentials


class DryRunSmsAdapter(BaseSmsAdapter):
    def __init__(self, credentials: SmsProviderCredentials, client: httpx.AsyncClient | None = None):
        super().__init__(credentials, client)

    async def send_sms(self, phone: str, payload: SmsPayload) -> str:
        return self._dry_run_id(phone)

    async def send_opportunity_sms(self, phone: str, message: str) -> str:
        return await self.send_sms(phone, SmsPayload(mode="text", text=message))
