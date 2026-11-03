#!/usr/bin/env python3
"""Independent reference values (TradingView exports or hand records) and their comparison
with replayed bars. Standard library only.

Reference files are CSV with an exact header (OHLC_REFERENCE_COLUMNS or
ZONE_REFERENCE_COLUMNS); templates are in nse/data/reference/. Every row records where it
came from and the chart's time zone and adjustment settings, because a comparison of
unadjusted bhavcopy prices with adjusted chart prices means nothing.

compare_ohlc() compares reference OHLC rows with a replay (nse_replay.ReplayResult):
  - D rows against the exact bhavcopy Decimals.
  - W, M, Q, HY and Y rows against the orchestrator's HTF candles (replay with those
    timeframes in htf), but only when the replay used a validated calendar (B17). Otherwise they are BLOCKED: the period boundaries and
    completeness would rest on an unvalidated calendar.
  - Each result is MATCH, MISMATCH, BLOCKED or NO_ACTUAL, and every non-match is
    classified: DATA_MISMATCH, CANDLE_CONSTRUCTION_MISMATCH, METHODOLOGY_AMBIGUITY or
    INSUFFICIENT_EVIDENCE. ENGINE_DEFECT is reserved for zone comparisons.
Zone references can be read and validated, but there is no zone comparison yet: its
matching rules are to be set against the first real references, not guessed.

Sources: TRADINGVIEW_EXPORT and YAHOO_FINANCE_SCREENSHOT rows must name their evidence file
(the export, or the screenshot image) and its SHA-256; TRADINGVIEW_MANUAL rows are read off
a chart and have none. Every Comparison keeps its row's source. A Yahoo Finance screenshot is
its own source, never TradingView data, and it is a redistribution of exchange data, not
evidence independent of NSE: a MATCH shows the replayed bars reproduce published NSE prices
and that the transcription is right, nothing more. Zone references must come from
TradingView (ZONE_SOURCES).

Coverage: compare_ohlc also returns a NO_REFERENCE row for every replayed daily bar with no
reference row (and, with a validated calendar, every W or M candle of a timeframe that has
references), so a missing date can never make partial coverage look complete.
coverage_summary() reports complete only when every row is a MATCH.
"""

import csv
import datetime
import importlib.util
import os
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

OHLC_REFERENCE_COLUMNS = (
    "symbol", "exchange", "timeframe", "bar_date", "open", "high", "low", "close",
    "source", "export_file", "export_sha256", "chart_timezone", "adjust_dividends",
    "adjust_splits", "recorded_on", "notes")
ZONE_REFERENCE_COLUMNS = (
    "symbol", "exchange", "timeframe", "indicator_settings", "side", "pattern",
    "base_start_date", "created_date", "proximal", "distal", "score_label", "tested",
    "first_test_date", "invalidated_date", "source", "chart_timezone", "adjust_dividends",
    "adjust_splits", "recorded_on", "notes")
TIMEFRAMES = ("D", "W", "M", "Q", "HY", "Y")    # OHLC references (D23 boundaries need Q/HY/Y checks, B8)
ZONE_TIMEFRAMES = ("D", "W", "M")               # Pine draws no Q/HY/Y zones (D11, NO_PINE_REFERENCE)
SETTINGS = ("ON", "OFF", "UNKNOWN")
SOURCES = ("TRADINGVIEW_EXPORT", "TRADINGVIEW_MANUAL", "YAHOO_FINANCE_SCREENSHOT")
ZONE_SOURCES = ("TRADINGVIEW_EXPORT", "TRADINGVIEW_MANUAL")      # zones are drawn by the indicator
NO_EVIDENCE_FILE_SOURCES = ("TRADINGVIEW_MANUAL",)

MATCH, MISMATCH, BLOCKED, NO_ACTUAL = "MATCH", "MISMATCH", "BLOCKED", "NO_ACTUAL"
NO_REFERENCE = "NO_REFERENCE"                    # a replayed bar with no reference row
DATA_MISMATCH = "DATA_MISMATCH"
CANDLE_CONSTRUCTION_MISMATCH = "CANDLE_CONSTRUCTION_MISMATCH"
ENGINE_DEFECT = "ENGINE_DEFECT"                  # zone comparisons only (not implemented yet)
METHODOLOGY_AMBIGUITY = "METHODOLOGY_AMBIGUITY"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

_MTF_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "mtf-freshness", "mtf_freshness.py")
_spec = importlib.util.spec_from_file_location("nse_mtf_freshness_periods", _MTF_PATH)
mtf = importlib.util.module_from_spec(_spec)       # for period_key / period_bounds only
_spec.loader.exec_module(mtf)

_DECIMAL = re.compile(r"\d+(\.\d+)?\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class ReferenceFormatError(ValueError):
    """A reference file or row is not in the agreed format; it is not used."""


@dataclass(frozen=True)
class OhlcReference:
    symbol: str
    timeframe: str
    bar_date: datetime.date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    source: str
    export_file: str
    export_sha256: str
    chart_timezone: str
    adjust_dividends: str
    adjust_splits: str
    recorded_on: datetime.date
    line: int


@dataclass
class Comparison:
    timeframe: str
    bar_date: datetime.date
    period: str
    status: str
    classification: Optional[str]
    expected: Optional[Dict[str, Decimal]]
    actual: Optional[Dict[str, Decimal]]
    max_abs_diff: Optional[Decimal]
    tolerance: Decimal
    note: str
    source: Optional[str] = None                 # the reference row's source; None for NO_REFERENCE


def _date(text, where):
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ReferenceFormatError("%s: %r is not YYYY-MM-DD" % (where, text))


def _rows(path, columns):
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != columns:
            raise ReferenceFormatError("%s: header must be exactly %s" % (path, ",".join(columns)))
        return [(n, dict(r)) for n, r in enumerate(reader, start=2)]


def _common(r, where, sources=SOURCES, timeframes=TIMEFRAMES):
    if not r["symbol"] or r["exchange"] != "NSE":
        raise ReferenceFormatError("%s: symbol required and exchange must be NSE" % where)
    if r["timeframe"] not in timeframes:
        raise ReferenceFormatError("%s: timeframe must be one of %s" % (where, ", ".join(timeframes)))
    if r["source"] not in sources:
        raise ReferenceFormatError("%s: source must be one of %s" % (where, ", ".join(sources)))
    if not r["chart_timezone"]:
        raise ReferenceFormatError("%s: chart_timezone is required" % where)
    for k in ("adjust_dividends", "adjust_splits"):
        if r[k] not in SETTINGS:
            raise ReferenceFormatError("%s: %s must be one of %s" % (where, k, ", ".join(SETTINGS)))
    return _date(r["recorded_on"], where + " recorded_on")


def read_ohlc_reference(path):
    out = []
    for n, r in _rows(path, OHLC_REFERENCE_COLUMNS):
        where = "%s line %d" % (path, n)
        recorded = _common(r, where)
        prices = {}
        for k in ("open", "high", "low", "close"):
            if not _DECIMAL.match(r[k]):
                raise ReferenceFormatError("%s: %s %r is not a plain decimal" % (where, k, r[k]))
            prices[k] = Decimal(r[k])
        if r["source"] not in NO_EVIDENCE_FILE_SOURCES and not (r["export_file"] and _SHA.match(r["export_sha256"])):
            raise ReferenceFormatError("%s: a %s row needs its evidence file in export_file and that "
                                       "file's SHA-256 in export_sha256" % (where, r["source"]))
        out.append(OhlcReference(r["symbol"], r["timeframe"], _date(r["bar_date"], where), prices["open"],
                                 prices["high"], prices["low"], prices["close"], r["source"], r["export_file"],
                                 r["export_sha256"], r["chart_timezone"], r["adjust_dividends"],
                                 r["adjust_splits"], recorded, n))
    return out


def read_zone_reference(path):
    """Validated zone-reference rows (dicts). No comparison is defined for them yet."""
    out = []
    for n, r in _rows(path, ZONE_REFERENCE_COLUMNS):
        where = "%s line %d" % (path, n)
        _common(r, where, ZONE_SOURCES, ZONE_TIMEFRAMES)
        if r["side"] not in ("demand", "supply"):
            raise ReferenceFormatError("%s: side must be demand or supply" % where)
        for k in ("proximal", "distal"):
            if not _DECIMAL.match(r[k]):
                raise ReferenceFormatError("%s: %s %r is not a plain decimal" % (where, k, r[k]))
        _date(r["created_date"], where + " created_date")
        if r["tested"] not in ("YES", "NO"):
            raise ReferenceFormatError("%s: tested must be YES or NO" % where)
        out.append(dict(r, line=n))
    return out


def _diff(expected, actual):
    return max(abs(expected[k] - actual[k]) for k in expected)


def compare_ohlc(references, replay, tolerance=Decimal("0")):
    """Compare reference OHLC rows with an nse_replay.ReplayResult. Nothing is skipped
    silently: every reference row yields one Comparison."""
    for ref in references:
        if ref.symbol != replay.symbol:
            raise ReferenceFormatError("line %d: reference for %s, replay for %s" % (ref.line, ref.symbol, replay.symbol))
    daily = {b.trade_date: b for b in replay.daily.bars}
    snap = replay.snapshot
    results, d_status = [], {}
    for ref in sorted((r for r in references if r.timeframe == "D"), key=lambda r: r.bar_date):
        d_status[ref.bar_date] = _compare_one(ref, ref.bar_date.isoformat(), daily.get(ref.bar_date), tolerance, results)
    for ref in sorted((r for r in references if r.timeframe != "D"), key=lambda r: (r.timeframe, r.bar_date)):
        period = mtf.period_key(ref.timeframe, ref.bar_date)
        if not snap.calendar_validated:
            results.append(Comparison(ref.timeframe, ref.bar_date, period, BLOCKED, INSUFFICIENT_EVIDENCE,
                                      _ohlc(ref), None, None, tolerance,
                                      "replay has no validated calendar (B17); HTF periods are not trusted",
                                      ref.source))
            continue
        series = snap.series.get(ref.timeframe)
        candle = next((h for h in (series.candles if series else []) if h.period_key == period), None)
        status = _compare_one(ref, period, candle, tolerance, results)
        if status == MISMATCH and results[-1].classification == DATA_MISMATCH:
            first, last = mtf.period_bounds(ref.timeframe, ref.bar_date)
            inside = [d for d in daily if first <= d <= last]
            all_daily_match = bool(inside) and all(d_status.get(d) == MATCH for d in inside)
            results[-1].classification = CANDLE_CONSTRUCTION_MISMATCH if all_daily_match else INSUFFICIENT_EVIDENCE
            results[-1].note = ("every daily bar in the period matches its reference" if all_daily_match
                                else "daily references for this period are missing or differ")
    # coverage: every replayed bar without a reference row is reported, never skipped
    referenced = {(r.timeframe, r.bar_date if r.timeframe == "D" else mtf.period_key(r.timeframe, r.bar_date))
                  for r in references}
    for d in sorted(daily):
        if ("D", d) not in referenced:
            results.append(Comparison("D", d, d.isoformat(), NO_REFERENCE, INSUFFICIENT_EVIDENCE, None,
                                      _ohlc(daily[d]), None, tolerance, "replayed bar has no reference row"))
    if snap.calendar_validated:
        for tf in sorted({r.timeframe for r in references} - {"D"}):
            for h in (snap.series[tf].candles if tf in snap.series else []):
                if (tf, h.period_key) not in referenced:
                    results.append(Comparison(tf, h.start.date(), h.period_key, NO_REFERENCE, INSUFFICIENT_EVIDENCE,
                                              None, _ohlc(h), None, tolerance, "replayed candle has no reference row"))
    return results


def coverage_summary(results):
    """Counts per status; complete only if there is at least one row and every row is a MATCH."""
    counts = {k: 0 for k in (MATCH, MISMATCH, BLOCKED, NO_ACTUAL, NO_REFERENCE)}
    for c in results:
        counts[c.status] += 1
    return {"complete": bool(results) and counts[MATCH] == len(results), "counts": counts,
            "no_reference": [(c.timeframe, c.bar_date) for c in results if c.status == NO_REFERENCE]}


def _ohlc(x):
    return {k: Decimal(str(getattr(x, k))) for k in ("open", "high", "low", "close")}


def _compare_one(ref, period, actual, tolerance, results):
    n = len(results)
    status = _compare_rows(ref, period, actual, tolerance, results)
    for c in results[n:]:
        c.source = ref.source
    return status


def _compare_rows(ref, period, actual, tolerance, results):
    expected = _ohlc(ref)
    if actual is None:
        results.append(Comparison(ref.timeframe, ref.bar_date, period, NO_ACTUAL, INSUFFICIENT_EVIDENCE,
                                  expected, None, None, tolerance, "no replayed bar for this period"))
        return NO_ACTUAL
    got = _ohlc(actual)
    diff = _diff(expected, got)
    if diff <= tolerance:
        results.append(Comparison(ref.timeframe, ref.bar_date, period, MATCH, None, expected, got, diff,
                                  tolerance, ""))
        return MATCH
    adjusted = not (ref.adjust_dividends == "OFF" and ref.adjust_splits == "OFF")
    results.append(Comparison(ref.timeframe, ref.bar_date, period, MISMATCH,
                              METHODOLOGY_AMBIGUITY if adjusted else DATA_MISMATCH, expected, got, diff, tolerance,
                              "chart adjustment is not OFF/OFF; bhavcopy prices are unadjusted" if adjusted else ""))
    return MISMATCH
