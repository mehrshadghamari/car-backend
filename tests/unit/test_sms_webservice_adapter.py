from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.domain.value_objects.sms import SmsPayload
from src.infrastructure.adapters.sms.provider_config import SmsProviderCredentials
from src.infrastructure.adapters.sms.sms_webservice_adapter import SmsWebServiceAdapter


def _mock_response(text: str, status_code: int = 200) -> httpx.Response:
    request = httpx.Request("GET", "https://api.sms-webservice.com/api/V3/Send")
    return httpx.Response(status_code, text=text, request=request)


@pytest.mark.asyncio
async def test_sms_webservice_send_text_without_sender():
    credentials = SmsProviderCredentials(
        driver="sms_webservice",
        slug="sms_webservice",
        config={"api_key": "key123", "sender": "", "base_url": "https://api.sms-webservice.com/api/V3"},
    )
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=_mock_response('{"id":"99"}'))
    adapter = SmsWebServiceAdapter(credentials, client=client)
    provider_id = await adapter.send_sms("09121234567", SmsPayload(mode="text", text="سلام"))
    assert provider_id
    called_url = str(client.get.await_args.args[0])
    assert "Send?" in called_url
    assert "Sender=" not in called_url
    assert "ApiKey=key123" in called_url


@pytest.mark.asyncio
async def test_sms_webservice_send_pattern():
    credentials = SmsProviderCredentials(
        driver="sms_webservice",
        slug="sms_webservice",
        config={"api_key": "key123", "base_url": "https://api.sms-webservice.com/api/V3"},
    )
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=_mock_response('{"id":"pattern-1"}'))
    adapter = SmsWebServiceAdapter(credentials, client=client)
    provider_id = await adapter.send_sms(
        "09121234567",
        SmsPayload(
            mode="pattern",
            pattern_id="tpl-1",
            pattern_slots=("۳۰ میلیون تومان", "پژو ۲۰۷", "car-alert.ir/g/x"),
        ),
    )
    assert "pattern" in provider_id
    called_url = str(client.get.await_args.args[0])
    assert "SendTokenSingle?" in called_url
    assert "TemplateKey=tpl-1" in called_url
    assert "p1=" in called_url
    assert "p3=" in called_url
