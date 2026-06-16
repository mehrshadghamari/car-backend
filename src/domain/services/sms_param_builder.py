from src.domain.entities.listing import Listing
from src.domain.entities.opportunity import Opportunity
from src.domain.services.sms_message_builder import build_gateway_sms_context
from src.domain.utils.persian_format import format_toman_commas


def gateway_link_params(
    opportunity: Opportunity,
    listing: Listing,
    gateway_token: str,
    app_host: str,
) -> dict[str, str]:
    ctx = build_gateway_sms_context(opportunity, listing, gateway_token, app_host)
    return {
        "discount_label": ctx.discount_label,
        "title": ctx.title,
        "price": ctx.price,
        "gateway_url": ctx.gateway_url,
        "price_line": ctx.price_line,
        "price_and_gateway": ctx.price_and_gateway,
        "footer": ctx.footer,
        "listing_price": format_toman_commas(listing.price),
    }


def otp_code_params(code: str) -> dict[str, str]:
    return {"code": code}


def portal_link_params(share_url: str) -> dict[str, str]:
    return {"share_url": share_url, "url": share_url}
