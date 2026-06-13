from src.domain.utils.persian_numbers import parse_kilometer
from src.domain.value_objects.divar_listing import DivarListingCard
from src.infrastructure.adapters.divar.url_converter import build_divar_post_url


def parse_open_finder_response(data: dict) -> list[DivarListingCard]:
    """Parse Divar open-platform finder/post response into listing cards."""
    cards: list[DivarListingCard] = []
    for post in data.get("posts") or []:
        token = post.get("token")
        if not token:
            continue
        title = post.get("title") or ""
        price_obj = post.get("price") or {}
        raw_price = price_obj.get("value")
        price = int(raw_price) if raw_price is not None and str(raw_price).isdigit() else 0

        vehicles = post.get("vehicles_fields") or {}
        usage_raw = vehicles.get("usage")
        kilometer = None
        if usage_raw is not None and str(usage_raw).strip() != "":
            kilometer = parse_kilometer(str(usage_raw))
            if kilometer is None and str(usage_raw).isdigit():
                kilometer = int(usage_raw)

        cards.append(
            DivarListingCard(
                token=token,
                title=title,
                price=price,
                kilometer=kilometer,
                district=post.get("district"),
                divar_url=build_divar_post_url(token),
            )
        )
    return cards
