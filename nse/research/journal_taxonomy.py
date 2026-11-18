"""Controlled journal review taxonomy for GTF P6.

Aligned to Rulebook Part 7 Chapter 5 (RB 3708-3774): process quality is separate from
financial outcome. A profitable trade is not automatically good; a loss is not
automatically a mistake. This module defines identifiers only. It does not invent
Rulebook rules or grade trades automatically.
"""

TAXONOMY_VERSION = "P6-RB-1"

# RB 3746-3758 outcome classes (owner-assigned).
OUTCOME_CLASSES = (
    "NOT_REVIEWED",
    "DISCIPLINE_LOSS",      # broke a rule and lost
    "PROBABILITY_LOSS",     # followed rules; loss is the cost of probability
    "DISCIPLINE_WIN",       # followed rules and won
    "LUCKY_WIN",            # broke a rule but still won
    "NOT_CLASSIFIED",
)

# Process/mistake categories (orthogonal to PnL).
MISTAKE_CATEGORIES = (
    "NOT_REVIEWED",
    "NONE",                 # no identified mistake
    "RULE_VIOLATION",
    "EXECUTION",
    "PLANNING",
    "RISK_MANAGEMENT",
    "DATA_LIMITATION",
    "PSYCHOLOGY",
)

REVIEW_STATUSES = ("NOT_REVIEWED", "REVIEWED")

NOTE_KINDS = (
    "PRE_TRADE_THESIS",
    "ENTRY_REASONING",
    "MARKET_CONTEXT",
    "EXIT_REASONING",
    "POST_TRADE_REVIEW",
    "LESSON",
    "FOLLOW_UP",
    "GENERAL",
)

OUTCOME_DEFINITIONS = {
    "NOT_REVIEWED": "Owner has not assigned an outcome class.",
    "DISCIPLINE_LOSS": "Rule broken and trade lost (RB 3748-3750).",
    "PROBABILITY_LOSS": "Rules followed; loss is probability cost (RB 3750-3751).",
    "DISCIPLINE_WIN": "Rules followed and trade won (RB 3755-3756).",
    "LUCKY_WIN": "Rule broken but trade won; still a process failure (RB 3757-3760).",
    "NOT_CLASSIFIED": "Reviewed without choosing a Rulebook outcome class.",
}

MISTAKE_DEFINITIONS = {
    "NOT_REVIEWED": "Mistake category not yet assigned.",
    "NONE": "No identified process mistake.",
    "RULE_VIOLATION": "An explicit Rulebook or checklist rule was broken.",
    "EXECUTION": "Fill timing, quantity, or order handling issue.",
    "PLANNING": "Plan construction, levels, or thesis issue.",
    "RISK_MANAGEMENT": "Sizing, stop handling, or portfolio-limit issue.",
    "DATA_LIMITATION": "Missing or incomplete data/evidence constrained the review.",
    "PSYCHOLOGY": "Discipline or emotional observation without a specific rule id.",
}


def validate_review(*, review_status, outcome_class, mistake_category, taxonomy_version):
    """Return None or raise ValueError with a clear message."""
    if taxonomy_version != TAXONOMY_VERSION:
        raise ValueError("unsupported taxonomy_version %r (expected %s)" % (taxonomy_version, TAXONOMY_VERSION))
    if review_status not in REVIEW_STATUSES:
        raise ValueError("unknown review_status %r" % (review_status,))
    if outcome_class not in OUTCOME_CLASSES:
        raise ValueError("unknown outcome_class %r" % (outcome_class,))
    if mistake_category not in MISTAKE_CATEGORIES:
        raise ValueError("unknown mistake_category %r" % (mistake_category,))
    if review_status == "NOT_REVIEWED":
        if outcome_class not in ("NOT_REVIEWED", "NOT_CLASSIFIED"):
            raise ValueError("NOT_REVIEWED status cannot carry a finished outcome_class")
        if mistake_category not in ("NOT_REVIEWED", "NONE"):
            raise ValueError("NOT_REVIEWED status cannot carry a finished mistake_category")
    if outcome_class in ("DISCIPLINE_LOSS", "LUCKY_WIN") and mistake_category == "NONE":
        raise ValueError("%s requires a mistake_category other than NONE" % outcome_class)
    if outcome_class == "PROBABILITY_LOSS" and mistake_category not in ("NONE", "DATA_LIMITATION"):
        raise ValueError("PROBABILITY_LOSS should use mistake_category NONE or DATA_LIMITATION")
    if outcome_class == "DISCIPLINE_WIN" and mistake_category not in ("NONE", "DATA_LIMITATION"):
        raise ValueError("DISCIPLINE_WIN should use mistake_category NONE or DATA_LIMITATION")
