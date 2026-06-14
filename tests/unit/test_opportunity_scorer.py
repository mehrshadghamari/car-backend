from decimal import Decimal

from src.domain.entities.opportunity import DealTag
from src.domain.services.opportunity_scorer import (
    deal_tag_for_hamrah_tier,
    deal_tag_for_match,
    deal_tag_for_urgent_sale_tier,
    evaluate_hamrah_mechanic_opportunity,
    evaluate_opportunity,
    evaluate_opportunity_tiers,
    evaluate_urgent_sale_opportunity,
)

# Khodro45 urgent-sale sample (smaple-khodro45.html)
LEFT = 1_911_000_000
MID = 2_033_000_000
RIGHT = 2_074_000_000


def test_urgent_sale_below_left_is_rejected():
    assert evaluate_urgent_sale_opportunity(1_900_000_000, LEFT, MID, RIGHT) == []


def test_urgent_sale_above_right_is_rejected():
    assert evaluate_urgent_sale_opportunity(2_075_000_000, LEFT, MID, RIGHT) == []


def test_urgent_sale_at_left_is_best():
    matches = evaluate_urgent_sale_opportunity(LEFT, LEFT, MID, RIGHT)
    assert len(matches) == 1
    assert matches[0].basis == "down"
    assert matches[0].deal_tag == DealTag.BEST.value
    assert matches[0].reference_price == RIGHT
    assert matches[0].discount_amount == RIGHT - LEFT


def test_urgent_sale_discount_uses_ceiling():
    matches = evaluate_urgent_sale_opportunity(1_810_000_000, 1_757_000_000, 1_869_000_000, 1_906_000_000)
    assert len(matches) == 1
    assert matches[0].reference_price == 1_906_000_000
    assert matches[0].discount_amount == 96_000_000
    assert matches[0].discount_pct > 0


def test_urgent_sale_at_middle_is_good():
    matches = evaluate_urgent_sale_opportunity(MID, LEFT, MID, RIGHT)
    assert len(matches) == 1
    assert matches[0].basis == "mid"
    assert matches[0].deal_tag == DealTag.GOOD.value


def test_urgent_sale_at_right_is_normal():
    matches = evaluate_urgent_sale_opportunity(RIGHT, LEFT, MID, RIGHT)
    assert len(matches) == 1
    assert matches[0].basis == "up"
    assert matches[0].deal_tag == DealTag.NORMAL.value


def test_urgent_sale_near_left_tags_best():
    matches = evaluate_urgent_sale_opportunity(1_970_000_000, LEFT, MID, RIGHT)
    assert matches[0].deal_tag == DealTag.BEST.value
    assert matches[0].basis == "down"


def test_urgent_sale_near_middle_tags_good():
    matches = evaluate_urgent_sale_opportunity(2_050_000_000, LEFT, MID, RIGHT)
    assert matches[0].deal_tag == DealTag.GOOD.value
    assert matches[0].basis == "mid"


def test_urgent_sale_near_right_tags_normal():
    matches = evaluate_urgent_sale_opportunity(2_065_000_000, LEFT, MID, RIGHT)
    assert matches[0].deal_tag == DealTag.NORMAL.value
    assert matches[0].basis == "up"


def test_urgent_sale_returns_single_match_only():
    matches = evaluate_urgent_sale_opportunity(2_000_000_000, LEFT, MID, RIGHT)
    assert len(matches) == 1


def test_deal_tag_for_urgent_sale_tier():
    assert deal_tag_for_urgent_sale_tier("down") == DealTag.BEST.value
    assert deal_tag_for_urgent_sale_tier("mid") == DealTag.GOOD.value
    assert deal_tag_for_urgent_sale_tier("up") == DealTag.NORMAL.value


def test_is_urgent_sale_in_valid_range():
    from src.domain.services.opportunity_scorer import is_urgent_sale_in_valid_range

    assert is_urgent_sale_in_valid_range(2_000_000_000, LEFT, MID, RIGHT) is True
    assert is_urgent_sale_in_valid_range(1_804_000_000, 1_663_000_000, 1_769_000_000, 1_804_000_000) is True
    assert is_urgent_sale_in_valid_range(1_900_000_000, 1_663_000_000, 1_769_000_000, 1_804_000_000) is False


def test_below_floor_is_not_opportunity_legacy():
    is_opp, is_below, discount, pct, score = evaluate_opportunity(
        listing_price=1800000000,
        price_down=1828000000,
        price_up=1981000000,
    )
    assert is_opp is False
    assert is_below is False
    assert discount == 0
    assert score == 0


def test_hamrah_above_mid_is_rejected():
    assert evaluate_hamrah_mechanic_opportunity(2_100_000_000, 1_828_000_000, 1_950_000_000, 2_100_000_000) == []


def test_hamrah_below_floor_is_rejected():
    assert evaluate_hamrah_mechanic_opportunity(1_800_000_000, 1_828_000_000, 1_950_000_000, 2_100_000_000) == []


def test_hamrah_discount_uses_mid_not_max():
    matches = evaluate_hamrah_mechanic_opportunity(1_900_000_000, 1_828_000_000, 1_950_000_000, 2_100_000_000)
    assert len(matches) == 1
    assert matches[0].reference_price == 1_950_000_000
    assert matches[0].discount_amount == 50_000_000
    assert matches[0].discount_pct == Decimal("2.56")


def test_hamrah_at_mid_is_good():
    matches = evaluate_hamrah_mechanic_opportunity(1_950_000_000, 1_828_000_000, 1_950_000_000, 2_100_000_000)
    assert len(matches) == 1
    assert matches[0].basis == "mid"
    assert matches[0].deal_tag == DealTag.GOOD.value
    assert matches[0].discount_amount == 0


def test_hamrah_near_floor_is_best():
    matches = evaluate_hamrah_mechanic_opportunity(1_830_000_000, 1_828_000_000, 1_950_000_000, 2_100_000_000)
    assert matches[0].deal_tag == DealTag.BEST.value
    assert matches[0].basis == "down"


def test_hamrah_returns_single_match_only():
    matches = evaluate_hamrah_mechanic_opportunity(1_900_000_000, 1_828_000_000, 1_950_000_000, 2_100_000_000)
    assert len(matches) == 1


def test_deal_tag_for_hamrah_tier():
    assert deal_tag_for_hamrah_tier("down") == DealTag.BEST.value
    assert deal_tag_for_hamrah_tier("mid") == DealTag.GOOD.value


def test_hamrah_mid_tier_creates_separate_match():
    matches = evaluate_opportunity_tiers(
        listing_price=1900000000,
        price_down=1828000000,
        price_mid=1950000000,
        price_up=2100000000,
        near_threshold_pct=0.02,
    )
    bases = {m.basis for m in matches}
    assert "mid" in bases
    assert "down" not in bases


def test_deal_tags_for_hamrah_legacy():
    assert deal_tag_for_match("down", True) == DealTag.BEST.value
    assert deal_tag_for_match("mid", True) == DealTag.GOOD.value
    assert deal_tag_for_match("mid", False) == DealTag.FAIR.value
