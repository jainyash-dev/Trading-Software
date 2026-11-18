#!/usr/bin/env python3
"""Independent completeness audit of the corporate-action store (PROMPT-01, section 9).

The event table (nse/data/corporate_actions/actions.csv) is never its own proof of
completeness. This audit reconciles it against a second, independent official source, the
held NSE bhavcopies, in both directions.

Finding behind the design (2026-11-09): NSE does NOT adjust PREVCLOSE in the bhavcopy for a
split. Example: TATASTEEL ex-date 2022-07-28 (1:10) has PREVCLOSE 959.4, the unadjusted
previous close, and opens at 98.1. So a price-scale event shows as a price GAP, not as a
PREVCLOSE break. A PREVCLOSE break only appears where the symbol left the EQ series and
PREVCLOSE refers to a trade in another series.

1. Gaps: for consecutive held EQ rows of each historical NIFTY 100 member symbol
   (2016-2025), the overnight ratio last close / next open. A ratio >= 1.4 or <= 1/1.4 is a
   split-sized candidate. The cut only selects rows for review; nothing passes because of it.
   Each candidate is classified as follows:
     EXPLAINED_BY_PRICE_ACTION   a recorded price action of the instrument (any symbol of its
                                 verified rename chain) has its ex-date in (previous row, row]
     SYMBOL_NOT_COVERED          no non-empty official CA response is held for the symbol
     UNEXPLAINED_ACROSS_EQ_ABSENCE  nothing recorded, and the symbol had no EQ row on held
                                 sessions between (it traded in another series): a move over
                                 weeks, not one session; listed for review
     UNEXPLAINED                 nothing recorded on consecutive sessions: a possible missing
                                 record (or a genuine market move); never turned into an event
2. Reverse: every recorded SPLIT / BONUS / CONSOLIDATION with a ratio (same instrument and
   ex-date combined: a bonus and a split on one day multiply). Is the observed gap at
   its ex-date consistent with the ratio (within 35% of it in log terms)?
     CONSISTENT / INCONSISTENT / NOT_OBSERVABLE (no EQ rows around it).
3. PREVCLOSE breaks, listed for completeness, with the held sessions without an EQ row
   between them.

Nothing is adjusted and no event is inferred from a price move.
Output: nse/output/data_readiness/ca_completeness_2016_2025.json.
"""
import csv
import datetime
import json
import os
import sys
from decimal import Decimal

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
from nse.research import corporate_actions as ca, instruments  # noqa: E402
from nse.research.deps import bhavcopy  # noqa: E402

U = os.path.join(ROOT, "nse", "data", "universe")
CA = os.path.join(ROOT, "nse", "data", "corporate_actions")
OUT = os.path.join(ROOT, "nse", "output", "data_readiness", "ca_completeness_2016_2025.json")
D = datetime.date.fromisoformat


def members(records):
    out = set()
    for name in ("nifty100_baseline.csv", "nifty100_changes.csv"):
        with open(os.path.join(U, name), newline="", encoding="utf-8") as fh:
            out.update(r["symbol"].strip() for r in csv.DictReader(fh))
    for r in records:
        if r.record_type == instruments.SYMBOL_CHANGE and (r.symbol in out or r.new_symbol in out):
            out |= {r.symbol, r.new_symbol}
    return sorted(s for s in out if s and not s.startswith("DUMMY"))


def chains(records, syms):
    """symbol -> every symbol of its verified rename chain."""
    group = {s: {s} for s in syms}
    for r in records:
        if r.record_type == instruments.SYMBOL_CHANGE and r.verified:
            g = group.get(r.symbol, {r.symbol}) | group.get(r.new_symbol, {r.new_symbol})
            for s in g:
                group[s] = g
    return group


def main():
    records = instruments.load(os.path.join(U, "instrument_records.csv"))
    syms = members(records)
    want = set(syms)
    rows = {}

    def keep(r):
        if r.series == "EQ" and r.symbol in want:
            rows.setdefault(r.symbol, []).append((r.trade_date, r.prev_close, r.close, r.isin, r.open))
        return False
    paths = bhavcopy.archive_paths(os.path.join(ROOT, "nse", "data", "eod", "raw"))
    files = bhavcopy.load_many(paths, bhavcopy.read_manifest(os.path.join(ROOT, "nse", "data", "eod", "manifest.csv")),
                               keep)
    held = [f.trade_date for f in files]
    actions = ca.load(os.path.join(CA, "actions.csv"))
    coverage = ca.load_coverage(os.path.join(CA, "coverage.csv"))
    group = chains(records, syms)

    def events(sym, lo, hi, kinds):
        return [a for a in actions if a.symbol in group.get(sym, {sym}) and a.action in kinds and lo < a.ex_date <= hi]

    def covered(sym, lo, hi):
        return any(ca.covered(coverage, s, lo, hi) for s in group.get(sym, {sym}))

    import math
    by_sym = {s: sorted(rows.get(s, [])) for s in syms}
    gaps, gcounts, disc = [], {}, []
    for sym in syms:
        seq = by_sym[sym]
        for (d0, _, c0, i0, _o0), (d1, p1, c1, i1, o1) in zip(seq, seq[1:]):
            if p1 != c0:
                disc.append({"symbol": sym, "last_date": d0.isoformat(), "date": d1.isoformat(),
                             "last_close": str(c0), "prev_close": str(p1),
                             "held_sessions_between_without_eq_row": sum(1 for d in held if d0 < d < d1)})
            if not o1 or not c0:
                continue
            r = float(c0 / o1)
            if 1 / 1.4 < r < 1.4:
                continue
            price = events(sym, d0, d1, ca.PRICE_ACTIONS)
            absent = sum(1 for d in held if d0 < d < d1)
            cls = ("EXPLAINED_BY_PRICE_ACTION" if price else
                   "SYMBOL_NOT_COVERED" if not covered(sym, d0, d1) else
                   "UNEXPLAINED_ACROSS_EQ_ABSENCE" if absent else "UNEXPLAINED")
            gcounts[cls] = gcounts.get(cls, 0) + 1
            gaps.append({"symbol": sym, "last_date": d0.isoformat(), "date": d1.isoformat(), "last_close": str(c0),
                         "held_sessions_between_without_eq_row": absent,
                         "open": str(o1), "ratio_close_to_open": round(r, 4), "isin_changed": i0 != i1,
                         "class": cls, "events": ["%s %s %s %s:%s" % (a.symbol, a.ex_date, a.action, a.ratio_from,
                                                                       a.ratio_to) for a in price]})
    rev, rcounts, done = [], {}, set()
    scale = [a for a in actions if a.action in ("SPLIT", "BONUS", "CONSOLIDATION") and a.ratio_from and a.ratio_to]
    for a in scale:
        key = (frozenset(group.get(a.symbol, {a.symbol})), a.ex_date)
        if key in done:
            continue                                  # same instrument and ex-date: one combined event
        done.add(key)
        same = [b for b in scale if b.symbol in key[0] and b.ex_date == a.ex_date]
        seq = sorted(x for s in group.get(a.symbol, {a.symbol}) for x in by_sym.get(s, []))
        after = [x for x in seq if x[0] >= a.ex_date][:1]
        before = [x for x in seq if x[0] < a.ex_date][-1:]
        expect = 1.0
        for b in same:
            expect *= b.ratio_to / b.ratio_from            # old shares -> new shares: price falls by this
        if not after or not before or not after[0][4]:
            cls, seen = "NOT_OBSERVABLE", None
        else:
            seen = float(before[0][2] / after[0][4])
            cls = "CONSISTENT" if abs(math.log(seen / expect)) <= math.log(1.35) else "INCONSISTENT"
        rcounts[cls] = rcounts.get(cls, 0) + 1
        rev.append({"symbol": a.symbol, "ex_date": a.ex_date.isoformat(), "action": "+".join(b.action for b in same),
                    "expected_ratio": round(expect, 4), "observed_close_to_open": round(seen, 4) if seen else None,
                    "class": cls})
    out = {"generated_on": datetime.date.today().isoformat(), "member_symbols": len(syms),
           "symbols_with_eq_rows": sum(1 for s in syms if rows.get(s)), "held_files": len(files),
           "actions_file_sha256": __import__("hashlib").sha256(open(os.path.join(CA, "actions.csv"), "rb").read()).hexdigest(),
           "loader_version": bhavcopy.LOADER_VERSION,
           "gaps": {"counts": gcounts, "rows": gaps},
           "recorded_scale_actions": {"counts": rcounts, "rows": rev},
           "prevclose_breaks": {"count": len(disc), "rows": disc},
           "method": __doc__}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True, default=str)
    print(json.dumps({"gaps": gcounts, "recorded_scale_actions": rcounts, "prevclose_breaks": len(disc),
                      "symbols": len(syms)}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
