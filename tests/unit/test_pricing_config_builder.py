from dataclasses import dataclass

from src.application.services.pricing_config_builder import (
    merge_hamrah_pricing_config,
    merge_khodro45_pricing_config,
    merge_pricing_config,
)


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


def test_merge_hamrah_uses_mapping_config_for_crawler():
    mapping = _FakeMapping(
        slug="2883",
        config={
            "brand": "peugeot",
            "model": "peugeot207",
            "type_id": "2883",
            "default_color": "ColorWhite",
            "default_body_condition": "WithoutColor",
            "color_map": {"سفید": "ColorWhite"},
        },
    )
    result = merge_hamrah_pricing_config(mapping)
    assert result["brand"] == "peugeot"
    assert result["model"] == "peugeot207"
    assert result["type_id"] == "2883"
    assert result["default_color"] == "ColorWhite"


def test_merge_pricing_config_routes_by_platform():
    mapping = _FakeMapping(slug="2883", config={"brand": "peugeot", "model": "peugeot207", "type_id": "2883"})
    hamrah = merge_pricing_config(mapping, "hamrah_mechanic")
    assert hamrah["type_id"] == "2883"
    khodro = merge_pricing_config(_FakeMapping(slug="cpe-peugeot-207pana-mt"), "khodro45")
    assert khodro["slug"] == "cpe-peugeot-207pana-mt"
