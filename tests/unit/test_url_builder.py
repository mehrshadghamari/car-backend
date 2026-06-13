from src.domain.services.url_builder import (
    build_divar_search_url,
    build_hamrah_price_url,
    normalize_hamrah_base_url,
)


def test_build_divar_url_year_min_usage_max():
    url = build_divar_search_url(
        city="tehran",
        divar_path="car/peugeot/207i/manual-p",
        production_year_min=1402,
        usage_max=80000,
    )
    assert "divar.ir/s/tehran/car/peugeot/207i/manual-p" in url
    assert "production-year=1402-" in url
    assert "usage=-80000" in url


def test_build_hamrah_url():
    url = build_hamrah_price_url(
        hamrah_brand="peugeot",
        hamrah_model="peugeot207",
        hamrah_type_id="2749",
        production_year=1403,
        kilometer=31000,
    )
    assert "hamrah-mechanic.com/carprice/peugeot/peugeot207/1403/2749" in url
    assert "kilometer=31000" in url


def test_build_hamrah_url_exact_preview_format():
    url = build_hamrah_price_url(
        hamrah_brand="peugeot",
        hamrah_model="peugeot207",
        hamrah_type_id="2749",
        production_year=1403,
        kilometer=35000,
    )
    assert url == (
        "https://www.hamrah-mechanic.com/carprice/peugeot/peugeot207/1403/2749/"
        "?kilometer=35000&clr=ColorWhite&bodycondition=WithoutColor"
    )
    assert "carpreice" not in url
    assert "%20" not in url


def test_normalize_hamrah_base_url_fixes_typo_and_path():
    assert (
        normalize_hamrah_base_url("https://www.hamrah-mechanic.com/carpreice")
        == "https://www.hamrah-mechanic.com"
    )
    assert (
        normalize_hamrah_base_url("https://www.hamrah-mechanic.com/carpreice/")
        == "https://www.hamrah-mechanic.com"
    )
