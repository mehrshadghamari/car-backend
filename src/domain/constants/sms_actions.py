from src.domain.compat import StrEnum


class SmsAction(StrEnum):
    """Application SMS actions — each maps to one row in sms_templates."""

    GATEWAY_LINK = "gateway_link"
    OTP_CODE = "otp_code"
    PORTAL_LINK = "portal_link"


class SmsSendMode(StrEnum):
    TEXT = "text"
    PATTERN = "pattern"


class SmsProviderDriver(StrEnum):
    DRY_RUN = "dry_run"
    SMS_IR = "sms_ir"
    SMS_WEBSERVICE = "sms_webservice"
