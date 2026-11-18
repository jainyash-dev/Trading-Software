"""Universe scanner: data readiness -> MTF replay -> qualification -> one ScanResult.

For each symbol, in sorted order:
  1. Data-quality findings from the input; any ERROR stops the symbol (DATA_INSUFFICIENT).
  2. mtf_freshness.replay on the daily base with D, W, M, Q, HY and Y, cut at as_of
     (nothing after as_of is read), with the calendar when one is given.
  3. qualification.evaluate_symbol, the one qualification pathway.
The result is a pure function of the inputs and the config: no clock is read, so the
same inputs and as_of give the same output. generated_at is recorded only if the caller
supplies it.

Trade types: MIT runs. WIT-75 / WIT-125 return BLOCKED for every symbol without building
anything: no intraday output exists until the 75/125-minute design is approved (M4b).
"""

import dataclasses
import datetime
from dataclasses import dataclass, field
from typing import List, Optional

from nse.research import corporate_actions, marketdata, models as m, qualification
from nse.research.deps import calendar as cal_mod, mtf, ze

HTF = ("D", "W", "M", "Q", "HY", "Y")

SYMBOL_EVALUATED = "EVALUATED"
SYMBOL_NO_EXECUTION_ZONE = "NO_FRESH_EXECUTION_ZONE"
SYMBOL_DATA_INSUFFICIENT = "DATA_INSUFFICIENT"
SYMBOL_BLOCKED = "BLOCKED"
SYMBOL_NOT_IN_UNIVERSE = "NOT_IN_UNIVERSE_AT_AS_OF"


@dataclass
class ScanConfig:
    as_of: datetime.datetime
    trade_type: str = m.MIT
    calendar: object = None
    calendar_label: str = "NONE"
    risk_per_trade: Optional[float] = None
    generated_at: Optional[str] = None       # caller-supplied; never read from a clock
    universe_label: str = "ADHOC"
    corporate_actions: Optional[list] = None  # corporate_actions.Action list; None: no file given (B7)
    corporate_action_coverage: Optional[dict] = None   # corporate_actions.load_coverage(); None: none (D52)


@dataclass
class SymbolResult:
    symbol: str
    status: str
    reasons: List[str]
    price: Optional[float]
    candidates: List[m.CandidateResult]
    blocked_zones: List[dict]
    fresh_zones: List[dict]
    tda: List[dict]
    series: dict
    findings: List[dict]
    provenance: dict
    limitations: List[str]


@dataclass
class ScanResult:
    pipeline_version: str
    engine_versions: dict
    as_of: str
    generated_at: Optional[str]
    trade_type: str
    calendar: str
    universe: str
    symbols: List[SymbolResult]
    limitations: List[str] = field(default_factory=list)

    def candidates(self):
        return [c for s in self.symbols for c in s.candidates]


def _fresh_zone_rows(symbol, snapshot):
    """Fresh-zone report rows (spec 12): zones the overlay sees as fresh, every TF.
    Tested, invalidated and unknown-freshness zones never appear (D3)."""
    rows = []
    for tf in HTF:
        s = snapshot.series.get(tf)
        if s is None or s.engine is None:
            continue
        for a in s.engine.assessments:
            st = snapshot.zones.get("%s:%s" % (tf, a.zone.id))
            if st is None or not st.usable_as_fresh_context:
                continue
            z = a.zone
            if z.side == "supply":
                label = "context: not a candidate"
            elif a.status == ze.ELIGIBLE and snapshot.incomplete_touches(z):
                # the same evidence that makes G1 MANUAL (audit 2026-11-06 M1)
                label = "%s: fresh to the last completed candle; an in-progress candle has reached the PL" \
                    % m.INCOMPLETE_CANDLE_TOUCH
            elif a.status == ze.ELIGIBLE:
                label = "ZONE_ELIGIBLE (downstream gates G3-G8 still apply)"
            elif a.status == ze.MANUAL_REVIEW:
                label = "ZONE_MANUAL_REVIEW: " + ", ".join(a.manual_review)
            else:
                label = "INELIGIBLE: " + ", ".join(a.reasons)
                since = len(s.candles) - 1 - z.created_index
                if ze.CORE_BELOW_7 in a.reasons and since < ze.Rules().legout_track_bars:
                    # audit M1, reporting only: later leg-out candles (PS 1771, RB 728) may still raise
                    # the score; it is re-assessed on each completed candle and is ineligible until then
                    label += " (LEGOUT_WINDOW_OPEN: %d of %d leg-out candles seen)" % (since, ze.Rules().legout_track_bars)
            rows.append({
                "symbol": symbol, "tf": tf, "zone_id": z.id, "side": z.side, "pattern": z.pattern,
                "proximal": z.proximal, "distal": z.distal, "normal_distal": z.normal_distal,
                "base_count_pine": z.base_count, "base_count_incl_transitions": z.base_count_incl_transitions,
                "zero_base": z.zero_base, "legout_count": z.legout_count,
                "legout_count_pine": a.evidence.get("legout_count_pine"), "has_gap": z.has_gap,
                "gap_size": z.gap_size, "strong_closing": z.strong_closing,
                "created_time": s.candles[z.created_index].end.isoformat(),
                "dl_touched": st.dl_touched_at is not None, "core": "%g/7" % a.score.core,
                "tags": list(a.tags), "zone_level": label})
    return rows


def _price(candles, snapshot):
    excluded = set(x.date for x in snapshot.excluded_candles)
    usable = [c for c in candles if c.end <= snapshot.as_of and c.start.date() not in excluded and c.complete]
    return usable[-1].close if usable else None


def _calendar_dates(config, start, end):
    """[(date, session_type)] strictly between start and end, or None when the calendar cannot
    classify one of them (coverage, unresolved, unverified source)."""
    session_type = getattr(config.calendar, "session_type", None)
    if session_type is None:
        return None                                  # a calendar without session types explains nothing
    out, d = [], start + datetime.timedelta(days=1)
    while d < end:
        try:
            out.append((d, session_type(d)))
        except cal_mod.CalendarError:
            return None
        d += datetime.timedelta(days=1)
    return out


def _explained_by_excluded_session(f, symbol, config, held_without_row=frozenset()):
    """D52: the reason text when a PREVCLOSE discontinuity is explained by a calendar gap, else
    None. All must hold: an official, hash-verified calendar classifies every date between the
    two held files; none is a trading day (so no expected file is missing); at least one is an
    excluded session (Muhurat / shortened), which the acquisition policy does not require and
    for which no file is held; verified corporate-action records cover the symbol across the gap
    and none is a price-scale action with an ex-date in it. Anything else stays a detected
    discontinuity (G0 MANUAL). The detection is never called a corporate action, and nothing
    else (recorded actions, identity findings) is affected."""
    if config.calendar is None or config.corporate_action_coverage is None or config.corporate_actions is None:
        return None                                  # coverage without the records proves nothing (QA)
    last = datetime.date.fromisoformat((f.extra or {}).get("last_date") or "0001-01-01")
    between = _calendar_dates(config, last, f.date)
    if not between:
        return None
    if any(st in (cal_mod.NORMAL, cal_mod.NORMAL_SPECIAL) for _, st in between):
        return None
    excluded = [d for d, st in between if st in (cal_mod.EXCLUDED_MUHURAT, cal_mod.EXCLUDED_SHORTENED)]
    if not excluded or any(d in held_without_row for d in excluded):
        return None                                  # a file IS held for the session: not "no EOD file" (QA)
    if not corporate_actions.covered(config.corporate_action_coverage, symbol, last, f.date):
        return None
    if any(a.symbol == symbol and a.action in corporate_actions.PRICE_ACTIONS and last < a.ex_date <= f.date
           for a in (config.corporate_actions or [])):
        return None
    return ("previous close differs from the last held close across calendar-excluded session(s) %s with no EOD file "
            "(official calendar); no recorded corporate action in the gap (verified coverage); not a corporate "
            "action (D52)" % ", ".join(d.isoformat() for d in excluded))


def _last_unresolved_date(inp, config):
    """The latest date from the first candle to as_of that the calendar cannot classify
    (its UNRESOLVED_ERRORS, L10), or None."""
    errors = tuple(getattr(config.calendar, "UNRESOLVED_ERRORS", ())) if config.calendar is not None else ()
    if not errors or not inp.candles:
        return None
    d, first = config.as_of.date(), inp.candles[0].start.date()
    while d >= first:
        try:
            config.calendar.is_trading_day(d)
        except errors:
            return d
        except cal_mod.CalendarError:
            pass                                     # coverage: handled by the replay
        d -= datetime.timedelta(days=1)
    return None


def _unobserved_excluded_sessions(inp, config, first):
    """Calendar-excluded sessions from the first candle to as_of with no candle held (D33, D52)."""
    excluded = getattr(config.calendar, "is_excluded_session", None)
    if excluded is None:
        return []
    held = set(c.start.date() for c in inp.candles)
    out, d, end = [], first, config.as_of.date()
    while d <= end:
        try:
            if excluded(d) and d not in held:
                out.append(d)
        except cal_mod.CalendarError:
            pass                                     # unclassifiable dates are handled by the overlay (D33, D39)
        d += datetime.timedelta(days=1)
    return out


def scan_symbol(inp, config):
    if config.trade_type not in m.TRADE_TYPES:
        raise ValueError("unknown trade type %r" % config.trade_type)
    known = inp.findings_at(config.as_of.date())          # nothing dated after as_of (prefix invariance)
    errors = [f for f in known if f.severity == marketdata.ERROR]
    findings = [f.to_dict() for f in known]
    limitations = sorted(set(inp.limitations))
    base = dict(symbol=inp.symbol, candidates=[], blocked_zones=[], fresh_zones=[], tda=[], series={},
                provenance=dict(inp.provenance), price=None)
    if config.trade_type != m.MIT:
        return SymbolResult(status=SYMBOL_BLOCKED, reasons=[qualification.M4B_INTRADAY_NOT_APPROVED],
                            findings=findings, limitations=limitations, **base)
    if errors:
        return SymbolResult(status=SYMBOL_DATA_INSUFFICIENT,
                            reasons=["%s: %s" % (f.code, f.detail) for f in errors],
                            findings=findings, limitations=limitations, **base)
    cut = _last_unresolved_date(inp, config)
    if cut is not None:
        # D54 / ED-44: a series never runs across an UNRESOLVED calendar date (L10), so the
        # history used starts after the last one before as_of; older timeframes then lack
        # history (fail-closed) instead of every later scan being blocked by that date
        inp = dataclasses.replace(inp, candles=[c for c in inp.candles if c.start.date() > cut])
        limitations = sorted(set(limitations) | {m.HISTORY_STARTS_AFTER_UNRESOLVED_DATE})
        findings.append(marketdata.Finding(inp.symbol, marketdata.WARNING, m.HISTORY_STARTS_AFTER_UNRESOLVED_DATE,
                                           "history used from the first session after %s, an UNRESOLVED calendar "
                                           "date (CAL-2, D54); earlier candles are not replayed" % cut,
                                           date=cut).to_dict())
    try:
        snap = mtf.replay(inp.candles, "D", htf=HTF, as_of=config.as_of, calendar=config.calendar)
    except cal_mod.CalendarCoverageError as e:
        return SymbolResult(status=SYMBOL_DATA_INSUFFICIENT, reasons=["CALENDAR_COVERAGE: %s" % e],
                            findings=findings, limitations=limitations, **base)
    except ValueError as e:
        return SymbolResult(status=SYMBOL_DATA_INSUFFICIENT, reasons=["REPLAY_INPUT: %s" % e],
                            findings=findings, limitations=limitations, **base)
    findings += [f.to_dict() for f in marketdata.snapshot_findings(inp.symbol, snap)]
    price = _price(inp.candles, snap)
    if price is None:
        return SymbolResult(status=SYMBOL_DATA_INSUFFICIENT, reasons=["NO_COMPLETED_CANDLE_AT_OR_BEFORE_AS_OF"],
                            findings=findings, limitations=limitations, **base)
    acts = []
    if config.corporate_actions is not None and inp.candles:
        acts = [a.to_dict() for a in corporate_actions.in_history(
            config.corporate_actions, inp.symbol, inp.candles[0].start.date(), config.as_of.date())]
    unobserved = []
    if inp.candles:
        first = inp.candles[0].start.date()
        held_without_row = frozenset(f.date for f in known if f.code == "NO_ROW_IN_FILE")
        for f in known:
            # R-12: a price-scale gap holds G0 unless a recorded price-scale action falls in the
            # same step (that action already holds G0). D52 never explains it: a calendar gap
            # does not move the whole session range by more than the band.
            if f.code != corporate_actions.PRICE_SCALE_GAP or not first < f.date:
                continue
            last = datetime.date.fromisoformat((f.extra or {}).get("last_date") or "0001-01-01")
            if any(a.symbol == inp.symbol and a.action in corporate_actions.PRICE_ACTIONS and last < a.ex_date <= f.date
                   for a in (config.corporate_actions or [])):
                findings.append(marketdata.Finding(inp.symbol, marketdata.INFO, "PRICE_SCALE_GAP_AT_RECORDED_ACTION",
                                                   "%s: gap on the ex-date of a recorded action; G0 is held by "
                                                   "CORPORATE_ACTION_IN_HISTORY" % f.date, date=f.date).to_dict())
                continue
            acts.append({"ex_date": f.date.isoformat(), "action": corporate_actions.PRICE_SCALE_GAP,
                         "ratio": f.extra["ratio"], "verified": False,
                         "source": "bhavcopy price range (%s)" % f.extra["file"]})
        for f in known:
            if f.code != "PREVCLOSE_DISCONTINUITY" or not first < f.date:
                continue
            why = _explained_by_excluded_session(f, inp.symbol, config, held_without_row)
            if why:
                findings.append(marketdata.Finding(inp.symbol, marketdata.INFO, "PREVCLOSE_EXPLAINED_BY_EXCLUDED_SESSION",
                                                   "%s: %s" % (f.date, why), date=f.date).to_dict())
                continue
            acts.append({"ex_date": f.date.isoformat(), "action": "PREVCLOSE_DISCONTINUITY", "ratio": f.extra["ratio"],
                         "verified": False, "source": "bhavcopy PREVCLOSE (%s)" % f.extra["file"]})
        unobserved = _unobserved_excluded_sessions(inp, config, first)
        for d in unobserved:
            findings.append(marketdata.Finding(inp.symbol, marketdata.WARNING, m.EXCLUDED_SESSION_UNOBSERVED,
                                               "%s: calendar-excluded session with no EOD file held" % d, date=d).to_dict())
        if unobserved and m.EXCLUDED_SESSION_UNOBSERVED not in limitations:
            limitations = sorted(set(limitations) | {m.EXCLUDED_SESSION_UNOBSERVED})
    ctx = qualification.SymbolContext(symbol=inp.symbol, trade_type=config.trade_type, snapshot=snap,
                                      price=price, limitations=limitations,
                                      risk_per_trade=config.risk_per_trade, corporate_actions=acts,
                                      corporate_action_coverage=config.corporate_action_coverage,
                                      unobserved_excluded_sessions=unobserved)
    ev = qualification.evaluate_symbol(ctx)
    if ev["gate0"].outcome == m.DATA_INSUFFICIENT:
        status, reasons = SYMBOL_DATA_INSUFFICIENT, list(ev["gate0"].reasons)
    elif ev["candidates"]:
        status, reasons = SYMBOL_EVALUATED, []
    else:
        status, reasons = SYMBOL_NO_EXECUTION_ZONE, ["no fresh demand zone on D passed the MTF overlay"]
    base.update(candidates=ev["candidates"], blocked_zones=ev["blocked_zones"],
                fresh_zones=_fresh_zone_rows(inp.symbol, snap), tda=ev["tda"], series=ev["series"], price=price)
    return SymbolResult(status=status, reasons=reasons, findings=findings, limitations=ev["limitations"], **base)


def scan(inputs, config, universe=None):
    """inputs: DailyInput per symbol. universe: optional universe.Universe; a symbol that
    is not a member at as_of is reported, not scanned."""
    as_of_date = config.as_of.date()
    members = None
    limitations = [m.TRADINGVIEW_PARITY_UNVERIFIED, m.NOT_EXTERNALLY_VALIDATED]
    if universe is not None:
        members = set(r.symbol for r in universe.members(as_of_date))
        limitations += universe.limitations(as_of_date)
    else:
        limitations.append(m.UNIVERSE_UNVERIFIED)
    if config.calendar is None:
        limitations.append(m.CALENDAR_UNVALIDATED)
    results = []
    for inp in sorted(inputs, key=lambda i: i.symbol):
        if members is not None and inp.symbol not in members:
            results.append(SymbolResult(inp.symbol, SYMBOL_NOT_IN_UNIVERSE, ["not a member at %s" % as_of_date],
                                        None, [], [], [], [], {}, [], dict(inp.provenance), []))
            continue
        results.append(scan_symbol(inp, config))
    # a member at as_of with no market-data input is reported, never silently dropped
    # (survivorship: a delisted or renamed member may simply have no file; B11)
    held = set(i.symbol for i in inputs)
    for sym in sorted((members or set()) - held):
        results.append(SymbolResult(sym, SYMBOL_DATA_INSUFFICIENT,
                                    ["NO_INPUT_FOR_UNIVERSE_MEMBER: a member at %s has no market data" % as_of_date],
                                    None, [], [], [], [], {}, [], {}, []))
    results.sort(key=lambda r: r.symbol)
    return ScanResult(
        pipeline_version=m.PIPELINE_VERSION,
        engine_versions={"zone_engine": ze.ENGINE_VERSION, "mtf_freshness": mtf.ENGINE_VERSION},
        as_of=config.as_of.isoformat(), generated_at=config.generated_at, trade_type=config.trade_type,
        calendar=config.calendar_label, universe=config.universe_label if universe is None else universe.name,
        symbols=results, limitations=sorted(set(limitations)))


def scan_history(inputs, as_of_times, config, universe=None):
    """Point-in-time scans (signal generation only). Each scan reads only candles that
    end at or before its own as_of. Outcome evaluation and fills are not implemented
    (B9, B12): no performance figure is produced."""
    out = []
    for t in sorted(as_of_times):
        cfg = dataclasses.replace(config, as_of=t)
        out.append(scan(inputs, cfg, universe))      # membership as of each scan date (B11)
    return out
