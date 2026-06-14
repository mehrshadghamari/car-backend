from typing import Any


def merge_khodro45_pricing_config(
    pricing_mapping,
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build Khodro45 pricing config; mapping.slug column is authoritative."""
    config = dict(existing or pricing_mapping.config or {})
    config["slug"] = pricing_mapping.slug
    config.setdefault("default_color", "Black")
    return config


def merge_hamrah_pricing_config(
    pricing_mapping,
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build Hamrah Mechanic pricing config for min/mid/max crawler."""
    stored = dict(pricing_mapping.config or {})
    config = dict(existing or stored)
    config["brand"] = stored.get("brand") or config.get("brand", "")
    config["model"] = stored.get("model") or config.get("model", "")
    config["type_id"] = str(stored.get("type_id") or pricing_mapping.slug or config.get("type_id", ""))
    config.setdefault("default_color", "ColorWhite")
    config.setdefault("default_body_condition", "WithoutColor")
    if stored.get("color_map"):
        config.setdefault("color_map", stored["color_map"])
    return config


def merge_pricing_config(
    pricing_mapping,
    pricing_platform_slug: str,
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if pricing_platform_slug == "hamrah_mechanic":
        return merge_hamrah_pricing_config(pricing_mapping, existing=existing)
    return merge_khodro45_pricing_config(pricing_mapping, existing=existing)
