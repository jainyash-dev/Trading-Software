"""Decision replay: what was known about ONE symbol at as_of, as one JSON bundle.

bundle(daily_input, scan_config) runs scanner.scan_symbol, the one qualification pathway
(spec 8; audit M4), and replays the same snapshot the scanner reads (mtf_freshness.replay
with the scanner's own arguments) only to show it: the completed candles of each
timeframe and every zone with the overlay's status. Nothing here decides anything:
  - candles are the snapshot's completed candles (end at or before as_of; the period in
    progress is never shown), so a bundle at T is identical whether or not later candles
    exist in the input (prefix invariance; spec 13);
  - a zone's freshness is structure.freshness_of(the overlay state) (D3): TESTED,
    INVALIDATED and UNKNOWN zones keep that label and are never styled as fresh;
  - overlay_kept marks the zones eligible_after_overlay / manual_review_after_overlay
    kept; candidates are only those in symbol_result (the scanner's).
WIT trade types and inputs with an ERROR finding get no replay, exactly as in the
scanner, so the bundle carries no candles for them (M4b; G0).
"""

import json
import os
import sys

from nse.research import marketdata, models as m, reports, scanner, structure
from nse.research.deps import calendar as cal_mod, mtf

BUNDLE_VERSION = "1.0.0"

# display classes (dashboard legend); a TESTED, INVALIDATED or UNKNOWN zone never gets a
# class that contains "fresh"
CLASS_FRESH_DEMAND = "z-fresh-demand"
CLASS_FRESH_SUPPLY = "z-fresh-supply-context"
CLASS_TESTED = "z-tested"
CLASS_INVALIDATED = "z-invalidated"
CLASS_UNKNOWN = "z-unknown"

CHART_NOTE = ("Chart data: completed candles of the replayed snapshot at or before as_of only; "
              "no in-progress period, no later candle. Display only: the decision is symbol_result.")


def display_class(side, freshness):
    if freshness == m.Z_FRESH:
        return CLASS_FRESH_DEMAND if side == "demand" else CLASS_FRESH_SUPPLY
    if freshness == m.Z_TESTED:
        return CLASS_TESTED
    if freshness == m.Z_INVALIDATED:
        return CLASS_INVALIDATED
    return CLASS_UNKNOWN


def _iso(v):
    return None if v is None else v.isoformat()


def _snapshot(inp, config):
    """The replay scan_symbol performs, with the same arguments, or (None, reason) when
    scan_symbol performs none (WIT, an ERROR finding) or it fails."""
    if config.trade_type != m.MIT:
        return None, "NO_REPLAY: trade type %s is BLOCKED (M4b)" % config.trade_type
    known = inp.findings_at(config.as_of.date())
    if any(f.severity == marketdata.ERROR for f in known):
        return None, "NO_REPLAY: an ERROR finding stops the symbol at G0"
    try:
        return mtf.replay(inp.candles, "D", htf=scanner.HTF, as_of=config.as_of, calendar=config.calendar), None
    except cal_mod.CalendarCoverageError as e:
        return None, "NO_REPLAY: CALENDAR_COVERAGE: %s" % e
    except ValueError as e:
        return None, "NO_REPLAY: REPLAY_INPUT: %s" % e


def _candles(series):
    return [{"period": h.period_key, "start": h.start.isoformat(), "end": h.end.isoformat(),
             "known_at": h.known_at.isoformat(), "open": h.open, "high": h.high, "low": h.low,
             "close": h.close} for h in series.candles]


def _zones(snap, tf):
    s = snap.series[tf]
    views = structure.zone_views(snap, tf)
    if views is None:
        return []
    kept = set(a.zone.id for a in snap.eligible_after_overlay(tf)[0])
    kept_manual = set(a.zone.id for a in snap.manual_review_after_overlay(tf)[0])
    out = []
    for a, v in zip(s.engine.assessments, views):          # zone_views walks the same list in order
        st = snap.zones.get("%s:%s" % (tf, v.zone_id))
        out.append({
            "tf": tf, "zone_id": v.zone_id, "side": v.side, "pattern": v.pattern,
            "proximal": v.proximal, "distal": v.distal, "normal_distal": v.normal_distal,
            "start_time": _iso(a.zone.start_time), "created_time": v.created_time,
            "freshness": v.freshness, "overlay_status": v.overlay_status,
            "overlay_reasons": v.overlay_reasons, "engine_status": v.engine_status, "core": v.core,
            "dl_untouched": v.dl_untouched,
            "first_touch_at": _iso(st.first_touch_at) if st else None,
            "base_touch_count": st.base_touch_count if st else None,
            "invalidation_known_at": _iso(st.invalidation_known_at) if st else None,
            "overlay_kept": ("ELIGIBLE_AFTER_OVERLAY" if v.zone_id in kept else
                             "MANUAL_REVIEW_AFTER_OVERLAY" if v.zone_id in kept_manual else None),
            "display_class": display_class(v.side, v.freshness)})
    return sorted(out, key=lambda z: (z["created_time"], z["zone_id"]))


def bundle(daily_input, scan_config):
    """JSON-serialisable dict: symbol, as_of, trade_type, calendar, candles {tf: [...]},
    zones {tf: [...]}, series {tf: status}, data_gaps, excluded_candles, symbol_result
    (reports-style dict of the SymbolResult) and limitations. A pure function of the
    inputs: no clock is read."""
    res = scanner.scan_symbol(daily_input, scan_config)
    snap, why = _snapshot(daily_input, scan_config)
    limitations = set(res.limitations) | {m.NOT_EXTERNALLY_VALIDATED, m.TRADINGVIEW_PARITY_UNVERIFIED,
                                          m.UNIVERSE_UNVERIFIED}
    if scan_config.calendar is None:
        limitations.add(m.CALENDAR_UNVALIDATED)
    out = {"bundle_version": BUNDLE_VERSION, "symbol": daily_input.symbol, "as_of": scan_config.as_of.isoformat(),
           "trade_type": scan_config.trade_type, "calendar": scan_config.calendar_label,
           "execution_tf": m.ROLES[scan_config.trade_type]["execution"],
           "candles": {}, "zones": {}, "series": {}, "data_gaps": [], "excluded_candles": [],
           "chart_note": CHART_NOTE, "replay": "NOT_RUN" if snap is None else "RUN"}
    if snap is None:
        limitations.add(why)
    else:
        limitations.update(snap.limitations)
        for tf in scanner.HTF:
            out["series"][tf] = structure.series_status(snap, tf)
            out["candles"][tf] = _candles(snap.series[tf])
            out["zones"][tf] = _zones(snap, tf)
        out["data_gaps"] = [{"date": g.date.isoformat(), "verified": g.verified, "kind": g.kind}
                            for g in snap.data_gaps]
        out["excluded_candles"] = [{"date": x.date.isoformat(), "classification": x.classification}
                                   for x in snap.excluded_candles]
    out["symbol_result"] = reports.to_dict(res)
    out["limitations"] = sorted(limitations)
    return json.loads(json.dumps(out, default=mtf.json_default, sort_keys=True))


def to_json(b):
    return json.dumps(b, sort_keys=True, indent=1) + "\n"


# --- CLI ------------------------------------------------------------------------------

def cmd_replay_decision(args):
    from nse.research import cli, dashboard          # lazy: cli imports this module
    try:
        as_of = cli._as_of(args.as_of)
        calendar = cal_mod.NseCalendar.load(args.calendar) if args.calendar else None
        symbol = args.symbol.strip().upper()
        if not symbol:
            raise ValueError("--symbol is empty")
        [inp] = cli._inputs(args, [symbol])
    except SystemExit as e:                          # cli._inputs reports a missing source this way
        print("error: %s" % e, file=sys.stderr)
        return 2
    except (ValueError, OSError, cal_mod.CalendarError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    cfg = scanner.ScanConfig(as_of=as_of, trade_type=args.trade_type, calendar=calendar,
                             calendar_label=args.calendar or "NONE", risk_per_trade=args.risk_per_trade)
    b = bundle(inp, cfg)
    os.makedirs(args.out, exist_ok=True)
    for name, text in (("decision.json", to_json(b)), ("decision.html", dashboard.render_decision(b))):
        with open(os.path.join(args.out, name), "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    print("%s at %s: %s; wrote %s: decision.json, decision.html"
          % (b["symbol"], b["as_of"], b["symbol_result"]["status"], args.out))
    return 0


def add_commands(subparsers):
    p = subparsers.add_parser("replay-decision",
                              help="what was known about one symbol at as-of: decision.json and decision.html")
    p.add_argument("--symbol", required=True)
    p.add_argument("--as-of", required=True)
    p.add_argument("--trade-type", default=m.MIT, choices=m.TRADE_TYPES)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv-dir", help="folder with one SYMBOL.csv per symbol")
    src.add_argument("--bhavcopy-dir", help="folder with legacy cm*bhav.csv.zip files")
    p.add_argument("--manifest", help="EOD manifest.csv (provenance check for bhavcopies)")
    p.add_argument("--series", default="EQ")
    p.add_argument("--source-label", default="USER_CSV")
    p.add_argument("--price-adjustment", default="UNKNOWN", choices=("UNKNOWN", "NONE", "ADJUSTED"))
    p.add_argument("--calendar", help="calendar folder; omitted -> CALENDAR_UNVALIDATED")
    p.add_argument("--risk-per-trade", type=float)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_replay_decision)
