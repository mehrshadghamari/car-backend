from src.domain.constants.opportunity_visibility import (
    CLIENT_VISIBLE_OPPORTUNITY_STATUSES,
    STAFF_REVIEWABLE_OPPORTUNITY_STATUSES,
    STAFF_SMS_ELIGIBLE_OPPORTUNITY_STATUSES,
)


def test_initial_opportunities_are_not_client_visible():
    assert "new" not in CLIENT_VISIBLE_OPPORTUNITY_STATUSES


def test_valid_opportunities_are_client_visible():
    assert "approved" in CLIENT_VISIBLE_OPPORTUNITY_STATUSES
    assert "notified" in CLIENT_VISIBLE_OPPORTUNITY_STATUSES


def test_only_new_opportunities_are_staff_reviewable():
    assert STAFF_REVIEWABLE_OPPORTUNITY_STATUSES == frozenset({"new"})


def test_only_valid_opportunities_are_sms_eligible():
    assert STAFF_SMS_ELIGIBLE_OPPORTUNITY_STATUSES == frozenset({"approved", "notified"})
