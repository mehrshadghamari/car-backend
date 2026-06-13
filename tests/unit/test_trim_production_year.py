from uuid import uuid4

from src.domain.entities.car_catalog import CarTrim
from src.domain.services.trim_production_year import (
    resolve_production_year_range,
    trim_production_year,
)


def _trim(year_title: str) -> CarTrim:
    return CarTrim(
        id=uuid4(),
        model_id=uuid4(),
        year_id=uuid4(),
        name="Manual",
        seo_slug="manual",
        year_title=year_title,
    )


def test_trim_production_year_from_title():
    assert trim_production_year(_trim("1403")) == 1403


def test_trim_production_year_persian_digits():
    assert trim_production_year(_trim("۱۴۰۳")) == 1403


def test_resolve_defaults_to_trim_year():
    year_min, year_max = resolve_production_year_range(_trim("1402"))
    assert year_min == 1402
    assert year_max == 1402


def test_resolve_keeps_explicit_range():
    trim = _trim("1403")
    year_min, year_max = resolve_production_year_range(
        trim, production_year_min=1401, production_year_max=1404
    )
    assert year_min == 1401
    assert year_max == 1404
