"""Daily market-data inputs for the scanner and their data-quality findings.

Two sources, both local files (D31; nothing is downloaded):
  - official NSE legacy bhavcopies, through nse/eod/nse_bhavcopy.py (strict loader,
    manifest provenance) and nse/eod/nse_replay.py (one symbol's bars);
  - a user-supplied daily CSV per symbol (date,open,high,low,close[,volume]), whose
    adjustment and provenance are unknown unless the caller states them.

A bhavcopy or CSV row has a date but no times, so candles are stamped with the regular
session 09:15-15:30 (audit L7, SESSION_TIMES_ASSUMED). Prices are as supplied; corporate
actions are never checked here (B7, CORPORATE_ACTIONS_UNVERIFIED).

Data-quality findings never repair data. A finding of severity ERROR dated at or before
as_of (or undated) stops the symbol at G0 (DATA_INSUFFICIENT); a finding about a later
trade date is not shown for an earlier scan, so it cannot change that scan. An error whose
date is unreadable is dated by its neighbouring rows when they bound it (D44, _bad_date);
otherwise it stays undated and blocks every scan. Nothing is sorted, de-duplicated or
filled to make it pass.
"""

import csv
import datetime
import hashlib
import math
import os
from dataclasses import dataclass, field
from typing import List, Optional

from nse.research import models as m
from nse.research.deps import mtf, replay_mod

ERROR, WARNING, INFO = "ERROR", "WARNING", "INFO"
CSV_COLUMNS = ("date", "open", "high", "low", "close")


@dataclass
class Finding:
    symbol: str
    severity: str
    code: str
    detail: str
    verified: bool = True        # False: an inference, e.g. a gap without a calendar
    date: Optional[datetime.date] = None   # the trade date it concerns; None: the whole input
    extra: Optional[dict] = None           # structured values behind the detail text

    def to_dict(self):
        return {"symbol": self.symbol, "severity": self.severity, "code": self.code,
                "detail": self.detail, "verified": self.verified,
                "date": self.date.isoformat() if self.date else None, "extra": self.extra}

    def known_at(self, as_of_date):
        """A finding about a later trade date says nothing about data at or before as_of."""
        return self.date is None or self.date <= as_of_date


@dataclass
class DailyInput:
    symbol: str
    candles: List[object]                      # mtf_freshness.TimedCandle, oldest first
    provenance: dict
    limitations: List[str] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)

    @property
    def errors(self):
        return [f for f in self.findings if f.severity == ERROR]

    def findings_at(self, as_of_date):
        return [f for f in self.findings if f.known_at(as_of_date)]


def _session(d):
    return (datetime.datetime.combine(d, mtf.SESSION_OPEN), datetime.datetime.combine(d, mtf.SESSION_CLOSE))


def check_rows(symbol, rows):
    """rows: (date, open, high, low, close, where). Returns findings; never modifies rows."""
    out = []
    seen = {}
    prev = None
    for d, o, h, l, c, where in rows:
        if d in seen:
            out.append(Finding(symbol, ERROR, "DUPLICATE_DATE", "%s at %s and %s" % (d, seen[d], where), date=d))
        seen.setdefault(d, where)
        if prev is not None and d < prev:
            # dated at the later row, so any scan that could have read both rows sees it
            out.append(Finding(symbol, ERROR, "OUT_OF_ORDER", "%s after %s (%s)" % (d, prev, where), date=prev))
        prev = d if prev is None or d > prev else prev
        vals = (o, h, l, c)
        if any(v is None or not math.isfinite(v) for v in vals):
            out.append(Finding(symbol, ERROR, "NON_NUMERIC_PRICE", "%s (%s)" % (d, where), date=d))
            continue
        if any(v <= 0 for v in vals):
            out.append(Finding(symbol, ERROR, "NON_POSITIVE_PRICE", "%s (%s)" % (d, where), date=d))
        if l > min(o, c) or h < max(o, c) or h < l:
            out.append(Finding(symbol, ERROR, "OHLC_INCONSISTENT", "%s O%s H%s L%s C%s (%s)" % (d, o, h, l, c, where),
                               date=d))
        if d.weekday() >= 5:
            out.append(Finding(symbol, WARNING, "WEEKEND_ROW",
                               "%s is a %s; the calendar decides whether it is a special session" % (d, d.strftime("%A")),
                               date=d))
    return out


def _float(text):
    try:
        v = float(text)
    except (TypeError, ValueError):
        return None
    return v


def _bad_date(symbol, line, text, rows, pos, file_ordered):
    """A row whose date cannot be read (D44). When the file shows no OUT_OF_ORDER or
    DUPLICATE_DATE anywhere and the valid rows on both sides of it are in date order, the
    row's true date is at or after the previous row's date (inclusive: it may be a duplicate
    of it), so the ERROR is dated there and blocks only scans on or after it; an earlier
    period is not contaminated. Otherwise (no previous row, or the file contradicts its own
    order) its impact cannot be bounded and it blocks every scan (date None)."""
    prev = rows[pos - 1][0] if pos > 0 else None
    nxt = rows[pos][0] if pos < len(rows) else None
    bounded = file_ordered and prev is not None and (nxt is None or prev < nxt)
    extra = {"rule": "D44", "previous_valid_date": prev.isoformat() if prev else None,
             "next_valid_date": nxt.isoformat() if nxt else None,
             "bound": "EARLIEST_POSSIBLE_DATE" if bounded else "UNBOUNDED"}
    return Finding(symbol, ERROR, "BAD_DATE", "line %d: %r" % (line, text), verified=not bounded,
                   date=prev if bounded else None, extra=extra)


def from_csv(path, symbol=None, source_label="USER_CSV", price_adjustment="UNKNOWN"):
    """One symbol's daily rows from a CSV with header date,open,high,low,close[,volume]."""
    symbol = symbol or os.path.splitext(os.path.basename(path))[0].upper()
    with open(path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    findings = []
    if reader.fieldnames is None or any(c not in reader.fieldnames for c in CSV_COLUMNS):
        findings.append(Finding(symbol, ERROR, "BAD_HEADER", "%s needs columns %s" % (path, ", ".join(CSV_COLUMNS))))
        return DailyInput(symbol, [], {"source": source_label, "file": path}, [], findings)
    rows, bad = [], []
    for i, r in enumerate(reader, 2):
        try:
            d = datetime.date.fromisoformat((r["date"] or "").strip())
        except ValueError:
            bad.append((i, r["date"], len(rows)))      # rows[pos - 1] and rows[pos] are its neighbours
            continue
        rows.append((d, _float(r["open"]), _float(r["high"]), _float(r["low"]), _float(r["close"]), "line %d" % i))
    row_findings = check_rows(symbol, rows)
    # a file shown to be out of order or duplicated anywhere cannot bound a lost row (QA 2026-11-08)
    ordered = not any(f.code in ("OUT_OF_ORDER", "DUPLICATE_DATE") for f in row_findings)
    findings += [_bad_date(symbol, i, text, rows, pos, ordered) for i, text, pos in bad]
    if any(f.date is not None for f in findings if f.code == "BAD_DATE"):
        findings.append(Finding(symbol, WARNING, "ERROR_DATE_BOUND_INFERRED",
                                "a BAD_DATE row was dated from its neighbouring rows (D44): scans before that date "
                                "are not blocked by it, on the assumption that the file is in date order",
                                False))
    findings += row_findings
    # every row with finite prices becomes a candle; the scanner refuses the symbol when an
    # ERROR finding is dated at or before as_of, and the replay never reads past as_of
    candles = []
    for d, o, h, l, c, _ in rows:
        if all(v is not None and math.isfinite(v) for v in (o, h, l, c)):
            s, e = _session(d)
            candles.append(mtf.TimedCandle(s, e, o, h, l, c))
    # R-12: the same price-scale screen as the bhavcopy path. A user file has no PREVCLOSE
    # and no corporate-action record of its own, so a whole-range gap beyond the band is a
    # finding whatever the file says about adjustment; the scanner then holds G0.
    from nse.research import corporate_actions
    last = None
    for d, o, h, l, c, _ in rows:
        if not all(v is not None and math.isfinite(v) for v in (o, h, l, c)):
            continue
        if last is not None and corporate_actions.price_scale_gap(last[1], l, h):
            findings.append(Finding(symbol, WARNING, corporate_actions.PRICE_SCALE_GAP,
                                    "%s: session range %s..%s is more than %s%% from the previous row's close %s "
                                    "(%s); a price-scale break is possible and is not adjusted (R-12, B7)"
                                    % (d, l, h, int(corporate_actions.SCALE_GAP_BAND * 100), last[1], last[0]),
                                    date=d, extra={"ratio": round(c / last[1], 6) if last[1] else None,
                                                   "file": os.path.basename(path),
                                                   "last_date": last[0].isoformat()}))
        last = (d, c)
    limitations = [m.SESSION_TIMES_ASSUMED, m.CORPORATE_ACTIONS_UNVERIFIED]
    if price_adjustment == "UNKNOWN":
        limitations.append(m.PRICE_ADJUSTMENT_UNKNOWN)
        findings.append(Finding(symbol, WARNING, "PRICE_ADJUSTMENT_UNKNOWN",
                                "adjustment of %s is not stated; split/bonus distortion possible (B7)" % path, False))
    prov = {"source": source_label, "file": os.path.basename(path), "sha256": hashlib.sha256(raw).hexdigest(),
            "rows": len(rows), "price_adjustment": price_adjustment}
    return DailyInput(symbol, candles, prov, limitations, findings)


def _formats(files):
    """The source format label: one format, or both joined with + (ED-20 switch inside the window)."""
    return "+".join(sorted(set(getattr(f, "format", "NSE_CM_BHAVCOPY_LEGACY") for f in files))) or "NSE_CM_BHAVCOPY_LEGACY"


def from_bhavcopy(files, symbol, series="EQ"):
    """One symbol's bars from loaded bhavcopy files, legacy or UDiFF (nse_bhavcopy.load_many)."""
    findings = []
    try:
        daily = replay_mod.daily_series(files, symbol, series)
    except replay_mod.ReplayInputError as e:
        findings.append(Finding(symbol, ERROR, "BHAVCOPY_INPUT", str(e)))
        return DailyInput(symbol, [], {"source": _formats(files)}, [], findings)
    rows = [(b.trade_date, float(b.open), float(b.high), float(b.low), float(b.close),
             "%s line %d" % (b.source_file, b.line)) for b in daily.bars]
    findings += check_rows(symbol, rows)
    for d in daily.missing_dates:
        other = d in daily.other_series_dates
        findings.append(Finding(symbol, WARNING, "NO_ROW_IN_FILE",
                                "%s: the bhavcopy has no %s %s row%s" % (d, symbol, series,
                                                                         " (traded in another series)" if other else ""),
                                date=d))
    if not daily.bars:
        findings.append(Finding(symbol, ERROR, "NO_BARS", "%s %s: no rows in %d files" % (symbol, series, len(files))))
    from nse.research import corporate_actions
    for x in corporate_actions.prevclose_discontinuities(files, symbol, series):
        gap = x["weekdays_between"]
        why = ("possible unadjusted corporate action (B7); NSE does not adjust PREVCLOSE on an ex-date, so an "
               "intact chain elsewhere does not rule one out (R-12)" if not gap else
               "%d weekday(s) between these held files: missing sessions or holidays may explain it; a corporate "
               "action is not established (B7)" % gap)
        findings.append(Finding(symbol, WARNING, "PREVCLOSE_DISCONTINUITY",
                                "%s: PREVCLOSE %s vs last close %s (%s, ratio %s); %s"
                                % (x["date"], x["prev_close"], x["last_close"], x["last_file"], x["ratio"], why),
                                date=x["date"], extra={"ratio": x["ratio"], "file": x["file"], "weekdays_between": gap,
                                                       "last_date": x["last_date"].isoformat()}))
    # R-12: NSE's PREVCLOSE is unadjusted on an ex-date, so a split never shows above; screen
    # the prices themselves. The scanner holds G0 unless a recorded action explains the step.
    for x in corporate_actions.price_scale_gaps(files, symbol, series):
        findings.append(Finding(symbol, WARNING, corporate_actions.PRICE_SCALE_GAP,
                                "%s: session range %s..%s is more than %s%% from the last close %s (%s, ratio %s); "
                                "a price-scale break is possible and is not adjusted (R-12, B7)"
                                % (x["date"], x["low"], x["high"], int(corporate_actions.SCALE_GAP_BAND * 100),
                                   x["last_close"], x["last_file"], x["ratio"]),
                                date=x["date"], extra={"ratio": x["ratio"], "file": x["file"],
                                                       "last_date": x["last_date"].isoformat()}))
    candles = replay_mod.timed_candles(daily, assume_regular_session=True) if daily.bars else []
    findings.append(Finding(symbol, WARNING, "CORPORATE_ACTIONS_UNVERIFIED",
                            "bhavcopy prices are unadjusted (price_adjustment NONE); corporate actions not checked (B7)"))
    prov = {"source": _formats(files), "series": series, "files": len(daily.sources),
            "provenance_status": sorted(set(s["provenance_status"] for s in daily.sources)),
            "first_file": daily.sources[0]["file_name"] if daily.sources else None,
            "last_file": daily.sources[-1]["file_name"] if daily.sources else None,
            "price_adjustment": daily.price_adjustment}
    return DailyInput(symbol, candles, prov, [m.SESSION_TIMES_ASSUMED, m.CORPORATE_ACTIONS_UNVERIFIED], findings)


def snapshot_findings(symbol, snapshot):
    """Findings the replay itself discovered: gaps, excluded sessions, unresolved dates."""
    out = []
    for g in snapshot.data_gaps:
        out.append(Finding(symbol, WARNING, g.kind, "%s%s" % (g.date.isoformat(),
                                                             "" if g.verified else " (no calendar: unverified)"),
                           g.verified))
    for x in snapshot.excluded_candles:
        out.append(Finding(symbol, INFO, "EXCLUDED_SESSION", "%s %s" % (x.date.isoformat(), x.classification)))
    for d in snapshot.unresolved_calendar_dates:
        out.append(Finding(symbol, WARNING, "CALENDAR_UNRESOLVED", d.isoformat()))
    for tf, s in sorted(snapshot.series.items()):
        if s.truncated_at:
            out.append(Finding(symbol, WARNING, "SERIES_TRUNCATED", "%s at %s: %s" % (tf, s.truncated_at, ", ".join(s.reasons))))
    return out
