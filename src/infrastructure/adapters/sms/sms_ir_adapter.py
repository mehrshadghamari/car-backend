import httpx

from src.domain.exceptions import ExternalServiceError
from src.domain.value_objects.sms import SmsPayload
from src.infrastructure.adapters.sms.base import BaseSmsAdapter
from src.infrastructure.adapters.sms.provider_config import SmsProviderCredentials


class SmsIrAdapter(BaseSmsAdapter):
    def __init__(self, credentials: SmsProviderCredentials, client: httpx.AsyncClient | None = None):
        super().__init__(credentials, client)

    async def send_sms(self, phone: str, payload: SmsPayload) -> str:
        if not self._credentials.api_key:
            return self._dry_run_id(phone)

        client = await self._get_client()
        headers = {
            "X-API-KEY": self._credentials.api_key,
            "Content-Type": "application/json",
        }
        base_url = self._credentials.get("base_url", "https://api.sms.ir/v1").rstrip("/")

        if payload.mode == "pattern":
            template_id = payload.pattern_id or self._credentials.get("template_id")
            if not template_id:
                raise ExternalServiceError("SMS.ir pattern mode requires template_id in provider config or template")
            parameters = [
                {"name": name, "value": value}
                for name, value in (payload.pattern_params or {}).items()
            ]
            if not parameters and payload.text:
                parameters = [{"name": "message", "value": payload.text}]
            body = {
                "mobile": phone,
                "templateId": int(template_id),
                "parameters": parameters,
            }
            url = f"{base_url}/send/verify"
            response = await client.post(url, json=body, headers=headers)
        else:
            text = payload.text or ""
            body = {
                "lineNumber": self._credentials.get("line_number"),
                "messageText": text,
                "mobiles": [phone],
            }
            url = f"{base_url}/send/bulk"
            response = await client.post(url, json=body, headers=headers)

        if response.status_code not in (200, 201):
            raise ExternalServiceError(f"SMS.ir send failed: {response.status_code} {response.text}")

        data = response.json()
        return str(data.get("data", {}).get("messageId", data.get("status", "sent")))

    async def send_opportunity_sms(self, phone: str, message: str) -> str:
        return await self.send_sms(phone, SmsPayload(mode="text", text=message))
