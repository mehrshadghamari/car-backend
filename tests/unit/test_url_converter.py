from src.infrastructure.adapters.divar.url_converter import build_json_schema_from_url, web_url_to_api_url


def test_web_url_to_api_url():
    url = "https://divar.ir/s/tehran/car/peugeot/207i/manual-p?production-year=1402-&usage=-80000"
    api_url, params = web_url_to_api_url(url)
    assert "api.divar.ir/v8/web-search/tehran/car/peugeot/207i/manual-p" in api_url
    assert "production-year" in params


def test_build_json_schema():
    url = "https://divar.ir/s/tehran/car/peugeot/207i/manual-p?production-year=1402-&usage=-80000"
    schema = build_json_schema_from_url(url)
    assert schema["category"]["value"] == "light"
    assert "production-year" in schema
    assert "usage" in schema
