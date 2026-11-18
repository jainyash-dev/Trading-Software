"""Data readiness: what local EOD evidence exists, what a scan at a given as_of needs, and
exactly what is missing. Reads local files only; downloads nothing (D31).

  inventory(bhavcopy_dir, manifest, calendar, as_of, symbols) -> dict

History needed for a scan at as_of (the period in progress never counts, D23):
  - Zone Engine on any timeframe: 3 completed candles (zone_engine.MIN_CANDLES)
  - Y, HY, Q: 3 completed calendar periods (conflict check, G5; TDA, EC1)
  - M: 3 completed months (curve, G3); 55 for the Monthly trend context (reported only)
  - W: 55 completed weeks (the MIT trend gate, G4; D14, D23)
  - D: 3 completed sessions
Every series must also be unbroken: a missing session ends it (D37), so the required
range must be complete, not just long enough. Raw availability says nothing about
adjusted-price correctness (B7).
"""

import datetime

from nse.research import trend
from nse.research.deps import bhavcopy, calendar as cal_mod, mtf, ze

NEEDED = {"D": ze.MIN_CANDLES, "W": trend.MIN_CANDLES, "M": ze.MIN_CANDLES, "Q": ze.MIN_CANDLES,
          "HY": ze.MIN_CANDLES, "Y": ze.MIN_CANDLES}
CONTEXT = {"M": trend.MIN_CANDLES}
PURPOSE = {"D": "execution zones", "W": "MIT trend gate (55 weeks)", "M": "curve (3 months)",
           "Q": "HTF conflict", "HY": "HTF conflict", "Y": "HTF conflict / TDA"}


def _period_start_back(tf, as_of_date, n):
    """First day of the n-th completed period before the one containing as_of_date."""
    first, _ = mtf.period_bounds(tf, as_of_date)
    d = first
    for _ in range(n):
        d = mtf.period_bounds(tf, d - datetime.timedelta(days=1))[0]
    return d


def required_start(as_of_date):
    """Earliest date each timeframe needs, for a scan at the close of as_of_date. A period
    that ends on as_of_date counts as completed only if as_of is its last session; this
    is conservative: it assumes the current period is in progress."""
    out = {tf: _period_start_back(tf, as_of_date, n) for tf, n in NEEDED.items()}
    out["M_context"] = _period_start_back("M", as_of_date, CONTEXT["M"])
    return out


def _calendar_dates(cal, start, end):
    """Trading dates per the calendar; dates it cannot answer for, and excluded (Muhurat,
    shortened) sessions, are listed separately."""
    trading, uncovered, unresolved, excluded = [], [], [], []
    d = start
    while d <= end:
        try:
            if cal.is_trading_day(d):
                trading.append(d)
            elif cal.is_excluded_session(d):
                excluded.append(d)
        except cal_mod.CalendarCoverageError:
            if d.weekday() < 5:
                uncovered.append(d)
        except cal_mod.CalendarAmbiguityError:
            unresolved.append(d)
        d += datetime.timedelta(days=1)
    return trading, uncovered, unresolved, excluded


def _ranges(dates):
    """Compress sorted dates into [first, last, count] runs of consecutive list items."""
    out = []
    for d in dates:
        if out and (d - out[-1][1]).days <= 4:
            out[-1][1] = d
            out[-1][2] += 1
        else:
            out.append([d, d, 1])
    return [{"from": a.isoformat(), "to": b.isoformat(), "sessions": n} for a, b, n in out]


def inventory(bhavcopy_dir, manifest_path, calendar_folder, as_of_date, symbols=(), window_start=None):
    """window_start: also cover an evaluation window from this date (signals from window_start
    to as_of need history before window_start; pass the window's first data date)."""
    out = {"as_of": as_of_date.isoformat(), "problems": [],
           "window_start": window_start.isoformat() if window_start else None}
    paths = bhavcopy.archive_paths(bhavcopy_dir)
    files = []
    if paths:
        try:
            manifest = bhavcopy.read_manifest(manifest_path) if manifest_path else None
            wanted = set(symbols)
            files = bhavcopy.load_many(paths, manifest, keep=lambda r: r.symbol in wanted)   # memory (ED-41)
        except bhavcopy.BhavcopyError as e:
            out["problems"].append("strict loader refused the archives: %s" % e)
    have = sorted(f.trade_date for f in files)
    out["eod_files"] = {"archives_found": len(paths), "archives_loaded": len(files),
                        "first": have[0].isoformat() if have else None,
                        "last": have[-1].isoformat() if have else None,
                        "runs": _ranges(have), "formats": sorted(set(f.format for f in files)),
                        "source_selection": "legacy up to %s, UDiFF from %s (ED-20)"
                                            % (bhavcopy.LEGACY_LAST_TRADE_DATE, bhavcopy.UDIFF_ONLY_FROM),
                        "price_adjustment": "NONE (unadjusted; B7)"}
    req = required_start(as_of_date)
    if window_start is not None:
        req["WINDOW"] = window_start
    start = min(req.values())
    out["required_start"] = {k: v.isoformat() for k, v in sorted(req.items())}
    cal = None
    try:
        cal = cal_mod.NseCalendar.load(calendar_folder) if calendar_folder else None
    except (cal_mod.CalendarError, OSError) as e:
        out["problems"].append("calendar not loadable: %s" % e)
    if cal is None:
        out["calendar"] = {"status": "UNAVAILABLE"}
        out["missing_sessions"] = None
    else:
        trading, uncovered, unresolved, excluded = _calendar_dates(cal, start, as_of_date)
        missing = [d for d in trading if d not in set(have)]
        out["calendar"] = {"status": "LOADED", "covered_years": cal.covered_years,
                           "unverified_sources": [s.source_ref for s in cal.unverified_sources],
                           "weekdays_without_calendar_coverage": _ranges(uncovered),
                           "unresolved_dates": [d.isoformat() for d in unresolved]}
        out["missing_sessions"] = {"count": len(missing), "runs": _ranges(missing)}
        closed_with_file = [d for d in have if start <= d <= as_of_date and d not in set(trading)
                            and d not in set(uncovered) and d not in set(unresolved) and d not in set(excluded)]
        out["files_on_non_trading_days"] = [d.isoformat() for d in closed_with_file]
        out["excluded_sessions"] = {"dates": [d.isoformat() for d in excluded],
                                    "with_file": [d.isoformat() for d in excluded if d in set(have)],
                                    "note": "Muhurat and shortened sessions: a file, if NSE publishes one, is kept "
                                            "as evidence and excluded from candles (D30); it is not required"}
        # per timeframe: is the required range complete?
        tf_rows = {}
        for tf, first in sorted(req.items()):
            need = [d for d in trading if d >= first]
            gap = [d for d in need if d not in set(have)]
            unc = [d for d in uncovered if d >= first]
            # an unresolved calendar date blocks the timeframes whose required range contains
            # it, and only those (MP1: the 2016-2019 Dhanteras rows must not block Daily in 2022)
            unr = [d for d in unresolved if d >= first]
            tf_rows[tf] = {"from": first.isoformat(),
                           "purpose": PURPOSE.get(tf, {"WINDOW": "evaluation window"}.get(tf, "Monthly trend context (reported only)")),
                           "sessions_needed": len(need), "sessions_missing": len(gap),
                           "weekdays_without_calendar": len(unc), "unresolved_dates": len(unr),
                           "ready": not gap and not unc and not unr}
        out["history"] = tf_rows
    sym = {}
    for s in symbols:
        rows = [(f.trade_date, any(r.symbol == s and r.series == "EQ" for r in f.rows)) for f in files]
        present = [d for d, ok in rows if ok]
        sym[s] = {"files_with_eq_row": len(present), "files_without_row": [d.isoformat() for d, ok in rows if not ok],
                  "first": present[0].isoformat() if present else None,
                  "last": present[-1].isoformat() if present else None}
    out["symbols"] = sym
    out["acquisition"] = acquisition_spec(out, req, as_of_date)
    out["ready_for_full_scan"] = bool(out.get("history")) and all(r["ready"] for k, r in out["history"].items()
                                                                  if k != "M_context")
    return out


def acquisition_spec(inv, req, as_of_date):
    """What to obtain, in what format, and how it will be accepted. Nothing is fetched."""
    start = min(v for k, v in req.items() if k != "M_context")
    sessions = (inv.get("missing_sessions") or {}).get("count")
    spec = {
        "eod": {"range": [start.isoformat(), as_of_date.isoformat()], "missing_session_count": sessions,
                "missing": (inv.get("missing_sessions") or {}).get("runs"),
                "source": "NSE capital-market bhavcopy, official NSE website (D31: user downloads)",
                "format": "legacy cmDDMMMYYYYbhav.csv.zip until the UDiFF switch (date unverified, B18); a UDiFF "
                          "sample must be documented before later dates can be loaded",
                "acceptance": ["manifest.csv row per archive and member with size and SHA-256",
                               "nse_bhavcopy strict loader accepts every file",
                               "calendar reconciliation: no missing session, no file on a closed day",
                               "python3 -m nse.validation.run_all --acceptance passes"]},
        "calendar": {"needed_years": sorted(set(range(start.year, as_of_date.year + 1)))},
        "corporate_actions": {"needed": "split, bonus, rights, consolidation events for every scanned symbol over "
                                        "the same range, with ex-dates and ratios, from an approved source (B7)",
                              "acceptance": ["file in nse/research/corporate_actions.py format with source SHA-256",
                                             "known events reproduced against the raw price discontinuity"]},
    }
    cal = inv.get("calendar") or {}
    spec["eod"]["weekdays_needing_calendar_and_data"] = cal.get("weekdays_without_calendar_coverage")
    covered = set(cal.get("covered_years") or [])
    spec["calendar"]["missing_years"] = [y for y in spec["calendar"]["needed_years"] if y not in covered]
    return spec
