from dataclasses import dataclass
from decimal import Decimal

from src.domain.entities.opportunity import DealTag


@dataclass(frozen=True)
class PriceTierMatch:
    basis: str
    reference_price: int
    is_below: bool
    discount_amount: int
    discount_pct: Decimal
    score: Decimal
    deal_tag: str


def deal_tag_for_match(basis: str, is_below: bool) -> str:
    """
    Legacy Hamrah / multi-tier helper.
    - best: matched against low/floor price
    - good: at or below mid price
    - fair: near mid price only
    """
    if basis == "down":
        return DealTag.BEST.value
    return DealTag.GOOD.value if is_below else DealTag.FAIR.value


def deal_tag_for_urgent_sale_tier(basis: str) -> str:
    """Khodro45 urgent-sale: tag by nearest reference tier."""
    return {
        "down": DealTag.BEST.value,
        "mid": DealTag.GOOD.value,
        "up": DealTag.NORMAL.value,
    }[basis]


def _evaluate_single_tier(
    listing_price: int,
    reference_price: int,
    near_threshold_pct: float,
) -> tuple[bool, bool, int, Decimal, Decimal]:
    discount_amount = reference_price - listing_price
    discount_pct = (
        Decimal(str(round((discount_amount / reference_price) * 100, 2)))
        if reference_price
        else Decimal("0")
    )
    is_below = listing_price <= reference_price
    is_near = listing_price <= int(reference_price * (1 + near_threshold_pct))
    is_opportunity = is_below or is_near
    score = Decimal(str(max(0, discount_amount)))
    return is_opportunity, is_below, discount_amount, discount_pct, score


def _build_tier_match(
    listing_price: int,
    basis: str,
    reference_price: int,
    deal_tag: str,
) -> PriceTierMatch:
    discount_amount = reference_price - listing_price
    discount_pct = (
        Decimal(str(round((discount_amount / reference_price) * 100, 2)))
        if reference_price
        else Decimal("0")
    )
    is_below = listing_price <= reference_price
    score = Decimal(str(max(0, discount_amount)))
    return PriceTierMatch(
        basis=basis,
        reference_price=reference_price,
        is_below=is_below,
        discount_amount=discount_amount,
        discount_pct=discount_pct,
        score=score,
        deal_tag=deal_tag,
    )


def is_urgent_sale_in_valid_range(
    listing_price: int,
    price_down: int | None,
    price_mid: int | None,
    price_up: int | None,
) -> bool:
    """True when listing price is within Khodro45 urgent-sale [left, right] band."""
    if not price_down or not price_mid or not price_up:
        return False
    if not (price_up > price_mid > price_down > 0):
        return False
    return price_down <= listing_price <= price_up


def _closest_urgent_sale_tier(
    listing_price: int,
    price_down: int,
    price_mid: int,
    price_up: int,
) -> tuple[str, int]:
    """
    Pick the nearest urgent-sale anchor (left / middle / right).
    Ties prefer the lower (cheaper) tier: down, then mid, then up.
    """
    tier_order = {"down": 0, "mid": 1, "up": 2}
    tiers = (
        ("down", price_down),
        ("mid", price_mid),
        ("up", price_up),
    )
    basis, reference = min(
        tiers,
        key=lambda item: (abs(listing_price - item[1]), tier_order[item[0]]),
    )
    return basis, reference


def _build_urgent_sale_match(
    listing_price: int,
    price_down: int,
    price_mid: int,
    price_up: int,
) -> PriceTierMatch:
    """Tag by nearest tier; discount always measured against ceiling (right/max)."""
    basis, _ = _closest_urgent_sale_tier(listing_price, price_down, price_mid, price_up)
    discount_amount = price_up - listing_price
    discount_pct = (
        Decimal(str(round((discount_amount / price_up) * 100, 2))) if price_up else Decimal("0")
    )
    return PriceTierMatch(
        basis=basis,
        reference_price=price_up,
        is_below=listing_price <= price_up,
        discount_amount=discount_amount,
        discount_pct=discount_pct,
        score=Decimal(str(max(0, discount_amount))),
        deal_tag=deal_tag_for_urgent_sale_tier(basis),
    )


def evaluate_urgent_sale_opportunity(
    listing_price: int,
    price_down: int | None,
    price_mid: int | None,
    price_up: int | None,
) -> list[PriceTierMatch]:
    """
    Khodro45 urgent-sale (قیمت فروش فوری) opportunity rules:

    - Valid only when left <= listing <= right (inclusive).
    - Below left or above right → no opportunity.
    - Exactly one opportunity per listing, tagged by nearest tier:
      near left → best, near middle → good, near right → normal.
    - Discount is always vs ceiling (right / max), never negative in-range.
    """
    if not price_down or not price_mid or not price_up:
        return []
    if not (price_up > price_mid > price_down > 0):
        return []
    if listing_price < price_down or listing_price > price_up:
        return []

    return [_build_urgent_sale_match(listing_price, price_down, price_mid, price_up)]


def deal_tag_for_hamrah_tier(basis: str) -> str:
    """Hamrah Mechanic: tag by nearest tier; ceiling for discount is always mid."""
    return {
        "down": DealTag.BEST.value,
        "mid": DealTag.GOOD.value,
    }[basis]


def _closest_hamrah_tier(
    listing_price: int,
    price_down: int,
    price_mid: int,
) -> tuple[str, int]:
    """Pick nearest Hamrah anchor (floor / mid). Ties prefer floor."""
    tier_order = {"down": 0, "mid": 1}
    tiers = (("down", price_down), ("mid", price_mid))
    basis, reference = min(
        tiers,
        key=lambda item: (abs(listing_price - item[1]), tier_order[item[0]]),
    )
    return basis, reference


def _build_hamrah_match(
    listing_price: int,
    price_down: int,
    price_mid: int,
) -> PriceTierMatch:
    """Discount and ceiling reference always use Hamrah mid price (not max)."""
    basis, _ = _closest_hamrah_tier(listing_price, price_down, price_mid)
    discount_amount = price_mid - listing_price
    discount_pct = (
        Decimal(str(round((discount_amount / price_mid) * 100, 2))) if price_mid else Decimal("0")
    )
    return PriceTierMatch(
        basis=basis,
        reference_price=price_mid,
        is_below=listing_price <= price_mid,
        discount_amount=discount_amount,
        discount_pct=discount_pct,
        score=Decimal(str(max(0, discount_amount))),
        deal_tag=deal_tag_for_hamrah_tier(basis),
    )


def evaluate_hamrah_mechanic_opportunity(
    listing_price: int,
    price_down: int | None,
    price_mid: int | None,
    price_up: int | None = None,
    near_threshold_pct: float = 0.02,
) -> list[PriceTierMatch]:
    """
    Hamrah Mechanic opportunity rules:

    - Mid price is the ceiling reference (price_up/max is not used).
    - Valid only when floor <= listing <= mid (inclusive).
    - Below floor or above mid → no opportunity.
    - Exactly one opportunity per listing; discount always vs mid.
    """
    del price_up, near_threshold_pct
    if not price_down or not price_mid:
        return []
    if not (price_mid > price_down > 0):
        return []
    if listing_price < price_down or listing_price > price_mid:
        return []
    return [_build_hamrah_match(listing_price, price_down, price_mid)]


def evaluate_opportunity_tiers(
    listing_price: int,
    price_down: int | None,
    price_mid: int | None,
    price_up: int | None = None,
    near_threshold_pct: float = 0.02,
) -> list[PriceTierMatch]:
    """Hamrah / legacy: return one match per reference tier (low + mid) that qualifies."""
    del price_up
    if price_down and price_down > 0 and listing_price < price_down:
        return []

    tiers: list[tuple[str, int]] = []
    if price_down and price_down > 0:
        tiers.append(("down", price_down))
    if price_mid and price_mid > 0 and (not price_down or price_mid != price_down):
        tiers.append(("mid", price_mid))

    matches: list[PriceTierMatch] = []
    for basis, reference_price in tiers:
        is_opp, is_below, discount_amount, discount_pct, score = _evaluate_single_tier(
            listing_price, reference_price, near_threshold_pct
        )
        if is_opp:
            matches.append(
                PriceTierMatch(
                    basis=basis,
                    reference_price=reference_price,
                    is_below=is_below,
                    discount_amount=discount_amount,
                    discount_pct=discount_pct,
                    score=score,
                    deal_tag=deal_tag_for_match(basis, is_below),
                )
            )
    return matches


def evaluate_opportunity(
    listing_price: int,
    price_down: int,
    price_up: int,
    near_threshold_pct: float = 0.02,
) -> tuple[bool, bool, int, Decimal, Decimal]:
    """
    Backward-compatible helper using the low (down) tier only.
    Returns: is_opportunity, is_below_floor, discount_amount, discount_pct, score
    """
    del price_up
    if listing_price < price_down:
        return False, False, 0, Decimal("0"), Decimal("0")

    is_opp, is_below, discount_amount, discount_pct, score = _evaluate_single_tier(
        listing_price, price_down, near_threshold_pct
    )
    return is_opp, is_below, discount_amount, discount_pct, score
