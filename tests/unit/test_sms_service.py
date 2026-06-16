import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.sms_service import SmsService
from src.domain.constants.sms_actions import SmsAction
from src.domain.entities.sms_config import SmsProvider, SmsTemplate
from src.infrastructure.config import Settings


@pytest.mark.asyncio
async def test_sms_service_send_gateway_link():
    provider = SmsProvider(
        id=uuid.uuid4(),
        slug="dry_run",
        name="Dry run",
        driver="dry_run",
        is_active=True,
        config={},
    )
    template = SmsTemplate(
        id=uuid.uuid4(),
        action=SmsAction.GATEWAY_LINK,
        name="Gateway",
        send_mode="text",
        text_body="{discount_label} {gateway_url}",
        pattern_key=None,
        pattern_slots=None,
        pattern_params=None,
        provider_id=provider.id,
        is_active=True,
        provider=provider,
    )
    repo = MagicMock()
    repo.get_active_template_by_action = AsyncMock(return_value=template)
    repo.get_provider_by_id = AsyncMock(return_value=provider)

    service = SmsService(repo, Settings())
    result = await service.send(
        SmsAction.GATEWAY_LINK,
        "09121234567",
        {"discount_label": "۳۰ میلیون تومان", "gateway_url": "car-alert.ir/g/abc"},
    )
    assert result.startswith("dry-run-")
