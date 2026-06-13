from src.domain.utils.persian_numbers import parse_jalali_year, parse_kilometer, parse_price_toman


def test_parse_price_toman():
    assert parse_price_toman("۲,۱۳۰,۰۰۰,۰۰۰ تومان") == 2130000000


def test_parse_kilometer():
    assert parse_kilometer("۴,۹۰۰ کیلومتر") == 4900


def test_parse_jalali_year():
    assert parse_jalali_year("۱۴۰۴ - ۲۰۲۵") == 1404
