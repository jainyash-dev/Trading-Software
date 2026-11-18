#!/usr/bin/env python3
"""Replay adapter: legacy bhavcopy files -> one symbol's daily bars -> the HTF freshness
orchestrator (nse/mtf-freshness). Standard library only.

It joins two existing pieces and adds no trading rule:
  - nse/eod/nse_bhavcopy.py loads and validates the files (B18 format evidence);
  - nse/mtf-freshness/mtf_freshness.replay runs the Zone Engine and the freshness overlay.

Rules:
  - Bars come only from loaded files. A trade date is a bar only if a file for that date
    exists and holds the symbol's row in the requested series. A file without the row
    is listed in missing_dates; dates with no file are never filled. Gap detection stays
    with the orchestrator and its calendar (D27, D28, D34).
  - Prices stay exact Decimals in DailyBar. The orchestrator takes floats, so the
    conversion happens only when candles are built for it (engine_numeric records this).
  - Prices are as published (price_adjustment NONE). Corporate actions are not checked
    (B7), so every result carries CORPORATE_ACTIONS_UNVERIFIED.
  - A bhavcopy row has a date but no times. Building candles stamps the regular session
    09:15-15:30 (mtf_freshness.SESSION_OPEN/CLOSE), which is an assumption (audit L7).
    It is refused unless the caller passes assume_regular_session=True, and the result
    then carries SESSION_TIMES_ASSUMED.
  - Without a validated calendar the result carries CALENDAR_UNVALIDATED (D28) and
    comparisons of HTF candles or zones are blocked (nse_reference).
  - The output is the orchestrator's snapshot, unchanged. Nothing here decides
    eligibility or produces candidates.
"""

import datetime
import importlib.util
import os
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

_HERE = os.path.dirname(os.path.abspath(__file__))
_MTF_PATH = os.path.join(os.path.dirname(_HERE), "mtf-freshness", "mtf_freshness.py")
_spec = importlib.util.spec_from_file_location("nse_mtf_freshness", _MTF_PATH)
mtf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mtf)

ADAPTER_VERSION = "1.0.0"
CORPORATE_ACTIONS_UNVERIFIED = "CORPORATE_ACTIONS_UNVERIFIED"   # B7
SESSION_TIMES_ASSUMED = "SESSION_TIMES_ASSUMED"                 # audit L7
CALENDAR_UNVALIDATED = mtf.CALENDAR_UNVALIDATED                 # D28
INSUFFICIENT_DAILY_BARS = "INSUFFICIENT_DAILY_BARS"


class ReplayInputError(ValueError):
    """The request cannot be replayed as given; nothing is assumed to make it work."""


@dataclass(frozen=True)
class DailyBar:
    trade_date: datetime.date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    traded_qty: int
    source_file: str
    source_sha256: str
    line: int


@dataclass
class DailySeries:
    symbol: str
    series: str
    bars: List[DailyBar]                       # oldest first, one per loaded file at most
    missing_dates: List[datetime.date]         # a file exists, but no row in this series
    other_series_dates: List[datetime.date]    # ...and the symbol traded in another series
    sources: List[dict]                        # one per file: name, sha256, provenance
    price_adjustment: str = "NONE"
    warnings: List[str] = field(default_factory=lambda: [CORPORATE_ACTIONS_UNVERIFIED])


@dataclass
class ReplayResult:
    symbol: str
    series: str
    daily: DailySeries
    snapshot: object                           # mtf_freshness.MtfSnapshot
    warnings: List[str]
    adapter_version: str = ADAPTER_VERSION
    engine_numeric: str = "float (mtf_freshness.TimedCandle)"


def daily_series(files, symbol, series="EQ"):
    """One symbol's bars from loaded BhavcopyFile objects (e.g. nse_bhavcopy.load_many)."""
    if not files:
        raise ReplayInputError("no bhavcopy files given")
    dates = [f.trade_date for f in files]
    if dates != sorted(dates) or len(set(dates)) != len(dates):
        raise ReplayInputError("files must be in date order with one file per trade date (use load_many)")
    bars, missing, other, sources = [], [], [], []
    for f in files:
        rows = [r for r in f.rows if r.symbol == symbol]
        sources.append({"file_name": f.source.file_name, "sha256": f.source.sha256,
                        "trade_date": f.trade_date.isoformat(), "price_adjustment": f.price_adjustment,
                        "provenance_status": (f.provenance or {}).get("provenance_status", "NO_MANIFEST")})
        if f.price_adjustment != "NONE":
            raise ReplayInputError("%s: price_adjustment %r; only unadjusted files are supported"
                                   % (f.source.file_name, f.price_adjustment))
        hit = [r for r in rows if r.series == series]
        if not hit:
            missing.append(f.trade_date)
            if rows:
                other.append(f.trade_date)
            continue
        r = hit[0]                              # the loader refuses duplicate symbol/series
        bars.append(DailyBar(r.trade_date, r.open, r.high, r.low, r.close, r.traded_qty,
                             f.source.file_name, f.source.sha256, r.line))
    return DailySeries(symbol, series, bars, missing, other, sources)


def timed_candles(daily, assume_regular_session=False):
    """Orchestrator candles for daily bars. Refused unless the regular-session assumption
    (09:15-15:30, audit L7) is accepted explicitly."""
    if not assume_regular_session:
        raise ReplayInputError("bhavcopy rows carry no session times; pass assume_regular_session=True "
                               "to stamp 09:15-15:30 (audit L7), which is recorded as SESSION_TIMES_ASSUMED")
    out = []
    for b in daily.bars:
        start = datetime.datetime.combine(b.trade_date, mtf.SESSION_OPEN)
        end = datetime.datetime.combine(b.trade_date, mtf.SESSION_CLOSE)
        out.append(mtf.TimedCandle(start, end, float(b.open), float(b.high), float(b.low), float(b.close)))
    return out


def replay_symbol(files, symbol, htf=("D", "W", "M"), as_of=None, calendar=None, series="EQ",
                  assume_regular_session=False, rules=None):
    """Daily bars of one symbol replayed through mtf_freshness.replay on a daily base."""
    daily = daily_series(files, symbol, series)
    if not daily.bars:
        raise ReplayInputError("%s %s: no rows in any of the %d files" % (symbol, series, len(files)))
    candles = timed_candles(daily, assume_regular_session)
    snapshot = mtf.replay(candles, "D", htf=htf, as_of=as_of, calendar=calendar, rules=rules)
    warnings = list(daily.warnings) + [SESSION_TIMES_ASSUMED]
    if calendar is None:
        warnings.append(CALENDAR_UNVALIDATED)
    if len(daily.bars) < mtf.ze.MIN_CANDLES:
        warnings.append(INSUFFICIENT_DAILY_BARS)
    return ReplayResult(symbol, series, daily, snapshot, warnings)
