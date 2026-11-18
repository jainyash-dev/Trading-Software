"""Shared input adapters for every command: the as-of parser and the local daily-input
loader. They used to live in cli.py (with a copy of the parser in scenarios.py), which
made backtest.py and decision_replay.py import the CLI module to reuse them. Moving them
here removes that domain -> CLI dependency (ENGINEERING_DECISIONS ED-14); cli._as_of,
cli._inputs and scenarios.parse_as_of stay as aliases with the same behaviour.

Inputs are local files only (D31). Nothing is fetched.
"""

import dataclasses
import datetime
import glob
import os

from nse.research import instruments, marketdata
from nse.research.deps import bhavcopy, mtf


class InputSourceError(ValueError):
    """A required local input source is missing (no archives, no symbols)."""


def parse_as_of(text):
    """A date (the 15:30 IST close of that day) or an ISO datetime."""
    if "T" in text or " " in text:
        return datetime.datetime.fromisoformat(text)
    return datetime.datetime.combine(datetime.date.fromisoformat(text), mtf.SESSION_CLOSE)


def load(symbols, csv_dir=None, bhavcopy_dir=None, manifest=None, series="EQ",
         source_label="USER_CSV", price_adjustment="UNKNOWN", instrument_records=None):
    """DailyInput per symbol from a folder of SYMBOL.csv files or of bhavcopy archives
    (legacy and UDiFF, each date in its selected format, ED-20). A symbol without a CSV
    gets an empty input with a NO_INPUT_FILE error (so G0 reports it); missing archives or
    symbols raise InputSourceError. Bhavcopy inputs get the instrument identity check
    (instruments.apply_to_input, ED-21), with instrument_records (a path or loaded
    records) when given; a CSV has no ISIN, so it is not checked."""
    if csv_dir:
        paths = sorted(glob.glob(os.path.join(csv_dir, "*.csv")))
        by_symbol = {os.path.splitext(os.path.basename(p))[0].upper(): p for p in paths}
        wanted = symbols or sorted(by_symbol)
        out = []
        for s in wanted:
            if s not in by_symbol:
                out.append(marketdata.DailyInput(s, [], {"source": "USER_CSV"}, [],
                                                 [marketdata.Finding(s, marketdata.ERROR, "NO_INPUT_FILE",
                                                                     "%s.csv not in %s" % (s, csv_dir))]))
            else:
                out.append(marketdata.from_csv(by_symbol[s], s, source_label, price_adjustment))
        return out
    paths = bhavcopy.archive_paths(bhavcopy_dir)
    if not paths:
        raise InputSourceError("no bhavcopy archives (cm*bhav.csv.zip or BhavCopy_NSE_CM_*.csv.zip) in %s"
                               % bhavcopy_dir)
    parsed_manifest = bhavcopy.read_manifest(manifest) if manifest else None
    if not symbols:
        raise InputSourceError("--symbols or --universe is required with --bhavcopy-dir")
    records = instruments.load(instrument_records) if isinstance(instrument_records, str) else instrument_records
    files = _load_needed_rows(paths, parsed_manifest, symbols, records, series)
    out = []
    for s in symbols:
        # D51: a renamed company's earlier rows are joined only through verified ISIN continuity
        segments, why, conflicts = instruments.lineage(records, s, files, series) if records else ([None], [], [])
        joined = instruments.join_files(files, segments, s.strip().upper()) if records else files
        inp = marketdata.from_bhavcopy(joined, s, series)
        for reason in why:
            inp.findings.append(marketdata.Finding(s, marketdata.WARNING, "LINEAGE_NOT_JOINED", reason))
        for day, reason in conflicts:                  # dated: earlier scans are unchanged (D44)
            inp.findings.append(marketdata.Finding(s, marketdata.ERROR, "LINEAGE_CONFLICT", reason, date=day))
        out.append(instruments.apply_to_input(inp, files, records, series, segments if records else None))
    return out


def _load_needed_rows(paths, manifest, symbols, records, series):
    """The archives, strictly loaded in full, keeping in memory only the rows the identity and
    series code reads (ED-41): the requested symbols and every symbol of their SYMBOL_CHANGE
    chains, plus, for the identity check, rows of `series` under ANY other symbol that traded
    one of their ISINs (apply_to_input: renames and reused ISINs). Those are found from a
    compact (ISIN, symbol) -> first / last date index built in the first pass, and fetched
    by a second pass over those dates only; the result equals loading every row."""
    names = set(s.strip().upper() for s in symbols)
    grew = True
    while grew:                                        # rename chains in both directions
        grew = False
        for r in records or []:
            if r.record_type == instruments.SYMBOL_CHANGE and (r.symbol in names) != (r.new_symbol in names):
                names |= {r.symbol, r.new_symbol}
                grew = True
    seen = {}

    def keep(row):
        if row.series == series:
            span = seen.setdefault((row.isin, row.symbol), [row.trade_date, row.trade_date])
            span[0], span[1] = min(span[0], row.trade_date), max(span[1], row.trade_date)
        return row.symbol in names
    files = bhavcopy.load_many(paths, manifest, keep)
    mine = set(i for i, s in seen if s in names)
    extra = {k: v for k, v in seen.items() if k[0] in mine and k[1] not in names}
    if not extra:
        return files
    lo, hi = min(v[0] for v in extra.values()), max(v[1] for v in extra.values())
    path_of = {os.path.basename(p): p for p in paths}
    out = []
    for f in files:
        if lo <= f.trade_date <= hi:
            more = [r for r in bhavcopy.load(path_of[f.source.file_name], manifest).rows
                    if r.series == series and (r.isin, r.symbol) in extra]
            f = dataclasses.replace(f, rows=f.rows + more)
        out.append(f)
    return out


def corporate_action_config(path):
    """(actions, coverage) for ScanConfig from a corporate_actions.py records file; the
    verified collection windows come from coverage.csv beside it when present (D52, D56).
    No path: (None, None), as before (B7)."""
    from nse.research import corporate_actions
    if not path:
        return None, None
    cov = os.path.join(os.path.dirname(os.path.abspath(path)), "coverage.csv")
    return corporate_actions.load(path), (corporate_actions.load_coverage(cov) if os.path.isfile(cov) else None)


def from_args(args, symbols):
    """load() with the command-line options (--csv-dir / --bhavcopy-dir, --manifest,
    --series, --source-label, --price-adjustment). A missing source stops the command
    with SystemExit and the message, as the CLI always has."""
    try:
        return load(symbols, csv_dir=args.csv_dir, bhavcopy_dir=args.bhavcopy_dir,
                    manifest=getattr(args, "manifest", None), series=getattr(args, "series", "EQ"),
                    source_label=getattr(args, "source_label", "USER_CSV"),
                    price_adjustment=getattr(args, "price_adjustment", "UNKNOWN"),
                    instrument_records=getattr(args, "instruments", None))
    except InputSourceError as e:
        raise SystemExit(str(e))
