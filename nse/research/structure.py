"""Zone views, location (curve), HTF conflict and coinciding classification.

Everything here reads an existing MtfSnapshot (nse/mtf-freshness). Freshness is the
overlay's, never the Zone Engine's own view: a zone is FRESH only when the overlay says
usable_as_fresh_context; TESTED and INVALIDATED come from the overlay status; every other
overlay status (data gap, unverified session, pending close beyond the DL, unresolved
flag) is UNKNOWN, and UNKNOWN is never treated as fresh or as absent.

Sources: spec 7.2 (curve; RB 1578-1628), 7.4 (conflict; RB 601, 1302-1316, 1402),
7.5 (coinciding; D15; RB 528, 1826-1856). No tolerance or threshold is invented: the
only numbers are the rulebook's 33.33 / 66.66 levels and the 5% / 10% bands of spec 7.4.
"""

import math
from dataclasses import dataclass
from typing import List, Optional

from nse.research import models as m
from nse.research.deps import mtf

# series availability
AVAILABLE = "AVAILABLE"
NOT_REQUESTED = "NOT_REQUESTED"
NO_COMPLETED_CANDLES = "NO_COMPLETED_CANDLES"
INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"      # fewer candles than the engine needs
TRUNCATED = "TRUNCATED"                            # a gap or unresolved date ends the series

# curve positions (RB 1595-1601)
VLOC, LOC, EQB, HOC, VHOC = "VLOC", "LOC", "EQB", "HOC", "VHOC"
BELOW_CURVE, ABOVE_CURVE = "BELOW_CURVE", "ABOVE_CURVE"
LEVEL_LOW, LEVEL_HIGH = 33.33, 66.66               # RB 1590: 0 / 33.33 / 66.66 / 100

# coinciding classes (approved M1 R3; spec 7.5)
COINCIDING = "COINCIDING"
INVALID_BELOW_HTF_DL = "INVALID_BELOW_HTF_DL"
AGGRESSIVE = "AGGRESSIVE"
# Backward-compatible name for callers that used the old geometric case. New results
# report the approved, distinct classification.
ABOVE_HTF_PL = AGGRESSIVE
NO_QUALIFYING_HTF_ZONE = "NO_QUALIFYING_HTF_ZONE"
HTF_ZONE_STATUS_UNKNOWN = "HTF_ZONE_STATUS_UNKNOWN"
HTF_ZONE_DL_STATUS_UNKNOWN = HTF_ZONE_STATUS_UNKNOWN  # compatibility alias


@dataclass
class ZoneView:
    tf: str
    zone_id: str
    side: str
    pattern: str
    proximal: float
    distal: float
    normal_distal: float
    created_time: str
    freshness: str             # models.Z_*
    overlay_status: str
    overlay_reasons: List[str]
    dl_untouched: Optional[bool]   # None when a gap or unresolved session hides the answer
    engine_status: str
    core: float

    @property
    def active(self):
        return self.freshness != m.Z_INVALIDATED

    def brief(self):
        return {"tf": self.tf, "zone_id": self.zone_id, "side": self.side, "pattern": self.pattern,
                "proximal": self.proximal, "distal": self.distal, "freshness": self.freshness,
                "overlay_status": self.overlay_status, "created": self.created_time}


def freshness_of(state):
    if state is None:
        return m.Z_UNKNOWN
    if state.usable_as_fresh_context:
        return m.Z_FRESH
    if state.status == mtf.INVALIDATED:
        return m.Z_INVALIDATED
    if state.status == mtf.TESTED:
        return m.Z_TESTED
    return m.Z_UNKNOWN


def series_status(snapshot, tf):
    s = snapshot.series.get(tf)
    if s is None:
        return {"tf": tf, "status": NOT_REQUESTED, "completed_candles": 0}
    out = {"tf": tf, "completed_candles": len(s.candles), "truncated_at": s.truncated_at,
           "in_progress_period": s.in_progress_period, "reasons": list(s.reasons),
           "last_completed_period": s.candles[-1].period_key if s.candles else None}
    if s.truncated_at is not None:
        out["status"] = TRUNCATED
    elif not s.candles:
        out["status"] = NO_COMPLETED_CANDLES
    elif s.engine is None or s.engine.insufficient_history:
        out["status"] = INSUFFICIENT_HISTORY
    else:
        out["status"] = AVAILABLE
    return out


def zone_views(snapshot, tf):
    """Every zone the engine found on tf with the overlay's view of it (audit view;
    never a candidate list). None when the series has no engine run."""
    s = snapshot.series.get(tf)
    if s is None or s.engine is None:
        return None
    out = []
    for a in s.engine.assessments:
        z = a.zone
        st = snapshot.zones.get("%s:%s" % (tf, z.id))
        fr = freshness_of(st)
        if st is None or st.status in (mtf.UNKNOWN_DATA_GAP, mtf.UNVERIFIED_SESSION):
            dl_untouched = None if (st is None or st.dl_touched_at is None) else False
        else:
            dl_untouched = st.dl_touched_at is None and z.dl_touch_index is None
        out.append(ZoneView(
            tf=tf, zone_id=z.id, side=z.side, pattern=z.pattern, proximal=z.proximal,
            distal=z.distal, normal_distal=z.normal_distal,
            created_time=s.candles[z.created_index].end.isoformat(), freshness=fr,
            overlay_status=st.status if st else "NO_OVERLAY_STATE",
            overlay_reasons=list(st.reasons) + list(st.manual_review) if st else [],
            dl_untouched=dl_untouched, engine_status=a.status, core=a.score.core))
    return out


# --- location / curve ------------------------------------------------------------------

def build_curve(views, price, loc_highs):
    """Curve boundaries for the current price (RB 1586-1590): nearest FRESH demand below
    and FRESH supply above. A tested zone is skipped (RB 1587, situation 3); a zone of
    unknown freshness stops the search, because it may be the true boundary."""
    out = {"price": price, "bottom": None, "top": None, "skipped_tested": [], "issues": []}
    demand = [v for v in views if v.side == "demand" and v.active]
    supply = [v for v in views if v.side == "supply" and v.active]

    for v in demand:
        if v.distal <= price <= v.proximal:            # price inside an HTF demand zone
            if v.freshness == m.Z_FRESH:
                out["bottom"] = v
            elif v.freshness == m.Z_TESTED:
                out["issues"].append("PRICE_INSIDE_TESTED_HTF_DEMAND %s (VLOC needs a fresh zone, RB 1587, 1597)" % v.zone_id)
            else:
                out["issues"].append("BOUNDARY_FRESHNESS_UNKNOWN %s" % v.zone_id)
    for v in supply:
        if v.proximal <= price <= v.distal:
            if v.freshness == m.Z_FRESH:
                out["top"] = v
            elif v.freshness == m.Z_TESTED:
                out["issues"].append("PRICE_INSIDE_TESTED_HTF_SUPPLY %s (RB 1587, 1601)" % v.zone_id)
            else:
                out["issues"].append("BOUNDARY_FRESHNESS_UNKNOWN %s" % v.zone_id)

    if out["bottom"] is None:
        for v in sorted((v for v in demand if v.proximal < price), key=lambda v: -v.proximal):
            if v.freshness == m.Z_FRESH:
                out["bottom"] = v
                break
            if v.freshness == m.Z_TESTED:
                out["skipped_tested"].append(v.zone_id)
                continue
            out["issues"].append("BOUNDARY_FRESHNESS_UNKNOWN %s" % v.zone_id)
            break
    if out["top"] is None:
        for v in sorted((v for v in supply if v.proximal > price), key=lambda v: v.proximal):
            if v.freshness == m.Z_FRESH:
                out["top"] = v
                break
            if v.freshness == m.Z_TESTED:
                out["skipped_tested"].append(v.zone_id)
                continue
            out["issues"].append("BOUNDARY_FRESHNESS_UNKNOWN %s" % v.zone_id)
            break
    if out["bottom"] is None and not any(i.startswith("BOUNDARY") for i in out["issues"]):
        out["issues"].append("NO_FRESH_DEMAND_BELOW (curve has no bottom)")
    if out["top"] is None and not any(i.startswith("BOUNDARY") for i in out["issues"]):
        if loc_highs and price >= max(loc_highs):
            out["issues"].append("NO_CURVE_HIGHEST_PRICE_IN_LOADED_HISTORY (RB 1605-1609 ATH case: "
                                 "no curve, follow trend; loaded history may not reach the true ATH)")
        else:
            out["issues"].append("NO_FRESH_SUPPLY_ABOVE (curve has no top)")
    return out


def positions(curve, price):
    """Set of curve positions for price. Two positions when price sits exactly on a
    level the rulebook draws as a boundary; empty when the curve is incomplete."""
    b, t = curve["bottom"], curve["top"]
    if b is None or t is None or curve["issues"]:
        return set()
    if price < b.distal:
        return {BELOW_CURVE}
    if price < b.proximal:
        return {VLOC}
    if price > t.distal:
        return {ABOVE_CURVE}
    if price > t.proximal:
        return {VHOC}
    pct = (price - b.proximal) / (t.proximal - b.proximal) * 100.0
    on = lambda level: math.isclose(pct, level, abs_tol=1e-9)    # float noise only, not a tolerance
    if on(0):
        return {VLOC, LOC}
    if on(100):
        return {HOC, VHOC}
    if on(LEVEL_LOW):
        return {LOC, EQB}
    if on(LEVEL_HIGH):
        return {EQB, HOC}
    if pct < LEVEL_LOW:
        return {LOC}
    if pct < LEVEL_HIGH:
        return {EQB}
    return {HOC}


def curve_pct(curve, price):
    b, t = curve["bottom"], curve["top"]
    if b is None or t is None:
        return None
    return round((price - b.proximal) / (t.proximal - b.proximal) * 100.0, 4)


# --- HTF conflict (spec 7.4) -------------------------------------------------------------

def _band(zone, ref):
    if zone.proximal <= ref <= zone.distal:
        return "INSIDE"
    if zone.proximal > ref:
        d = (zone.proximal - ref) / ref * 100.0
        return "WITHIN_5" if d <= 5.0 else ("WITHIN_10" if d <= 10.0 else "CLEAR")
    return "CLEAR"


def htf_conflict(views_by_tf, status_by_tf, refs, reject_tfs, evidence_tfs):
    """refs: {"PL": x, "ENTRY_MIN": y, "ENTRY_MAX": z}. Returns (outcome, reasons, findings)."""
    findings, reasons, outcomes = [], [], []
    for tf in tuple(reject_tfs) + tuple(evidence_tfs):
        st = status_by_tf.get(tf, {}).get("status", NOT_REQUESTED)
        if st != AVAILABLE:
            if tf in reject_tfs:
                reasons.append("HTF_DATA_%s_%s (absence of conflict cannot be established)" % (st, tf))
                outcomes.append(m.DATA_INSUFFICIENT)
            else:
                reasons.append("HTF_EVIDENCE_%s_%s (Weekly/Yearly conflict evidence unavailable)" % (st, tf))
                outcomes.append(m.MANUAL)
            continue
        for v in views_by_tf.get(tf) or []:
            if v.side != "supply" or not v.active:
                continue                                  # broken opposing zone: RB 1313
            bands = {k: _band(v, r) for k, r in refs.items()}
            per_ref = set()
            for band in bands.values():
                if band == "CLEAR":
                    per_ref.add(m.PASS)
                elif tf in evidence_tfs:
                    per_ref.add(m.MANUAL)
                elif v.freshness == m.Z_FRESH:
                    per_ref.add(m.FAIL if band in ("INSIDE", "WITHIN_5") else m.MANUAL)
                else:                                     # tested or unknown freshness
                    per_ref.add(m.MANUAL)
            if per_ref == {m.PASS}:
                continue
            if len(per_ref) == 1:
                o = per_ref.pop()
            else:
                o = m.MANUAL                              # the measuring point decides (PL vs entry)
            outcomes.append(o)
            findings.append({"zone": v.brief(), "bands": bands, "outcome": o})
            reasons.append("%s %s %s supply %s: %s" % (
                "CONFLICT_RF2" if o == m.FAIL else "CONFLICT_REVIEW", tf, v.freshness, v.zone_id,
                ", ".join("%s=%s" % kv for kv in sorted(bands.items()))))
    if m.FAIL in outcomes:
        return m.FAIL, reasons, findings
    if m.DATA_INSUFFICIENT in outcomes:
        return m.DATA_INSUFFICIENT, reasons, findings
    if m.MANUAL in outcomes:
        return m.MANUAL, reasons, findings
    return m.PASS, reasons or ["NO_OPPOSING_HTF_ZONE_WITHIN_10_PERCENT"], findings


# --- coinciding (spec 7.5, D15) ---------------------------------------------------------

def coinciding(views, exec_proximal, exec_distal):
    """Classify execution demand against the relevant HTF demand by interval overlap.

    Zone ranges are inclusive [DL, PL]. A known HTF zone qualifies under D15 only when
    its DL has never been touched; a PL touch alone does not disqualify it. An execution
    zone wholly above a qualifying HTF zone is AGGRESSIVE, never COINCIDING. Its trading
    outcome remains manual until the Rulebook's separate Aggressive conditions can be
    evaluated.
    """
    demand = [v for v in views if v.side == "demand" and v.active]
    unknown = [v for v in demand if v.dl_untouched is None or v.freshness == m.Z_UNKNOWN]
    qualifying = [v for v in demand if v.dl_untouched and v.freshness != m.Z_UNKNOWN]
    exec_low, exec_high = sorted((exec_distal, exec_proximal))

    def overlaps(v):
        zone_low, zone_high = sorted((v.distal, v.proximal))
        return max(exec_low, zone_low) <= min(exec_high, zone_high)

    overlapping = [v for v in qualifying if overlaps(v)]
    if overlapping:
        return COINCIDING, overlapping[0], unknown
    if any(overlaps(v) for v in unknown):
        return HTF_ZONE_STATUS_UNKNOWN, None, unknown

    # No interval overlap: distinguish an execution zone above the HTF demand (Aggressive)
    # from one below its DL (invalid), using both actual zone boundaries.
    below = sorted((v for v in qualifying if exec_low > max(v.proximal, v.distal)),
                   key=lambda v: -max(v.proximal, v.distal))
    if below:
        return AGGRESSIVE, below[0], unknown
    above = sorted((v for v in qualifying if exec_high < min(v.proximal, v.distal)),
                   key=lambda v: min(v.proximal, v.distal))
    if above:
        return INVALID_BELOW_HTF_DL, above[0], unknown
    return NO_QUALIFYING_HTF_ZONE, None, unknown
