from decimal import Decimal
from uuid import uuid4

from src.domain.entities.listing import Listing
from src.domain.entities.opportunity import Opportunity, OpportunityStatus
from src.domain.services.sms_message_builder import (
    build_gateway_sms_context,
    build_gateway_text_message,
    GatewaySmsComposer,
    short_gateway_url,
)
from src.domain.utils.persian_format import format_toman_discount_label
from src.infrastructure.config import Settings


def _listing(**kwargs) -> Listing:
    defaults = dict(
        id=uuid4(),
        external_token="tok",
        title="پژو ۲۰۷ پانا سفید مدل ۱۴۰۳ در حد صفر",
        price=1_850_000_000,
        production_year=1403,
        kilometer=5000,
        divar_url="https://divar.ir/v/test",
        crawl_target_id=uuid4(),
    )
    defaults.update(kwargs)
    return Listing(**defaults)


def _opportunity(**kwargs) -> Opportunity:
    defaults = dict(
        id=uuid4(),
        listing_id=uuid4(),
        crawl_target_id=uuid4(),
        listing_price=1_850_000_000,
        market_price_down=1_880_000_000,
        market_price_up=1_920_000_000,
        discount_amount=30_000_000,
        discount_pct=Decimal("1.6"),
        score=Decimal("30000000"),
        status=OpportunityStatus.APPROVED,
        is_below_floor=False,
    )
    defaults.update(kwargs)
    return Opportunity(**defaults)


def test_format_toman_discount_label_million_persian_digits():
    assert format_toman_discount_label(30_000_000) == "۳۰ میلیون تومان"


def test_short_gateway_url_strips_protocol():
    assert short_gateway_url("https://car-alert.ir", "abc") == "car-alert.ir/g/abc"


def test_gateway_text_message_matches_expected_shape():
    ctx = build_gateway_sms_context(
        _opportunity(discount_amount=30_000_000),
        _listing(),
        "ZoiMzNoAxKTwK21DBtIzjw",
        "https://car-alert.ir",
    )
    message = build_gateway_text_message(
        ctx,
        "{discount_label} زیر قیمت بازار {title} قیمت : {price} تومان  مشاهده آگهی در دیوار : {gateway_url}",
    )
    assert message.startswith("۳۰ میلیون تومان زیر قیمت بازار پژو ۲۰۷ پانا")
    assert "1,850,000,000" in message
    assert "car-alert.ir/g/ZoiMzNoAxKTwK21DBtIzjw" in message


def test_gateway_composer_text_mode():
    settings = Settings(
        sms_send_mode="text",
        app_host="https://car-alert.ir",
    )
    composer = GatewaySmsComposer(settings)
    payload = composer.build_payload(_opportunity(), _listing(), "tok123")
    assert payload.mode == "text"
    assert payload.text
    assert "car-alert.ir/g/tok123" in payload.text


def test_gateway_composer_pattern_mode_sms_webservice():
    settings = Settings(
        sms_provider="sms_webservice",
        sms_send_mode="pattern",
        sms_webservice_pattern_template_key="opp-alert",
        sms_webservice_pattern_p1="discount_label",
        sms_webservice_pattern_p2="title",
        sms_webservice_pattern_p3="price_and_gateway",
        app_host="https://car-alert.ir",
    )
    composer = GatewaySmsComposer(settings)
    payload = composer.build_payload(_opportunity(), _listing(), "tok123")
    assert payload.mode == "pattern"
    assert payload.pattern_id == "opp-alert"
    assert payload.pattern_slots[0] == "۳۰ میلیون تومان"
    assert "car-alert.ir/g/tok123" in payload.pattern_slots[2]
