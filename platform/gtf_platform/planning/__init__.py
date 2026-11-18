"""Trade-planning desk helpers for GTF P4.

Eligibility stays in the canonical research pipeline. Caps and ED-3 stay in the
research journal via the desk adapter. This package extends the platform
trade_plan row with lifecycle, audit, notes and preview enrichment. It never
places an order.
"""

from gtf_platform.planning import service
from gtf_platform.planning.states import PLAN_STATES, allowed_transitions

__all__ = ["PLAN_STATES", "allowed_transitions", "service"]
