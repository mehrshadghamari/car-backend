from src.domain.services.url_builder import build_khodro45_price_url


def test_build_khodro45_price_url():
    url = build_khodro45_price_url(
        slug="cpe-peugeot-207pana-at",
        production_year=1403,
        kilometer=31000,
        color_id="Black",
    )
    assert url == (
        "https://khodro45.com/carprice/cpe-peugeot-207pana-at/"
        "?year=1403&color_id=Black&kilometer=31000"
    )
