from src.domain.entities.sms_config import SmsProvider, SmsTemplate
from src.domain.services.sms_template_renderer import build_sms_payload, render_text_template


def test_render_text_template():
    text = render_text_template("سلام {name}", {"name": "کاربر"})
    assert text == "سلام کاربر"


def test_build_text_payload():
    template = SmsTemplate(
        id=None,
        action="gateway_link",
        name="Gateway",
        send_mode="text",
        text_body="{discount_label} {title}",
        pattern_key=None,
        pattern_slots=None,
        pattern_params=None,
        provider_id=None,
        is_active=True,
    )
    payload = build_sms_payload(template, {"discount_label": "۳۰ میلیون", "title": "پژو ۲۰۷"})
    assert payload.mode == "text"
    assert payload.text == "۳۰ میلیون پژو ۲۰۷"


def test_build_pattern_payload_sms_webservice():
    provider = SmsProvider(
        id=None,
        slug="sms_webservice",
        name="WS",
        driver="sms_webservice",
        is_active=True,
        config={},
    )
    template = SmsTemplate(
        id=None,
        action="gateway_link",
        name="Gateway",
        send_mode="pattern",
        text_body=None,
        pattern_key="tpl-99",
        pattern_slots=["discount_label", "title", "price_and_gateway"],
        pattern_params=None,
        provider_id=None,
        is_active=True,
        provider=provider,
    )
    payload = build_sms_payload(
        template,
        {
            "discount_label": "۳۰ میلیون تومان",
            "title": "پژو ۲۰۷",
            "price_and_gateway": "car-alert.ir/g/x",
        },
    )
    assert payload.mode == "pattern"
    assert payload.pattern_id == "tpl-99"
    assert payload.pattern_slots == ("۳۰ میلیون تومان", "پژو ۲۰۷", "car-alert.ir/g/x")
