import httpx

from src.application.ports.external import NotificationPort
from src.domain.exceptions import ExternalServiceError
from src.infrastructure.config import Settings


class SmsIrAdapter(NotificationPort):
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self._settings = settings
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def send_opportunity_sms(self, phone: str, message: str) -> str:
        if not self._settings.sms_ir_api_key:
            return f"dry-run-{phone}"

        client = await self._get_client()
        headers = {
            "X-API-KEY": self._settings.sms_ir_api_key,
            "Content-Type": "application/json",
        }

        if self._settings.sms_ir_template_id:
            payload = {
                "mobile": phone,
                "templateId": int(self._settings.sms_ir_template_id),
                "parameters": [{"name": "message", "value": message}],
            }
            url = f"{self._settings.sms_ir_base_url}/send/verify"
        else:
            payload = {
                "lineNumber": self._settings.sms_ir_line_number,
                "messageText": message,
                "mobiles": [phone],
            }
            url = f"{self._settings.sms_ir_base_url}/send/bulk"

        response = await client.post(url, json=payload, headers=headers)
        if response.status_code not in (200, 201):
            raise ExternalServiceError(f"SMS.ir send failed: {response.status_code} {response.text}")

        data = response.json()
        return str(data.get("data", {}).get("messageId", data.get("status", "sent")))

    async def close(self) -> None:
        if self._owns_client and self._client:
            await self._client.aclose()
            self._client = None
