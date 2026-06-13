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
