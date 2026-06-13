_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def normalize_persian_digits(text: str) -> str:
    return text.translate(_PERSIAN_DIGITS).translate(_ARABIC_DIGITS)


def parse_price_toman(text: str | None) -> int | None:
    if not text:
        return None
    normalized = normalize_persian_digits(text)
    digits = "".join(c for c in normalized if c.isdigit())
    return int(digits) if digits else None


def parse_kilometer(text: str | None) -> int | None:
    if not text:
        return None
    normalized = normalize_persian_digits(text)
    digits = "".join(c for c in normalized if c.isdigit())
    return int(digits) if digits else None


def parse_jalali_year(text: str | None) -> int | None:
    if not text:
        return None
    normalized = normalize_persian_digits(text)
    import re

    match = re.search(r"(13|14)\d{2}", normalized)
    if match:
        return int(match.group())
    match = re.search(r"(13|14)\d{2}", text)
    return int(match.group()) if match else None


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        355666
        + (365 * gy)
        + ((gy2 + 3) // 4)
        - ((gy2 + 99) // 100)
        + ((gy2 + 399) // 400)
        + gd
        + g_d_m[gm - 1]
    )
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def catalog_year_to_jalali(title: str | None) -> int | None:
    """Normalize catalog year titles (Jalali or Gregorian) to Jalali for Divar filtering."""
    if not title:
        return None
    jalali = parse_jalali_year(title)
    if jalali:
        return jalali
    import re

    normalized = normalize_persian_digits(title.strip())
    match = re.match(r"^(\d{4})$", normalized)
    if match:
        gy = int(match.group(1))
        if 1900 <= gy <= 2100:
            jy, _, _ = gregorian_to_jalali(gy, 7, 1)
            return jy
    return None
