#!/usr/bin/env python3
"""Higher-timeframe freshness orchestrator for the NSE Zone Engine. Standard library only.

The Zone Engine (nse/zone-engine/zone_engine.py) tests a weekly zone only when the
whole weekly candle completes, as the Pine Script does (PS 2701-2706). The Rulebook
says ANY candle touching the proximal line makes a zone tested (RB 264, 683-697), and
zone status must be updated after every session (RB 292, 1508). This module applies
every completed candle of the finest reliable base series to the higher-timeframe
zones, so a weekly zone touched on Tuesday is tested at Tuesday's close (blocker B16).

It reads no market data, connects to no broker and never places an order. It
produces no entry candidates. Entry eligibility stays with the Zone Engine; the only
thing this module can do to it is REMOVE a zone the overlay no longer sees as fresh
(eligible_after_overlay). It never adds one.

Approved decisions (nse/docs/DECISION_LOG.md, design approval of 2026-10-26):
  A1  A completed higher-timeframe candle closing beyond the distal line invalidates
      the zone (PS 2667, 2718). A base-candle close beyond it is evidence only: status
      BASE_CLOSE_BEYOND_DL_PENDING (manual review, never fresh) until that higher-
      timeframe period completes.
  A2  Both counts are kept: base_touch_count (one per touching base candle) and the
      engine's htf_test_count (Pine reference view). Only fresh vs tested gates.
  A3  The base is the finest reliable completed series supplied. Every event records
      the source timeframe and the candle's start and end; a daily base gives
      day-level timing, never intraday.
  A4  A missing session after a zone became knowable and before any touch makes the
      zone UNKNOWN_DATA_GAP. Freshness is never inferred from missing candles.
  A5  Without a trading calendar a period counts as complete only once a candle from
      a later period exists (one session late, never early), every missing weekday
      is an unverified gap, and the snapshot carries CALENDAR_UNVALIDATED.

Phase 1 correctness audit remediation (H1, H2; nse/docs/PHASE1_CORRECTNESS_AUDIT.md):
  H1  Session classification runs before aggregation. A candle on a calendar-excluded
      session (Muhurat, shortened; D30) never enters an HTF candle or the touch count;
      if it reaches a zone's proximal or distal line after creation the zone needs
      manual review (EXCLUDED_SESSION_TOUCH), because no rule says what such a touch
      means. A candle whose session cannot be classified (a weekend date without a
      calendar, an intraday candle outside 09:15-15:30, a candle on a day the calendar
      says is closed) is also kept out, and every zone whose formation-to-as_of span
      contains it is UNVERIFIED_SESSION. Every kept-out candle is listed in
      excluded_candles; none is dropped silently.
  H2  Data gaps count from the first day of the first formation period (leg-in, else
      base) through as_of, not only after creation: missing data could have changed
      the geometry. With a calendar, a period with no data at all also ends the
      series, as a partly missing one does: candles are never stitched across a gap.
  An untouched zone with any unresolved manual-review flag is MANUAL_REVIEW, never FRESH.
  L10 A date the calendar cannot classify (it raises one of calendar.UNRESOLVED_ERRORS,
      e.g. an UNRESOLVED row) is handled per date: its candles are set aside as
      CALENDAR_UNRESOLVED, it is never a gap, every period containing it ends its series
      (HTF_SERIES_TRUNCATED_AT_UNRESOLVED_CALENDAR) and every zone whose formation-to-as_of
      span contains it is UNVERIFIED_SESSION. Any other calendar error (missing coverage)
      stops the replay.
  Without a calendar, a weekday Muhurat or shortened session looks like a normal day
  and cannot be detected; only CALENDAR_UNVALIDATED marks that limitation.

Order of work for one replay (the as-of time cuts the input first):
  1. Keep completed base candles whose END is at or before as_of; set aside, with a
     classification, every candle not from a normal session (H1).
  2. Build completed higher-timeframe candles (calendar periods, D23). The period in
     progress is never used. A period with a known missing session ends the series.
  3. Run the Zone Engine on each completed series (candle time = period end).
  4. For each zone, apply base candles that START at or after the end of its creation
     period (RB 682: after the leg-out closed), up to the end of its invalidating
     period, if any.
  5. Derive the status: INVALIDATED > BASE_CLOSE_BEYOND_DL_PENDING > TESTED >
     UNVERIFIED_SESSION > UNKNOWN_DATA_GAP > MANUAL_REVIEW > FRESH. An untouched zone
     keeps every session and gap reason, whichever of the last four wins.
Tested and invalidated are permanent as as_of moves forward; replay is a pure function
of its inputs.

Session times are NSE's regular session, 09:15-15:30 IST (RB 186, 3323). All
datetimes must be in one convention (all naive IST or all timezone-aware).
"""

import datetime
import importlib.util
import json
import math
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

_ZE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "zone-engine", "zone_engine.py")
_spec = importlib.util.spec_from_file_location("nse_zone_engine", _ZE_PATH)
ze = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ze)

ENGINE_VERSION = "1.0.0"

SESSION_OPEN = datetime.time(9, 15)
SESSION_CLOSE = datetime.time(15, 30)
# intraday base intervals must tile the 375-minute session exactly (RB 186-193)
INTRADAY_MINUTES = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "25m": 25, "75m": 75, "125m": 125}
BASE_TIMEFRAMES = ["D"] + list(INTRADAY_MINUTES)
HTF_ORDER = ["D", "W", "M", "Q", "HY", "Y"]

FRESH = "FRESH"
TESTED = "TESTED"
BASE_CLOSE_BEYOND_DL_PENDING = "BASE_CLOSE_BEYOND_DL_PENDING"   # A1: manual review
INVALIDATED = "INVALIDATED"
UNKNOWN_DATA_GAP = "UNKNOWN_DATA_GAP"                           # A4
UNVERIFIED_SESSION = "UNVERIFIED_SESSION"                       # H1: session not classifiable
MANUAL_REVIEW = "MANUAL_REVIEW"                                 # untouched, but a flag is unresolved

PL_TOUCH = "PL_TOUCH"
DL_TOUCH = "DL_TOUCH"
BASE_CLOSE_BEYOND_DL = "BASE_CLOSE_BEYOND_DL"

CALENDAR_UNVALIDATED = "CALENDAR_UNVALIDATED"                   # A5
HTF_SERIES_TRUNCATED_AT_GAP = "HTF_SERIES_TRUNCATED_AT_GAP"
HTF_SERIES_TRUNCATED_AT_UNRESOLVED_CALENDAR = "HTF_SERIES_TRUNCATED_AT_UNRESOLVED_CALENDAR"  # L10
CALENDAR_UNRESOLVED_DATES = "CALENDAR_UNRESOLVED_DATES"         # L10: snapshot limitation
PARTIAL_FIRST_PERIOD = "PARTIAL_FIRST_PERIOD"                   # D23
BASE_CLOSE_BEYOND_DL_RESOLVED = "BASE_CLOSE_BEYOND_DL_RESOLVED_NOT_INVALIDATED"
OVERLAY_NOT_FRESH = "OVERLAY_NOT_FRESH"
EXCLUDED_SESSION_TOUCH = "EXCLUDED_SESSION_TOUCH"               # H1: manual review

# candle classifications for excluded_candles (H1); the first two come from the
# calendar (nse_calendar.session_type) and are excluded by D30
CONFIRMED_EXCLUSIONS = ("EXCLUDED_MUHURAT", "EXCLUDED_SHORTENED")
OUTSIDE_REGULAR_HOURS = "OUTSIDE_REGULAR_HOURS"
NOT_A_TRADING_DAY = "NOT_A_TRADING_DAY"         # calendar without session_type says closed
CALENDAR_UNRESOLVED = "CALENDAR_UNRESOLVED"     # L10: the calendar cannot classify the date


# --- models ---------------------------------------------------------------------

@dataclass(frozen=True)
class TimedCandle:
    start: datetime.datetime
    end: datetime.datetime
    open: float
    high: float
    low: float
    close: float
    complete: bool = True


@dataclass
class HtfCandle:
    tf: str
    period_key: str
    start: datetime.datetime
    end: datetime.datetime            # end of the last base candle in the period
    known_at: datetime.datetime       # when the period is confirmed complete
    open: float
    high: float
    low: float
    close: float
    sessions_present: int
    sessions_expected: Optional[int]  # None without a calendar
    partial_first_period: bool


@dataclass
class TouchEvent:
    kind: str
    time: datetime.datetime           # the base candle's end: when the event became known
    candle_start: datetime.datetime
    source_tf: str                    # A3: the precision of this timestamp
    price: float
    htf_period_key: str


@dataclass
class DataGap:
    date: datetime.date
    verified: bool                    # True with a calendar or for a partial intraday session
    kind: str                         # MISSING_SESSION or PARTIAL_SESSION


@dataclass
class ExcludedCandle:
    date: datetime.date
    classification: str               # a CONFIRMED_EXCLUSIONS value, or why it is unresolved
    candle: TimedCandle


@dataclass
class ZoneTouchState:
    key: str
    tf: str
    zone_id: str
    side: str
    pattern: str
    proximal: float
    distal: float
    creation_period_end: datetime.datetime
    known_at: datetime.datetime
    events: List[TouchEvent] = field(default_factory=list)
    first_touch_at: Optional[datetime.datetime] = None
    base_touch_count: int = 0
    htf_test_count: int = 0           # the Zone Engine / Pine reference view (A2)
    dl_touched_at: Optional[datetime.datetime] = None
    invalidated_period_end: Optional[datetime.datetime] = None
    invalidation_known_at: Optional[datetime.datetime] = None
    engine_status: str = ""
    status: str = FRESH
    reasons: List[str] = field(default_factory=list)
    manual_review: List[str] = field(default_factory=list)

    @property
    def usable_as_fresh_context(self):
        return self.status == FRESH and not self.manual_review


@dataclass
class HtfSeries:
    tf: str
    candles: List[HtfCandle]
    engine: Optional[object]          # zone_engine.EngineResult
    in_progress_period: Optional[str]
    truncated_at: Optional[str]
    reasons: List[str]


@dataclass
class MtfSnapshot:
    engine_version: str
    as_of: datetime.datetime
    base_tf: str
    calendar_validated: bool
    limitations: List[str]
    base_candles_used: int
    ignored_incomplete: List[datetime.datetime]
    data_gaps: List[DataGap]
    excluded_candles: List[ExcludedCandle]
    unresolved_calendar_dates: List[datetime.date]   # L10, from first candle to as_of
    series: Dict[str, HtfSeries]
    zones: Dict[str, ZoneTouchState]

    def eligible_after_overlay(self, tf):
        """The Zone Engine's eligible zones on tf, minus any the overlay does not see as
        fresh. Returns (kept, blocked); blocked holds (assessment, reasons)."""
        s = self.series.get(tf)
        if s is None or s.engine is None:
            return [], []
        kept, blocked = [], []
        for a in s.engine.eligible:
            st = self.zones.get("%s:%s" % (tf, a.zone.id))
            if st is not None and st.usable_as_fresh_context:
                kept.append(a)
            else:
                why = [OVERLAY_NOT_FRESH] + ([st.status] if st else []) + (st.manual_review if st else [])
                blocked.append((a, why))
        return kept, blocked

    def to_dict(self):
        """Every field plus the derived views (audit L4): each zone's usable_as_fresh_context
        and, per timeframe, the eligible_after_overlay result as kept ids and blocked ids
        with reasons."""
        out = asdict(self)
        for tf, s in self.series.items():
            out["series"][tf]["engine"] = None if s.engine is None else s.engine.to_dict()
        for key, z in self.zones.items():
            out["zones"][key]["usable_as_fresh_context"] = z.usable_as_fresh_context
        out["overlay"] = {}
        for tf in self.series:
            kept, blocked = self.eligible_after_overlay(tf)
            out["overlay"][tf] = {"kept": [a.zone.id for a in kept],
                                  "blocked": [{"zone_id": a.zone.id, "reasons": why} for a, why in blocked]}
        return out

    def to_json(self, **kw):
        """to_dict() as JSON: dates and datetimes in ISO 8601, keys sorted (deterministic)."""
        return json.dumps(self.to_dict(), default=json_default, sort_keys=True, **kw)


def json_default(value):
    """json.dumps hook: dates and datetimes as ISO 8601. Anything else is refused, never
    stringified, so an unexpected type cannot slip into a validation artifact."""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    raise TypeError("not JSON-serialisable: %s" % type(value).__name__)


# --- calendar periods (D23) --------------------------------------------------------

def period_key(tf, d):
    if tf == "D":
        return d.isoformat()
    if tf == "W":
        y, w, _ = d.isocalendar()
        return "%04d-W%02d" % (y, w)
    if tf == "M":
        return "%04d-%02d" % (d.year, d.month)
    if tf == "Q":
        return "%04d-Q%d" % (d.year, (d.month - 1) // 3 + 1)
    if tf == "HY":
        return "%04d-H%d" % (d.year, 1 if d.month <= 6 else 2)
    if tf == "Y":
        return "%04d" % d.year
    raise ValueError("unknown timeframe %r" % tf)


def period_bounds(tf, d):
    """First and last calendar date of the period containing d."""
    if tf == "D":
        return d, d
    if tf == "W":
        first = d - datetime.timedelta(days=d.weekday())
        return first, first + datetime.timedelta(days=6)
    if tf == "M":
        first = d.replace(day=1)
    elif tf == "Q":
        first = datetime.date(d.year, 3 * ((d.month - 1) // 3) + 1, 1)
    elif tf == "HY":
        first = datetime.date(d.year, 1 if d.month <= 6 else 7, 1)
    elif tf == "Y":
        first = datetime.date(d.year, 1, 1)
    else:
        raise ValueError("unknown timeframe %r" % tf)
    months = {"M": 1, "Q": 3, "HY": 6, "Y": 12}[tf]
    m = first.month - 1 + months
    nxt = datetime.date(first.year + m // 12, m % 12 + 1, 1)
    return first, nxt - datetime.timedelta(days=1)


def _days(a, b):
    d = a
    while d <= b:
        yield d
        d += datetime.timedelta(days=1)


# --- validation -------------------------------------------------------------------

def _validate(candles, base_tf):
    aware = None
    prev = None
    for i, c in enumerate(candles):
        for v in (c.open, c.high, c.low, c.close):
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
                raise ValueError("base candle %d has a non-numeric price" % i)
        if c.low > min(c.open, c.close) or c.high < max(c.open, c.close):
            raise ValueError("base candle %d has inconsistent OHLC" % i)
        for t in (c.start, c.end):
            if not isinstance(t, datetime.datetime):
                raise ValueError("base candle %d times must be datetime" % i)
            is_aware = t.tzinfo is not None
            if aware is None:
                aware = is_aware
            elif aware != is_aware:
                raise ValueError("mixed naive and timezone-aware datetimes (index %d)" % i)
        if not c.start < c.end or c.start.date() != c.end.date():
            raise ValueError("base candle %d must start before it ends, on one date" % i)
        if base_tf in INTRADAY_MINUTES:
            if c.end - c.start != datetime.timedelta(minutes=INTRADAY_MINUTES[base_tf]):
                raise ValueError("base candle %d is not a %s candle" % (i, base_tf))
            # wholly outside the session is classified later (H1); straddling is malformed
            if c.start.time() < SESSION_OPEN < c.end.time() or c.start.time() < SESSION_CLOSE < c.end.time():
                raise ValueError("base candle %d straddles the 09:15-15:30 session boundary" % i)
        if prev is not None:
            if base_tf == "D" and c.start.date() <= prev.start.date():
                raise ValueError("daily base candles must be one per date, in order (index %d)" % i)
            if c.start < prev.end:
                raise ValueError("base candles overlap or are out of order (index %d)" % i)
        prev = c


class _CalendarDays(object):
    """is_trading_day per date: True, False, or None when the calendar raises one of the
    errors it declares in UNRESOLVED_ERRORS for that date (L10). Any other error, such as
    missing coverage, propagates. Without a calendar every weekday is expected (A5)."""

    def __init__(self, calendar):
        self.calendar = calendar
        self.errors = tuple(getattr(calendar, "UNRESOLVED_ERRORS", ())) if calendar is not None else ()
        self.cache = {}

    def trading(self, d):
        if self.calendar is None:
            return d.weekday() < 5
        if d not in self.cache:
            try:
                self.cache[d] = bool(self.calendar.is_trading_day(d))
            except self.errors:
                self.cache[d] = None
        return self.cache[d]


def _classify(candles, base_tf, calendar, days):
    """Split candles into normal-session ones and ExcludedCandle records (H1, L10)."""
    kept, excluded = [], []
    for c in candles:
        d = c.start.date()
        trading = days.trading(d)
        if calendar is None:
            why = None if trading else UNVERIFIED_SESSION
        elif trading is None:
            why = CALENDAR_UNRESOLVED
        elif trading:
            why = None
        else:
            session_type = getattr(calendar, "session_type", None)
            why = session_type(d) if session_type is not None else NOT_A_TRADING_DAY
        if why is None and base_tf in INTRADAY_MINUTES and (
                c.start.time() < SESSION_OPEN or c.end.time() > SESSION_CLOSE):
            why = OUTSIDE_REGULAR_HOURS if calendar is not None else UNVERIFIED_SESSION
        if why is None:
            kept.append(c)
        else:
            excluded.append(ExcludedCandle(d, why, c))
    return kept, excluded


def _close_of(d, tzinfo):
    return datetime.datetime.combine(d, SESSION_CLOSE, tzinfo=tzinfo)


# --- replay -----------------------------------------------------------------------

def replay(base_candles, base_tf, htf=("W", "M", "Q", "HY", "Y"), as_of=None, calendar=None,
           rules=None):
    """Pure function: same inputs, same snapshot.

    base_candles  TimedCandle sequence, oldest first: the finest reliable series (A3)
    base_tf       "D" or an intraday interval that divides 375 minutes
    htf           higher timeframes to track; each must be coarser than base_tf, except
                  that "D" may repeat a daily base so daily zones get the same session
                  and gap checks as every other timeframe
    as_of         datetime; nothing ending after it is read (default: last candle end)
    calendar      object with is_trading_day(date) -> bool, or None (A5 fallback).
                  Optional: session_type(date) -> str names excluded sessions (D33), and
                  UNRESOLVED_ERRORS, a tuple of exception types that mean "this one date
                  cannot be classified" (L10); every other exception stops the replay.
    """
    if base_tf not in BASE_TIMEFRAMES:
        raise ValueError("unsupported base timeframe %r; allowed: %s" % (base_tf, ", ".join(BASE_TIMEFRAMES)))
    htf = list(htf)
    for tf in htf:
        if tf not in HTF_ORDER:
            raise ValueError("timeframe %r is not above base %r" % (tf, base_tf))
    if len(set(htf)) != len(htf):
        raise ValueError("duplicate timeframe in htf")

    candles = list(base_candles)
    if as_of is None:
        as_of = max((c.end for c in candles), default=None)
    if as_of is None:
        raise ValueError("no base candles and no as_of")
    candles = [c for c in candles if c.end <= as_of]          # step 1: nothing from the future
    _validate(candles, base_tf)
    k = len(candles)
    while k > 0 and not candles[k - 1].complete:
        k -= 1
    if any(not c.complete for c in candles[:k]):
        raise ValueError("an incomplete base candle is followed by completed ones")
    ignored = [c.end for c in candles[k:]]
    days = _CalendarDays(calendar)
    candles, excluded = _classify(candles[:k], base_tf, calendar, days)
    tz = as_of.tzinfo

    limitations = []
    if calendar is None:
        limitations.append(CALENDAR_UNVALIDATED)

    # trading days: present, partial (intraday base only), expected
    by_day = {}
    for c in candles:
        by_day.setdefault(c.start.date(), []).append(c)
    complete_days = set()
    gaps = []
    for d, cs in by_day.items():
        if base_tf == "D":
            complete_days.add(d)
            continue
        whole = (cs[0].start.time() == SESSION_OPEN and cs[-1].end.time() == SESSION_CLOSE
                 and all(cs[j].end == cs[j + 1].start for j in range(len(cs) - 1)))
        if whole:
            complete_days.add(d)
        elif _close_of(d, tz) <= as_of:
            gaps.append(DataGap(d, True, "PARTIAL_SESSION"))
    if candles:
        first_day = candles[0].start.date()
        last_closed = as_of.date() if _close_of(as_of.date(), tz) <= as_of else as_of.date() - datetime.timedelta(days=1)
        for d in _days(first_day, last_closed):
            if days.trading(d) and d not in by_day:            # an unresolved date is never a gap
                gaps.append(DataGap(d, calendar is not None, "MISSING_SESSION"))
    gaps.sort(key=lambda g: g.date)
    gap_days = set(g.date for g in gaps)
    seen = [c.start.date() for c in candles] + [x.date for x in excluded]
    unresolved_dates = [] if calendar is None or not seen else \
        [d for d in _days(min(seen), as_of.date()) if days.trading(d) is None]
    if unresolved_dates:
        limitations.append(CALENDAR_UNRESOLVED_DATES)

    series = {}
    zones = {}
    for tf in sorted(htf, key=HTF_ORDER.index):
        s = _build_series(tf, candles, complete_days, gap_days, days.trading, calendar, as_of, tz)
        if s.candles:
            ec = [ze.Candle(h.end, h.open, h.high, h.low, h.close) for h in s.candles]
            s.engine = ze.run_engine(ec, tf, rules=rules)
        series[tf] = s
        if s.engine is None:
            continue
        completed_keys = set(h.period_key for h in s.candles)
        for a in s.engine.assessments:
            st = _overlay(tf, a, s, candles, excluded, unresolved_dates, base_tf, completed_keys,
                          gaps, as_of, tz)
            zones[st.key] = st

    return MtfSnapshot(engine_version=ENGINE_VERSION, as_of=as_of, base_tf=base_tf,
                       calendar_validated=calendar is not None, limitations=limitations,
                       base_candles_used=len(candles), ignored_incomplete=ignored,
                       data_gaps=gaps, excluded_candles=excluded,
                       unresolved_calendar_dates=unresolved_dates, series=series, zones=zones)


def _build_series(tf, candles, complete_days, gap_days, expected_day, calendar, as_of, tz):
    periods = []                      # (key, [base candles]) in order
    for c in candles:
        key = period_key(tf, c.start.date())
        if not periods or periods[-1][0] != key:
            periods.append((key, []))
        periods[-1][1].append(c)
    out, reasons = [], []
    in_progress, truncated = None, None
    series_first_day = candles[0].start.date() if candles else None
    prev_last = None
    for n, (key, cs) in enumerate(periods):
        first, last = period_bounds(tf, cs[0].start.date())
        if calendar is not None and prev_last is not None:
            between = list(_days(prev_last + datetime.timedelta(days=1),
                                 cs[0].start.date() - datetime.timedelta(days=1)))
            skipped = [d for d in between if d in gap_days or expected_day(d) is None]
            if skipped:                                       # a whole period without data
                truncated = period_key(tf, min(skipped))
                reasons.append(_truncation_reason(min(skipped), gap_days))
                break
        if calendar is not None and any(expected_day(d) is None for d in _days(first, last)):
            truncated = key                                   # its sessions are unknown (L10)
            reasons.append(HTF_SERIES_TRUNCATED_AT_UNRESOLVED_CALENDAR)
            break
        days_present = sorted(set(c.start.date() for c in cs))
        if any(d not in complete_days for d in days_present if _close_of(d, tz) <= as_of):
            truncated = key                                   # a partial session is a known gap
        expected = [d for d in _days(max(first, series_first_day), last) if expected_day(d)]
        if calendar is not None:
            last_trading = expected[-1] if expected else last
            if _close_of(last_trading, tz) > as_of:
                in_progress = key
                break
            if any(d not in complete_days for d in expected):
                truncated = key
            known_at = cs[-1].end
            sessions_expected = len(expected)
        else:
            if n + 1 >= len(periods):
                in_progress = key                             # no later evidence yet (A5)
                break
            known_at = periods[n + 1][1][0].end
            sessions_expected = None
        if truncated is not None:
            reasons.append(HTF_SERIES_TRUNCATED_AT_GAP)
            break
        whole_first = [d for d in _days(first, last) if expected_day(d)]
        partial_first = n == 0 and bool(whole_first) and cs[0].start.date() > whole_first[0]
        out.append(HtfCandle(
            tf=tf, period_key=key, start=cs[0].start, end=cs[-1].end, known_at=known_at,
            open=cs[0].open, high=max(c.high for c in cs), low=min(c.low for c in cs),
            close=cs[-1].close, sessions_present=len(days_present),
            sessions_expected=sessions_expected, partial_first_period=partial_first))
        prev_last = cs[-1].start.date()
    else:
        trailing = [] if calendar is None or prev_last is None else \
            [d for d in _days(prev_last + datetime.timedelta(days=1), as_of.date())
             if d in gap_days or expected_day(d) is None]
        if trailing:                                          # expected periods after the data
            truncated = period_key(tf, min(trailing))
            reasons.append(_truncation_reason(min(trailing), gap_days))
    return HtfSeries(tf=tf, candles=out, engine=None, in_progress_period=in_progress,
                     truncated_at=truncated, reasons=reasons)


def _truncation_reason(d, gap_days):
    return HTF_SERIES_TRUNCATED_AT_GAP if d in gap_days else HTF_SERIES_TRUNCATED_AT_UNRESOLVED_CALENDAR


def _touches(c, z):
    """(proximal touched, distal touched) by candle c for zone z."""
    if z.is_demand:
        return c.low <= z.proximal, c.low <= z.distal
    return c.high >= z.proximal, c.high >= z.distal


def _overlay(tf, assessment, s, candles, excluded, unresolved_dates, base_tf, completed_keys,
             gaps, as_of, tz):
    z = assessment.zone
    h = s.candles
    created = h[z.created_index]
    st = ZoneTouchState(
        key="%s:%s" % (tf, z.id), tf=tf, zone_id=z.id, side=z.side, pattern=z.pattern,
        proximal=z.proximal, distal=z.distal,
        creation_period_end=created.end, known_at=created.known_at,
        htf_test_count=z.test_count, engine_status=assessment.status)
    stop = None
    if z.invalidated_index is not None:
        inv = h[z.invalidated_index]
        st.invalidated_period_end, st.invalidation_known_at = inv.end, inv.known_at
        stop = inv.end
    demand = z.is_demand
    for c in candles:
        if c.start < created.end:                 # creation period and earlier: RB 682
            continue
        if stop is not None and c.start >= stop:  # invalidation is permanent
            break
        pkey = period_key(tf, c.start.date())
        if (c.low <= z.proximal) if demand else (c.high >= z.proximal):
            st.events.append(TouchEvent(PL_TOUCH, c.end, c.start, base_tf,
                                        c.low if demand else c.high, pkey))
            st.base_touch_count += 1
            if st.first_touch_at is None:
                st.first_touch_at = c.end
        if (c.low <= z.distal) if demand else (c.high >= z.distal):
            st.events.append(TouchEvent(DL_TOUCH, c.end, c.start, base_tf,
                                        c.low if demand else c.high, pkey))
            if st.dl_touched_at is None:
                st.dl_touched_at = c.end
        if (c.close < z.distal) if demand else (c.close > z.distal):
            st.events.append(TouchEvent(BASE_CLOSE_BEYOND_DL, c.end, c.start, base_tf, c.close, pkey))

    # the Pine view can never see a touch the base series did not (HTF low = min of base lows)
    touched_periods = set(e.htf_period_key for e in st.events if e.kind == PL_TOUCH)
    for t in z.test_indices:
        if h[t].period_key not in touched_periods:
            raise RuntimeError("inconsistent data: engine test in %s without a base touch (%s)"
                               % (h[t].period_key, st.key))

    # H1: excluded sessions never test the zone, but a touch there is not ignored either
    for x in excluded:
        if x.classification not in CONFIRMED_EXCLUSIONS or x.candle.start < created.end:
            continue
        if stop is not None and x.candle.start >= stop:
            continue
        if any(_touches(x.candle, z)):
            if EXCLUDED_SESSION_TOUCH not in st.manual_review:
                st.manual_review.append(EXCLUDED_SESSION_TOUCH)
            st.reasons.append("%s %s %s" % (EXCLUDED_SESSION_TOUCH, x.date.isoformat(), x.classification))

    if z.start_index == 0 or z.legin_index == 0 or z.created_index == 0:
        if h[0].partial_first_period:
            st.manual_review.append(PARTIAL_FIRST_PERIOD)
    beyond = [e for e in st.events if e.kind == BASE_CLOSE_BEYOND_DL]
    pending = [e for e in beyond if e.htf_period_key not in completed_keys]
    if z.invalidated_index is not None:
        st.status = INVALIDATED
    elif pending:
        st.status = BASE_CLOSE_BEYOND_DL_PENDING
        st.manual_review.append(BASE_CLOSE_BEYOND_DL)
    elif st.first_touch_at is not None:
        st.status = TESTED
        if beyond:
            st.manual_review.append(BASE_CLOSE_BEYOND_DL_RESOLVED)
    else:
        # H2: from the first day of the first formation period (leg-in, else base) through
        # as_of; the period's own first session may be the one that is missing
        first = z.start_index if z.legin_index is None else min(z.legin_index, z.start_index)
        formation_first_day = period_bounds(tf, h[first].start.date())[0]
        unresolved = sorted(set(x.date for x in excluded
                                if x.classification not in CONFIRMED_EXCLUSIONS + (CALENDAR_UNRESOLVED,)
                                and x.date >= formation_first_day))
        ambiguous = [d for d in unresolved_dates if d >= formation_first_day]
        relevant = [g for g in gaps if g.date >= formation_first_day and _close_of(g.date, tz) <= as_of]
        st.reasons.extend("%s %s" % (UNVERIFIED_SESSION, d.isoformat()) for d in unresolved)
        st.reasons.extend("%s %s" % (CALENDAR_UNRESOLVED, d.isoformat()) for d in ambiguous)
        st.reasons.extend("%s %s%s" % (g.kind, g.date.isoformat(), "" if g.verified else " (unverified: no calendar)")
                          for g in relevant)
        if unresolved or ambiguous:
            st.status = UNVERIFIED_SESSION
        elif relevant:
            st.status = UNKNOWN_DATA_GAP
        elif st.manual_review:
            st.status = MANUAL_REVIEW
        else:
            st.status = FRESH
    return st
