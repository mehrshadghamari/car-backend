from dataclasses import dataclass

from src.domain.entities.listing import Listing
from src.domain.entities.opportunity import Opportunity
from src.domain.utils.persian_format import format_toman_commas, format_toman_discount_label
from src.domain.value_objects.sms import SmsPayload
from src.infrastructure.config import Settings


@dataclass(frozen=True)
class GatewaySmsContext:
    discount_label: str
    title: str
    price: str
    gateway_url: str
    price_line: str
    price_and_gateway: str
    footer: str


def short_gateway_url(app_host: str, gateway_token: str) -> str:
    host = app_host.rstrip("/")
    if host.startswith("https://"):
        host = host[8:]
    elif host.startswith("http://"):
        host = host[7:]
    return f"{host}/g/{gateway_token}"


def build_gateway_sms_context(
    opportunity: Opportunity,
    listing: Listing,
    gateway_token: str,
    app_host: str,
) -> GatewaySmsContext:
    discount_label = format_toman_discount_label(opportunity.discount_amount)
    title = (listing.title or "خودرو").strip()
    price = format_toman_commas(listing.price)
    gateway_url = short_gateway_url(app_host, gateway_token)
    price_line = f"{price} تومان"
    price_and_gateway = f"{price} تومان  مشاهده آگهی در دیوار : {gateway_url}"
    footer = price_and_gateway
    return GatewaySmsContext(
        discount_label=discount_label,
        title=title,
        price=price,
        gateway_url=gateway_url,
        price_line=price_line,
        price_and_gateway=price_and_gateway,
        footer=footer,
    )


def _context_as_dict(ctx: GatewaySmsContext) -> dict[str, str]:
    return {
        "discount_label": ctx.discount_label,
        "title": ctx.title,
        "price": ctx.price,
        "gateway_url": ctx.gateway_url,
        "price_line": ctx.price_line,
        "price_and_gateway": ctx.price_and_gateway,
        "footer": ctx.footer,
    }


def build_gateway_text_message(ctx: GatewaySmsContext, template: str) -> str:
    return template.format(**_context_as_dict(ctx))


def _pattern_slot_values(ctx: GatewaySmsContext, slot_names: list[str]) -> tuple[str, ...]:
    values = _context_as_dict(ctx)
    return tuple(values.get(name, "") for name in slot_names)


class GatewaySmsComposer:
    def __init__(self, settings: Settings):
        self._settings = settings

    def build_context(
        self,
        opportunity: Opportunity,
        listing: Listing,
        gateway_token: str,
    ) -> GatewaySmsContext:
        return build_gateway_sms_context(opportunity, listing, gateway_token, self._settings.app_host)

    def build_payload(
        self,
        opportunity: Opportunity,
        listing: Listing,
        gateway_token: str,
    ) -> SmsPayload:
        ctx = self.build_context(opportunity, listing, gateway_token)
        mode = (self._settings.sms_send_mode or "text").lower()
        if mode == "pattern":
            return self._build_pattern_payload(ctx)
        return SmsPayload(mode="text", text=build_gateway_text_message(ctx, self._settings.sms_gateway_text_template))

    def _build_pattern_payload(self, ctx: GatewaySmsContext) -> SmsPayload:
        provider = (self._settings.sms_provider or "dry_run").lower()
        values = _context_as_dict(ctx)

        if provider == "sms_webservice":
            slot_names = [
                name.strip()
                for name in (self._settings.sms_webservice_pattern_p1, self._settings.sms_webservice_pattern_p2, self._settings.sms_webservice_pattern_p3)
                if name and name.strip()
            ]
            if not slot_names:
                slot_names = ["discount_label", "title", "footer"]
            slots = _pattern_slot_values(ctx, slot_names[:3])
            return SmsPayload(
                mode="pattern",
                pattern_id=self._settings.sms_webservice_pattern_template_key or None,
                pattern_slots=slots,
            )

        param_names = [
            name.strip()
            for name in self._settings.sms_ir_pattern_param_names.split(",")
            if name.strip()
        ]
        if not param_names:
            param_names = ["discount_label", "title", "price", "gateway_url"]
        pattern_params = {name: values.get(name, "") for name in param_names}
        return SmsPayload(
            mode="pattern",
            pattern_id=self._settings.sms_ir_template_id or None,
            pattern_params=pattern_params,
        )
