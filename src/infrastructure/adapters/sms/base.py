import httpx

from src.application.ports.external import NotificationPort
from src.infrastructure.adapters.sms.provider_config import SmsProviderCredentials


class BaseSmsAdapter(NotificationPort):
    def __init__(self, credentials: SmsProviderCredentials, client: httpx.AsyncClient | None = None):
        self._credentials = credentials
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _dry_run_id(self, phone: str) -> str:
        return f"dry-run-{phone}"

    async def close(self) -> None:
        if self._owns_client and self._client:
            await self._client.aclose()
            self._client = None
