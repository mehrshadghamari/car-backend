from src.infrastructure.adapters.divar.detail_parser import parse_post_detail


def _car_detail_payload(
    *,
    group_items: list[dict] | None = None,
    rows: list[tuple[str, str]] | None = None,
) -> dict:
    widgets = []
    if group_items is not None:
        widgets.append(
            {
                "widget_type": "GROUP_INFO_ROW",
                "data": {"items": group_items},
            }
        )
    for title, value in rows or []:
        widgets.append(
            {
                "widget_type": "UNEXPANDABLE_ROW",
                "data": {"title": title, "value": value},
            }
        )
    return {
        "sections": [
            {
                "widgets": [
                    {
                        "widget_type": "LEGEND_TITLE_ROW",
                        "data": {"title": "207 پانا ارتقا TU5+ رینگ مشکی"},
                    },
                    *widgets,
                ]
            }
        ],
        "seo": {"title": "207 پانا"},
    }


def test_parse_group_info_row_km_year_color():
    data = _car_detail_payload(
        group_items=[
            {"value": "۷۶۰۰"},
            {"value": "۱۴۰۴ - ۲۰۲۵"},
            {"value": "تیتانیوم"},
        ],
        rows=[("قیمت پایه", "‏۲,۰۷۰,۰۰۰,۰۰۰ تومان")],
    )
    detail = parse_post_detail("gajkQZ-X", data)
    assert detail.kilometer == 7600
    assert detail.production_year == 1404
    assert detail.color == "تیتانیوم"
    assert detail.price == 2_070_000_000
    assert "207" in detail.title


def test_parse_zero_km_listing():
    data = _car_detail_payload(
        group_items=[
            {"value": "۰"},
            {"value": "۱۴۰۴ - ۲۰۲۵"},
            {"value": "سفید"},
        ]
    )
    detail = parse_post_detail("gakwUoul", data)
    assert detail.kilometer == 0
    assert detail.production_year == 1404
    assert detail.color == "سفید"


def test_parse_high_km_not_confused_with_year():
    data = _car_detail_payload(
        group_items=[
            {"value": "۱۴۰۰۰"},
            {"value": "۱۴۰۳ - ۲۰۲۴"},
            {"value": "سفید"},
        ]
    )
    detail = parse_post_detail("gajUAgYY", data)
    assert detail.kilometer == 14000
    assert detail.production_year == 1403
    assert detail.color == "سفید"


def test_parse_labeled_rows_fallback():
    data = _car_detail_payload(
        rows=[
            ("کارکرد", "۴۵,۰۰۰"),
            ("سال ساخت", "۱۴۰۲"),
            ("رنگ", "مشکی"),
        ]
    )
    detail = parse_post_detail("legacy", data)
    assert detail.kilometer == 45000
    assert detail.production_year == 1402
    assert detail.color == "مشکی"
