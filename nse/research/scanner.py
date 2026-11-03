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
    if inp.candles:
        first = inp.candles[0].start.date()
        acts += [{"ex_date": f.date.isoformat(), "action": "PREVCLOSE_DISCONTINUITY", "ratio": f.extra["ratio"],
                  "verified": False, "source": "bhavcopy PREVCLOSE (%s)" % f.extra["file"]}
                 for f in known if f.code == "PREVCLOSE_DISCONTINUITY" and first < f.date]
    ctx = qualification.SymbolContext(symbol=inp.symbol, trade_type=config.trade_type, snapshot=snap,
                                      price=price, limitations=limitations,
                                      risk_per_trade=config.risk_per_trade, corporate_actions=acts)
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
