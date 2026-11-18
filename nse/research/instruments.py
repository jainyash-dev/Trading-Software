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

from nse.research import marketdata, models as m

COLUMNS = ("record_type", "symbol", "new_symbol", "isin", "series", "effective_from", "effective_to", "source",
           "source_file", "source_sha256", "recorded_on", "notes")
LISTING, SYMBOL_CHANGE, DELISTING, MERGER, ISIN_CHANGE = "LISTING", "SYMBOL_CHANGE", "DELISTING", "MERGER", "ISIN_CHANGE"
RECORD_TYPES = (LISTING, SYMBOL_CHANGE, DELISTING, MERGER, ISIN_CHANGE)
_ORDER = {LISTING: 0, ISIN_CHANGE: 1, SYMBOL_CHANGE: 2, MERGER: 3, DELISTING: 4}   # same-day order
_ISIN = re.compile(r"IN[A-Z0-9]{10}\Z")          # as nse_bhavcopy checks it

RESOLVED = "RESOLVED"
UNKNOWN_INSTRUMENT = "UNKNOWN_INSTRUMENT"
UNVERIFIED = "UNVERIFIED"
ISIN_CHANGED_WITHOUT_RECORD = "ISIN_CHANGED_WITHOUT_RECORD"
SYMBOL_REUSED_FOR_DIFFERENT_ISIN = "SYMBOL_REUSED_FOR_DIFFERENT_ISIN"
SYMBOL_CHANGED_WITHOUT_RECORD = "SYMBOL_CHANGED_WITHOUT_RECORD"
ISIN_RECORD_MISMATCH = "ISIN_RECORD_MISMATCH"
SYMBOL_HISTORY_SPLIT = "SYMBOL_HISTORY_SPLIT"


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
    source_file: str = ""       # as recorded on the row; the evidence the hash check read
    source_sha256: str = ""

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
            verified = m.source_verified(path, r["source"], r["source_file"], r["source_sha256"])
            out.append(Record(kind, sym, new, isin, r["series"].strip() or "EQ", start, end, verified,
                              r["source"].strip(), i, r["source_file"].strip(), r["source_sha256"].strip().lower()))
    return sorted(out, key=_key)


# --- rename policy (D51; P0 review REV-1) -------------------------------------------------
# Two tickers are the same instrument only through a SYMBOL_CHANGE record whose cited source
# hashes to its recorded SHA-256, and only from that record's effective date. A similar name,
# a shared promoter, a later business relationship or an unverified row never links them.
RENAME_VERIFIED = "VERIFIED_DATED_RENAME"
RENAME_UNVERIFIED = "UNVERIFIED_NOT_USED"


def rename_links(records):
    """The auditable rename table: one row per SYMBOL_CHANGE record, verified or not."""
    return [{"previous_symbol": r.symbol, "new_symbol": r.new_symbol, "isin": r.isin,
             "effective_from": r.effective_from.isoformat(), "evidence": r.source,
             "evidence_file": r.source_file, "evidence_sha256": r.source_sha256, "record_line": r.line,
             "status": RENAME_VERIFIED if r.verified else RENAME_UNVERIFIED}
            for r in records if r.record_type == SYMBOL_CHANGE]


def verified_rename_into(records, symbol, after, on_or_before):
    """The one VERIFIED SYMBOL_CHANGE record into `symbol` whose effective date d satisfies
    after < d <= on_or_before, or None. Two such records are ambiguous and give None."""
    symbol = symbol.strip().upper()
    hits = [r for r in records if r.record_type == SYMBOL_CHANGE and r.verified and r.new_symbol == symbol
            and after < r.effective_from <= on_or_before]
    return hits[0] if len(hits) == 1 else None


def verified_rename_names(records, symbol):
    """`symbol` and every ticker joined to it through VERIFIED SYMBOL_CHANGE records that
    share one ISIN along the chain (both directions, cycle-safe), sorted. An unverified
    record, or a record whose ISIN differs from the chain's, ends the walk."""
    symbol = symbol.strip().upper()
    changes = [r for r in records if r.record_type == SYMBOL_CHANGE and r.verified]
    # review L-1: renames under two different ISINs touching one ticker are ambiguous; no join
    if len(set(r.isin for r in changes if symbol in (r.symbol, r.new_symbol))) > 1:
        return [symbol]
    seen, todo, isins = {symbol}, [symbol], set()
    while todo:
        s = todo.pop()
        for r in changes:
            if s not in (r.symbol, r.new_symbol) or (isins and r.isin not in isins):
                continue
            isins.add(r.isin)
            for other in (r.symbol, r.new_symbol):
                if other not in seen:
                    seen.add(other)
                    todo.append(other)
    return sorted(seen)


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


@dataclass(frozen=True)
class Segment:
    """One symbol's part of an instrument's history: trade dates start..end inclusive (None: open)."""
    symbol: str
    start: Optional[datetime.date]
    end: Optional[datetime.date]
    isin: str = ""
    record_line: int = 0


def lineage(records, symbol, files, series="EQ"):
    """(segments oldest first, reasons). D51 (owner 2026-11-09): a renamed company's history
    is connected ONLY through verified ISIN continuity and effective dates. Walking back from
    `symbol`, a predecessor is joined only when there is a VERIFIED SYMBOL_CHANGE record
    old -> new with ISIN I effective D, and in the files: every row of the new symbol from
    D carries I, every row of the old symbol carries I, the old symbol has no row on or
    after D and the new symbol none before D. A ticker or a name alone never joins two
    companies. When any check fails the walk stops there and `reasons` says why; the
    unjoined history then keeps its SYMBOL_HISTORY_SPLIT restriction (DATA_INSUFFICIENT).

    Point in time (QA 2026-11-09): only evidence dated BEFORE the change can refuse the join.
    Evidence dated on or after it (the old symbol still trading the same ISIN, or the new
    symbol's first row under another ISIN) never undoes the join retroactively; it is
    returned in `conflicts` as (date, reason) and becomes a dated ERROR, so scans from that
    date are DATA_INSUFFICIENT and earlier ones are unchanged (D44). A later ISIN change of
    the new symbol is a separate dated event (isin_consistency), and rows of the old ticker
    under a different ISIN after the change are another instrument and are never joined.
    Returns (segments, reasons, conflicts)."""
    sym = symbol.strip().upper()
    obs = {}
    for d, s_, i in observations_from_bhavcopies(files, None, series):
        obs.setdefault(s_, []).append((d, i))
    segments, reasons, conflicts, current, seen = [Segment(sym, None, None)], [], [], sym, {sym}
    while True:
        changes = [r for r in (records or []) if r.record_type == SYMBOL_CHANGE and r.new_symbol == current]
        if not changes:
            break
        if len(changes) > 1:
            reasons.append("%d SYMBOL_CHANGE records into %s: ambiguous, not joined" % (len(changes), current))
            break
        r = changes[0]
        old, eff, isin = r.symbol, r.effective_from, r.isin
        head = segments[0]                                  # the current symbol's own part so far
        new_rows = [(d, i) for d, i in obs.get(current, []) if head.end is None or d <= head.end]
        before = [(d, i) for d, i in obs.get(old, []) if d < eff]
        why = None
        if not r.verified:
            why = "records line %d is not verified (D31)" % r.line
        elif old in seen:
            why = "SYMBOL_CHANGE cycle at %s" % old
        elif not before:
            why = "no rows of %s before the change date %s" % (old, eff)
        elif any(i != isin for _, i in before):
            why = "%s rows before %s carry an ISIN other than %s" % (old, eff, isin)
        elif any(d < eff for d, _ in new_rows):
            why = "%s has rows before the change date %s" % (current, eff)
        if why:
            reasons.append("%s -> %s not joined: %s" % (old, current, why))
            break
        overlap = sorted(d for d, i in obs.get(old, []) if d >= eff and i == isin)
        if overlap:
            conflicts.append((overlap[0], "%s still trades %s on %s, on or after its change to %s (%s)"
                              % (old, isin, overlap[0], current, eff)))
        first_new = sorted((d, i) for d, i in new_rows if d >= eff)[:1]
        if first_new and first_new[0][1] != isin:
            conflicts.append((first_new[0][0], "%s's first row after the change (%s) carries %s, not %s"
                              % (current, first_new[0][0], first_new[0][1], isin)))
        segments[0] = Segment(head.symbol, eff, head.end, isin, r.line)
        segments.insert(0, Segment(old, None, eff - datetime.timedelta(days=1), isin, r.line))
        seen.add(old)
        current = old
    return segments, reasons, conflicts


def join_files(files, segments, symbol):
    """Copies of the loaded files in which each predecessor segment's rows are relabelled as
    `symbol` (prices, ISIN and provenance unchanged), so one series spans the rename. The
    loaded files themselves are never modified."""
    import copy
    import dataclasses
    if len(segments) == 1:
        return files
    out = []
    for f in files:
        rows = []
        for r in f.rows:
            for seg in segments[:-1]:
                if r.symbol == seg.symbol and (seg.end is None or f.trade_date <= seg.end):
                    r = dataclasses.replace(r, symbol=symbol)
                    break
            rows.append(r)
        g = copy.copy(f)
        g.rows = rows
        out.append(g)
    return out


def apply_to_input(inp, files, records=None, series="EQ", segments=None):
    """Identity check for one symbol's bhavcopy input (ED-21), in place; returns inp.

    The symbol's own (date, symbol, ISIN) observations go through isin_consistency, with
    the records when given and with none otherwise. Every finding is dated, so an ERROR
    (an ISIN change no record explains, or an ISIN the records contradict) stops the symbol
    at G0 (DATA_INSUFFICIENT) from that trade date on and leaves earlier scans unchanged
    (D44). Unless every observation resolves through verified records, the input carries
    IDENTITY_UNVERIFIED: unknown identity is never reported as checked.

    The symbol's ISINs are also looked up under every other symbol in the files. When one
    of them traded under another symbol before this symbol's first row (a rename or a
    reused ISIN), this symbol's series starts mid-history: price action before the change
    (supply above price, breaches) is not in it. That is a dated ERROR, SYMBOL_HISTORY_SPLIT,
    whether or not a record explains the rename, because the series is assembled by symbol
    and is not joined across the change (contrarian review 2026-11-09; TD-13)."""
    sym = inp.symbol.strip().upper()
    segments = segments or [Segment(sym, None, None)]
    names = set(sg.symbol for sg in segments)
    within = lambda d, sg: (sg.start is None or d >= sg.start) and (sg.end is None or d <= sg.end)
    allobs = observations_from_bhavcopies(files, None, series)
    obs = [(d, s, i) for d, s, i in allobs for sg in segments if s == sg.symbol and within(d, sg)]
    mine = set(i for _, _, i in obs)
    shared = [(d, s, i) for d, s, i in allobs if i in mine and s not in names]
    found = [f for f in isin_consistency(records or [], obs + shared) if f.symbol in names]
    if obs:
        first = min(d for d, _, _ in obs)
        before = sorted((d, s, i) for d, s, i in shared if d < first)
        if before:
            d0, s0, i0 = before[-1]
            found.append(_finding(SYMBOL_HISTORY_SPLIT, marketdata.ERROR, sym,
                                  "ISIN %s traded as %s up to %s before %s's first row on %s: the series starts "
                                  "mid-history and is not joined across the change" % (i0, s0, d0, sym, first),
                                  first, extra={"isin": i0, "other_symbol": s0, "other_last_date": d0.isoformat()}))
    # In the scan path these mean the series is not one known instrument (QA 2026-11-09):
    # a symbol reused for another ISIN joins two instruments' prices (successors are distinct),
    # and a symbol the SUPPLIED records do not cover is unknown identity. Both become dated
    # ERRORs, so G0 is DATA_INSUFFICIENT from that date and earlier scans are unchanged.
    escalate = {SYMBOL_REUSED_FOR_DIFFERENT_ISIN} | ({UNKNOWN_INSTRUMENT} if records is not None else set())
    found = [_finding(f.code, marketdata.ERROR, f.symbol, f.detail, f.date, f.verified, f.extra)
             if f.code in escalate else f for f in found]
    inp.findings.extend(found)
    # Prefix invariance: the limitation and provenance depend on the records file only, never
    # on market data after any as_of; dated findings carry everything else (findings_at).
    mine_records = [r for r in (records or []) if r.symbol == sym or r.new_symbol == sym]
    records_verified = records is not None and bool(mine_records) and all(r.verified for r in mine_records)
    if not records_verified and m.IDENTITY_UNVERIFIED not in inp.limitations:
        inp.limitations.append(m.IDENTITY_UNVERIFIED)
    inp.provenance["identity"] = {"records_supplied": records is not None, "symbol_records": len(mine_records),
                                  "records_verified": records_verified,
                                  "lineage": [{"symbol": sg.symbol, "from": sg.start.isoformat() if sg.start else None,
                                               "to": sg.end.isoformat() if sg.end else None, "isin": sg.isin or None,
                                               "record_line": sg.record_line or None} for sg in segments],
                                  "note": "per-date identity findings are in findings (dated)"}
    return inp


def observations_from_bhavcopies(files, symbols=None, series="EQ"):
    """(date, symbol, isin) for every row of series (files from nse_bhavcopy.load_many)."""
    want = set(s.upper() for s in symbols) if symbols else None
    return [(f.trade_date, r.symbol, r.isin) for f in files for r in f.rows
            if r.series == series and (want is None or r.symbol in want)]


def cmd_instruments_check(args):
    from nse.research.deps import bhavcopy
    try:
        records = load(args.records)
        paths = sorted(set(bhavcopy.archive_paths(args.bhavcopy_dir)) |
                       set(glob.glob(os.path.join(args.bhavcopy_dir, "cm*bhav.csv"))))
        if not paths:
            raise InstrumentError("no bhavcopy files (legacy cm*bhav.csv[.zip] or UDiFF archives) in %s" % args.bhavcopy_dir)
        symbols = [x.strip().upper() for x in (args.symbols or "").split(",") if x.strip()]
        want, obs = set(symbols), []

        def keep(r):                                  # observations only; no row kept in memory (ED-41)
            if r.series == args.series and (not want or r.symbol in want):
                obs.append((r.trade_date, r.symbol, r.isin))
            return False
        files = bhavcopy.load_many(paths, bhavcopy.read_manifest(args.manifest) if args.manifest else None, keep)
    except (OSError, ValueError) as e:
        print("instruments-check: %s" % e)
        return 2
    obs.sort(key=lambda o: o[0])                      # date order, file order within a date (stable)
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
    p.add_argument("--bhavcopy-dir", required=True, help="folder with bhavcopy files (legacy or UDiFF)")
    p.add_argument("--manifest", help="EOD manifest.csv (provenance check for the bhavcopies)")
    p.add_argument("--symbols", help="comma-separated symbols; omitted: every symbol observed")
    p.add_argument("--series", default="EQ")
    p.add_argument("--out", help="also write the JSON here")
    p.set_defaults(func=cmd_instruments_check)
