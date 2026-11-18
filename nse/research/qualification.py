"""The one qualification pathway: execution zones from the MTF overlay -> G0-G8 -> status.

Spec section 8 is the authority; every gate cites its section and sources. The rules:
  - Execution zones come ONLY from MtfSnapshot.eligible_after_overlay (G2 can pass) and
    MtfSnapshot.manual_review_after_overlay (G2 is MANUAL at best). A zone the overlay
    blocks is never evaluated as a candidate; it is listed in blocked_zones with the
    overlay's reasons (tested and invalidated zones: not listed, D3).
  - Each gate returns PASS, FAIL, MANUAL, DATA_INSUFFICIENT, BLOCKED or NOT_EVALUATED.
    Unknown is never PASS. The final status is the most restrictive outcome
    (models.derive_status), so no later gate can undo an earlier failure.
  - WIT (75/125-minute execution) is BLOCKED: the intraday session and gap design (audit
    M4b) is not approved (user decision 2026-10-28). The gate logic still runs for
    WIT roles so it can be tested, but no WIT result can be anything but BLOCKED.
  - Nothing here approves a trade. The best status is ACTIONABLE CANDIDATE: MANUAL
    CHECKS PENDING, which always carries the manual checklist.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from nse.research import confluence, corporate_actions, levels, models as m, structure, topdown, trend
from nse.research.deps import mtf, ze

M4B_INTRADAY_NOT_APPROVED = ("INTRADAY_DESIGN_NOT_APPROVED: 75/125-minute session and gap design "
                             "(audit M4b) awaits user approval; no intraday output (user decision 2026-10-28)")


@dataclass
class SymbolContext:
    symbol: str
    trade_type: str
    snapshot: object                 # mtf_freshness.MtfSnapshot
    price: float                     # close of the last completed base candle at or before as_of
    limitations: List[str] = field(default_factory=list)
    data_errors: List[str] = field(default_factory=list)   # data-quality findings of severity ERROR
    risk_per_trade: Optional[float] = None
    corporate_actions: List[dict] = field(default_factory=list)   # price-scale actions in the replayed history (B7)
    # None: no verified coverage file. A dict is the hash-verified windows from load_coverage.
    # An empty dict is not evidence that no corporate action occurred (P01-H1).
    corporate_action_coverage: object = None
    # calendar-excluded sessions (Muhurat, shortened) in the history with no candle held: their
    # price action is unknown, so D33's EXCLUDED_SESSION_TOUCH cannot be checked (D52)
    unobserved_excluded_sessions: List[object] = field(default_factory=list)


def _replay_span(ctx, exec_tf):
    """(first candle date, last completed candle date) of the execution series, or None
    when it has no candle. G0 cannot reach PASS on an empty series: AVAILABLE requires candles."""
    series = ctx.snapshot.series.get(exec_tf)
    candles = getattr(series, "candles", None) or []
    if not candles:
        return None
    # The last completed execution candle, not the as_of label. An as_of at noon and
    # the previous close can describe the same candles; the coverage window follows them.
    return candles[0].start.date(), candles[-1].end.date()


def _g(gate, outcome, reasons=None, manual=None, evidence=None, sources=None):
    return m.GateResult(gate, outcome, list(reasons or []), list(manual or []), dict(evidence or {}),
                        list(sources or []))


def _combine(outcomes):
    """One outcome from several readings of the same check: identical -> that outcome;
    different -> MANUAL (the ambiguity changes the result)."""
    s = set(outcomes)
    if len(s) == 1:
        return s.pop()
    return m.MANUAL


# --- the alignment matrix, long rows (spec 7.6; RB 1886-1903; curve table RB 1595-1601) ---

def matrix_long(position, reading, coinciding_class):
    """(outcome, reason) for one location position and one trend reading."""
    up = reading in trend.UPS
    if position == structure.VLOC:
        if reading == trend.STRONG_UP:
            return m.PASS, "VLOC + Strong Up: execute (RB 1889-1890)"
        if reading == trend.SIDEWAYS:
            if coinciding_class == structure.COINCIDING:
                return m.PASS, "VLOC + Sideways + Coinciding: execute (RB 1891)"
            return m.MANUAL, "VLOC + Sideways needs Coinciding (RB 1891)"
        if reading == trend.DOWN:
            return m.MANUAL, "VLOC + Down: Confirmation Entry only (RB 1892), deferred strategy"
        return m.MANUAL, "VLOC + %s: not a matrix row" % reading
    if position == structure.LOC:
        if reading in (trend.STRONG_UP, trend.MODERATE_UP):
            return m.PASS, "LOC + %s: execute (RB 1893-1894)" % reading
        if reading == trend.SIDEWAYS:
            return m.MANUAL, "LOC + Sideways needs sector support (RB 1895); sector not evaluated (D6)"
        if reading == trend.DOWN:
            return m.FAIL, "LOC + Down: reject (RB 1896)"
        return m.MANUAL, "LOC + %s: not a matrix row" % reading
    if position == structure.EQB:
        if reading == trend.STRONG_UP:
            return m.PASS, "EQB + Strong Up: buy only (RB 1897)"
        if reading == trend.SIDEWAYS:
            return m.FAIL, "EQB + Sideways: do nothing (RB 1899)"
        if reading == trend.DOWN:
            return m.FAIL, "EQB + Down: trade only in the trend direction, no counter-trend buy (RB 1599)"
        return m.MANUAL, "EQB + %s: the matrix needs Strong Up (RB 1897; D14 note)" % reading
    if position == structure.HOC:
        if up:
            return m.FAIL, "HOC + Up: reject, buying expensive (RB 1901)"
        if reading == trend.SIDEWAYS:
            return m.MANUAL, "HOC + Sideways: sector-supported exception not evaluated (RB 1600; D6)"
        if reading == trend.DOWN:
            return m.MANUAL, "HOC + Down: apply RF3; no exception is inferred (R5)"
        return m.MANUAL, "HOC + %s: sector-supported exception not evaluated (RB 1600; D6)" % reading
    if position == structure.VHOC:
        return m.FAIL, "VHOC: no buy (RB 1601)"
    return m.MANUAL, "position %s is outside the curve" % position


# --- gates ---------------------------------------------------------------------------

def _g0(ctx, roles, exec_status):
    reasons, manual = [], []
    if ctx.trade_type != m.MIT:
        return _g(m.GATES[0], m.BLOCKED, [M4B_INTRADAY_NOT_APPROVED], sources=["audit M4b", "D16", "spec 9.3"])
    if ctx.data_errors:
        return _g("G0", m.DATA_INSUFFICIENT, ["DATA_QUALITY_ERROR: " + e for e in ctx.data_errors],
                  sources=["spec 8 G0", "spec 11"])
    if exec_status["status"] != structure.AVAILABLE:
        return _g("G0", m.DATA_INSUFFICIENT,
                  ["EXECUTION_SERIES_%s (%s)" % (exec_status["status"], roles["execution"])],
                  evidence={"series": exec_status}, sources=["spec 8 G0", "D23", "D27", "D37"])
    snap = ctx.snapshot
    if not snap.calendar_validated:
        manual.append(m.CALENDAR_UNVALIDATED)
        reasons.append("CALENDAR_UNVALIDATED: no official calendar was supplied; missing weekdays are "
                       "unverified gaps and special sessions cannot be detected (D28)")
    # detected from the prices, not recorded: a PREVCLOSE break, or a price-scale gap (R-12)
    detected_codes = ("PREVCLOSE_DISCONTINUITY", corporate_actions.PRICE_SCALE_GAP)
    recorded = [a for a in ctx.corporate_actions if a["action"] not in detected_codes]
    detected = [a for a in ctx.corporate_actions if a["action"] in detected_codes]
    for code, items in (("CORPORATE_ACTION_IN_HISTORY", recorded), ("PRICE_DISCONTINUITY_IN_HISTORY", detected)):
        if items:
            manual.append(code)
            reasons.append("%s: unadjusted prices span %s; zones, breaches and trends across it are unreliable and "
                           "nothing is adjusted (B7)"
                           % (code, ", ".join("%s %s %s" % (a["ex_date"], a["action"], a["ratio"]) for a in items)))
    span = _replay_span(ctx, roles["execution"])
    coverage_span = None
    if span is not None:
        start, end = span
        coverage_span = [start.isoformat(), end.isoformat()]
        if ctx.corporate_action_coverage is None:
            manual.append("CORPORATE_ACTION_COVERAGE_UNKNOWN")
            reasons.append("CORPORATE_ACTION_COVERAGE_UNKNOWN: no verified corporate-action coverage for %s "
                           "from %s to %s; an empty event list is not evidence that none occurred (P01-H1)"
                           % (ctx.symbol, start.isoformat(), end.isoformat()))
        elif not corporate_actions.covered(ctx.corporate_action_coverage, ctx.symbol, start, end):
            manual.append("CORPORATE_ACTION_COVERAGE_UNVERIFIED")
            reasons.append("CORPORATE_ACTION_COVERAGE_UNVERIFIED: %s from %s to %s is outside a hash-verified "
                           "coverage window; an empty official response is not coverage (P01-H1)"
                           % (ctx.symbol, start.isoformat(), end.isoformat()))
    if snap.unresolved_calendar_dates:
        manual.append(mtf.CALENDAR_UNRESOLVED_DATES)
        reasons.append("CALENDAR_UNRESOLVED_DATES: %s" % ", ".join(d.isoformat() for d in snap.unresolved_calendar_dates))
    ev = {"base_candles_used": snap.base_candles_used, "data_gaps": len(snap.data_gaps),
          "excluded_candles": len(snap.excluded_candles), "ignored_incomplete": len(snap.ignored_incomplete),
          "execution_series": exec_status, "corporate_action_coverage_span": coverage_span}
    return _g("G0", m.MANUAL if manual else m.PASS, reasons or ["completed candles only; execution series complete"],
              manual, ev, ["spec 8 G0", "D23", "D28", "D33", "D34"])


def _g1(ctx, roles, a, state, exec_candles):
    z = a.zone
    # defence in depth: the overlay already guarantees all of this (D2, D3)
    if not (z.is_demand and z.active and z.fresh and state is not None and state.usable_as_fresh_context
            and state.base_touch_count == 0 and state.status == mtf.FRESH):
        raise AssertionError("overlay returned a zone that is not a fresh demand zone: %s" % z.id)
    ev = {"overlay_status": state.status, "base_touch_count": state.base_touch_count,
          "htf_test_count": state.htf_test_count, "dl_touched": state.dl_touched_at is not None,
          "invalidated": False}
    reasons = ["fresh, unbreached demand zone per the MTF overlay (test_count 0)"]
    # an in-progress candle is ignored for zones (D23) but has already traded into this one:
    # freshness after it is unknown until it completes (spec 6.2), so never a plain PASS
    touches = ctx.snapshot.incomplete_touches(z)
    if touches:
        ev["incomplete_candle_touches"] = [{"end": e.isoformat(), "proximal": pl, "distal": dl}
                                           for e, pl, dl in touches]
        return _g("G1", m.MANUAL, reasons + [
            "%s: an in-progress candle ending %s has reached the proximal line%s; the zone is fresh only up "
            "to the last completed candle" % (m.INCOMPLETE_CANDLE_TOUCH, touches[0][0].isoformat(),
                                              " and the distal line" if touches[0][2] else "")],
            [m.INCOMPLETE_CANDLE_TOUCH], ev, ["D23", "RB 264, 683-697", "R4"])
    first = z.legin_index if z.legin_index is not None else z.start_index
    since = exec_candles[first].start.date() if 0 <= first < len(exec_candles) else None
    unseen = [d for d in ctx.unobserved_excluded_sessions if since is None or d >= since]
    if unseen:
        # D33: an excluded session that reaches the zone makes it manual; with no file held for
        # that session the check cannot be made, so freshness across it is unknown (D52)
        ev["unobserved_excluded_sessions"] = [d.isoformat() for d in unseen]
        return _g("G1", m.MANUAL, reasons + [
            "%s: %s inside the zone's span has no EOD file; whether it reached the zone is unknown (D33, D52)"
            % (m.EXCLUDED_SESSION_UNOBSERVED, ", ".join(d.isoformat() for d in unseen))],
            [m.EXCLUDED_SESSION_UNOBSERVED], ev, ["D33", "D52"])
    if ctx.trade_type == m.MIT:
        return _g("G1", m.PASS, reasons, evidence=ev, sources=["D2", "D3", "audit M4", "RB 264, 683-697"])
    since = len(exec_candles) - 1 - z.created_index
    ev["candles_since_formation"] = since
    if since <= 8:
        return _g("G1", m.PASS, reasons + ["formed %d candles ago (<= 8)" % since], evidence=ev,
                  sources=["RB 1403, 1788-1801", "D16"])
    note = "formed %d candles ago: 9-10 is manual; > 10 manual%s (RB 1788 vs 1797-1801)" % (
        since, "; > 20 must re-verify HTF conditions" if since > 20 else "")
    return _g("G1", m.MANUAL, reasons + [note], ["WIT_RECENCY"], ev, ["RB 1403, 1788-1801", "D16"])


def _g2(a):
    z = a.zone
    ev = {"core": a.score.core, "freshness": a.score.freshness, "strength": a.score.strength,
          "base": a.score.base, "base_basis": a.score.base_basis,
          "readings": [{"name": r.name, "core": r.core, "source": r.source} for r in a.readings],
          "engine_status": a.status, "tags": list(a.tags)}
    if a.status == ze.ELIGIBLE:
        return _g("G2", m.PASS, ["core 7/7 under D12 definitions, no source disagreement"],
                  evidence=ev, sources=["RB 661, 829", "D12", "spec 5.1"])
    if a.status == ze.MANUAL_REVIEW:
        return _g("G2", m.MANUAL, ["a reading reaches 7/7 but the sources disagree: " + ", ".join(a.manual_review)],
                  list(a.manual_review), ev, ["D12", "spec 5.1"])
    raise AssertionError("G2 got a zone the overlay should not have kept: %s %s" % (z.id, a.status))


def _g3(ctx, roles, views, status):
    tf = roles["location"]
    st = status[tf]
    if st["status"] != structure.AVAILABLE:
        return _g("G3", m.DATA_INSUFFICIENT, ["LOCATION_SERIES_%s (%s)" % (st["status"], tf)],
                  evidence={"series": st}, sources=["spec 7.2"]), None, set()
    highs = [c.high for c in ctx.snapshot.series[tf].candles]
    curve = structure.build_curve(views[tf], ctx.price, highs)
    pos_cmp = structure.positions(curve, ctx.price)
    ev = {"tf": tf, "price": ctx.price,
          "bottom": curve["bottom"].brief() if curve["bottom"] else None,
          "top": curve["top"].brief() if curve["top"] else None,
          "pct_at_price": structure.curve_pct(curve, ctx.price),
          "position_at_price": sorted(pos_cmp),
          "skipped_tested_boundaries": curve["skipped_tested"], "issues": curve["issues"],
          "redrawn_past_tested": curve.get("redrawn_past", [])}
    src = ["spec 7.2", "RB 1578-1628"] + (["P-LOC-2"] if curve.get("redrawn_past") else [])
    if curve["issues"] or not pos_cmp:
        return _g("G3", m.MANUAL, curve["issues"] or ["curve incomplete"], ["LOCATION_UNDETERMINED"],
                  ev, src), curve, set()
    pos = pos_cmp
    reasons, manual = [], []
    if pos & {structure.BELOW_CURVE, structure.ABOVE_CURVE}:
        return _g("G3", m.MANUAL, reasons + ["price outside the curve"], ["LOCATION_OUTSIDE_CURVE"],
                  ev, src), curve, set()
    per = []
    for p in sorted(pos):
        if p == structure.VHOC:
            per.append(m.FAIL)
            reasons.append("VHOC: do not buy (RB 1601)")
        elif p == structure.HOC:
            per.append(m.MANUAL)
            reasons.append("HOC: buy only in extreme circumstances with sector support (RB 1600); "
                           "sector not evaluated (D6)")
        else:
            per.append(m.PASS)
            reasons.append("%s: location permits a buy; the matrix decides with the trend (G4)" % p)
    out = _combine(per)
    if out == m.MANUAL:
        manual.append("LOCATION_REVIEW")
    return _g("G3", out, reasons, manual, ev, src), curve, pos


def _g4(ctx, roles, positions, coinc_class):
    gate = trend.trend_for(ctx.snapshot, roles["trend_gate"])
    context = [trend.trend_for(ctx.snapshot, tf) for tf in roles["trend_context"]]
    ev = {"gate": gate, "context": context, "positions": sorted(positions)}
    src = ["spec 7.3, 7.6", "D14", "D21" if ctx.trade_type == m.MIT else "D22", "RB 1672-1711"]
    if gate["status"] in (trend.TRUNCATED, trend.UNAVAILABLE):
        return _g("G4", m.DATA_INSUFFICIENT, ["TREND_GATE_%s (%s)" % (gate["status"], roles["trend_gate"])],
                  evidence=ev, sources=src), gate
    if gate["status"] == trend.INSUFFICIENT_HISTORY:
        return _g("G4", m.MANUAL, ["TREND_GATE_INSUFFICIENT_HISTORY: %d of %d completed %s candles (D14, D23)"
                                   % (gate["candles"], gate["needed"], roles["trend_gate"])],
                  ["TREND_INSUFFICIENT_HISTORY"], ev, src), gate
    if not positions:
        return _g("G4", m.MANUAL, ["the alignment matrix needs a location (G3 undetermined)"],
                  ["MATRIX_NEEDS_LOCATION"], ev, src), gate
    per, reasons = [], []
    for p in sorted(positions):
        for r in gate["readings"]:
            o, why = matrix_long(p, r, coinc_class)
            if (o == m.PASS and ctx.trade_type == m.MIT and p in (structure.VLOC, structure.LOC)
                    and r in (trend.SIDEWAYS, trend.DOWN)):
                o, why = m.MANUAL, why + "; Weekly trend may oppose the Monthly buy bias: extreme caution (RB 1232, D21)"
            per.append(o)
            reasons.append("%s x %s -> %s: %s" % (p, r, o, why))
    out = _combine(per)
    manual = ["MATRIX_REVIEW"] if out == m.MANUAL else []
    return _g("G4", out, reasons, manual, ev, src), gate


def _g5(ctx, roles, views, status, rng, exec_pl, curve):
    refs = {k: v for k, v in (("PL", exec_pl), ("ENTRY_MIN", rng["entry"][0]), ("ENTRY_MAX", rng["entry"][1]))
            if v is not None}
    out, reasons, findings = structure.htf_conflict(views, status, refs, roles["conflict_reject"],
                                                    roles["conflict_evidence"])
    if ctx.trade_type != m.MIT and curve is not None and curve.get("bottom") is not None:
        b = curve["bottom"]                       # WIT: weekly location DZ vs Monthly structure
        for v in views.get("M") or []:
            if v.side == "supply" and v.active:
                band = structure._band(v, b.proximal)
                if band == "INSIDE":
                    out = m.FAIL
                    reasons.append("WIT weekly location DZ inside Monthly supply %s: toxic (RB 1402)" % v.zone_id)
                elif band in ("WITHIN_5", "WITHIN_10") and out != m.FAIL:
                    out = m.MANUAL if out == m.PASS else out
                    reasons.append("WIT weekly location DZ near Monthly supply %s (RB 1402; 'near' undefined)" % v.zone_id)
    # D43: an opposing Pine-only supply inside the conflict bands cannot be validated, so it
    # makes G5 MANUAL; it never FAILs it and never clears it
    pine = []
    for tf in tuple(roles["conflict_reject"]) + tuple(roles["conflict_evidence"]):
        if status.get(tf, {}).get("status") != structure.AVAILABLE:
            continue                                  # already DATA_INSUFFICIENT / MANUAL above
        for pz in structure.pine_only_zones(ctx.snapshot, tf, "supply"):
            bands = {k: structure._band(pz, r) for k, r in refs.items()}
            if any(b != "CLEAR" for b in bands.values()):
                pine.append({"zone": pz.brief(), "bands": bands, "outcome": m.MANUAL})
                reasons.append("PINE_ONLY_OPPOSING_ZONE %s supply %s: %s (cannot be validated independently; D43)"
                               % (tf, pz.zone_id, ", ".join("%s=%s" % kv for kv in sorted(bands.items()))))
    if pine and out == m.PASS:
        out = m.MANUAL
    manual = ["HTF_CONFLICT_REVIEW"] if out == m.MANUAL else []
    if pine:
        manual.append("PINE_ONLY_ZONE_REVIEW")
    return _g("G5", out, reasons, manual, {"refs": refs, "findings": findings, "pine_only_findings": pine},
              ["spec 7.4", "RB 601, 1302-1316", "RF2"] + (["D43"] if pine else []))


def _g6(ctx, roles, views, status, z, curve, positions):
    tf = roles["coinciding"]
    if status[tf]["status"] != structure.AVAILABLE:
        return _g("G6", m.DATA_INSUFFICIENT, ["COINCIDING_SERIES_%s (%s)" % (status[tf]["status"], tf)],
                  sources=["spec 7.5", "D15"]), None
    cls, zone, unknown = structure.coinciding(views[tf], z.proximal, z.distal)
    ev = {"class": cls, "htf_zone": zone.brief() if zone else None,
          "htf_zone_dl_untouched": zone.dl_untouched if zone else None,
          "execution_range": [min(z.proximal, z.distal), max(z.proximal, z.distal)],
          "zones_with_unknown_status": [u.brief() for u in unknown]}
    src = ["spec 7.5", "D15", "RB 1826-1856"]
    if cls == structure.COINCIDING:
        if (curve and curve.get("bottom") is not None and zone.zone_id != curve["bottom"].zone_id
                and structure.VLOC in positions):
            return _g("G6", m.MANUAL, ["coinciding HTF zone differs from the fresh curve boundary at VLOC"],
                      ["COINCIDING_ZONE_IS_NOT_CURVE_BOUNDARY"], ev, src), cls
        return _g("G6", m.PASS, ["execution demand range overlaps a %s demand zone whose DL is untouched" % tf],
                  evidence=ev, sources=src), cls
    if cls == structure.INVALID_BELOW_HTF_DL:
        return _g("G6", m.FAIL, ["execution zone below the HTF location zone's DL: invalid (RB 1856)"],
                  evidence=ev, sources=src), cls
    if cls == structure.AGGRESSIVE:
        return _g("G6", m.MANUAL, ["execution demand is above and does not overlap the HTF zone; "
                                   "Aggressive is distinct from Coinciding and its Rulebook conditions need review"],
                  ["AGGRESSIVE_ENTRY_REVIEW"], ev, src), cls
    if cls == structure.HTF_ZONE_STATUS_UNKNOWN:
        return _g("G6", m.MANUAL, ["the HTF zone's freshness or DL-touch status is unknown"],
                  ["COINCIDING_DL_STATUS_UNKNOWN"], ev, src), cls
    if unknown:
        return _g("G6", m.MANUAL, ["no qualifying HTF zone, but some HTF zones have unknown freshness or DL-touch status"],
                  ["COINCIDING_DL_STATUS_UNKNOWN"], ev, src), cls
    return _g("G6", m.PASS, ["known absence of a qualifying %s location demand zone: G6 passes as Standard" % tf],
              evidence=ev, sources=src), cls


def _g7(ctx, roles, views, status, z, rng):
    tf = roles["target"]
    ev = {"ranges": rng, "target_tf": tf}
    src = ["spec 6", "RB 82, 2010, 2097-2102, 2268-2328", "D7", "D9", "B9", "RF8"]
    bad = rng["problems"]
    if bad:
        ev["levels_valid"] = False
        return _g("G7", m.MANUAL, ["LEVELS_INVALID: " + "; ".join(bad) + ". No R:R or quantity is computed."],
                  ["LEVELS_INVALID"], ev, src)
    ev["levels_valid"] = True
    if status[tf]["status"] != structure.AVAILABLE:
        return _g("G7", m.DATA_INSUFFICIENT, ["TARGET_SERIES_%s (%s)" % (status[tf]["status"], tf)],
                  evidence=ev, sources=src)
    target, issue = levels.select_target(views[tf], rng["entry"][1], z.proximal)
    # D43: an opposing Pine-only supply above the entry and below the structural target (or
    # anywhere above the entry when there is none) may be the real nearest target; it is
    # never used as one, and it makes G7 MANUAL. One Pine itself recorded as touched cannot
    # be the target (the target must be FRESH, RB 551-558; select_target skips tested zones);
    # only that positive evidence excludes it, never the absence of a touch
    pine = [pz for pz in structure.pine_only_zones(ctx.snapshot, tf, "supply")
            if pz.tested is not True and pz.distal > rng["entry"][0]
            and (target is None or pz.proximal < target.proximal)]
    if pine:
        src = src + ["D43"]
        ev["pine_only_zones_below_target"] = [pz.brief() for pz in pine]
    pine_reason = ["PINE_ONLY_OPPOSING_ZONE %s below the target: %s (cannot be validated independently; "
                   "never an automatic target; D43)" % (tf, ", ".join(pz.zone_id for pz in pine))] if pine else []
    pine_manual = ["PINE_ONLY_ZONE_REVIEW"] if pine else []
    ref_tf = roles["target_reference"]
    if ref_tf and status.get(ref_tf, {}).get("status") == structure.AVAILABLE:
        ref, ref_issue = levels.select_target(views[ref_tf], rng["entry"][1], z.proximal)
        ev["reference_target"] = ref.brief() if ref else ref_issue
    ev["quantity"] = levels.quantity_range(rng, ctx.risk_per_trade)
    if target is None:
        risk_max = rng["entry"][1] - min(v for pair in rng["sl"].values() for v in pair)
        ev["mathematical_2_to_1_reference"] = round(rng["entry"][1] + levels.MIN_RR * risk_max, 4)
        return _g("G7", m.MANUAL, [issue, "2:1 mathematical target shown as a reference only (D9; RB 2268-2328)"]
                  + pine_reason, ["NO_STRUCTURAL_TARGET"] + pine_manual, ev, src)
    rr = levels.rr_range(rng, target.proximal)
    ev["target"] = target.brief()
    ev["rr"] = rr
    if rr["status"] == levels.FAIL_ALL:
        return _g("G7", m.FAIL, ["RF8: R:R < 2 for every buffer and SL choice: %s" % rr["rr"]] + pine_reason,
                  pine_manual, evidence=ev, sources=src)
    if rr["status"] == levels.PASS_ALL and not pine:
        return _g("G7", m.PASS, ["R:R >= 2 for every buffer and SL choice: %s" % rr["rr"]], evidence=ev, sources=src)
    if rr["status"] == levels.PASS_ALL:
        return _g("G7", m.MANUAL, ["R:R >= 2 for every buffer and SL choice to the structural target: %s" % rr["rr"]]
                  + pine_reason, pine_manual, ev, src)
    return _g("G7", m.MANUAL, ["R:R depends on the buffer and SL choice: %s" % rr["rr"]] + pine_reason,
              ["RR_DEPENDS_ON_BUFFER"] + pine_manual, ev, src)


def _g8(ctx, g4_trend, positions, z, g5, g7, tda_rows):
    items, manual, out = [], [], m.PASS
    items.append({"item": "RF1 zone tested 2+ times", "result": m.PASS, "note": "test_count 0 (G1)"})
    items.append({"item": "RF2 inside opposing HTF zone", "result": g5.outcome, "note": "evaluated in G5"})
    readings = (g4_trend or {}).get("readings") or []
    if not readings:
        rf3 = m.MANUAL
        note = "trend gate unavailable: RF3 cannot be evaluated"
    elif set(readings) == {trend.DOWN} and structure.VLOC not in positions:
        rf3 = m.FAIL
        note = "ITF trend clearly down and not at VLOC; overrides are never automated (spec 2 item 11)"
    elif trend.DOWN in readings:
        rf3 = m.MANUAL
        note = "ITF trend may be down (ambiguous band or VLOC)"
    else:
        rf3 = m.PASS
        note = "ITF trend not down"
    items.append({"item": "RF3 trend strongly against", "result": rf3, "note": note})
    items.append({"item": "RF6 F&O without size control", "result": m.PASS, "note": "cash equity only (D2)"})
    if z.strong_closing:
        rf7, note = m.PASS, "leg-out closed beyond the leg-in extreme (RB 451)"
    else:
        rf7, note = m.MANUAL, "leg-out did not close beyond the leg-in extreme: reaction zone check (RF7)"
    items.append({"item": "RF7 reaction zone with poor closing", "result": rf7, "note": note})
    items.append({"item": "RF8 no 2:1 R:R", "result": g7.outcome, "note": "evaluated in G7"})
    tda_missing = [r["tf"] for r in tda_rows if r["series"]["status"] != structure.AVAILABLE]
    ec1 = m.MANUAL if tda_missing else m.PASS
    items.append({"item": "Essential Check 1: TDA complete", "result": ec1,
                  "note": "unavailable: %s" % ", ".join(tda_missing) if tda_missing else "every TDA timeframe available"})
    rng = levels.ranges(z.proximal, z.distal, z.normal_distal)
    items.append({"item": "Essential Checks 5-6: entry above PL, SL below DL, with buffer",
                  "result": m.PASS if rng.get("valid") else m.MANUAL,
                  "note": "by construction of the G7 ranges" if rng.get("valid") else
                          "levels invalid (%s); G7 reports them" % "; ".join(rng.get("problems") or [])})
    if ctx.risk_per_trade is None:
        items.append({"item": "Essential Check 7: position size", "result": m.MANUAL,
                      "note": "risk per trade not configured; quantity not computed"})
    for name, result in (("RF3", rf3), ("RF7", rf7), ("EC1", ec1)):
        if result == m.FAIL:
            out = m.FAIL
        elif result == m.MANUAL and out != m.FAIL:
            out = m.MANUAL
            manual.append(name)
    if ctx.risk_per_trade is None:
        manual.append("EC7_POSITION_SIZE")
        out = m.MANUAL if out == m.PASS else out
    return _g("G8", out, ["%s: %s (%s)" % (i["item"], i["result"], i["note"]) for i in items], manual,
              {"items": items, "always_manual": ["RF4 garbage chart", "RF5 emotion", "RF9 mental state",
                                                 "RF10 scared money", "Essential Check 10"]},
              ["RB 594-631", "spec 8 G8"])


# --- one symbol -------------------------------------------------------------------------

def _zone_record(a, state, exec_candles):
    z = a.zone
    return {
        "zone_id": z.id, "tf": None, "side": z.side, "pattern": z.pattern,
        "proximal": z.proximal, "distal": z.distal, "normal_distal": z.normal_distal,
        "exceptional_dl": z.exceptional, "zero_base": z.zero_base,
        "base_count_pine": z.base_count, "base_count_incl_transitions": z.base_count_incl_transitions,
        "legout_count": z.legout_count, "legout_count_pine": a.evidence.get("legout_count_pine"),
        "has_gap": z.has_gap, "gap_size": z.gap_size, "strong_closing": z.strong_closing,
        "start_time": exec_candles[z.start_index].end.isoformat(),
        "created_time": exec_candles[z.created_index].end.isoformat(),
        "dl_touched": state.dl_touched_at is not None, "test_count": z.test_count,
        "core": "%g/7" % a.score.core, "engine_status": a.status, "engine_manual_review": list(a.manual_review),
        "engine_manual_checks": list(a.manual_checks), "tags": list(a.tags),
        "overlay_status": state.status, "overlay_base_touch_count": state.base_touch_count,
    }


def evaluate_symbol(ctx):
    """Every candidate for one symbol and trade type, plus the audit of zones the overlay
    blocked. Returns dict(candidates, blocked_zones, tda, symbol_gate0, views_status)."""
    if ctx.trade_type not in m.TRADE_TYPES:
        raise ValueError("unknown trade type %r" % ctx.trade_type)
    roles = m.ROLES[ctx.trade_type]
    snap = ctx.snapshot
    exec_tf = roles["execution"]
    all_tfs = sorted(set(m.TDA_TIMEFRAMES) | {exec_tf}, key=lambda t: (m.TDA_TIMEFRAMES + (exec_tf,)).index(t))
    status = {tf: structure.series_status(snap, tf) for tf in all_tfs}
    views = {tf: structure.zone_views(snap, tf) for tf in all_tfs}
    tda_rows = topdown.tda(snap, ctx.price, list(m.TDA_TIMEFRAMES) + ([exec_tf] if exec_tf not in m.TDA_TIMEFRAMES else []))
    g0 = _g0(ctx, roles, status[exec_tf])
    limitations = sorted(set(ctx.limitations) | set(snap.limitations) |
                         {m.TRADINGVIEW_PARITY_UNVERIFIED, m.NOT_EXTERNALLY_VALIDATED})

    kept_e, blocked_e = snap.eligible_after_overlay(exec_tf)
    kept_m, blocked_m = snap.manual_review_after_overlay(exec_tf)
    blocked = []
    for a, why in blocked_e + blocked_m:
        st = snap.zones.get("%s:%s" % (exec_tf, a.zone.id))
        status_ = st.status if st else "NO_OVERLAY_STATE"
        if status_ in (mtf.TESTED, mtf.INVALIDATED):
            disposition = "NOT_LISTED (D3)"
        elif status_ in (mtf.UNKNOWN_DATA_GAP, mtf.UNVERIFIED_SESSION):
            disposition = m.STATUS_DATA_INSUFFICIENT
        else:
            disposition = "OVERLAY_MANUAL_REVIEW (not a candidate)"
        blocked.append({"zone_id": a.zone.id, "tf": exec_tf, "engine_status": a.status,
                        "overlay_status": status_, "reasons": list(why), "disposition": disposition})

    candidates = []
    exec_series = snap.series.get(exec_tf)
    exec_candles = exec_series.candles if exec_series else []
    for a in kept_e + kept_m:
        state = snap.zones.get("%s:%s" % (exec_tf, a.zone.id))
        z = a.zone
        rec = _zone_record(a, state, exec_candles)
        rec["tf"] = exec_tf
        # spec 5.3 X/14 display: information only, computed after and apart from the gates
        rec["pre_entry_score"] = confluence.score14(snap, exec_tf, [t for t in m.TDA_TIMEFRAMES if t != exec_tf], a)
        rng = levels.ranges(z.proximal, z.distal, z.normal_distal)
        if g0.outcome in (m.DATA_INSUFFICIENT,):
            gates = [g0] + [_g(n, m.NOT_EVALUATED, ["stopped at G0"]) for n in m.GATES[1:]]
        else:
            g1 = _g1(ctx, roles, a, state, exec_candles)
            g2 = _g2(a)
            g3, curve, positions = _g3(ctx, roles, views, status)
            g6, coinc = _g6(ctx, roles, views, status, z, curve, positions)
            g4, gate_trend = _g4(ctx, roles, positions, coinc)
            g5 = _g5(ctx, roles, views, status, rng, z.proximal, curve)
            g7 = _g7(ctx, roles, views, status, z, rng)
            g8 = _g8(ctx, gate_trend, positions, z, g5, g7, tda_rows)
            gates = [g0, g1, g2, g3, g4, g5, g6, g7, g8]
        st = m.derive_status(gates)
        status_reasons = ["%s %s: %s" % (g.gate, g.outcome, "; ".join(g.reasons[:3]))
                          for g in gates if g.outcome not in (m.PASS, m.NOT_EVALUATED)]
        manual_review = ["%s:%s" % (g.gate, x) for g in gates for x in g.manual_review]
        checks = [{"code": c, "check": t, "source": s} for c, t, s in m.CHECKLIST]
        if z.zero_base:
            checks.append({"code": ze.TAG_ZB, "check": "zero-base score is Pine's reference, not rulebook-defined",
                           "source": "D13"})
        ev_for, ev_against = _evidence(gates)
        candidates.append(m.CandidateResult(
            symbol=ctx.symbol, trade_type=ctx.trade_type, execution_tf=exec_tf,
            as_of=snap.as_of.isoformat(), zone=rec, gates=gates, status=st,
            status_reasons=status_reasons, manual_review=manual_review, manual_checks=checks,
            evidence_for=ev_for, evidence_against=ev_against, levels=rng, limitations=limitations))
    candidates.sort(key=lambda c: (m.STATUS_ORDER.index(c.status) * -1, c.zone["created_time"], c.zone["zone_id"]))
    return {"candidates": candidates, "blocked_zones": blocked, "tda": tda_rows, "gate0": g0,
            "series": status, "limitations": limitations}


def _evidence(gates):
    ev_for, ev_against = [], []
    for g in gates:
        if g.outcome == m.PASS:
            ev_for.append("%s: %s" % (g.gate, g.reasons[0] if g.reasons else "pass"))
        elif g.outcome in (m.FAIL, m.MANUAL, m.DATA_INSUFFICIENT, m.BLOCKED):
            ev_against.append("%s %s: %s" % (g.gate, g.outcome, g.reasons[0] if g.reasons else ""))
    g4 = [g for g in gates if g.gate == "G4"][0]
    for c in g4.evidence.get("context", []):
        if trend.DOWN in (c.get("readings") or []):
            ev_against.append("%s trend context reads down (mandatory context, not a gate; D21)" % c["tf"])
    return ev_for, ev_against
