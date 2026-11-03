"""NSE demand and supply research pipeline: top-down analysis, G0-G8 qualification,
scanning, reports and readiness. Standard library only.

It is a research and decision-support tool. It never places, modifies or cancels an
order, never connects to a broker or network, and never approves a trade: the best
status any result can reach is ACTIONABLE CANDIDATE: MANUAL CHECKS PENDING
(nse/docs/IMPLEMENTATION_SPECIFICATION.md section 8).

Execution zones come only from nse/mtf-freshness MtfSnapshot.eligible_after_overlay and
manual_review_after_overlay (audit M4). Nothing here re-runs or bypasses the Zone Engine.
"""

import os as _os
import sys as _sys
import time as _time

_sys.dont_write_bytecode = True     # scans and tests leave no __pycache__ in the working tree


def _drop_own_cache():
    cached = globals().get("__cached__")
    if cached and _os.path.isfile(cached) and _time.time() - _os.path.getmtime(cached) <= 10:
        _os.remove(cached)
        folder = _os.path.dirname(cached)
        if not _os.listdir(folder):
            _os.rmdir(folder)


try:
    _drop_own_cache()
except OSError:
    pass
