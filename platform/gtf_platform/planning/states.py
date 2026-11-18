"""Platform trade-plan lifecycle states.

These organise the planning desk. They do not override candidate_status,
zone freshness, or journal cap/ED-3 enforcement.
"""

from __future__ import annotations

PLAN_STATES = frozenset(
    {
        "DRAFT",
        "AWAITING_OWNER",
        "APPROVED",
        "REJECTED",
        "CANCELLED",
        "EXPIRED",
    }
)

# Directed edges for platform-row transitions. Journal-derived display states
# (ORDER_RECORDED / FILLED / CLOSED) are enrichment only and are not stored here.
_TRANSITIONS: dict[str, frozenset[str]] = {
    "DRAFT": frozenset({"AWAITING_OWNER", "APPROVED", "REJECTED", "CANCELLED"}),
    "AWAITING_OWNER": frozenset({"DRAFT", "APPROVED", "REJECTED", "CANCELLED"}),
    "APPROVED": frozenset({"CANCELLED", "EXPIRED"}),
    "REJECTED": frozenset({"DRAFT"}),
    "CANCELLED": frozenset(),
    "EXPIRED": frozenset(),
}

# Approval may proceed from DRAFT (existing P1 path) or AWAITING_OWNER (explicit review).
APPROVABLE = frozenset({"DRAFT", "AWAITING_OWNER"})
CANCELABLE = frozenset({"DRAFT", "AWAITING_OWNER", "APPROVED"})
REJECTABLE = frozenset({"DRAFT", "AWAITING_OWNER"})


def allowed_transitions(state: str) -> list[str]:
    return sorted(_TRANSITIONS.get(state, frozenset()))


def can_transition(from_state: str, to_state: str) -> bool:
    return to_state in _TRANSITIONS.get(from_state, frozenset())
