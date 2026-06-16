"""Which opportunity statuses are visible to end users (client app)."""

CLIENT_VISIBLE_OPPORTUNITY_STATUSES: frozenset[str] = frozenset({"approved", "notified"})

STAFF_REVIEWABLE_OPPORTUNITY_STATUSES: frozenset[str] = frozenset({"new", "approved", "notified"})
