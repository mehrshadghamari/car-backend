from src.domain.utils.persian_format import format_toman_commas, format_toman_discount_label, to_persian_digits


def test_to_persian_digits():
    assert to_persian_digits("30") == "۳۰"


def test_format_toman_commas():
    assert format_toman_commas(1_850_000_000) == "1,850,000,000"


def test_format_toman_discount_label_billion():
    assert "میلیارد" in format_toman_discount_label(1_500_000_000)
