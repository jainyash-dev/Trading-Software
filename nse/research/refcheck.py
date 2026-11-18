"""Zone comparison against recorded indicator references (B10). Reads rows validated by
nse/eod/nse_reference.read_zone_reference; never edits the implementation to agree.

Matching key (PROPOSED reading P-REF-1, DECISION_LOG D41): timeframe, side, and the
calendar period of created_date (the candle the zone appears on; for W and M TradingView
labels a bar by its first date, so the period, not the date, is compared). Fields compared:
  pattern, proximal, distal (against the zone's DL and its normal DL; the reference may draw
  either), tested, first_test_date, invalidated_date.
Prices compare as Decimals rounded to the reference's own precision, with tolerance 0 by
default; any tolerance must be passed explicitly and is reported.

Results per reference row: MATCH, MISMATCH (fields listed) or NO_ACTUAL; per engine zone in
the referenced window with no reference row: NO_REFERENCE. Classification never says
ENGINE_DEFECT on its own:
  - METHODOLOGY_AMBIGUITY where D12 makes the implementation differ on purpose: tested /
    first_test_date on W or M (the overlay tests on every daily candle, Pine at the HTF
    close, PR8), or a reference zone the engine's Pine profile also draws (PR1);
  - INSUFFICIENT_EVIDENCE otherwise: a person investigates before anything changes.
Coverage is complete only when every row matches and nothing is NO_REFERENCE.
"""

import datetime
from decimal import Decimal

from nse.research.deps import mtf

MATCH, MISMATCH, NO_ACTUAL, NO_REFERENCE = "MATCH", "MISMATCH", "NO_ACTUAL", "NO_REFERENCE"
METHODOLOGY_AMBIGUITY = "METHODOLOGY_AMBIGUITY"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


def _dec(value, like):
    places = len(like.split(".")[1]) if "." in like else 0
    return Decimal(str(value)).quantize(Decimal(1).scaleb(-places))


def _d(text):
    return datetime.date.fromisoformat(text) if text else None


def compare_zones(refs, snapshot, tolerance=Decimal("0")):
    results = []
    by_key = {}
    windows = {}
    for tf, s in snapshot.series.items():
        if s.engine is None:
            continue
        for a in s.engine.assessments:
            z = a.zone
            key = (tf, z.side, s.candles[z.created_index].period_key)
            by_key.setdefault(key, []).append((a, s))
    seen = set()
    for r in refs:
        tf = r["timeframe"]
        created = _d(r["created_date"])
        key = (tf, r["side"], mtf.period_key(tf, created))
        w = windows.setdefault(tf, [created, created])
        w[0], w[1] = min(w[0], created), max(w[1], created)
        found = by_key.get(key, [])
        if not found:
            pine = [p for p in (snapshot.series[tf].engine.pine_only_zones if tf in snapshot.series
                                and snapshot.series[tf].engine else [])
                    if snapshot.series[tf].candles[p["created_index"]].period_key == key[2] and p["side"] == r["side"]]
            results.append({"line": r["line"], "key": list(key), "status": NO_ACTUAL,
                            "classification": METHODOLOGY_AMBIGUITY if pine else INSUFFICIENT_EVIDENCE,
                            "note": "drawn only by the Pine profile (D12, PR1)" if pine else "no zone with this key"})
            continue
        a, s = found[0]
        seen.add((tf, a.zone.id))
        z = a.zone
        st = snapshot.zones.get("%s:%s" % (tf, z.id))
        diffs = {}
        if r["pattern"] and r["pattern"] != z.pattern:
            diffs["pattern"] = (r["pattern"], z.pattern)
        p = _dec(z.proximal, r["proximal"])
        if abs(p - Decimal(r["proximal"])) > tolerance:
            diffs["proximal"] = (r["proximal"], str(p))
        dists = [_dec(z.distal, r["distal"]), _dec(z.normal_distal, r["distal"])]
        if min(abs(x - Decimal(r["distal"])) for x in dists) > tolerance:
            diffs["distal"] = (r["distal"], [str(x) for x in dists])
        tested = st is not None and st.first_touch_at is not None
        if (r["tested"] == "YES") != tested:
            diffs["tested"] = (r["tested"], "YES" if tested else "NO")
        ft = st.first_touch_at.date() if st is not None and st.first_touch_at else None
        if r["first_test_date"] and _d(r["first_test_date"]) != ft:
            diffs["first_test_date"] = (r["first_test_date"], ft.isoformat() if ft else None)
        inv = s.candles[z.invalidated_index].end.date() if z.invalidated_index is not None else None
        ref_inv = _d(r["invalidated_date"])
        if (ref_inv is None) != (inv is None) or (ref_inv and mtf.period_key(tf, ref_inv) != mtf.period_key(tf, inv)):
            diffs["invalidated_date"] = (r["invalidated_date"], inv.isoformat() if inv else None)
        timing_only = set(diffs) <= {"tested", "first_test_date"} and tf in ("W", "M")
        results.append({"line": r["line"], "key": list(key), "zone_id": z.id,
                        "status": MATCH if not diffs else MISMATCH,
                        "classification": None if not diffs else (METHODOLOGY_AMBIGUITY if timing_only
                                                                  else INSUFFICIENT_EVIDENCE),
                        "differences": {k: list(v) if isinstance(v, tuple) else v for k, v in diffs.items()},
                        "tolerance": str(tolerance)})
    for (tf, side, period), found in sorted(by_key.items()):
        if tf not in windows:
            continue
        first, last = windows[tf]
        for a, s in found:
            created = s.candles[a.zone.created_index].end.date()
            if first <= created <= last and (tf, a.zone.id) not in seen:
                results.append({"key": [tf, side, period], "zone_id": a.zone.id, "status": NO_REFERENCE,
                                "classification": INSUFFICIENT_EVIDENCE, "note": "engine zone with no reference row"})
    counts = {k: sum(1 for x in results if x["status"] == k) for k in (MATCH, MISMATCH, NO_ACTUAL, NO_REFERENCE)}
    return {"results": results, "counts": counts,
            "complete": bool(results) and counts[MATCH] == len(results),
            "note": "references must come from TradingView (B10); a MISMATCH is investigated, never auto-resolved"}


# --- trend (SMA 50) references -----------------------------------------------------------
# A recorded SMA 50 value read from TradingView (plot value or export column) for one bar.
TREND_COLUMNS = ("symbol", "exchange", "timeframe", "bar_date", "sma50", "source", "export_file", "export_sha256",
                 "chart_timezone", "adjust_dividends", "adjust_splits", "recorded_on", "notes")
TREND_TIMEFRAMES = ("D", "W", "M", "Q", "HY", "Y")


def read_trend_reference(path):
    import csv
    import re
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != TREND_COLUMNS:
            raise ValueError("%s: header must be exactly %s" % (path, ",".join(TREND_COLUMNS)))
        for n, r in enumerate(reader, 2):
            if r["exchange"] != "NSE" or r["timeframe"] not in TREND_TIMEFRAMES:
                raise ValueError("%s line %d: exchange NSE and a timeframe in %s required" % (path, n, TREND_TIMEFRAMES))
            if not re.match(r"\d+(\.\d+)?\Z", r["sma50"]):
                raise ValueError("%s line %d: sma50 must be a plain decimal" % (path, n))
            if r["source"] not in ("TRADINGVIEW_EXPORT", "TRADINGVIEW_MANUAL"):
                raise ValueError("%s line %d: trend references come from TradingView" % (path, n))
            out.append(dict(r, line=n, bar_date=datetime.date.fromisoformat(r["bar_date"])))
    return out


def compare_trend(refs, snapshot, period=50, tolerance=Decimal("0")):
    """SMA(period) of completed closes ending with the reference bar's period, against the
    recorded value. NO_ACTUAL when the period is not a completed candle or history is short."""
    results = []
    for r in refs:
        tf = r["timeframe"]
        key = mtf.period_key(tf, r["bar_date"])
        s = snapshot.series.get(tf)
        keys = [c.period_key for c in s.candles] if s else []
        if key not in keys or keys.index(key) + 1 < period:
            results.append({"line": r["line"], "tf": tf, "period": key, "status": NO_ACTUAL,
                            "classification": INSUFFICIENT_EVIDENCE,
                            "note": "no completed candle for this period" if key not in keys
                                    else "fewer than %d completed candles" % period})
            continue
        i = keys.index(key)
        closes = [c.close for c in s.candles[i + 1 - period:i + 1]]
        got = _dec(sum(closes) / period, r["sma50"])
        diff = abs(got - Decimal(r["sma50"]))
        adjusted = not (r["adjust_dividends"] == "OFF" and r["adjust_splits"] == "OFF")
        status = MATCH if diff <= tolerance else MISMATCH
        results.append({"line": r["line"], "tf": tf, "period": key, "status": status, "expected": r["sma50"],
                        "actual": str(got), "difference": str(diff), "tolerance": str(tolerance),
                        "classification": None if status == MATCH else (METHODOLOGY_AMBIGUITY if adjusted
                                                                        else INSUFFICIENT_EVIDENCE)})
    counts = {k: sum(1 for x in results if x["status"] == k) for k in (MATCH, MISMATCH, NO_ACTUAL)}
    return {"results": results, "counts": counts, "complete": bool(results) and counts[MATCH] == len(results)}


PENDING_EXTERNAL_EVIDENCE = "PENDING_EXTERNAL_EVIDENCE"
COMPARED_NOT_CERTIFIED = "COMPARED_NOT_CERTIFIED"


def _line_of(row):
    return row.line if hasattr(row, "line") else row["line"]


def reject_duplicate_observations(rows, key, label):
    """Two observations of the same bar or zone are a recording error, not two votes."""
    seen = {}
    for row in rows:
        k = key(row)
        line = _line_of(row)
        if k in seen:
            raise ValueError("duplicate %s %s at lines %s and %s" % (label, k, seen[k], line))
        seen[k] = line


def _plain(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def external_comparison_report(replay, ohlc_rows=(), zone_rows=(), trend_rows=(),
                               ohlc_tolerance=Decimal("0"), zone_tolerance=Decimal("0"),
                               trend_tolerance=Decimal("0")):
    """Compare already-read reference rows with one replay. Writes nothing.

    certifies_external_validation is always false. A row MATCH is a comparison
    result. It does not close T-005, and it does not copy an engine value into
    an observation. Yahoo rows are compared and are not TradingView evidence.
    """
    from nse.research.deps import reference
    reject_duplicate_observations(ohlc_rows, lambda r: (r.timeframe, r.bar_date), "OHLC observation")
    reject_duplicate_observations(zone_rows, lambda r: (r["timeframe"], r["side"], r["created_date"],
                                                        r["proximal"], r["distal"]), "zone observation")
    reject_duplicate_observations(trend_rows, lambda r: (r["timeframe"], r["bar_date"]), "SMA observation")
    supplied = bool(ohlc_rows or zone_rows or trend_rows)
    calendar_validated = bool(getattr(replay.snapshot, "calendar_validated", False))
    ohlc = reference.compare_ohlc(list(ohlc_rows), replay, ohlc_tolerance) if ohlc_rows else []
    zones = compare_zones(list(zone_rows), replay.snapshot, zone_tolerance) if zone_rows else {"results": [], "complete": False}
    trend = compare_trend(list(trend_rows), replay.snapshot, tolerance=trend_tolerance) if trend_rows else {
        "results": [], "complete": False}
    sources = sorted(set([r.source for r in ohlc_rows] + [r["source"] for r in zone_rows]
                         + [r["source"] for r in trend_rows]))
    return {
        "status": COMPARED_NOT_CERTIFIED if supplied else PENDING_EXTERNAL_EVIDENCE,
        "certifies_external_validation": False,
        "t005_closed": False,
        "calendar_validated": calendar_validated,
        "series": "EQ",
        "sources": sources,
        "yahoo_is_not_tradingview": "YAHOO_FINANCE_SCREENSHOT" in sources,
        "ohlc": _plain({"results": [c.__dict__ for c in ohlc], "summary": reference.coverage_summary(ohlc)}),
        "zones": _plain(zones),
        "trend": _plain(trend),
        "note": "No observation was created by this comparison. T-005 stays open until a person supplies "
                "TradingView evidence and reviews every difference.",
    }
