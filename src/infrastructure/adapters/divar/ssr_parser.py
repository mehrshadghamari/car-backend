import json
import re

from src.domain.utils.persian_numbers import parse_kilometer, parse_price_toman
from src.domain.value_objects.divar_listing import DivarListingCard, DivarSearchPage
from src.infrastructure.adapters.divar.url_converter import build_divar_post_url


def extract_preloaded_state(html: str) -> dict:
    match = re.search(r"window\.__PRELOADED_STATE__\s*=\s*(\{.+)", html, re.DOTALL)
    if not match:
        raise ValueError("Could not find __PRELOADED_STATE__ in Divar HTML")

    data = match.group(1)
    depth = 0
    end = 0
    for i, char in enumerate(data):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return json.loads(data[:end])


def parse_search_page_from_html(html: str) -> DivarSearchPage:
    state = extract_preloaded_state(html)
    nb = state.get("nb", {})
    listings: list[DivarListingCard] = []
    seen_tokens: set[str] = set()

    for widget in nb.get("listWidgets", []):
        data = widget.get("data", {})
        if data.get("widgetType") != "POST_ROW":
            continue
        row = data.get("dto", {}).get("data", {})
        token = row.get("action", {}).get("payload", {}).get("token")
        if not token or token in seen_tokens:
            continue
        seen_tokens.add(token)
        price = parse_price_toman(row.get("middle_description_text"))
        if price is None:
            continue
        listings.append(
            DivarListingCard(
                token=token,
                title=row.get("title", ""),
                price=price,
                kilometer=parse_kilometer(row.get("top_description_text")),
                district=row.get("bottom_description_text"),
                divar_url=build_divar_post_url(token),
            )
        )

    pagination = nb.get("pagination", {})
    pagination_data = pagination.get("data", {})
    last_post_date_epoch = None
    if pagination_data.get("last_post_date"):
        from datetime import datetime

        dt = datetime.fromisoformat(pagination_data["last_post_date"].replace("Z", "+00:00"))
        last_post_date_epoch = int(dt.timestamp() * 1_000_000)

    for widget in nb.get("listWidgets", []):
        action_log = widget.get("actionLog", {})
        info = action_log.get("server_side_info", {}).get("info", {})
        if info.get("last_post_date_epoch"):
            last_post_date_epoch = int(info["last_post_date_epoch"])
            break

    return DivarSearchPage(
        listings=listings,
        last_post_date_epoch=last_post_date_epoch,
        has_more=pagination.get("hasMore", False),
    )


def parse_widget_list_response(data: dict) -> DivarSearchPage:
    listings: list[DivarListingCard] = []
    seen_tokens: set[str] = set()

    for widget in data.get("widget_list", []):
        if widget.get("widget_type") != "POST_ROW":
            continue
        row = widget.get("data", {})
        token = row.get("action", {}).get("payload", {}).get("token")
        if not token or token in seen_tokens:
            continue
        seen_tokens.add(token)
        price = parse_price_toman(row.get("middle_description_text"))
        if price is None:
            continue
        listings.append(
            DivarListingCard(
                token=token,
                title=row.get("title", ""),
                price=price,
                kilometer=parse_kilometer(row.get("top_description_text")),
                district=row.get("bottom_description_text"),
                divar_url=build_divar_post_url(token),
            )
        )

    last_post_date = data.get("last_post_date")
    last_post_date_epoch = int(last_post_date) if last_post_date and last_post_date > 0 else None

    return DivarSearchPage(
        listings=listings,
        last_post_date_epoch=last_post_date_epoch,
        has_more=bool(listings) and last_post_date_epoch is not None,
    )
