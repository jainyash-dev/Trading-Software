"""Command line for the research scanner. Run from the repository root:

  python3 -m nse.research.cli scan --as-of 2022-03-31 --symbols INFY \\
      --bhavcopy-dir nse/data/eod/raw --manifest nse/data/eod/manifest.csv \\
      --calendar nse/data/calendar --out nse/output/scan-2022-03-31

  python3 -m nse.research.cli scan --as-of 2024-06-28 --csv-dir my_daily_csvs --out nse/output/x
  python3 -m nse.research.cli inventory --as-of 2024-01-31 --symbols INFY
  python3 -m nse.research.cli backtest --model model.json --start 2023-01-02 --end 2024-01-31 \\
      --symbols INFY --bhavcopy-dir nse/data/eod/raw --manifest nse/data/eod/manifest.csv \\
      --calendar nse/data/calendar --out nse/output/bt.json
  python3 -m nse.research.cli readiness

Inputs are local files only (D31). --as-of is a date (the 15:30 IST close of that day)
or an ISO datetime. Nothing is fetched, no broker is contacted and no trade is approved.
Exit code: 0 when the scan ran (whatever the statuses), 2 on a usage or input error.
"""

import argparse
import datetime
import json
import os
import sys
from decimal import Decimal

sys.dont_write_bytecode = True        # a scan leaves no __pycache__ in the working tree

from nse.research import backtest, inputs as inputs_, inventory, manifest_tool, marketdata, models as m, refcheck, reports, readiness, run_manifest, scanner, universe as uni  # noqa: E402
from nse.research.deps import bhavcopy, calendar as cal_mod
import importlib  # noqa: E402

# modules that register further subcommands through add_commands(subparsers). An import
# error here stops the CLI: a command is never silently missing.
COMMAND_MODULES = ("health", "eod_coverage", "acquisition", "store", "backtest", "explain", "alerts", "narrative", "decision_replay", "dashboard", "risk", "instruments", "scenarios", "pipeline")


# shared with every command module (nse/research/inputs.py, ED-14); names kept for callers
_as_of = inputs_.parse_as_of
_inputs = inputs_.from_args


def cmd_scan(args):
    as_of = _as_of(args.as_of)
    universe = None
    symbols = None
    if args.universe:
        universe = uni.load(args.universe)
        symbols = [r.symbol for r in universe.members(as_of.date())]
    elif args.symbols:
        universe = uni.adhoc(args.symbols.split(","))
        symbols = [r.symbol for r in universe.rows]
    calendar = cal_mod.NseCalendar.load(args.calendar) if args.calendar else None
    acts, cov = inputs_.corporate_action_config(getattr(args, "corporate_actions", None))
    cfg = scanner.ScanConfig(as_of=as_of, trade_type=args.trade_type, calendar=calendar,
                             calendar_label=args.calendar or "NONE", risk_per_trade=args.risk_per_trade,
                             generated_at=args.generated_at, universe_label=universe.name if universe else "ADHOC",
                             corporate_actions=acts, corporate_action_coverage=cov)
    if args.trade_type == m.MIT:
        inputs = _inputs(args, symbols)
    else:                                       # WIT is BLOCKED (M4b): nothing is loaded
        inputs = [marketdata.DailyInput(s, [], {}, [], []) for s in (symbols or [])]
    result = scanner.scan(inputs, cfg, universe)
    written = reports.write_all(result, args.out)
    params = {k: getattr(args, k, None) for k in ("as_of", "trade_type", "symbols", "universe", "calendar",
                                                  "risk_per_trade", "generated_at", "series", "source_label",
                                                  "price_adjustment", "csv_dir", "bhavcopy_dir", "manifest",
                                                  "instruments", "corporate_actions")}
    params = run_manifest.relative_paths(params, run_manifest.PATH_PARAMS)
    manifest = run_manifest.build("scan", as_of, params,
                                  run_manifest.scan_input_paths(args, [i.symbol for i in inputs],
                                                                loads_data=args.trade_type == m.MIT),
                                  limitations=result.limitations)
    run_manifest.write(manifest, args.out, written)
    print(json.dumps(reports.summary(result), sort_keys=True, indent=1))
    print("wrote %s: %s, %s (%s)" % (args.out, ", ".join(written), run_manifest.MANIFEST_NAME, manifest["run_id"]))
    return 0


def cmd_inventory(args):
    inv = inventory.inventory(args.bhavcopy_dir, args.manifest, args.calendar, _as_of(args.as_of).date(),
                              [x.strip().upper() for x in (args.symbols or "").split(",") if x.strip()],
                              window_start=datetime.date.fromisoformat(args.window_start) if args.window_start else None)
    text = json.dumps(inv, sort_keys=True, indent=1)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    return 0


def cmd_backtest(args):
    with open(args.model, encoding="utf-8") as fh:
        spec = json.load(fh)
    spec["statuses"] = tuple(spec.get("statuses", ()))
    model = backtest.ExecutionModel(**spec)          # every field required; TypeError lists what is missing
    start, end = _as_of(args.start), _as_of(args.end)
    universe = uni.load(args.universe) if args.universe else uni.adhoc(args.symbols.split(","))
    symbols = sorted(set(r.symbol for r in universe.rows))
    inputs = _inputs(args, symbols)
    dates = sorted(set(c.end for i in inputs for c in i.candles if start <= c.end <= end))
    calendar = cal_mod.NseCalendar.load(args.calendar) if args.calendar else None
    acts, cov = inputs_.corporate_action_config(getattr(args, "corporate_actions", None))
    cfg = scanner.ScanConfig(as_of=end, calendar=calendar, calendar_label=args.calendar or "NONE",
                             risk_per_trade=args.risk_per_trade, universe_label=universe.name,
                             corporate_actions=acts, corporate_action_coverage=cov)
    res = backtest.run(inputs, dates, cfg, model, split=_as_of(args.split) if args.split else None,
                       universe=None if universe.adhoc else universe)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(backtest.to_json(res) + "\n")
    params = {k: getattr(args, k, None) for k in ("model", "start", "end", "split", "symbols", "universe", "calendar",
                                                  "risk_per_trade", "series", "source_label", "price_adjustment",
                                                  "csv_dir", "bhavcopy_dir", "manifest", "instruments",
                                                  "corporate_actions")}
    params = run_manifest.relative_paths(params, run_manifest.PATH_PARAMS)
    folder, name = os.path.split(os.path.abspath(args.out))
    manifest = run_manifest.build("backtest", end, params, run_manifest.scan_input_paths(args, symbols) + [args.model],
                                  limitations=res["limitations"], assumptions=spec)
    run_manifest.write(manifest, folder, [name], name=name + ".manifest.json")
    print(json.dumps({"signals": res["signals"], "metrics": res["metrics"], "limitations": res["limitations"]},
                     sort_keys=True, indent=1))
    return 0


def cmd_manifest_rows(args):
    rows = manifest_tool.rows_for(args.files, args.manifest, args.source_page, args.downloaded_on,
                                  args.provenance_status)
    if args.append:
        manifest_tool.append(args.manifest, rows)
        print("appended %d rows to %s" % (len(rows), args.manifest))
    else:
        sys.stdout.write(manifest_tool.to_csv(rows))
    return 0


def cmd_readiness(args):
    print(json.dumps(readiness.report(), sort_keys=True, indent=1))
    return 0


def cmd_compare_references(args):
    """Replay one symbol with the official calendar and compare supplied reference files.

    Does not create observations, does not pass assume_regular_session, and does not
    certify T-005. EQ rows only.
    """
    from nse.research.deps import bhavcopy, reference, replay_mod
    if not args.calendar:
        raise ValueError("compare-references requires --calendar; regular sessions are not assumed")
    symbol = args.symbol.strip().upper()
    calendar = cal_mod.NseCalendar.load(args.calendar)
    manifest = bhavcopy.read_manifest(args.manifest) if args.manifest else None
    files = bhavcopy.load_many(bhavcopy.archive_paths(args.bhavcopy_dir), manifest,
                               keep=lambda r: r.symbol == symbol)
    htf = tuple(x.strip() for x in args.htf.split(",") if x.strip())
    replay = replay_mod.replay_symbol(files, symbol, htf=htf, as_of=_as_of(args.as_of) if args.as_of else None,
                                      calendar=calendar, series="EQ", assume_regular_session=False)
    ohlc = reference.read_ohlc_reference(args.ohlc) if args.ohlc else []
    zones = reference.read_zone_reference(args.zones) if args.zones else []
    trend = refcheck.read_trend_reference(args.trend) if args.trend else []
    report = refcheck.external_comparison_report(
        replay, ohlc, zones, trend, ohlc_tolerance=Decimal(args.ohlc_tolerance),
        zone_tolerance=Decimal(args.zone_tolerance), trend_tolerance=Decimal(args.trend_tolerance))
    report["symbol"] = symbol
    report["calendar"] = args.calendar
    text = json.dumps(report, sort_keys=True, indent=1)
    if args.out:
        folder = os.path.dirname(os.path.abspath(args.out))
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="python3 -m nse.research.cli", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="scan symbols at one as-of time and write JSON/CSV reports")
    s.add_argument("--as-of", required=True)
    s.add_argument("--trade-type", default=m.MIT, choices=m.TRADE_TYPES)
    g = s.add_mutually_exclusive_group()
    g.add_argument("--symbols", help="comma-separated ad-hoc universe (UNIVERSE_UNVERIFIED)")
    g.add_argument("--universe", help="universe CSV (nse/research/universe.py format)")
    src = s.add_mutually_exclusive_group(required=True)
    src.add_argument("--bhavcopy-dir", help="folder with bhavcopy archives (legacy cm*bhav.csv.zip and UDiFF)")
    src.add_argument("--csv-dir", help="folder with one SYMBOL.csv per symbol")
    s.add_argument("--manifest", help="EOD manifest.csv (provenance check for bhavcopies)")
    s.add_argument("--corporate-actions", help="corporate-action records CSV (corporate_actions.py format); "
                 "coverage.csv beside it gives the verified collection windows (D50, D52)")
    s.add_argument("--instruments", help="instrument identity records CSV (instruments.py format); "
                 "omitted -> IDENTITY_UNVERIFIED, ISIN changes still checked")
    s.add_argument("--series", default="EQ")
    s.add_argument("--source-label", default="USER_CSV")
    s.add_argument("--price-adjustment", default="UNKNOWN", choices=("UNKNOWN", "NONE", "ADJUSTED"))
    s.add_argument("--calendar", help="calendar folder (nse/data/calendar); omitted -> CALENDAR_UNVALIDATED")
    s.add_argument("--risk-per-trade", type=float, help="RPT in rupees, for the quantity range")
    s.add_argument("--generated-at", help="label recorded in the reports; no clock is read")
    s.add_argument("--out", required=True, help="output folder (nse/output/ is git-ignored)")
    s.set_defaults(func=cmd_scan)
    iv = sub.add_parser("inventory", help="local EOD and calendar coverage, history needed for an as-of, acquisition spec")
    iv.add_argument("--as-of", required=True)
    iv.add_argument("--bhavcopy-dir", default="nse/data/eod/raw")
    iv.add_argument("--manifest", default="nse/data/eod/manifest.csv")
    iv.add_argument("--calendar", default="nse/data/calendar")
    iv.add_argument("--symbols", help="comma-separated symbols for coverage")
    iv.add_argument("--window-start", help="first date of the evaluation window's data (e.g. 2021-01-01)")
    iv.add_argument("--out", help="also write the JSON here")
    iv.set_defaults(func=cmd_inventory)
    b = sub.add_parser("backtest", help="simulate point-in-time signals with a user-supplied execution model")
    b.add_argument("--model", required=True, help="JSON with every backtest.ExecutionModel field (no defaults)")
    b.add_argument("--start", required=True, help="first signal date")
    b.add_argument("--end", required=True, help="last signal date")
    b.add_argument("--split", help="in-sample up to this date, out-of-sample after")
    bg = b.add_mutually_exclusive_group(required=True)
    bg.add_argument("--symbols")
    bg.add_argument("--universe")
    bs = b.add_mutually_exclusive_group(required=True)
    bs.add_argument("--bhavcopy-dir")
    bs.add_argument("--csv-dir")
    b.add_argument("--manifest")
    b.add_argument("--corporate-actions", help="corporate-action records CSV (corporate_actions.py format); "
                 "coverage.csv beside it gives the verified collection windows (D50, D52)")
    b.add_argument("--instruments", help="instrument identity records CSV (instruments.py format); "
                 "omitted -> IDENTITY_UNVERIFIED, ISIN changes still checked")
    b.add_argument("--series", default="EQ")
    b.add_argument("--source-label", default="USER_CSV")
    b.add_argument("--price-adjustment", default="UNKNOWN", choices=("UNKNOWN", "NONE", "ADJUSTED"))
    b.add_argument("--calendar")
    b.add_argument("--risk-per-trade", type=float)
    b.add_argument("--out", required=True)
    b.set_defaults(func=cmd_backtest)
    mf = sub.add_parser("manifest-rows", help="manifest rows for downloaded legacy bhavcopy archives (strictly parsed)")
    mf.add_argument("files", nargs="+")
    mf.add_argument("--manifest", default="nse/data/eod/manifest.csv")
    mf.add_argument("--source-page", required=True, help="the page the files came from, as you recorded it")
    mf.add_argument("--downloaded-on", required=True, help="YYYY-MM-DD or UNKNOWN (never a file time)")
    mf.add_argument("--provenance-status", required=True, help="e.g. USER_CONFIRMED")
    mf.add_argument("--append", action="store_true", help="append to the manifest instead of printing")
    mf.set_defaults(func=cmd_manifest_rows)
    r = sub.add_parser("readiness", help="print the capability readiness table")
    r.set_defaults(func=cmd_readiness)
    cr = sub.add_parser("compare-references",
                        help="compare OHLC, zone and SMA-50 reference files with an EQ replay (does not certify T-005)")
    cr.add_argument("--symbol", required=True)
    cr.add_argument("--bhavcopy-dir", required=True)
    cr.add_argument("--manifest", help="EOD manifest.csv")
    cr.add_argument("--calendar", required=True, help="official calendar folder; required, never assume_regular_session")
    cr.add_argument("--as-of", help="optional replay cutoff")
    cr.add_argument("--htf", default="D,W,M,Q,HY,Y")
    cr.add_argument("--ohlc", help="OHLC reference CSV; omitted means that evidence is absent")
    cr.add_argument("--zones", help="zone reference CSV")
    cr.add_argument("--trend", help="SMA-50 reference CSV")
    cr.add_argument("--ohlc-tolerance", default="0")
    cr.add_argument("--zone-tolerance", default="0")
    cr.add_argument("--trend-tolerance", default="0")
    cr.add_argument("--out", help="write the JSON report here; observations are not written back")
    cr.set_defaults(func=cmd_compare_references)
    for name in COMMAND_MODULES:      # each module registers its own subcommands
        importlib.import_module("nse.research." + name).add_commands(sub)
    args = p.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, TypeError, OSError, manifest_tool.ManifestError, uni.UniverseError, cal_mod.CalendarError, bhavcopy.BhavcopyError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
