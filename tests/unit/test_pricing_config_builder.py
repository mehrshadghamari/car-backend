from dataclasses import dataclass

from src.application.services.pricing_config_builder import merge_khodro45_pricing_config


@dataclass
class _FakeMapping:
    slug: str
    config: dict | None = None


def test_merge_khodro45_uses_column_slug_over_stale_config():
    mapping = _FakeMapping(
        slug="cpe-peugeot-207pana-mt",
        config={
            "slug": "cpe-peugeot-207pana-at",
            "default_color": "Black",
            "color_map": {"سفید": "White"},
        },
    )
    result = merge_khodro45_pricing_config(mapping)
    assert result["slug"] == "cpe-peugeot-207pana-mt"
    assert result["color_map"] == {"سفید": "White"}


def test_merge_khodro45_preserves_existing_color_map():
    mapping = _FakeMapping(slug="cpe-peugeot-207pana-mt", config={"color_map": {"مشکی": "Black"}})
    existing = {"slug": "cpe-peugeot-207pana-at", "default_color": "Silver"}
    result = merge_khodro45_pricing_config(mapping, existing=existing)
    assert result["slug"] == "cpe-peugeot-207pana-mt"
    assert result["default_color"] == "Silver"
