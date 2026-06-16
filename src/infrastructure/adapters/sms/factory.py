import httpx

from src.application.ports.external import NotificationPort
from src.domain.constants.sms_actions import SmsProviderDriver
from src.infrastructure.adapters.sms.dry_run_adapter import DryRunSmsAdapter
from src.infrastructure.adapters.sms.provider_config import SmsProviderCredentials
from src.infrastructure.adapters.sms.sms_ir_adapter import SmsIrAdapter
from src.infrastructure.adapters.sms.sms_webservice_adapter import SmsWebServiceAdapter


def create_sms_adapter(
    credentials: SmsProviderCredentials,
    client: httpx.AsyncClient | None = None,
) -> NotificationPort:
    driver = (credentials.driver or SmsProviderDriver.DRY_RUN).strip().lower()
    if driver == SmsProviderDriver.SMS_IR:
        return SmsIrAdapter(credentials, client)
    if driver in (SmsProviderDriver.SMS_WEBSERVICE, "sms-webservice", "sms_web_service"):
        return SmsWebServiceAdapter(credentials, client)
    return DryRunSmsAdapter(credentials, client)
