"""Pre-entry X/14 score display (spec 5.1, 5.3; D4; RB 846-1001, 1027-1033). INFORMATION ONLY.

Nothing here feeds a gate or a status: G2 requires the core 7/7 and the rest of the
qualification is G3-G8. The Rulebook's confluence factors are shown the way spec 5.1
decides, so the trader sees them without the system pretending to have judged them:

  core (7)        engine score, evaluated (G2 decides eligibility, not this module)
  sector (+2)     NOT_EVALUATED (D6): never 0, shown as "max +2" in the upper bound
  HTF EMA 20 (+2) PROVISIONAL: count of higher timeframes whose EMA 20 at as_of lies inside
                  the execution zone range (RB 506, 904-908). The "trending timeframe only"
                  condition (RB 511, 915) is a manual check, so the points are provisional
  crossover (+1)  PROVISIONAL: EMA 20 crossed above EMA 50 on the execution timeframe after
                  the zone was created, with the cross inside the zone range (RB 570, 925);
                  "trending market" is a manual check
  gap (+1)        PROVISIONAL: the zone has a gap (engine has_gap); meaningfulness is manual
                  (RB 941, 960) and the strength / gap double count is unresolved (N6)
  RSI/Stoch (+1)  NOT_EVALUATED pre-entry (spec 5.1)
  pattern         post-entry journal field only (D4), never counted here

EMA: standard exponential average seeded with the SMA of the first 20 completed closes,
the usual Pine ta.ema convention; TradingView parity is NOT verified (B8). A timeframe
with fewer than PERIOD completed candles, or a truncated series, is reported and counts 0
with the reason shown (unknown is never a point).
"""

from nse.research import structure

EMA_FAST = 20
EMA_SLOW = 50
EVALUATED = "EVALUATED"
PROVISIONAL = "PROVISIONAL"
NOT_EVALUATED = "NOT_EVALUATED"

PART_E = ((12, "Exceptional"), (10, "Very Strong"), (8, "Good"), (7, "Minimum Acceptable"))  # RB 1027-1033


def ema_series(values, n):
    """EMA values aligned with values (None before the seed). SMA seed of the first n."""
    out = [None] * len(values)
    if len(values) < n:
        return out
    alpha = 2.0 / (n + 1)
    e = sum(values[:n]) / float(n)
    out[n - 1] = e
    for i in range(n, len(values)):
        e = alpha * values[i] + (1 - alpha) * e
        out[i] = e
    return out


def part_e(total):
    for floor, name in PART_E:
        if total >= floor:
            return name
    return "Reject"


def _inside(v, lo, hi):
    return v is not None and lo <= v <= hi


def htf_ema20(snapshot, htfs, lo, hi):
    rows, count = [], 0
    for tf in htfs:
        st = structure.series_status(snapshot, tf)
        s = snapshot.series.get(tf)
        if st["status"] in (structure.NOT_REQUESTED, structure.TRUNCATED, structure.NO_COMPLETED_CANDLES) or s is None:
            rows.append({"tf": tf, "ema20": None, "inside_zone": None, "reason": "series %s" % st["status"]})
            continue
        closes = [c.close for c in s.candles]
        if len(closes) < EMA_FAST:
            rows.append({"tf": tf, "ema20": None, "inside_zone": None,
                         "reason": "%d of %d completed candles" % (len(closes), EMA_FAST)})
            continue
        e = ema_series(closes, EMA_FAST)[-1]
        inside = _inside(e, lo, hi)
        count += 1 if inside else 0
        rows.append({"tf": tf, "ema20": round(e, 4), "inside_zone": inside, "reason": None})
    return min(2, count), rows


def crossover(exec_candles, created_index, lo, hi):
    closes = [c.close for c in exec_candles]
    fast, slow = ema_series(closes, EMA_FAST), ema_series(closes, EMA_SLOW)
    for i in range(created_index + 1, len(closes)):          # after creation: RB 570 'pre-existing'
        if None in (fast[i], slow[i], fast[i - 1], slow[i - 1]):
            continue
        if fast[i - 1] <= slow[i - 1] and fast[i] > slow[i] and _inside(fast[i], lo, hi):
            return 1, {"cross_time": exec_candles[i].end.isoformat(), "ema20": round(fast[i], 4),
                       "ema50": round(slow[i], 4)}
    if len(closes) < EMA_SLOW:
        return 0, {"reason": "%d of %d completed candles for EMA 50" % (len(closes), EMA_SLOW)}
    return 0, {"reason": "no golden cross inside the zone after its creation"}


def score14(snapshot, exec_tf, htfs, assessment):
    """The spec 5.3 display for one execution zone assessment."""
    z = assessment.zone
    lo, hi = min(z.proximal, z.distal), max(z.proximal, z.distal)
    core = assessment.score.core
    exec_series = snapshot.series.get(exec_tf)
    exec_candles = exec_series.candles if exec_series else []
    ema_pts, ema_rows = htf_ema20(snapshot, htfs, lo, hi)
    x_pts, x_ev = crossover(exec_candles, z.created_index, lo, hi)
    gap_pts = 1 if z.has_gap else 0
    items = [
        {"factor": "core", "max": 7, "points": core, "state": EVALUATED, "source": "RB 661, 829; G2"},
        {"factor": "sector", "max": 2, "points": None, "state": NOT_EVALUATED, "source": "D6; RB 484-499, 851-895"},
        {"factor": "htf_ema20", "max": 2, "points": ema_pts, "state": PROVISIONAL,
         "manual": "only TRENDING timeframes count; EMA slicing candle bodies is ignored (RB 511, 513, 915)",
         "evidence": ema_rows, "source": "RB 500-516, 896-918"},
        {"factor": "crossover", "max": 1, "points": x_pts, "state": PROVISIONAL,
         "manual": "valid only in a TRENDING market (RB 570, 925)", "evidence": x_ev, "source": "RB 565-573, 919-933"},
        {"factor": "gap", "max": 1, "points": gap_pts, "state": PROVISIONAL,
         "manual": "gap meaningfulness (RB 941, 960); strength/gap double count unresolved (N6)",
         "evidence": {"has_gap": z.has_gap, "gap_size": z.gap_size}, "source": "RB 934-964"},
        {"factor": "rsi_stochastic", "max": 1, "points": None, "state": NOT_EVALUATED,
         "source": "spec 5.1; RB 574-583, 965-987"},
    ]
    evaluated = sum(i["points"] for i in items if i["points"] is not None)
    upper = evaluated + sum(i["max"] for i in items if i["state"] == NOT_EVALUATED)
    provisional = [i for i in items if i["state"] == PROVISIONAL]
    display = ("Core: %g/7 | Pre-entry: %g/14 evaluated (provisional: %s); not evaluated: sector (max +2), "
               "RSI/Stoch (max +1); upper bound: %g/14"
               % (core, evaluated, ", ".join("%s +%d" % (i["factor"], i["points"]) for i in provisional), upper))
    return {"items": items, "evaluated": evaluated, "upper_bound": upper, "display": display,
            "part_e_evaluated": part_e(evaluated), "part_e_upper_bound": part_e(upper),
            "note": "information only; no gate or status uses this score (spec 5.1, D4). "
                    "EMA values not compared with TradingView (B8)."}
