"""Product workflow states for opportunities.

These states organise research. They are not GTF methodology verdicts and never
override canonical_status or zone freshness.
"""

from __future__ import annotations

import sqlite3

from gtf_platform.errors import ApiError
from gtf_platform.opportunity import repository
from gtf_platform.store import new_id, record_audit, utcnow

WORKFLOW_STATES = frozenset(
    {
        "DISCOVERED",
        "UNDER_REVIEW",
        "SHORTLISTED",
        "REJECTED",
        "EXPIRED",
        "BLOCKED",
        "ARCHIVED",
    }
)

# Directed edges. Reopening is allowed only into UNDER_REVIEW and never resets
# canonical_status or zone evidence (those fields are immutable on the row).
_TRANSITIONS: dict[str, frozenset[str]] = {
    "DISCOVERED": frozenset({"UNDER_REVIEW", "SHORTLISTED", "REJECTED", "EXPIRED", "BLOCKED", "ARCHIVED"}),
    "UNDER_REVIEW": frozenset({"SHORTLISTED", "REJECTED", "EXPIRED", "BLOCKED", "ARCHIVED", "DISCOVERED"}),
    "SHORTLISTED": frozenset({"UNDER_REVIEW", "REJECTED", "EXPIRED", "BLOCKED", "ARCHIVED"}),
    "REJECTED": frozenset({"UNDER_REVIEW", "ARCHIVED"}),
    "EXPIRED": frozenset({"UNDER_REVIEW", "ARCHIVED"}),
    "BLOCKED": frozenset({"UNDER_REVIEW", "ARCHIVED", "EXPIRED"}),
    "ARCHIVED": frozenset({"UNDER_REVIEW"}),
}

DESTRUCTIVE_TARGETS = frozenset({"REJECTED", "EXPIRED", "ARCHIVED"})

# Shortlisting is desk organisation only, but must not look like a GTF pass when
# the stored canonical status is already non-qualifying.
_NON_QUALIFYING = frozenset({"BLOCKED", "REJECTED", "DATA_INSUFFICIENT"})


def allowed_transitions(state: str, *, canonical_status: str | None = None) -> list[str]:
    targets = set(_TRANSITIONS.get(state, frozenset()))
    if canonical_status in _NON_QUALIFYING:
        targets.discard("SHORTLISTED")
    return sorted(targets)


def apply_transition(
    connection: sqlite3.Connection,
    opportunity_id: str,
    *,
    to_state: str,
    actor: str,
    reason: str | None,
) -> dict:
    if to_state not in WORKFLOW_STATES:
        raise ApiError(400, "REQUEST_INVALID", "Unknown workflow state")
    row = repository.get_opportunity(connection, opportunity_id)
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Opportunity not found")
    from_state = row["workflow_state"]
    if to_state == from_state:
        raise ApiError(409, "CONFLICT", "Opportunity is already in that workflow state")
    if to_state not in _TRANSITIONS.get(from_state, frozenset()):
        raise ApiError(
            409,
            "CONFLICT",
            "Transition from %s to %s is not allowed" % (from_state, to_state),
        )
    if to_state == "SHORTLISTED" and row.get("canonical_status") in _NON_QUALIFYING:
        raise ApiError(
            409,
            "CONFLICT",
            "Cannot shortlist an opportunity whose stored canonical status is %s"
            % row.get("canonical_status"),
        )
    note = (reason or "").strip()
    if to_state in DESTRUCTIVE_TARGETS and not note:
        raise ApiError(400, "REQUEST_INVALID", "A reason is required for %s" % to_state)
    if len(note) > 500:
        raise ApiError(400, "REQUEST_INVALID", "Transition reason is too long")
    now = utcnow()
    history_id = new_id("oth")
    connection.execute(
        """
        UPDATE opportunity
        SET workflow_state = ?, updated_at = ?
        WHERE opportunity_id = ?
        """,
        (to_state, now, opportunity_id),
    )
    connection.execute(
        """
        INSERT INTO opportunity_transition (
            history_id, opportunity_id, from_state, to_state, actor, reason, at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (history_id, opportunity_id, from_state, to_state, actor, note or None, now),
    )
    after = repository.get_opportunity(connection, opportunity_id)
    record_audit(
        connection,
        actor=actor,
        action="opportunity.transition",
        object_id=opportunity_id,
        before=row,
        after=after,
    )
    # canonical_status is intentionally untouched.
    return after  # type: ignore[return-value]
