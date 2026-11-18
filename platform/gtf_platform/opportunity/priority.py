"""Organizational priority - descriptive ordering only.

Not a trading score. Not validated against returns (P7). Factors are transparent
and must never override canonical_status.
"""

from __future__ import annotations

from typing import Any

# Lower is higher priority for list ordering. Labels are for disclosure only.
_STATUS_WEIGHT = {
    "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING": 10,
    "MANUAL_REVIEW": 20,
    "DATA_INSUFFICIENT": 30,
    "BLOCKED": 40,
    "REJECTED": 50,
}

_WORKFLOW_WEIGHT = {
    "SHORTLISTED": 5,
    "UNDER_REVIEW": 10,
    "DISCOVERED": 15,
    "BLOCKED": 25,
    "REJECTED": 40,
    "EXPIRED": 45,
    "ARCHIVED": 50,
}

_QUALITY_WEIGHT = {
    "EXPLORATORY": 0,
    "UNKNOWN": 5,
    "UNAVAILABLE": 10,
    "FIXTURE": 20,
    # CERTIFIED reserved; if ever present it sorts ahead of exploratory.
    "CERTIFIED": -5,
}

DISCLOSURE = (
    "Organizational priority is a research-desk ordering aid. "
    "It does not predict returns, does not approve trades, and does not "
    "override the canonical scanner status."
)


def organizational_priority(row: dict[str, Any]) -> dict[str, Any]:
    status = str(row.get("canonical_status") or "")
    workflow = str(row.get("workflow_state") or "")
    quality = str(row.get("source_quality") or "UNKNOWN")
    fixture = bool(row.get("fixture"))
    if fixture:
        quality = "FIXTURE"
    score = (
        _STATUS_WEIGHT.get(status, 35)
        + _WORKFLOW_WEIGHT.get(workflow, 30)
        + _QUALITY_WEIGHT.get(quality, 5)
    )
    # Fixtures always sort after real exploratory rows with the same workflow.
    if fixture:
        score += 100
    return {
        "score": score,
        "factors": {
            "canonical_status_weight": _STATUS_WEIGHT.get(status, 35),
            "workflow_weight": _WORKFLOW_WEIGHT.get(workflow, 30),
            "source_quality_weight": _QUALITY_WEIGHT.get(quality, 5),
            "fixture_penalty": 100 if fixture else 0,
        },
        "authoritative": False,
        "disclosure": DISCLOSURE,
    }
