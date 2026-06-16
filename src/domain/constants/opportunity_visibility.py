"""Which opportunity statuses are visible to end users (client app)."""

CLIENT_VISIBLE_OPPORTUNITY_STATUSES: frozenset[str] = frozenset({"approved", "notified"})

# Staff can mark initial (new) opportunities as valid (approved) or rejected.
STAFF_REVIEWABLE_OPPORTUNITY_STATUSES: frozenset[str] = frozenset({"new"})

# Only validated opportunities may be sent via SMS (gateway or portal share).
STAFF_SMS_ELIGIBLE_OPPORTUNITY_STATUSES: frozenset[str] = frozenset({"approved", "notified"})
