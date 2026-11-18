"""Historical EOD coverage report: every raw file, one by one, against the manifest and the
trading calendar. Local files only (D31); nothing is downloaded, repaired or inferred.

Unlike inventory (which loads the archive set at once and stops at the first refusal), each
file here gets its own verdict, so one bad file cannot hide the state of the others:
  - name, kind, size, SHA-256 and the manifest record it matches (or why it does not);
  - format triage (acquisition.detect_format): LEGACY_BHAVCOPY, UDIFF_BHAVCOPY or UNKNOWN;
  - the strict loader's verdict (nse_bhavcopy.load, legacy or UDiFF). The loader refuses a whole file
    on any invalid record, so a LOADED file has no invalid or incomplete OHLC / quantity
    field, and a REFUSED file's reason names the first bad line;
  - EQ row count, non-EQ series counts and symbols with rows but no EQ row.
Dates: two loaded files for one trade date are a duplicate. They are reported as
IDENTICAL_CONTENT when the CSV bytes match (an archive and its own extracted member),
otherwise CONFLICTING. A calendar trading day with no loaded file is MISSING; it is never
called a holiday unless the official calendar says so. Weekdays the calendar does not cover
are listed separately as UNVERIFIED, not as missing or closed.
Symbols: for each requested symbol, the trading days whose file has no EQ row. Across the
held files, symbols with an EQ row in some files and not in others are counted, and
non-EQ-only days are listed (a symbol may trade in BE/BZ only that day).

File states (MP1; each implies the one before, and they are different claims):
  DOWNLOADED             the file is in raw_dir
  PARSED                 the strict loader accepts its content (legacy or UDiFF schema)
  VALIDATED              ...and its name, size and SHA-256 match its manifest records
  ACCEPTED_FOR_RESEARCH  ...and it is an archive in the format selected for its date
                         (ED-20), the official calendar classifies that date as a trading
                         day, and no other file supplies conflicting or refused content for
                         the date. A standalone CSV whose bytes equal an archive's member
                         (IDENTICAL_CONTENT) stays VALIDATED: research inputs read archives
A file that stops at a state keeps the reason it went no further. eod_ready is True only
when every calendar trading day in the window has an accepted file and no file is refused,
conflicting or unclassifiable. It covers the EOD files alone: data_ready is always False
here, because DATA_READY also needs a reviewed universe and identity evidence (owner
instruction 2026-11-09, D49, D51), which this report does not evaluate. dataset.dataset_id is the SHA-256 of the sorted
(trade date, file SHA-256) pairs of accepted files: the same files give the same id.
"""

import datetime
import glob
import hashlib
import json
import os
import sys
import zipfile

from nse.research import acquisition, inventory as inv
from nse.research.deps import bhavcopy, calendar as cal_mod

REPORT_VERSION = "2.1.0"           # 2.1.0: eod_ready (EOD only) and data_ready (never claimed here)
DOWNLOADED, PARSED, VALIDATED, ACCEPTED = "DOWNLOADED", "PARSED", "VALIDATED", "ACCEPTED_FOR_RESEARCH"
STATES = (DOWNLOADED, PARSED, VALIDATED, ACCEPTED)
KNOWN_LIMITATIONS = (
    "prices are as published and unadjusted; corporate actions are not applied (B7)",
    "identity history is not supplied; an absent symbol is not called missing data (B11)",
    "session times are not in the files; candles assume 09:15-15:30 (audit L7)",
    "TradingView parity is not verified (B8, B10, B17)",
    "a file NSE serves today is not proof of what was published on the trade date",
)


def _name_date(name):
    try:
        return bhavcopy._name_date(name).isoformat()
    except Exception:                                  # not a legacy name: no date is inferred
        return None


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _csv_bytes_sha(path):
    """SHA-256 of the CSV bytes (the member, for an archive): equal for a zip and its member."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            infos = z.infolist()
            if len(infos) != 1:
                return None
            return hashlib.sha256(z.read(infos[0])).hexdigest()
    return _sha(path)


def file_audit(raw_dir, manifest_path=None):
    """One record per file in raw_dir (sorted by name)."""
    manifest = None
    manifest_problem = None
    if manifest_path:
        try:
            manifest = bhavcopy.read_manifest(manifest_path)
        except (bhavcopy.BhavcopyError, OSError) as e:
            manifest_problem = str(e)
    out = []
    for path in sorted(p for p in glob.glob(os.path.join(raw_dir, "*")) if os.path.isfile(p)):
        name = os.path.basename(path)
        rec = {"file": name, "size_bytes": os.path.getsize(path), "sha256": _sha(path),
               "format": acquisition.detect_format(path), "status": None, "reason": None, "state": DOWNLOADED,
               "loaded_format": None, "schema_version": None,
               "trade_date": None, "eq_rows": None, "non_eq_series": None, "non_eq_only_symbols": None,
               "isin_missing_eq_rows": None, "last_price_empty_rows": None, "rejected_non_eq_rows": None,
               "csv_sha256": None,
               "provenance_status": None}
        if rec["format"] == acquisition.UNKNOWN:
            rec.update(status="NOT_LOADED", reason="the header is neither the legacy nor a UDiFF bhavcopy header")
            out.append(rec)
            continue
        try:
            f = bhavcopy.load(path, manifest)
        except bhavcopy.ProvenanceError as e:
            rec.update(status="REFUSED_PROVENANCE", reason=str(e))
            try:
                bhavcopy.load(path)                      # content alone: PARSED, provenance failed
                rec["state"] = PARSED
            except bhavcopy.BhavcopyError:
                pass
        except bhavcopy.BhavcopyError as e:
            rec.update(status="REFUSED", reason=str(e))
        else:
            eq = f.eq_rows
            rec.update(status="LOADED", state=VALIDATED if manifest else PARSED, loaded_format=f.format,
                       schema_version=f.schema_version, trade_date=f.trade_date.isoformat(), eq_rows=len(eq),
                       last_price_empty_rows=sum(1 for r in f.rows if r.last is None),
                       rejected_non_eq_rows=[{"line": x[0], "series": x[1], "symbol": x[2], "reason": x[3]}
                                             for x in f.rejected_rows],
                       non_eq_series=dict(sorted(f.non_eq_series.items())),
                       non_eq_only_symbols=len(f.non_eq_only_symbols),
                       isin_missing_eq_rows=sum(1 for r in eq if not r.isin),
                       csv_sha256=_csv_bytes_sha(path),
                       provenance_status=(f.provenance or {}).get("provenance_status") if manifest else "NO_MANIFEST")
            rec["_file"] = f
        out.append(rec)
    return out, manifest_problem


def coverage(raw_dir, manifest_path, calendar_folder, start, end, symbols=()):
    """The coverage report for trade dates start..end (inclusive dates)."""
    files, manifest_problem = file_audit(raw_dir, manifest_path)
    loaded = [r for r in files if r["status"] == "LOADED"]
    by_date = {}
    for r in loaded:
        by_date.setdefault(r["trade_date"], []).append(r)
    duplicates = []
    for d, rs in sorted(by_date.items()):
        if len(rs) > 1:
            same = len(set(r["csv_sha256"] for r in rs)) == 1
            duplicates.append({"trade_date": d, "files": [r["file"] for r in rs],
                               "kind": "IDENTICAL_CONTENT" if same else "CONFLICTING"})
    # a refused legacy file named for a date that another file supplies: two sources for one
    # date, one of them unusable (QA 2026-11-08)
    for r in files:
        if r["status"] in ("REFUSED", "REFUSED_PROVENANCE"):
            named = _name_date(r["file"])
            if named and named in by_date:
                duplicates.append({"trade_date": named, "files": sorted([x["file"] for x in by_date[named]]
                                                                        + [r["file"]]), "kind": "ONE_REFUSED"})
    duplicates.sort(key=lambda x: (x["trade_date"], x["kind"]))
    have = sorted(datetime.date.fromisoformat(d) for d in by_date)
    in_window = [d for d in have if start <= d <= end]
    report = {"report_version": REPORT_VERSION, "window": [start.isoformat(), end.isoformat()],
              "raw_dir": raw_dir, "manifest": manifest_path, "manifest_problem": manifest_problem,
              "files": [{k: v for k, v in r.items() if k != "_file"} for r in files],
              "counts": {"files": len(files), "loaded": len(loaded),
                         "by_status": _count(r["status"] for r in files),
                         "by_format": _count(r["format"] for r in files)},
              "dates": {"earliest": have[0].isoformat() if have else None,
                        "latest": have[-1].isoformat() if have else None,
                        "distinct_trade_dates": len(have), "in_window": len(in_window),
                        "runs": inv._ranges(have)},
              "duplicates": duplicates}
    cal = None
    try:
        cal = cal_mod.NseCalendar.load(calendar_folder) if calendar_folder else None
    except (cal_mod.CalendarError, OSError) as e:
        report["calendar_problem"] = str(e)
    if cal is None:
        report["calendar"] = {"status": "UNAVAILABLE",
                              "note": "without the official calendar no date can be called missing or a holiday"}
    else:
        trading, uncovered, unresolved, excluded = inv._calendar_dates(cal, start, end)
        held = set(have)
        missing = [d for d in trading if d not in held]
        report["calendar"] = {
            "status": "LOADED", "covered_years": cal.covered_years,
            "trading_days_in_window": len(trading), "held": len([d for d in trading if d in held]),
            "missing": {"count": len(missing), "runs": inv._ranges(missing),
                        "by_year": _count(str(d.year) for d in missing)},
            "unverified_weekdays": {"count": len(uncovered), "runs": inv._ranges(uncovered)},
            "unresolved_dates": [d.isoformat() for d in unresolved],
            "excluded_sessions": [{"date": d.isoformat(), "type": cal.session_type(d), "file_held": d in held}
                                  for d in excluded],
            # only a date the official calendar positively classifies as closed; a date it
            # cannot answer for (any weekday or weekend outside its coverage) is UNVERIFIED
            "files_on_non_trading_days": [d.isoformat() for d in in_window if _closed(cal, d)],
            "files_on_unclassifiable_dates": [d.isoformat() for d in in_window if _closed(cal, d) is None]}
    files_by_date = {d: by_date[d][0]["_file"] for d in by_date}
    eq_sets = {d: set(r.symbol for r in f.eq_rows) for d, f in files_by_date.items()}
    union = set().union(*eq_sets.values()) if eq_sets else set()
    gappy = sorted(s for s in union if any(s not in v for v in eq_sets.values()))
    report["symbols"] = {
        "eq_symbols_seen": len(union), "eq_symbols_absent_on_some_held_dates": len(gappy),
        "requested": {s: {"held_dates_with_eq_row": sum(1 for v in eq_sets.values() if s in v),
                          "held_dates_without_eq_row": sorted(d for d, v in eq_sets.items() if s not in v),
                          "non_eq_only_dates": sorted(d for d, f in files_by_date.items()
                                                      if s in f.non_eq_only_symbols)}
                      for s in symbols},
        "note": "a symbol absent from a file may be suspended, renamed, newly listed or delisted; identity "
                "history (B11) is needed before an absence is called missing data"}
    _states(report, files, by_date, cal, start, end)
    report["udiff"] = {"files": [r["file"] for r in files if r["format"] == acquisition.UDIFF_BHAVCOPY],
                       "schema_versions": sorted(set(r["schema_version"] for r in files if r["schema_version"])),
                       "status": "SUPPORTED (ED-20): verified schemas %s" % ", ".join(sorted(bhavcopy.UDIFF_SCHEMAS))}
    return report


def _states(report, files, by_date, cal, start, end):
    """ACCEPTED_FOR_RESEARCH, the dataset identity and eod_ready (module docstring)."""
    conflicted = set(d["trade_date"] for d in report["duplicates"] if d["kind"] != "IDENTICAL_CONTENT")
    for r in files:
        if r["state"] != VALIDATED:
            continue
        d = datetime.date.fromisoformat(r["trade_date"])
        if not r["file"].endswith(".zip"):
            r["reason"] = "standalone CSV; research inputs read the archive (nse_bhavcopy.archive_paths)"
        elif r["loaded_format"] != bhavcopy.selected_format(d):
            r["reason"] = "%s is not the format selected for %s (ED-20)" % (r["loaded_format"], d)
        elif cal is None:
            r["reason"] = "no official calendar: the date cannot be confirmed as a trading day"
        elif r["trade_date"] in conflicted:
            r["reason"] = "another file supplies the same date"
        else:
            try:
                ok = cal.is_trading_day(d)
            except cal_mod.CalendarError as e:
                ok, r["reason"] = False, "calendar: %s" % e
            if ok:
                r["state"] = ACCEPTED
                r["role"] = "TRADING_DAY"
            elif not r["reason"] and _excluded(cal, d):
                # D30 / D33 / D52: an official file of a calendar-excluded session is accepted in its
                # own role: held for the touch check, never for candles, never trading-day coverage
                r["state"], r["role"] = ACCEPTED, "EXCLUDED_SESSION_D33"
            elif not r["reason"]:
                r["reason"] = "the official calendar does not classify %s as a trading day" % d
    accepted = sorted((r["trade_date"], r["sha256"]) for r in files if r["state"] == ACCEPTED)
    trading_accepted = set(r["trade_date"] for r in files if r.get("role") == "TRADING_DAY")
    in_window = [x for x in accepted if start.isoformat() <= x[0] <= end.isoformat()]
    ident = hashlib.sha256("".join("%s %s\n" % x for x in in_window).encode()).hexdigest()
    manifest_sha = _sha(report["manifest"]) if report["manifest"] and os.path.isfile(report["manifest"]) else None
    report["files"] = [{k: v for k, v in r.items() if k != "_file"} for r in files]
    report["counts"]["by_state"] = {s: sum(1 for r in files if STATES.index(r["state"]) >= STATES.index(s))
                                    for s in STATES}
    report["counts"]["by_schema"] = _count(r["schema_version"] for r in files if r["schema_version"])
    report["dataset"] = {"dataset_id": ident, "accepted_dates_in_window": len(in_window),
                         "manifest_sha256": manifest_sha, "loader_version": bhavcopy.LOADER_VERSION,
                         "report_version": REPORT_VERSION,
                         "source_selection": {"legacy_last_trade_date": bhavcopy.LEGACY_LAST_TRADE_DATE.isoformat(),
                                              "udiff_only_from": bhavcopy.UDIFF_ONLY_FROM.isoformat(),
                                              "evidence": "NSE/MSD/62424 (ED-20)"}}
    calr = report["calendar"]
    accepted_dates = set(x[0] for x in in_window if x[0] in trading_accepted)
    if calr.get("status") == "LOADED":
        trading = calr["trading_days_in_window"]
        calr["accepted"] = len(accepted_dates)
        calr["coverage_pct"] = round(100.0 * len(accepted_dates) / trading, 2) if trading else None
    blockers = []
    if calr.get("status") != "LOADED":
        blockers.append("no official calendar")
    else:
        if calr["missing"]["count"]:
            blockers.append("%d calendar trading days without a file" % calr["missing"]["count"])
        if calr["unverified_weekdays"]["count"] or calr["unresolved_dates"]:
            blockers.append("dates the calendar cannot classify")
    copies = [r["file"] for r in files if r["state"] == VALIDATED and not r["file"].endswith(".zip")
              and r["trade_date"] in accepted_dates]
    stopped = [r["file"] for r in files if r["state"] != ACCEPTED and r["file"] not in copies]
    if stopped:
        blockers.append("%d file(s) not accepted for research" % len(stopped))
    if conflicted:
        blockers.append("%d date(s) with conflicting or refused duplicate files" % len(conflicted))
    report["data_ready"] = {"ready": False, "reason": "EOD files are one input; DATA_READY also needs the reviewed "
                            "universe (D49) and identity evidence (D51), not evaluated by this report"}
    report["eod_ready"] = {"ready": not blockers, "blockers": blockers,
                                "not_accepted_files": stopped, "standalone_copies_of_accepted_archives": copies,
                                "note": "files existing is not coverage; only ACCEPTED_FOR_RESEARCH files count"}
    report["known_limitations"] = list(KNOWN_LIMITATIONS)


def _excluded(cal, d):
    try:
        return cal.is_excluded_session(d)
    except cal_mod.CalendarError:
        return False


def _closed(cal, d):
    """True: the calendar says d is not a trading day and not an excluded session; False: it
    is one of those; None: the calendar cannot classify d (coverage or ambiguity)."""
    try:
        return not cal.is_trading_day(d) and not cal.is_excluded_session(d)
    except cal_mod.CalendarError:
        return None


def _count(items):
    out = {}
    for x in items:
        out[x] = out.get(x, 0) + 1
    return dict(sorted(out.items()))


def cmd_eod_coverage(args):
    try:
        start, end = datetime.date.fromisoformat(args.start), datetime.date.fromisoformat(args.end)
    except ValueError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    rep = coverage(args.raw_dir, args.manifest, args.calendar, start, end,
                   [s for s in (args.symbols or "").split(",") if s])
    text = json.dumps(rep, indent=1, sort_keys=True)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(json.dumps({"counts": rep["counts"], "dates": {k: v for k, v in rep["dates"].items() if k != "runs"},
                      "missing": (rep["calendar"].get("missing") or {}).get("count"),
                      "coverage_pct": rep["calendar"].get("coverage_pct"),
                      "duplicates": len(rep["duplicates"]), "dataset_id": rep["dataset"]["dataset_id"],
                      "eod_ready": rep["eod_ready"]["ready"], "data_ready": False}, sort_keys=True, indent=1))
    return 0


def add_commands(sub):
    p = sub.add_parser("eod-coverage", help="per-file EOD coverage, duplicates and missing sessions (local files)")
    p.add_argument("--raw-dir", default="nse/data/eod/raw")
    p.add_argument("--manifest", default="nse/data/eod/manifest.csv")
    p.add_argument("--calendar", default="nse/data/calendar")
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument("--symbols", help="comma-separated symbols to report")
    p.add_argument("--out", help="write the full JSON report here")
    p.set_defaults(func=cmd_eod_coverage)
