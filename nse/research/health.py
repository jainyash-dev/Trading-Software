"""System health check: is this checkout able to run research, and on what evidence?

  python3 -m nse.research.cli health [--out health.json]

Each check reports OK, WARNING (runs, with a limitation), FAIL (must be fixed) or
UNAVAILABLE (optional local evidence is absent). Exit code 1 if any check FAILS.
It reads local files only (D31), modifies nothing and reads no clock. It does not run
the test suite: `python3 -m nse.validation.run_all` does that. A healthy system is not a
validated one: external validation stays pending (readiness.py).
"""

import glob
import importlib
import json
import os

from nse.research import readiness
from nse.research.deps import CALENDAR_DIR, EOD_MANIFEST, EOD_RAW_DIR, REFERENCE_DIR, ROOT, bhavcopy, calendar as cal_mod
from nse.validation import protected

OK, WARNING, FAIL, UNAVAILABLE = "OK", "WARNING", "FAIL", "UNAVAILABLE"

# every research module must import cleanly (an import error is a FAIL, never a skip)
MODULES = ("models", "marketdata", "universe", "structure", "trend", "levels", "topdown", "qualification",
           "scanner", "reports", "readiness", "inventory", "corporate_actions", "refcheck", "backtest",
           "manifest_tool", "health")
OPTIONAL_MODULES = ("acquisition", "instruments", "risk", "scenarios", "decision_replay", "dashboard",
                    "explain", "alerts", "narrative", "store")


def _check(name, status, detail, **extra):
    out = {"check": name, "status": status, "detail": detail}
    out.update(extra)
    return out


def check_protected(root=ROOT):
    bad = protected.check(root)
    if bad:
        return _check("protected_files", FAIL, "changed or missing: %s" % ", ".join(b[0] for b in bad))
    return _check("protected_files", OK, "%d protected files match their pinned SHA-256" % len(protected.PROTECTED))


def check_modules():
    failed, present = [], []
    for name in MODULES + OPTIONAL_MODULES:
        path = os.path.join(ROOT, "nse", "research", name + ".py")
        if name in OPTIONAL_MODULES and not os.path.isfile(path):
            continue
        try:
            importlib.import_module("nse.research." + name)
            present.append(name)
        except Exception as e:                     # reported, never hidden
            failed.append("%s: %s: %s" % (name, type(e).__name__, e))
    if failed:
        return _check("research_modules", FAIL, "; ".join(failed), imported=present)
    return _check("research_modules", OK, "%d modules import" % len(present), imported=present)


def check_calendar(folder=CALENDAR_DIR):
    if not os.path.isfile(os.path.join(folder, "sources.csv")):
        return _check("calendar", UNAVAILABLE, "no calendar at %s: scans run CALENDAR_UNVALIDATED (D28)" % folder)
    try:
        cal = cal_mod.NseCalendar.load(folder)
    except cal_mod.CalendarError as e:
        return _check("calendar", FAIL, "calendar does not load: %s" % e)
    unresolved = sorted(e.date.isoformat() for e in cal.events if e.status == "UNRESOLVED")
    # loads and hash-verifies. D40 is USER_APPROVED (decision log section 1F). B17 external
    # validation is still open, so this check stays WARNING. Approval is not validation.
    return _check("calendar", WARNING,
                  "official circular tables for %s; not externally validated (B17); "
                  "D40 is USER_APPROVED in the decision log and is not external validation; "
                  "20 Jan 2024 hours remain an inference from NSE/CMTR/41180"
                  % ", ".join(str(y) for y in cal.covered_years),
                  covered_years=cal.covered_years,
                  unverified_sources=sorted(s.source_ref for s in cal.unverified_sources),
                  unresolved_dates=unresolved)


def check_eod(raw_dir=EOD_RAW_DIR, manifest_path=EOD_MANIFEST):
    if not os.path.isfile(manifest_path):
        return _check("eod_data", UNAVAILABLE, "no EOD manifest at %s" % manifest_path)
    try:
        rows = bhavcopy.read_manifest(manifest_path)
    except bhavcopy.BhavcopyError as e:
        return _check("eod_data", FAIL, "manifest does not load: %s" % e)
    archives = sorted((r for r in rows if r["kind"] == "ARCHIVE"), key=lambda r: r["trade_date"])
    held = set(os.path.basename(p) for p in glob.glob(os.path.join(raw_dir, "*.zip")))
    listed = set(r["file_name"] for r in archives)
    missing = sorted(listed - held)
    unlisted = sorted(held - listed)
    dates = [r["trade_date"] for r in archives if r["file_name"] in held]
    detail = ("%d archives held (%s to %s); prices unadjusted (B7); legacy format only, UDiFF unverified (B18)"
              % (len(dates), dates[0] if dates else "-", dates[-1] if dates else "-"))
    status = WARNING
    if unlisted:
        status = FAIL
        detail += "; archives without provenance rows: %s" % ", ".join(unlisted)
    if not held:
        status = UNAVAILABLE
        detail = "no local EOD archives (git-ignored, D31); scans need --csv-dir or downloaded bhavcopies"
    return _check("eod_data", status, detail, archives_held=len(dates), listed_but_absent=missing,
                  held_without_manifest=unlisted)


def check_reference(folder=REFERENCE_DIR):
    files = sorted(os.path.relpath(p, folder) for p in glob.glob(os.path.join(folder, "**", "*.csv"), recursive=True)
                   if not p.endswith(".template.csv"))
    if not files:
        return _check("reference_data", UNAVAILABLE, "no reference records: nothing is reference-validated")
    return _check("reference_data", WARNING,
                  "%d reference file(s); none is an independent TradingView record unless its provenance says so "
                  "(B8, B10)" % len(files), files=files)


def check_inputs_not_built_in():
    # these inputs have no data in the repository by design; their absence is a limitation, not a fault
    return _check("owner_inputs", WARNING,
                  "no Nifty 100 constituent file (B11, D1: every scan is UNIVERSE_UNVERIFIED unless --universe "
                  "is given), no corporate-action records (B7), no instrument history, no intraday data (B6)")


def check_readiness():
    caps = readiness.report()
    ext = [c["id"] for c in caps if c.get("externally_validated")]
    if ext:
        return _check("readiness", FAIL, "readiness claims external validation without recorded evidence: %s"
                      % ", ".join(ext))
    return _check("readiness", OK, "%d capabilities; none claims external validation" % len(caps))


def report():
    checks = [check_protected(), check_modules(), check_calendar(), check_eod(), check_reference(),
              check_inputs_not_built_in(), check_readiness()]
    counts = {}
    for c in checks:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    return {"checks": checks, "status_counts": dict(sorted(counts.items())),
            "healthy": not any(c["status"] == FAIL for c in checks),
            "note": "Health means the checkout can run research on local files. It is not validation: "
                    "run `python3 -m nse.validation.run_all` for tests, and see readiness for evidence."}


def cmd_health(args):
    rep = report()
    text = json.dumps(rep, sort_keys=True, indent=1)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    return 0 if rep["healthy"] else 1


def add_commands(sub):
    h = sub.add_parser("health", help="can this checkout run research? protected files, modules, local data")
    h.add_argument("--out", help="also write the JSON here")
    h.set_defaults(func=cmd_health)
