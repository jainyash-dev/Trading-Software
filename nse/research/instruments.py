"""Instrument identity over time: symbol <-> ISIN with effective dates (spec 9.1; D1; B11).

No history is built in. A records file states, row by row, what an official document says:

    record_type,symbol,new_symbol,isin,series,effective_from,effective_to,source,source_file,source_sha256,recorded_on,notes

record_type (effective_from is the first day the record is in force, inclusive):
  LISTING        symbol trades under isin from effective_from; effective_to (inclusive) may
                 be empty (still listed)
  SYMBOL_CHANGE  the isin trades as new_symbol instead of symbol from effective_from
  ISIN_CHANGE    symbol trades under isin (the NEW ISIN) from effective_from; the ISIN it
                 had before ends that day
  DELISTING      symbol / isin is no longer listed from effective_from
  MERGER         symbol / isin merged into new_symbol (may be empty); no longer listed from
                 effective_from. The successor is a different instrument, not a rename.
A row without source and a 64-hex source_sha256 (D31) is UNVERIFIED and every identity
built on it says so. A symbol the records do not cover is UNKNOWN_INSTRUMENT, never a guess.
isin_consistency() checks the records against (date, symbol, isin) observations from
bhavcopies (the legacy bhavcopy has an ISIN column, nse_bhavcopy.BhavRow.isin).
"""

import csv
import datetime
import glob
import json
import os
import re
from dataclasses import dataclass
from typing import Optional

from nse.research import marketdata

COLUMNS = ("record_type", "symbol", "new_symbol", "isin", "series", "effective_from", "effective_to", "source",
           "source_file", "source_sha256", "recorded_on", "notes")
LISTING, SYMBOL_CHANGE, DELISTING, MERGER, ISIN_CHANGE = "LISTING", "SYMBOL_CHANGE", "DELISTING", "MERGER", "ISIN_CHANGE"
RECORD_TYPES = (LISTING, SYMBOL_CHANGE, DELISTING, MERGER, ISIN_CHANGE)
_ORDER = {LISTING: 0, ISIN_CHANGE: 1, SYMBOL_CHANGE: 2, MERGER: 3, DELISTING: 4}   # same-day order
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ISIN = re.compile(r"IN[A-Z0-9]{10}\Z")          # as nse_bhavcopy checks it

RESOLVED = "RESOLVED"
UNKNOWN_INSTRUMENT = "UNKNOWN_INSTRUMENT"
UNVERIFIED = "UNVERIFIED"
ISIN_CHANGED_WITHOUT_RECORD = "ISIN_CHANGED_WITHOUT_RECORD"
SYMBOL_REUSED_FOR_DIFFERENT_ISIN = "SYMBOL_REUSED_FOR_DIFFERENT_ISIN"
SYMBOL_CHANGED_WITHOUT_RECORD = "SYMBOL_CHANGED_WITHOUT_RECORD"
ISIN_RECORD_MISMATCH = "ISIN_RECORD_MISMATCH"


class InstrumentError(ValueError):
    pass


@dataclass(frozen=True)
class Record:
    record_type: str
    symbol: str
    new_symbol: str
    isin: str
    series: str
    effective_from: datetime.date
    effective_to: Optional[datetime.date]
    verified: bool
    source: str
    line: int

    def to_dict(self):
        return {"record_type": self.record_type, "symbol": self.symbol, "new_symbol": self.new_symbol or None,
                "isin": self.isin, "series": self.series, "effective_from": self.effective_from.isoformat(),
                "effective_to": self.effective_to.isoformat() if self.effective_to else None,
                "verified": self.verified, "source": self.source, "line": self.line}


def load(path):
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise InstrumentError("%s: header must be exactly %s" % (path, ",".join(COLUMNS)))
        out = []
        for i, r in enumerate(reader, 2):
            where = "%s line %d" % (path, i)
            kind = r["record_type"].strip()
            if kind not in RECORD_TYPES:
                raise InstrumentError("%s: record_type must be one of %s" % (where, ", ".join(RECORD_TYPES)))
            try:
                start = datetime.date.fromisoformat(r["effective_from"].strip())
                end = datetime.date.fromisoformat(r["effective_to"].strip()) if r["effective_to"].strip() else None
            except ValueError:
                raise InstrumentError("%s: dates must be YYYY-MM-DD" % where)
            sym, new, isin = r["symbol"].strip().upper(), r["new_symbol"].strip().upper(), r["isin"].strip().upper()
            if not sym:
                raise InstrumentError("%s: empty symbol" % where)
            if not _ISIN.match(isin):
                raise InstrumentError("%s: isin %r is not IN + 10 letters or digits" % (where, isin))
            if end is not None and kind != LISTING:
                raise InstrumentError("%s: effective_to is only allowed on LISTING rows" % where)
            if end is not None and end < start:
                raise InstrumentError("%s: effective_to before effective_from" % where)
            if kind == SYMBOL_CHANGE and (not new or new == sym):
                raise InstrumentError("%s: SYMBOL_CHANGE needs a new_symbol different from symbol" % where)
            if kind in (LISTING, DELISTING, ISIN_CHANGE) and new:
                raise InstrumentError("%s: new_symbol is only allowed on SYMBOL_CHANGE and MERGER rows" % where)
            verified = bool(r["source"].strip()) and bool(_SHA.match(r["source_sha256"].strip().lower()))
            out.append(Record(kind, sym, new, isin, r["series"].strip() or "EQ", start, end, verified,
                              r["source"].strip(), i))
    return sorted(out, key=_key)


def _key(r):
    return (r.effective_from, _ORDER[r.record_type], r.line, r.symbol)


def _events(records):
    """(date, order, record, action) with the LISTING end as its own event the day after."""
    ev = []
    for r in records:
        ev.append((r.effective_from, _ORDER[r.record_type], r.line, r, "start"))
        if r.record_type == LISTING and r.effective_to is not None:
            ev.append((r.effective_to + datetime.timedelta(days=1), -1, r.line, r, "end"))
    return sorted(ev, key=lambda e: (e[0], e[1], e[2]))


def state_at(records, date):
    """{isin: (symbol, [records that made it so])} for instruments listed on date, using only
    records in force on date (point in time), and {old isin: new isin} ISIN links so far."""
    active, links = {}, {}
    for d, _, _, r, action in _events(records):
        if d > date:
            break
        if action == "end":
            if r.isin in active and active[r.isin][0] == r.symbol:
                del active[r.isin]
        elif r.record_type == LISTING:
            active[r.isin] = (r.symbol, [r])
        elif r.record_type == SYMBOL_CHANGE:
            prev = active.get(r.isin, (None, []))[1]
            active[r.isin] = (r.new_symbol, prev + [r])
        elif r.record_type == ISIN_CHANGE:
            olds = [i for i, (s, _) in active.items() if s == r.symbol and i != r.isin]
            prev = []
            for i in olds:
                prev += active.pop(i)[1]
                links[i] = r.isin
            active[r.isin] = (r.symbol, prev + [r])
        else:                                         # DELISTING, MERGER
            active.pop(r.isin, None)
    return active, links


def symbol_at(records, isin, date):
    """The symbol isin trades under on date, or None (not listed, or not in the records)."""
    hit = state_at(records, date)[0].get(isin.upper())
    return hit[0] if hit else None


def history(records, symbol):
    """Every symbol linked to symbol by SYMBOL_CHANGE rows, in both directions, cycle-safe.
    A symbol that comes back (A -> B -> A) is reported as a cycle; it is not followed twice."""
    symbol = symbol.upper()
    changes = [r for r in records if r.record_type == SYMBOL_CHANGE]
    seen, todo, used = {symbol}, [symbol], []
    while todo:
        s = todo.pop()
        for r in changes:
            if s in (r.symbol, r.new_symbol):
                if r not in used:
                    used.append(r)
                for other in (r.symbol, r.new_symbol):
                    if other not in seen:
                        seen.add(other)
                        todo.append(other)
    used.sort(key=_key)
    order = []
    for r in used:
        for s in (r.symbol, r.new_symbol):
            if s not in order:
                order.append(s)
    cycle = len(used) >= len(seen) > 1          # a chain of n symbols has n - 1 changes
    related = [r for r in records if r.symbol in seen or r.new_symbol in seen]
    return {"symbol": symbol, "symbols": order or [symbol], "changes": [r.to_dict() for r in used],
            "isins": sorted(set(r.isin for r in related)), "cycle": cycle,
            "verified": bool(related) and all(r.verified for r in related),
            "known": bool(related)}


def resolve(records, symbol, date):
    """Canonical identity of the instrument trading as symbol on date. canonical_id is the
    earliest ISIN of its ISIN_CHANGE lineage. UNKNOWN_INSTRUMENT when no record says what
    symbol is on date, or when two ISINs claim it (a records contradiction)."""
    symbol = symbol.upper()
    active, links = state_at(records, date)
    hits = sorted(i for i, (s, _) in active.items() if s == symbol)
    base = {"symbol": symbol, "date": date.isoformat()}
    if len(hits) != 1:
        if hits:
            reason = "two or more ISINs are listed as %s on %s: %s" % (symbol, date, ", ".join(hits))
        elif any(symbol in (r.symbol, r.new_symbol) for r in records):
            reason = "the records cover %s, but not as a listed symbol on %s" % (symbol, date)
        else:
            reason = "no record for %s" % symbol
        return dict(base, status=UNKNOWN_INSTRUMENT, reason=reason, isin=None, canonical_id=None, verified=False)
    isin = hits[0]
    back = {new: old for old, new in links.items()}
    lineage = [isin]
    while lineage[-1] in back and back[lineage[-1]] not in lineage:
        lineage.append(back[lineage[-1]])
    used = active[isin][1]
    verified = all(r.verified for r in used)
    out = dict(base, status=RESOLVED, isin=isin, canonical_id="ISIN:" + lineage[-1],
               isin_lineage=list(reversed(lineage)), symbols=history([r for r in records if r.effective_from <= date], symbol)["symbols"],
               records=[r.line for r in used], verified=verified, reason=None)
    if not verified:
        out["limitations"] = [UNVERIFIED]
    return out


def _finding(code, severity, symbol, detail, date=None, verified=True, extra=None):
    return marketdata.Finding(symbol, severity, code, detail, verified, date, extra)


def isin_consistency(records, observations):
    """Findings (marketdata.Finding) for records and (date, symbol, isin) observations:
      UNVERIFIED                        a record row without source and source_sha256
      UNKNOWN_INSTRUMENT                an observed symbol no record covers on that date
      ISIN_RECORD_MISMATCH              the records list the symbol under another ISIN that day
      ISIN_CHANGED_WITHOUT_RECORD       the symbol's ISIN changed and no record explains it
      SYMBOL_REUSED_FOR_DIFFERENT_ISIN  the symbol's ISIN changed because the records end one
                                        instrument and list another under the same symbol: the
                                        two price histories must not be joined
      SYMBOL_CHANGED_WITHOUT_RECORD     one ISIN observed under two symbols, no SYMBOL_CHANGE
    Sorted by (date, symbol, code). Each transition is reported once."""
    out = []
    for r in records:
        if not r.verified:
            out.append(_finding(UNVERIFIED, marketdata.WARNING, r.symbol, "records line %d (%s) has no source and "
                                "64-hex source_sha256 (D31)" % (r.line, r.record_type), r.effective_from, False,
                                {"line": r.line}))
    obs = sorted(set((d, s.strip().upper(), i.strip().upper()) for d, s, i in observations))
    cache = {}

    def state(d):
        if d not in cache:
            cache[d] = state_at(records, d)
        return cache[d]

    last_by_symbol, last_by_isin, unknown, mismatched = {}, {}, set(), set()
    for d, s, i in obs:
        active, links = state(d)
        listed = sorted(x for x, (sym, _) in active.items() if sym == s)
        if not listed and s not in unknown:
            unknown.add(s)
            out.append(_finding(UNKNOWN_INSTRUMENT, marketdata.WARNING, s, "no record lists %s on %s" % (s, d), d,
                                extra={"isin": i}))
        elif listed and i not in listed and (s, i, tuple(listed)) not in mismatched:
            mismatched.add((s, i, tuple(listed)))
            out.append(_finding(ISIN_RECORD_MISMATCH, marketdata.ERROR, s, "observed ISIN %s, records list %s on %s"
                                % (i, ", ".join(listed), d), d, extra={"isin": i, "records": listed}))
        prev = last_by_symbol.get(s)
        if prev and prev[1] != i:
            d0, i0 = prev
            if _isin_change_between(records, s, i0, i, d0, d):
                pass
            elif _reuse_between(records, s, i0, i, d0, d):
                out.append(_finding(SYMBOL_REUSED_FOR_DIFFERENT_ISIN, marketdata.WARNING, s,
                                    "%s was %s up to %s and %s from %s: different instruments per the records"
                                    % (s, i0, d0, i, d), d, extra={"old_isin": i0, "new_isin": i}))
            else:
                out.append(_finding(ISIN_CHANGED_WITHOUT_RECORD, marketdata.ERROR, s,
                                    "ISIN %s on %s, %s on %s; no record explains the change"
                                    % (i0, d0, i, d), d, extra={"old_isin": i0, "new_isin": i}))
        last_by_symbol[s] = (d, i)
        prev = last_by_isin.get(i)
        if prev and prev[1] != s:
            d0, s0 = prev
            if not any(r.record_type == SYMBOL_CHANGE and r.isin == i and r.symbol == s0 and r.new_symbol == s
                       and d0 < r.effective_from <= d for r in records):
                out.append(_finding(SYMBOL_CHANGED_WITHOUT_RECORD, marketdata.ERROR, s,
                                    "ISIN %s traded as %s on %s and as %s on %s; no SYMBOL_CHANGE record"
                                    % (i, s0, d0, s, d), d, extra={"isin": i, "old_symbol": s0}))
        last_by_isin[i] = (d, s)
    return sorted(out, key=lambda f: (f.date or datetime.date.min, f.symbol, f.code, f.detail))


def _isin_change_between(records, symbol, old, new, d0, d1):
    return any(r.record_type == ISIN_CHANGE and r.symbol == symbol and r.isin == new and d0 < r.effective_from <= d1
               for r in records)


def _reuse_between(records, symbol, old, new, d0, d1):
    """The records end old (as symbol) and start new (as symbol) between d0 and d1."""
    a0, _ = state_at(records, d0)
    a1, _ = state_at(records, d1)
    return (a0.get(old, (None,))[0] == symbol and old not in a1 and a1.get(new, (None,))[0] == symbol
            and new not in a0)


def observations_from_bhavcopies(files, symbols=None, series="EQ"):
    """(date, symbol, isin) for every row of series (files from nse_bhavcopy.load_many)."""
    want = set(s.upper() for s in symbols) if symbols else None
    return [(f.trade_date, r.symbol, r.isin) for f in files for r in f.rows
            if r.series == series and (want is None or r.symbol in want)]


def cmd_instruments_check(args):
    from nse.research.deps import bhavcopy
    try:
        records = load(args.records)
        paths = sorted(glob.glob(os.path.join(args.bhavcopy_dir, "cm*bhav.csv.zip")) +
                       glob.glob(os.path.join(args.bhavcopy_dir, "cm*bhav.csv")))
        if not paths:
            raise InstrumentError("no legacy bhavcopy files (cm*bhav.csv[.zip]) in %s" % args.bhavcopy_dir)
        files = bhavcopy.load_many(paths, bhavcopy.read_manifest(args.manifest) if args.manifest else None)
    except (OSError, ValueError) as e:
        print("instruments-check: %s" % e)
        return 2
    symbols = [x.strip().upper() for x in (args.symbols or "").split(",") if x.strip()]
    obs = observations_from_bhavcopies(files, symbols or None, args.series)
    findings = isin_consistency(records, obs)
    last = files[-1].trade_date
    names = symbols or sorted(set(s for _, s, _ in obs))
    out = {"records": args.records, "records_count": len(records),
           "records_unverified": sum(1 for r in records if not r.verified),
           "bhavcopy_files": len(files), "first_date": files[0].trade_date.isoformat(), "last_date": last.isoformat(),
           "observations": len(obs), "findings": [f.to_dict() for f in findings],
           "finding_counts": _counts(findings),
           "resolved_at_last_date": [resolve(records, s, last) for s in names],
           "note": "Records are what the cited documents say; nothing is inferred from the bhavcopy alone. "
                   "Not externally validated (B11)."}
    text = json.dumps(out, sort_keys=True, indent=1)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    return 1 if any(f.severity == marketdata.ERROR for f in findings) else 0


def _counts(findings):
    c = {}
    for f in findings:
        c[f.code] = c.get(f.code, 0) + 1
    return dict(sorted(c.items()))


def add_commands(subparsers):
    p = subparsers.add_parser("instruments-check", help="check symbol/ISIN records against bhavcopy ISINs (B11)")
    p.add_argument("--records", required=True, help="instrument records CSV (nse/research/instruments.py format)")
    p.add_argument("--bhavcopy-dir", required=True, help="folder with legacy cm*bhav.csv[.zip] files")
    p.add_argument("--manifest", help="EOD manifest.csv (provenance check for the bhavcopies)")
    p.add_argument("--symbols", help="comma-separated symbols; omitted: every symbol observed")
    p.add_argument("--series", default="EQ")
    p.add_argument("--out", help="also write the JSON here")
    p.set_defaults(func=cmd_instruments_check)
