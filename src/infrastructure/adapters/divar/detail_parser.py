from src.domain.utils.persian_numbers import parse_jalali_year, parse_kilometer, parse_price_toman
from src.domain.value_objects.divar_listing import DivarListingDetail


def _apply_labeled_attr(
    key: str,
    value: str,
    *,
    price: int | None,
    kilometer: int | None,
    production_year: int | None,
    color: str | None,
    brand_model: str | None,
    district: str | None,
) -> tuple[int | None, int | None, int | None, str | None, str | None, str | None]:
    if "قیمت" in key:
        price = parse_price_toman(value) or price
    elif "کارکرد" in key:
        kilometer = parse_kilometer(value) or kilometer
    elif "سال" in key or "مدل" in key:
        production_year = parse_jalali_year(value) or production_year
    elif "رنگ" in key:
        color = value
    elif "برند" in key:
        brand_model = value
    elif "محله" in key or "منطقه" in key:
        district = value
    return price, kilometer, production_year, color, brand_model, district


def _parse_group_info_items(items: list) -> tuple[int | None, int | None, str | None]:
    """Divar car posts expose km / year / color as bare values in GROUP_INFO_ROW."""
    values = [str(item.get("value")).strip() for item in items if item.get("value")]
    if len(values) >= 3:
        return parse_kilometer(values[0]), parse_jalali_year(values[1]), values[2]

    kilometer: int | None = None
    production_year: int | None = None
    color: str | None = None

    for value in values:
        year = parse_jalali_year(value)
        if year and ("-" in value or "سال" in value or len(value) <= 6):
            production_year = year
            continue

        km = parse_kilometer(value)
        if km is not None and kilometer is None and not parse_jalali_year(value):
            kilometer = km
            continue

        if not color:
            color = value

    return kilometer, production_year, color


def _walk_title_value(obj, results: list[tuple[str, str]]) -> None:
    if isinstance(obj, dict):
        title = obj.get("title") or obj.get("label")
        value = obj.get("value") or obj.get("text")
        if title and value and isinstance(value, str):
            results.append((str(title), value))
        for v in obj.values():
            _walk_title_value(v, results)
    elif isinstance(obj, list):
        for item in obj:
            _walk_title_value(item, results)


def parse_post_detail(token: str, data: dict) -> DivarListingDetail:
    title = ""
    price: int | None = None
    kilometer: int | None = None
    production_year: int | None = None
    color: str | None = None
    brand_model: str | None = None
    district: str | None = None

    for section in data.get("sections", []):
        for widget in section.get("widgets") or []:
            widget_type = widget.get("widget_type")
            widget_data = widget.get("data") or {}

            if widget_type == "LEGEND_TITLE_ROW" and widget_data.get("title"):
                title = widget_data["title"]

            if widget_type == "GROUP_INFO_ROW":
                km, year, col = _parse_group_info_items(widget_data.get("items") or [])
                kilometer = kilometer if kilometer is not None else km
                production_year = production_year or year
                color = color or col

            labeled_title = widget_data.get("title") or widget_data.get("label")
            labeled_value = widget_data.get("value") or widget_data.get("text")
            if labeled_title and labeled_value and isinstance(labeled_value, str):
                price, kilometer, production_year, color, brand_model, district = _apply_labeled_attr(
                    str(labeled_title).strip(),
                    labeled_value,
                    price=price,
                    kilometer=kilometer,
                    production_year=production_year,
                    color=color,
                    brand_model=brand_model,
                    district=district,
                )

    if not title:
        for section in data.get("sections", []):
            section_data = section.get("data", section)
            if section_data.get("title"):
                title = section_data["title"]
                break
    if not title:
        title = data.get("seo", {}).get("title", "")

    # Legacy/alternate payloads still nested in arbitrary nodes
    results: list[tuple[str, str]] = []
    _walk_title_value(data, results)
    for key, value in results:
        price, kilometer, production_year, color, brand_model, district = _apply_labeled_attr(
            key.strip(),
            value,
            price=price,
            kilometer=kilometer,
            production_year=production_year,
            color=color,
            brand_model=brand_model,
            district=district,
        )

    return DivarListingDetail(
        token=token,
        title=title,
        price=price or 0,
        kilometer=kilometer,
        production_year=production_year,
        color=color,
        brand_model=brand_model,
        district=district,
    )
