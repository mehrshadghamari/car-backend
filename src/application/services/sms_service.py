import logging

import httpx

from src.application.ports.sms_config_repository import SmsConfigRepository
from src.domain.constants.sms_actions import SmsAction
from src.domain.exceptions import ValidationError
from src.domain.services.sms_template_renderer import build_sms_payload
from src.infrastructure.adapters.sms.factory import create_sms_adapter
from src.infrastructure.adapters.sms.provider_config import SmsProviderCredentials
from src.infrastructure.config import Settings

logger = logging.getLogger(__name__)


class SmsService:
    """Send SMS by action enum — template + provider loaded from database."""

    def __init__(
        self,
        config_repo: SmsConfigRepository,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
    ):
        self._config_repo = config_repo
        self._settings = settings
        self._client = client

    async def send(self, action: SmsAction | str, phone: str, params: dict[str, str]) -> str:
        action_key = str(action)
        template = await self._config_repo.get_active_template_by_action(action_key)
        if not template or not template.is_active:
            raise ValidationError(f"قالب پیامک برای عملیات «{action_key}» فعال نیست")

        provider = template.provider
        if not provider:
            provider = await self._config_repo.get_provider_by_id(template.provider_id)
        if not provider or not provider.is_active:
            raise ValidationError("ارائه‌دهنده پیامک این قالب غیرفعال است")

        template.provider = provider
        payload = build_sms_payload(template, params)
        credentials = SmsProviderCredentials(
            driver=provider.driver,
            slug=provider.slug,
            config=provider.config or {},
        )
        adapter = create_sms_adapter(credentials, self._client)
        try:
            return await adapter.send_sms(phone, payload)
        except Exception as exc:
            logger.warning("SMS send failed action=%s provider=%s: %s", action_key, provider.slug, exc)
            raise
