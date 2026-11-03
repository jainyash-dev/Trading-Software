"""Entry, stop-loss, target and R:R ranges (spec 6; D7, D9, B9).

No buffer value is chosen. Every tier that could apply is used and the result is a
range (spec 6.3):
  - tiers are the rulebook's printed ranges (RB 2016-2020 entry, RB 2097-2102 SL);
  - which price selects the tier is unresolved (B9), so the tiers of the zone's PL and
    both DLs all count, and tier edges are inclusive on both sides (B9 overlapping edges);
  - SL ranges are given for the normal and the exceptional DL (RB 2116-2128);
  - the volatility increase of the SL buffer (RB 2108-2110) is a manual consideration and
    is not applied numerically.
R:R status over every combination: PASS_ALL (>= 2 everywhere), FAIL_ALL (< 2 everywhere,
RF8) or DEPENDS_ON_BUFFER (manual). The 2:1 threshold is the rulebook's (RB 82, RF8).
"""

import math
from decimal import ROUND_FLOOR, Decimal

from nse.research import models as m

MIN_RR = 2.0                          # RB 82; RF8
INF = float("inf")
# (price low, price high, entry buffer min, max, SL buffer min, max), as printed
TIERS = (
    (0.0, 100.0, 0.25, 0.50, 0.50, 1.0),
    (100.0, 500.0, 0.50, 2.0, 1.0, 3.0),
    (500.0, 2000.0, 2.0, 5.0, 3.0, 8.0),
    (2000.0, INF, 5.0, 10.0, 8.0, 15.0),
)
PASS_ALL = "PASS_ALL"
FAIL_ALL = "FAIL_ALL"
DEPENDS_ON_BUFFER = "DEPENDS_ON_BUFFER"


def tiers_for(prices):
    return [t for t in TIERS if any(t[0] <= p <= t[1] for p in prices)]


def ranges(proximal, distal, normal_distal):
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in (proximal, distal, normal_distal)):
        return {"tiers": [], "entry": [None, None], "sl": {"normal": [None, None], "exceptional": [None, None]},
                "exceptional_dl": None, "manual_considerations": [],
                "problems": ["NON_FINITE_OR_NON_POSITIVE_ZONE_PRICE"], "valid": False}
    tiers = tiers_for([proximal, distal, normal_distal])
    e_min = proximal + min(t[2] for t in tiers)
    e_max = proximal + max(t[3] for t in tiers)
    sl_lo = min(t[4] for t in tiers)
    sl_hi = max(t[5] for t in tiers)
    sl = {"normal": [normal_distal - sl_hi, normal_distal - sl_lo],
          "exceptional": [distal - sl_hi, distal - sl_lo]}
    out = {"tiers": [list(t[:2]) if t[1] != INF else [t[0], None] for t in tiers],
            "entry": [round(e_min, 4), round(e_max, 4)],
            "sl": {k: [round(a, 4), round(b, 4)] for k, (a, b) in sl.items()},
            "exceptional_dl": distal != normal_distal,
            "manual_considerations": ["SL buffer +50-100% in volatile, news-driven markets (RB 2108-2110) "
                                      "is not applied numerically",
                                      "Shri Krishna SL (location-zone DL) is a reference only (RB 2116-2128)"]}
    out["problems"] = problems(proximal, distal, normal_distal, out)
    out["valid"] = not out["problems"]
    return out


def problems(proximal, distal, normal_distal, rng):
    """Reasons the levels cannot be used; an empty list means they are coherent. An invalid
    set is reported as such, never turned into a plausible R:R."""
    out = []
    vals = [proximal, distal, normal_distal] + list(rng["entry"]) + [v for pair in rng["sl"].values() for v in pair]
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in vals):
        return ["NON_FINITE_LEVEL"]
    if not proximal > normal_distal >= distal:
        out.append("ZONE_GEOMETRY_INVALID: demand needs PL above the normal DL, which is at or above the exceptional DL")
    if min(v for pair in rng["sl"].values() for v in pair) <= 0:
        out.append("STOP_LOSS_NOT_POSITIVE: the printed SL buffer exceeds the DL (tier 'Below 100')")
    if rng["entry"][0] > rng["entry"][1]:
        out.append("ENTRY_RANGE_INVERTED")
    return out


def rr_range(rng, target):
    e_min, e_max = rng["entry"]
    sl_all = [v for pair in rng["sl"].values() for v in pair]
    sl_lowest, sl_highest = min(sl_all), max(sl_all)
    worst = (target - e_max) / (e_max - sl_lowest)
    best = (target - e_min) / (e_min - sl_highest)
    if worst >= MIN_RR:
        status = PASS_ALL
    elif best < MIN_RR:
        status = FAIL_ALL
    else:
        status = DEPENDS_ON_BUFFER
    return {"rr": [round(worst, 4), round(best, 4)], "status": status,
            "risk_per_share": [round(e_min - sl_highest, 4), round(e_max - sl_lowest, 4)]}


def quantity_range(rng, risk_per_trade):
    """Qty = floor(RPT / (Entry - SL)) (RB 42, 2162, 2203-2204); RPT is a user input."""
    if risk_per_trade is None:
        return None
    # exact decimal arithmetic on the printed prices: float subtraction can make
    # 100.30 - 100.10 = 0.2000000000000028 and floor(1000 / it) = 4999 instead of 5000
    e_min, e_max = (Decimal(str(v)) for v in rng["entry"])
    sl_all = [Decimal(str(v)) for pair in rng["sl"].values() for v in pair]
    risks = [e_min - max(sl_all), e_max - min(sl_all)]
    rpt = Decimal(str(risk_per_trade))
    return [int((rpt / r).to_integral_value(rounding=ROUND_FLOOR)) for r in sorted(risks, reverse=True)]


def select_target(views, entry_max, exec_proximal):
    """Nearest FRESH opposing supply PL above the entry (RB 551-558, 2276-2280).
    Returns (zone or None, issue or None). A tested zone is skipped (the target must be
    fresh); a zone of unknown freshness, or one inside the entry range, stops the search."""
    supply = sorted((v for v in views if v.side == "supply" and v.active and v.proximal > exec_proximal),
                    key=lambda v: v.proximal)
    for v in supply:
        if v.proximal <= entry_max:
            return None, "TARGET_ZONE_INSIDE_ENTRY_RANGE %s" % v.zone_id
        if v.freshness == m.Z_FRESH:
            return v, None
        if v.freshness == m.Z_TESTED:
            continue
        return None, "TARGET_FRESHNESS_UNKNOWN %s" % v.zone_id
    return None, "NO_FRESH_SUPPLY_ABOVE_ENTRY"
