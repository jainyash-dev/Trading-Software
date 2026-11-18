"""Opportunity intelligence: workflow metadata over stored scan candidates.

Does not compute GTF eligibility. Canonical status is copied from the stored
research envelope and never rewritten by lifecycle transitions.
"""

from gtf_platform.opportunity.ingest import ingest_scan
from gtf_platform.opportunity.lifecycle import (
    WORKFLOW_STATES,
    apply_transition,
    allowed_transitions,
)
from gtf_platform.opportunity.priority import organizational_priority
from gtf_platform.opportunity.repository import (
    add_note,
    get_opportunity,
    list_history,
    list_notes,
    list_opportunities,
    opportunity_view,
)

__all__ = [
    "WORKFLOW_STATES",
    "add_note",
    "allowed_transitions",
    "apply_transition",
    "get_opportunity",
    "ingest_scan",
    "list_history",
    "list_notes",
    "list_opportunities",
    "opportunity_view",
    "organizational_priority",
]
