import re

_PHONE_RE = re.compile(r"^09\d{9}$")


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone.strip())
    if digits.startswith("98") and len(digits) == 12:
        digits = "0" + digits[2:]
    if digits.startswith("9") and len(digits) == 10:
        digits = "0" + digits
    if not _PHONE_RE.match(digits):
        raise ValueError("شماره موبایل معتبر نیست (مثال: 09121234567)")
    return digits
