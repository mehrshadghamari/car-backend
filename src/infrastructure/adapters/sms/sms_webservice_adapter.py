from urllib.parse import urlencode

import httpx

from src.domain.exceptions import ExternalServiceError
from src.domain.value_objects.sms import SmsPayload
from src.infrastructure.adapters.sms.base import BaseSmsAdapter
from src.infrastructure.adapters.sms.provider_config import SmsProviderCredentials


class SmsWebServiceAdapter(BaseSmsAdapter):
    """Async client for https://api.sms-webservice.com/api/V3 (text + pattern)."""

    def __init__(self, credentials: SmsProviderCredentials, client: httpx.AsyncClient | None = None):
        super().__init__(credentials, client)

    def _base_url(self) -> str:
        base = self._credentials.get("base_url", "https://api.sms-webservice.com/api/V3")
        return base.rstrip("/") + "/"

    async def send_sms(self, phone: str, payload: SmsPayload) -> str:
        if not self._credentials.api_key:
            return self._dry_run_id(phone)

        client = await self._get_client()
        if payload.mode == "pattern":
            return await self._send_pattern(client, phone, payload)
        return await self._send_text(client, phone, payload)

    async def _send_text(self, client: httpx.AsyncClient, phone: str, payload: SmsPayload) -> str:
        text = payload.text or ""
        params: dict[str, str] = {
            "ApiKey": self._credentials.api_key,
            "Text": text,
            "Recipients": phone,
        }
        sender = self._credentials.get("sender").strip()
        if sender:
            params["Sender"] = sender

        url = f"{self._base_url()}Send?{urlencode(params)}"
        response = await client.get(url)
        if response.status_code not in (200, 201):
            raise ExternalServiceError(
                f"SMS WebService text send failed: {response.status_code} {response.text}"
            )
        return self._extract_provider_id(response)

    async def _send_pattern(
        self,
        client: httpx.AsyncClient,
        phone: str,
        payload: SmsPayload,
    ) -> str:
        template_key = payload.pattern_id or self._credentials.get("pattern_template_key")
        if not template_key:
            raise ExternalServiceError(
                "SMS WebService pattern mode requires pattern_key on template or pattern_template_key in provider config"
            )

        slots = list(payload.pattern_slots or ())
        params: dict[str, str] = {
            "ApiKey": self._credentials.api_key,
            "TemplateKey": template_key,
            "Destination": phone,
        }
        for index, value in enumerate(slots[:3], start=1):
            params[f"p{index}"] = value

        url = f"{self._base_url()}SendTokenSingle?{urlencode(params)}"
        response = await client.get(url)
        if response.status_code not in (200, 201):
            raise ExternalServiceError(
                f"SMS WebService pattern send failed: {response.status_code} {response.text}"
            )
        return self._extract_provider_id(response)

    @staticmethod
    def _extract_provider_id(response: httpx.Response) -> str:
        text = (response.text or "").strip()
        return text[:120] if text else "sent"

    async def send_opportunity_sms(self, phone: str, message: str) -> str:
        return await self.send_sms(phone, SmsPayload(mode="text", text=message))
