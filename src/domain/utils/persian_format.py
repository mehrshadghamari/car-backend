"""Persian-friendly formatting for SMS and UI copy."""

_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"


def to_persian_digits(value: str | int) -> str:
    text = str(value)
    return "".join(_PERSIAN_DIGITS[int(ch)] if ch.isdigit() else ch for ch in text)


def format_toman_commas(amount: int) -> str:
    return f"{amount:,}"


def format_toman_discount_label(discount_amount: int) -> str:
    """e.g. 30_000_000 -> '۳۰ میلیون تومان'."""
    if discount_amount <= 0:
        return "زیر قیمت بازار"
    if discount_amount >= 1_000_000_000:
        billions = discount_amount / 1_000_000_000
        if billions == int(billions):
            core = f"{int(billions)} میلیارد تومان"
        else:
            core = f"{billions:.1f} میلیارد تومان"
        return to_persian_digits(core)
    if discount_amount >= 1_000_000:
        millions = discount_amount / 1_000_000
        if millions == int(millions):
            core = f"{int(millions)} میلیون تومان"
        else:
            core = f"{millions:.1f} میلیون تومان"
        return to_persian_digits(core)
    if discount_amount >= 1_000:
        thousands = discount_amount / 1_000
        if thousands == int(thousands):
            core = f"{int(thousands)} هزار تومان"
        else:
            core = f"{thousands:.1f} هزار تومان"
        return to_persian_digits(core)
    return f"{to_persian_digits(discount_amount)} تومان"
