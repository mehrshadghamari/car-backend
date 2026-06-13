"""Resolve Jalali production year from catalog trim."""

from src.domain.entities.car_catalog import CarTrim
from src.domain.utils.persian_numbers import catalog_year_to_jalali, normalize_persian_digits, parse_jalali_year


def trim_production_year(trim: CarTrim) -> int | None:
    if not trim.year_title:
        return None
    jalali = catalog_year_to_jalali(trim.year_title)
    if jalali:
        return jalali
    title = normalize_persian_digits(trim.year_title.strip())
    if title.isdigit():
        return int(title)
    return parse_jalali_year(trim.year_title)


def resolve_production_year_range(
    trim: CarTrim,
    *,
    production_year_min: int | None = None,
    production_year_max: int | None = None,
) -> tuple[int | None, int | None]:
    """Default purchase/pool year filters from trim when not provided."""
    trim_year = trim_production_year(trim)
    year_min = production_year_min if production_year_min is not None else trim_year
    year_max = production_year_max if production_year_max is not None else trim_year
    return year_min, year_max
