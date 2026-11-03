"""Single validation command for the repository. Run from the repository root:

  python3 -m nse.validation.run_all                 # every check
  python3 -m nse.validation.run_all --group strategy_gates --group lookahead
  python3 -m nse.validation.run_all --acceptance    # a missing local prerequisite FAILS
  python3 -m nse.validation.run_all --list
  python3 -m nse.validation.run_all --acceptance --require-window 2021-01-01 2025-12-31

Checks, in order:
  1. repository   protected-file hashes, `git diff --check`, nothing staged, every test
                  module assigned to a group (so no test can be left out silently)
  2. test groups  each group's unittest modules, run in this process (REQUIRED)
  3. local data   calendar circulars hash-verified; EOD archives against the manifest;
                  calendar vs EOD reconciliation over the dates held (OPTIONAL: needs the
                  git-ignored evidence, D31)
  4. reference    INFY OHLC reference vs the replayed bhavcopies (OPTIONAL)
  5. readiness    readiness.report() with the test modules that passed in THIS run

Results are PASS, FAIL, SKIPPED_PREREQUISITE (tests skipped for missing local evidence)
or UNAVAILABLE (an optional check whose inputs are absent). UNAVAILABLE and skips are
never counted as passes: the verdict names them. Exit code 1 if any check FAILED, or,
with --acceptance (which always runs everything), if any evidence is missing; 0 otherwise. A JSON report is written to
--out (default nse/output/validation/report.json, git-ignored).
"""

import argparse
import datetime
import glob
import io
import json
import os
import subprocess
import sys
import time
import unittest

sys.dont_write_bytecode = True        # validation leaves no __pycache__ in the working tree

from nse.validation import protected  # noqa: E402

ROOT = protected.ROOT
TESTS = os.path.join(ROOT, "tests")
ACCEPTANCE_ENV = "NSE_PHASE1_ACCEPTANCE"

GROUPS = (
    ("repository", ["test_repo"]),
    ("zone_engine", ["test_zone_engine"]),
    ("mtf_freshness", ["test_mtf_freshness"]),
    ("data", ["test_nse_bhavcopy", "test_nse_calendar", "test_nse_calendar_data", "test_nse_replay"]),
    ("strategy_gates", ["test_research_gates", "test_research_confluence"]),
    ("lookahead", ["test_research_lookahead"]),
    ("integration", ["test_research_integration", "test_research_e2e"]),
    ("adversarial", ["test_research_adversarial"]),
    ("reports", ["test_research_reports"]),
    ("data_readiness", ["test_research_data"]),
    ("backtest", ["test_research_backtest"]),
    ("acquisition", ["test_research_acquisition"]),
    ("store", ["test_research_store"]),
    ("research_assistant", ["test_research_explain", "test_research_alerts"]),
    ("dashboard", ["test_research_dashboard"]),
    ("risk_instruments", ["test_research_risk", "test_research_instruments"]),
    ("scenarios", ["test_research_scenarios"]),
    ("health", ["test_research_health"]),
    ("hooks", ["test_claude_hooks"]),
    ("council", ["test_llm_council"]),
    ("validation_framework", ["test_validation_runner"]),
    ("legacy_day_trader_skills", ["test_alerts", "test_analyst", "test_broker", "test_budget", "test_entry",
                                  "test_exit", "test_news", "test_pelosi", "test_risk", "test_scanner",
                                  "test_timemachine"]),
)
PASS, FAIL, SKIPPED, UNAVAILABLE = "PASS", "FAIL", "SKIPPED_PREREQUISITE", "UNAVAILABLE"


def _git(*args):
    p = subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def check_repository():
    out = {"name": "repository_checks", "required": True, "details": {}}
    problems = []
    bad = protected.check()
    out["details"]["protected_files"] = {rel: "OK" if all(rel != b[0] for b in bad) else "CHANGED OR MISSING"
                                         for rel in sorted(protected.PROTECTED)}
    if bad:
        problems.append("protected file changed or missing: %s" % ", ".join(b[0] for b in bad))
    code, so, se = _git("diff", "--check")
    out["details"]["git_diff_check"] = "clean" if code == 0 else (so + se).strip()[:2000]
    if code not in (0,):
        problems.append("git diff --check reports problems")
    code, so, _ = _git("diff", "--cached", "--name-only")
    staged = [x for x in so.splitlines() if x]
    out["details"]["staged_files"] = staged
    if staged:
        problems.append("files are staged; staging needs explicit user authorisation")
    code, so, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    out["details"]["branch"] = so.strip()
    code, so, _ = _git("rev-parse", "--short", "HEAD")
    out["details"]["head"] = so.strip()
    assigned = set(x for _, mods in GROUPS for x in mods)
    present = set(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(TESTS, "test_*.py")))
    out["details"]["unassigned_test_modules"] = sorted(present - assigned)
    out["details"]["missing_test_modules"] = sorted(assigned - present)
    if present - assigned:
        problems.append("test modules not in any validation group: %s" % ", ".join(sorted(present - assigned)))
    if assigned - present:
        problems.append("validation groups name missing test modules: %s" % ", ".join(sorted(assigned - present)))
    out["status"] = FAIL if problems else PASS
    out["problems"] = problems
    return out


class _Result(unittest.TextTestResult):
    pass


def run_group(name, modules):
    if TESTS not in sys.path:
        sys.path.insert(0, TESTS)
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    suite = unittest.TestSuite()
    load_errors = []
    for mod in modules:
        try:
            suite.addTests(unittest.defaultTestLoader.loadTestsFromName(mod))
        except Exception as e:                      # an import error is a failure, never a skip
            load_errors.append("%s: %s: %s" % (mod, type(e).__name__, e))
    stream = io.StringIO()
    t0 = time.time()
    res = unittest.TextTestRunner(stream=stream, verbosity=0, resultclass=_Result).run(suite)
    skips = [(t.id(), why) for t, why in res.skipped]
    prereq = [s for s in skips if why_is_prereq(s[1])]
    other_skips = [s for s in skips if not why_is_prereq(s[1])]
    failed = res.failures + res.errors
    status = PASS
    if failed or load_errors or other_skips or res.unexpectedSuccesses:
        status = FAIL
    elif prereq:
        status = SKIPPED
    return {"name": name, "required": True, "modules": modules, "status": status,
            "ran": res.testsRun, "failures": len(res.failures), "errors": len(res.errors) + len(load_errors),
            "skipped": len(skips), "seconds": round(time.time() - t0, 2),
            "failed_tests": [{"test": t.id(), "trace": tb[-1500:]} for t, tb in failed],
            "load_errors": load_errors, "prerequisite_skips": [{"test": i, "reason": w} for i, w in prereq],
            "other_skips": [{"test": i, "reason": w} for i, w in other_skips]}


def why_is_prereq(reason):
    return str(reason).startswith("PREREQUISITE MISSING")


# a file on a Muhurat or shortened session is expected evidence (D30 excludes the session
# from candles; the replay classifies it), not a disagreement with the calendar
RECONCILIATION_PROBLEMS = ("missing_eod_on_trading_day", "eod_on_closed_day", "outside_coverage", "unresolved")
RECONCILIATION_INFO = ("eod_on_excluded_session",)


def check_local_data(window=None):
    from nse.research.deps import CALENDAR_DIR, EOD_MANIFEST, EOD_RAW_DIR, bhavcopy, calendar
    out = {"name": "local_data", "required": False, "details": {}}
    circ = os.path.join(CALENDAR_DIR, "circulars")
    zips = sorted(glob.glob(os.path.join(EOD_RAW_DIR, "cm*bhav.csv.zip")))
    if not os.path.isdir(circ) or not zips:
        out["status"] = FAIL if window is not None else UNAVAILABLE    # a required window cannot be unavailable
        out["details"]["missing"] = [p for p, ok in ((circ, os.path.isdir(circ)), (EOD_RAW_DIR, bool(zips))) if not ok]
        return out
    problems = []
    cal = calendar.NseCalendar.load(CALENDAR_DIR)
    out["details"]["calendar_covered_years"] = cal.covered_years
    out["details"]["calendar_unverified_sources"] = [s.source_ref for s in cal.unverified_sources]
    if cal.unverified_sources:
        problems.append("calendar sources not hash-verified: %s" % ", ".join(s.source_ref for s in cal.unverified_sources))
    try:
        files = bhavcopy.load_many(zips, bhavcopy.read_manifest(EOD_MANIFEST))
    except bhavcopy.BhavcopyError as e:
        problems.append("EOD archives fail the strict loader with the manifest: %s" % e)
        files = []
    out["details"]["eod_archives_loaded"] = len(files)
    if files:
        dates = [f.trade_date for f in files]
        # reconcile month by month only where the archives cover the whole month
        months = sorted(set((d.year, d.month) for d in dates))
        recon = {}
        for y, mth in months:
            first = datetime.date(y, mth, 1)
            last = (datetime.date(y + mth // 12, mth % 12 + 1, 1) - datetime.timedelta(days=1))
            in_month = [d for d in dates if first <= d <= last]
            r = calendar.reconcile(cal, in_month, first, last)
            issues = {k: [d.isoformat() for d in getattr(r, k)] for k in RECONCILIATION_PROBLEMS if getattr(r, k)}
            info = {k: [d.isoformat() for d in getattr(r, k)] for k in RECONCILIATION_INFO if getattr(r, k)}
            recon["%04d-%02d" % (y, mth)] = {"eod_files": len(in_month), "issues": issues, "info": info}
        out["details"]["reconciliation"] = recon
        out["details"]["note"] = ("a month with one or two files shows every other session as missing: that is "
                                  "missing EOD evidence, not a calendar defect")
        for k, v in recon.items():
            if v["eod_files"] >= 15 and v["issues"]:
                problems.append("calendar vs EOD disagree in %s: %s" % (k, v["issues"]))
        if window is not None:
            r = calendar.reconcile(cal, dates, window[0], window[1])
            missing = [d.isoformat() for d in r.missing_eod_on_trading_day]
            out["details"]["required_window"] = {"from": window[0].isoformat(), "to": window[1].isoformat(),
                                                 "missing_sessions": len(missing), "first_missing": missing[:20],
                                                 "outside_calendar_coverage": len(r.outside_coverage),
                                                 "unresolved": [d.isoformat() for d in r.unresolved],
                                                 "eod_on_closed_day": [d.isoformat() for d in r.eod_on_closed_day]}
            if missing or r.outside_coverage or r.unresolved or r.eod_on_closed_day:
                problems.append("required window %s to %s is not complete: %d missing sessions, %d weekdays outside "
                                "calendar coverage, %d unresolved, %d files on closed days"
                                % (window[0], window[1], len(missing), len(r.outside_coverage), len(r.unresolved),
                                   len(r.eod_on_closed_day)))
    out["status"] = FAIL if problems else PASS
    out["problems"] = problems
    return out


def check_reference():
    from nse.research.deps import EOD_MANIFEST, EOD_RAW_DIR, REFERENCE_DIR, bhavcopy, reference, replay_mod
    out = {"name": "reference_comparison", "required": False, "details": {}}
    ref = os.path.join(REFERENCE_DIR, "INFY", "ohlc_reference.csv")
    zips = sorted(glob.glob(os.path.join(EOD_RAW_DIR, "cm*2022bhav.csv.zip")))
    if not os.path.isfile(ref) or not zips:
        out["status"] = UNAVAILABLE
        out["details"]["missing"] = [p for p, ok in ((ref, os.path.isfile(ref)), (EOD_RAW_DIR, bool(zips))) if not ok]
        return out
    refs = reference.read_ohlc_reference(ref)
    files = bhavcopy.load_many(zips, bhavcopy.read_manifest(EOD_MANIFEST))
    rp = replay_mod.replay_symbol(files, "INFY", htf=("D", "W", "M"), assume_regular_session=True)
    results = reference.compare_ohlc(refs, rp)
    summ = reference.coverage_summary(results)
    out["details"]["coverage"] = summ["counts"]
    out["details"]["complete"] = summ["complete"]
    out["details"]["sources"] = sorted(set(r.source for r in refs))
    out["details"]["note"] = ("Yahoo Finance republishes NSE data: a MATCH shows the replay reproduces published "
                              "prices, not independent validation. No TradingView reference is recorded.")
    out["status"] = FAIL if summ["counts"].get(reference.MISMATCH) else PASS
    out["problems"] = ["OHLC mismatches: %d" % summ["counts"][reference.MISMATCH]] if out["status"] == FAIL else []
    return out


def verdict(checks, acceptance):
    """(verdict text, exit code). Skips and UNAVAILABLE evidence are never a plain PASS; in
    acceptance mode missing evidence is a failure (exit 1), like any failed check."""
    failed = [c["name"] for c in checks if c["status"] == FAIL and c.get("required", True)]
    optional_failed = [c["name"] for c in checks if c["status"] == FAIL and not c.get("required", True)]
    skipped = [c["name"] for c in checks if c["status"] == SKIPPED]
    unavailable = [c["name"] for c in checks if c["status"] == UNAVAILABLE]
    parts = []
    if failed:
        parts.append("FAIL: " + ", ".join(failed))
    if optional_failed:
        parts.append("OPTIONAL_FAILED: " + ", ".join(optional_failed))
    if acceptance and (skipped or unavailable):
        parts.append("EVIDENCE_MISSING: " + ", ".join(skipped + unavailable))
    if parts:
        return "FAIL (" + "; ".join(parts) + ")", 1
    text = "PASS"
    if skipped:
        text += "_WITH_SKIPPED_PREREQUISITES: " + ", ".join(skipped)
    if unavailable:
        text += "; EVIDENCE_UNAVAILABLE: " + ", ".join(unavailable)
    return text, 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="python3 -m nse.validation.run_all")
    p.add_argument("--group", action="append", help="run only these test groups (repeatable)")
    p.add_argument("--acceptance", action="store_true", help="missing local prerequisites FAIL (sets %s=1)" % ACCEPTANCE_ENV)
    p.add_argument("--no-data", action="store_true", help="skip the optional local-data and reference checks")
    p.add_argument("--out", default=os.path.join(ROOT, "nse", "output", "validation", "report.json"))
    p.add_argument("--list", action="store_true", help="list the groups and exit")
    p.add_argument("--require-window", nargs=2, metavar=("FROM", "TO"),
                   help="local_data FAILS unless every calendar trading session FROM..TO has an EOD file")
    args = p.parse_args(argv)
    if args.list:
        for name, mods in GROUPS:
            print("%-26s %s" % (name, ", ".join(mods)))
        return 0
    if args.acceptance and (args.group or args.no_data):
        p.error("--acceptance runs every check; it cannot be combined with --group or --no-data")
    if args.acceptance:
        os.environ[ACCEPTANCE_ENV] = "1"
    names = [g for g, _ in GROUPS]
    for g in args.group or []:
        if g not in names:
            p.error("unknown group %r; use --list" % g)
    checks = [check_repository()]
    for name, mods in GROUPS:
        if args.group and name not in args.group:
            continue
        checks.append(run_group(name, mods))
    window = None
    if args.require_window:
        window = tuple(datetime.date.fromisoformat(x) for x in args.require_window)
        if args.no_data:
            p.error("--require-window needs the local data check; drop --no-data")
    if not args.no_data and not args.group:
        for fn in (lambda: check_local_data(window), check_reference):
            try:
                checks.append(fn())
            except Exception as e:                  # an optional check that crashes is a FAIL, not a pass
                checks.append({"name": getattr(fn, "__name__", "local_data"), "required": False, "status": FAIL,
                               "problems": ["%s: %s" % (type(e).__name__, e)]})
    passed_modules = set()
    for c in checks:
        if c.get("modules") and c["status"] == PASS:
            passed_modules.update(c["modules"])
    from nse.research import readiness
    report = {"acceptance_mode": args.acceptance, "checks": checks,
              "readiness": readiness.report(passed_modules),
              "totals": {k: sum(c.get(k, 0) for c in checks) for k in ("ran", "failures", "errors", "skipped")}}
    report["verdict"], exit_code = verdict(checks, args.acceptance)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, sort_keys=True, indent=1)
        fh.write("\n")
    for c in checks:
        extra = ""
        if "ran" in c:
            extra = "ran %d, failures %d, errors %d, skipped %d" % (c["ran"], c["failures"], c["errors"], c["skipped"])
        print("%-26s %-22s %s" % (c["name"], c["status"], extra))
        for prob in c.get("problems", []):
            print("    - %s" % prob)
        for f in c.get("failed_tests", []):
            print("    - FAILED %s" % f["test"])
        for f in c.get("load_errors", []):
            print("    - LOAD ERROR %s" % f)
        for f in c.get("prerequisite_skips", []):
            print("    - SKIPPED %s: %s" % (f["test"], f["reason"]))
    print("totals: %s" % report["totals"])
    print("verdict: %s  (report: %s)" % (report["verdict"], os.path.relpath(args.out, ROOT)))
    print("Software tests are not external validation; see the readiness section of the report.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
