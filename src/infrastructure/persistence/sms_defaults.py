"""Default SMS providers and templates (stable IDs for idempotent seeding)."""

from __future__ import annotations

import uuid

PROVIDER_DRY_RUN_ID = uuid.UUID("a1000001-0001-4001-8001-000000000001")
PROVIDER_SMS_IR_ID = uuid.UUID("a1000001-0001-4001-8001-000000000002")
PROVIDER_SMS_WEBSERVICE_ID = uuid.UUID("a1000001-0001-4001-8001-000000000003")

GATEWAY_TEXT_TEMPLATE = (
    "{discount_label} زیر قیمت بازار {title} قیمت : {price} تومان  "
    "مشاهده آگهی در دیوار : {gateway_url}"
)

OTP_TEXT_TEMPLATE = "کد ورود شما: {code}"
PORTAL_TEXT_TEMPLATE = "فرصت‌های خرید خودرو برای شما:\n{share_url}"

SMS_WEBSERVICE_BASE_URL = "https://api.sms-webservice.com/api/V3"
SMS_IR_BASE_URL = "https://api.sms.ir/v1"

GATEWAY_PATTERN_SLOTS = ["discount_label", "title", "price_and_gateway"]
GATEWAY_PATTERN_PARAMS = ["discount_label", "title", "price", "gateway_url"]
