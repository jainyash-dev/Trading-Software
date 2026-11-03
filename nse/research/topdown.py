"""Top-down analysis table (spec 7.1; D11): Y -> HY -> Q -> M -> W -> execution TF.

For every timeframe: whether it is available, how many completed candles it has, the
nearest FRESH demand zone below and FRESH supply zone above the price, and any zone of
unknown freshness that sits closer than those (so "none found" is never confused with
"could not be determined"). Tested zones are counted, never listed as zone results (D3).
"""

from nse.research import models as m
from nse.research import structure


def _nearest(views, side, price):
    if side == "demand":
        cands = sorted((v for v in views if v.side == side and v.active and v.proximal < price),
                       key=lambda v: -v.proximal)
    else:
        cands = sorted((v for v in views if v.side == side and v.active and v.proximal > price),
                       key=lambda v: v.proximal)
    unknown_closer = []
    for v in cands:
        if v.freshness == m.Z_FRESH:
            return v.brief(), [u.brief() for u in unknown_closer]
        if v.freshness == m.Z_UNKNOWN:
            unknown_closer.append(v)
    return None, [u.brief() for u in unknown_closer]


def tda(snapshot, price, timeframes):
    rows = []
    for tf in timeframes:
        st = structure.series_status(snapshot, tf)
        row = {"tf": tf, "series": st, "fresh_demand_below": None, "fresh_supply_above": None,
               "unknown_freshness_closer": [], "zone_counts": {}, "missing": []}
        views = structure.zone_views(snapshot, tf)
        if st["status"] != structure.AVAILABLE:
            row["missing"].append("%s: %s" % (tf, st["status"]))
        if views is not None:
            row["fresh_demand_below"], ud = _nearest(views, "demand", price)
            row["fresh_supply_above"], us = _nearest(views, "supply", price)
            row["unknown_freshness_closer"] = ud + us
            counts = {}
            for v in views:
                counts[v.freshness] = counts.get(v.freshness, 0) + 1
            row["zone_counts"] = dict(sorted(counts.items()))
            if row["fresh_demand_below"] is None:
                row["missing"].append("no fresh demand zone below the price" +
                                      (" found; closer zones have unknown freshness" if ud else " found"))
            if row["fresh_supply_above"] is None:
                row["missing"].append("no fresh supply zone above the price" +
                                      (" found; closer zones have unknown freshness" if us else " found"))
        rows.append(row)
    return rows
