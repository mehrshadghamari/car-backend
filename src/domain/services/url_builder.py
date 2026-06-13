from urllib.parse import urlencode, urlparse

DIVAR_WEB_BASE = "https://divar.ir"
KHODRO45_BASE = "https://khodro45.com"
HAMRAH_WEB_BASE = "https://www.hamrah-mechanic.com"
HAMRAH_CARPRICE_SEGMENT = "carprice"


def normalize_hamrah_base_url(base_url: str) -> str:
    """Keep only scheme+host; fix common typos like carpreice -> carprice."""
    cleaned = base_url.strip().replace("carpreice", HAMRAH_CARPRICE_SEGMENT)
    parsed = urlparse(cleaned)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return cleaned.rstrip("/")


def build_divar_search_url(
    city: str,
    divar_path: str,
    production_year_min: int | None = None,
    production_year_max: int | None = None,
    usage_min: int | None = None,
    usage_max: int | None = None,
) -> str:
    """
    Build Divar search URL from car model path and user filters.

    Examples:
      production_year_min=1402 -> ?production-year=1402-
      production_year 1402-1405 -> ?production-year=1402-1405
      usage_max=80000 -> ?usage=-80000
      usage 20000-80000 -> ?usage=20000-80000
    """
    path = divar_path.lstrip("/")
    base = f"{DIVAR_WEB_BASE}/s/{city}/{path}"
    params: dict[str, str] = {}

    if production_year_min is not None and production_year_max is not None:
        params["production-year"] = f"{production_year_min}-{production_year_max}"
    elif production_year_min is not None:
        params["production-year"] = f"{production_year_min}-"
    elif production_year_max is not None:
        params["production-year"] = f"-{production_year_max}"

    if usage_min is not None and usage_max is not None:
        params["usage"] = f"{usage_min}-{usage_max}"
    elif usage_max is not None:
        params["usage"] = f"-{usage_max}"
    elif usage_min is not None:
        params["usage"] = f"{usage_min}-"

    if not params:
        return base
    return f"{base}?{urlencode(params)}"


def build_hamrah_price_url(
    hamrah_brand: str,
    hamrah_model: str,
    hamrah_type_id: str,
    production_year: int,
    kilometer: int,
    color: str = "ColorWhite",
    body_condition: str = "WithoutColor",
    base_url: str = HAMRAH_WEB_BASE,
) -> str:
    base = normalize_hamrah_base_url(base_url)
    path = (
        f"/{HAMRAH_CARPRICE_SEGMENT}/{hamrah_brand}/{hamrah_model}/"
        f"{production_year}/{hamrah_type_id}/"
    )
    query = urlencode(
        {
            "kilometer": kilometer,
            "clr": color,
            "bodycondition": body_condition,
        }
    )
    return f"{base}{path}?{query}"


def build_khodro45_price_url(
    slug: str,
    production_year: int,
    kilometer: int,
    color_id: str = "Black",
    base_url: str = KHODRO45_BASE,
) -> str:
    base = base_url.rstrip("/")
    return (
        f"{base}/carprice/{slug}/"
        f"?year={production_year}&color_id={color_id}&kilometer={kilometer}"
    )


def build_hamrah_api_url(
    build_id: str,
    hamrah_brand: str,
    hamrah_model: str,
    hamrah_type_id: str,
    production_year: int,
    kilometer: int,
    color: str = "ColorWhite",
    body_condition: str = "WithoutColor",
) -> str:
    base = "https://www.hamrah-mechanic.com"
    return (
        f"{base}/_next/data/{build_id}/carprice/"
        f"{hamrah_brand}/{hamrah_model}/{production_year}/{hamrah_type_id}.json"
        f"?kilometer={kilometer}&clr={color}&bodycondition={body_condition}"
    )
