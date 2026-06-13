"""URL paths for user portal (public) and staff routes (secret UUID prefix)."""

import re

from src.infrastructure.config import get_settings

_UUID_SEGMENT = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_UUID_PATH_RE = re.compile(
    r"^/portal/"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    r"/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    r"(/|$)",
    re.IGNORECASE,
)


def user_site_path() -> str:
    """Public client UI (login, dashboard) at domain root."""
    return "/"


def portal_secret_prefix() -> str:
    settings = get_settings()
    return f"/portal/{settings.portal_path_uuid_1}/{settings.portal_path_uuid_2}"


def portal_admin_path() -> str:
    return f"{portal_secret_prefix()}/admin"


def portal_docs_path() -> str:
    return f"{portal_secret_prefix()}/docs"


def portal_redoc_path() -> str:
    return f"{portal_secret_prefix()}/redoc"


def portal_openapi_path() -> str:
    return f"{portal_secret_prefix()}/openapi.json"


def portal_results_path() -> str:
    return f"{portal_secret_prefix()}/results"


def portal_trim_mapping_path() -> str:
    return f"{portal_secret_prefix()}/trim-mapping"


def is_portal_uuid_shaped_path(path: str) -> bool:
    """True for /portal/{uuid}/{uuid}/… (staff area shape)."""
    return _UUID_PATH_RE.match(path) is not None


def is_wrong_portal_secret_path(path: str) -> bool:
    """True when path looks like /portal/{uuid}/{uuid}/… but UUIDs do not match config."""
    match = _UUID_PATH_RE.match(path)
    if not match:
        return False
    settings = get_settings()
    u1, u2 = match.group(1).lower(), match.group(2).lower()
    return u1 != settings.portal_path_uuid_1 or u2 != settings.portal_path_uuid_2


def legacy_portal_redirect_target(rest: str) -> str | None:
    """Map old /portal/… user paths to /…; return None for staff UUID paths."""
    if not rest:
        return "/"
    parts = rest.split("/")
    if (
        len(parts) >= 2
        and _UUID_SEGMENT.match(parts[0])
        and _UUID_SEGMENT.match(parts[1])
    ):
        return None
    return f"/{rest}"
