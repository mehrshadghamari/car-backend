from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


DIVAR_WEB_BASE = "https://divar.ir"
DIVAR_API_BASE = "https://api.divar.ir/v8/web-search"


def web_url_to_api_url(listing_url: str) -> tuple[str, dict[str, list[str]]]:
    """Convert Divar web search URL to API URL and query params."""
    parsed = urlparse(listing_url)
    path = parsed.path
    if path.startswith("/s/"):
        path = path[3:]
    api_path = f"{DIVAR_API_BASE}/{path.lstrip('/')}"
    query_params = parse_qs(parsed.query)
    return api_path, query_params


def build_json_schema_from_url(listing_url: str, divar_brand_model: str | None = None) -> dict:
    """Build Divar API json_schema from listing URL path and query."""
    parsed = urlparse(listing_url)
    path_parts = [p for p in parsed.path.split("/") if p]
    query = parse_qs(parsed.query)

    schema: dict = {
        "category": {"value": "light"},
        "cities": ["1"],
    }

    brand_model_name = divar_brand_model
    if not brand_model_name and len(path_parts) >= 4 and path_parts[0] == "s":
        brand_model_slug = "/".join(path_parts[3:])
        brand_model_name = _slug_to_brand_model(brand_model_slug)
    if brand_model_name:
        schema["brand_model"] = {"repeated_string": {"value": [brand_model_name]}}

    if "production-year" in query:
        year_val = query["production-year"][0]
        if year_val.endswith("-"):
            minimum = year_val.rstrip("-")
            if "-" in minimum:
                parts = minimum.split("-")
                schema["production-year"] = {
                    "number_range": {"minimum": parts[0], "maximum": parts[1]}
                }
            else:
                schema["production-year"] = {"number_range": {"minimum": minimum}}
        elif year_val.startswith("-"):
            schema["production-year"] = {"number_range": {"maximum": year_val.lstrip("-")}}
        else:
            parts = year_val.split("-")
            if len(parts) == 2:
                schema["production-year"] = {
                    "number_range": {"minimum": parts[0], "maximum": parts[1]}
                }

    if "usage" in query:
        usage_val = query["usage"][0]
        if usage_val.startswith("-"):
            schema["usage"] = {"number_range": {"maximum": usage_val.lstrip("-")}}
        elif usage_val.endswith("-"):
            schema["usage"] = {"number_range": {"minimum": usage_val.rstrip("-")}}
        elif "-" in usage_val:
            parts = usage_val.split("-")
            schema["usage"] = {"number_range": {"minimum": parts[0], "maximum": parts[1]}}

    return schema


def _slug_to_brand_model(slug: str) -> str | None:
    mapping = {
        "car/peugeot/207i/manual-p": "Peugeot 207i Manual P",
        "car/peugeot/207i/automatic-p": "Peugeot 207i Automatic P",
        "car/peugeot/206/5": "Peugeot 206 Type 5",
        "car/dena/plus/automatic": "Dena plus 1700cc Automatic",
    }
    return mapping.get(slug)


def build_divar_post_url(token: str) -> str:
    return f"{DIVAR_WEB_BASE}/v/{token}"
