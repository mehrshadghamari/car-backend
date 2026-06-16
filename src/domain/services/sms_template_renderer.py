from src.domain.entities.sms_config import SmsTemplate
from src.domain.value_objects.sms import SmsPayload


def render_text_template(template_body: str, params: dict[str, str]) -> str:
    try:
        return template_body.format(**params)
    except KeyError as exc:
        missing = str(exc).strip("'")
        raise ValueError(f"SMS template missing param: {missing}") from exc


def build_sms_payload(template: SmsTemplate, params: dict[str, str]) -> SmsPayload:
    mode = (template.send_mode or "text").lower()
    if mode == "pattern":
        return _build_pattern_payload(template, params)
    body = template.text_body or ""
    return SmsPayload(mode="text", text=render_text_template(body, params))


def _build_pattern_payload(template: SmsTemplate, params: dict[str, str]) -> SmsPayload:
    driver = (template.provider.driver if template.provider else "").lower()
    pattern_key = template.pattern_key

    if driver == "sms_webservice":
        slot_names = list(template.pattern_slots or [])
        if not slot_names:
            slot_names = ["discount_label", "title", "price_and_gateway"]
        slots = tuple(params.get(name, "") for name in slot_names[:3])
        return SmsPayload(mode="pattern", pattern_id=pattern_key, pattern_slots=slots)

    param_names = list(template.pattern_params or [])
    if not param_names:
        param_names = list(params.keys())
    pattern_params = {name: params.get(name, "") for name in param_names}
    return SmsPayload(
        mode="pattern",
        pattern_id=pattern_key,
        pattern_params=pattern_params,
    )
