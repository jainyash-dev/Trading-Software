"""Universe membership (D1: Nifty 100; B11: point-in-time membership).

No constituent list is built in. A universe file records, per symbol, the period it was
a member and the official document that says so:

    symbol,series,isin,index_name,effective_from,effective_to,source,source_file,source_sha256,recorded_on,notes

effective_to may be empty (still a member). source must name the NSE Indices document;
source_sha256 is the hash of the local copy (D31). A row without both is UNVERIFIED.
members(as_of) uses only rows in force at as_of, so a historical scan never uses later
constituents. A symbol list typed on the command line is an ad-hoc universe: every
result then carries UNIVERSE_UNVERIFIED.
"""

import csv
import datetime
from dataclasses import dataclass
from typing import List, Optional

from nse.research import models as m

COLUMNS = ("symbol", "series", "isin", "index_name", "effective_from", "effective_to", "source",
           "source_file", "source_sha256", "recorded_on", "notes")

# D59: membership-based Nifty 100 research uses this date onward. Candles before it may
# warm indicators. They are not a point-in-time Nifty 100 universe, and no later list is
# used to fill them in.
PROVISIONAL_MEMBERSHIP_START = datetime.date(2020, 12, 31)


class UniverseError(ValueError):
    pass


@dataclass(frozen=True)
class Membership:
    symbol: str
    series: str
    effective_from: datetime.date
    effective_to: Optional[datetime.date]
    verified: bool
    source: str
    isin: str = ""            # as recorded in the universe file; "" for ad-hoc rows


@dataclass
class Universe:
    name: str
    rows: List[Membership]
    adhoc: bool = False

    def members(self, as_of_date):
        out = {}
        for r in self.rows:
            if r.effective_from <= as_of_date and (r.effective_to is None or as_of_date <= r.effective_to):
                out[r.symbol] = r
        return [out[k] for k in sorted(out)]

    def balance(self, as_of_date, expected):
        """(member count on as_of_date, whether it equals expected), e.g. expected=100 for
        Nifty 100 (D1). Reports only; members() and limitations() are unchanged."""
        n = len(self.members(as_of_date))
        return n, n == expected

    def limitations(self, as_of_date):
        out = []
        # D59 is a research-window label, not a certification. An ad-hoc symbol list is
        # already UNIVERSE_UNVERIFIED and is not a Nifty 100 membership study.
        if not self.adhoc and as_of_date < PROVISIONAL_MEMBERSHIP_START:
            out.append(m.MEMBERSHIP_BEFORE_PROVISIONAL_WINDOW)
        members = self.members(as_of_date)
        # no member on the date (e.g. before the file's first period) is unknown membership,
        # never a verified universe (PROMPT-01 audit: all([]) was True)
        if self.adhoc or not members or not all(r.verified for r in members):
            out.append(m.UNIVERSE_UNVERIFIED)
        return out


def adhoc(symbols, series="EQ"):
    syms = sorted(set(s.strip().upper() for s in symbols if s.strip()))
    if not syms:
        raise UniverseError("no symbols given")
    return Universe("ADHOC", [Membership(s, series, datetime.date.min, None, False, "command line") for s in syms],
                    adhoc=True)


def load(path, name=None):
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise UniverseError("%s: header must be exactly %s" % (path, ",".join(COLUMNS)))
        rows = []
        for i, r in enumerate(reader, 2):
            try:
                start = datetime.date.fromisoformat(r["effective_from"])
                end = datetime.date.fromisoformat(r["effective_to"]) if r["effective_to"].strip() else None
            except ValueError:
                raise UniverseError("%s line %d: dates must be YYYY-MM-DD" % (path, i))
            if not r["symbol"].strip():
                raise UniverseError("%s line %d: empty symbol" % (path, i))
            if end is not None and end < start:
                raise UniverseError("%s line %d: effective_to before effective_from" % (path, i))
            verified = m.source_verified(path, r["source"], r["source_file"], r["source_sha256"])
            rows.append(Membership(r["symbol"].strip().upper(), r["series"].strip() or "EQ", start, end,
                                   verified, r["source"].strip(), r["isin"].strip().upper()))
    # one membership period per symbol at a time: overlapping rows would let the last one win
    # silently (members() keeps one row per symbol), so they are refused
    by_symbol = {}
    for r in rows:
        by_symbol.setdefault(r.symbol, []).append(r)
    for sym, rs in sorted(by_symbol.items()):
        rs = sorted(rs, key=lambda r: r.effective_from)
        for a, b in zip(rs, rs[1:]):
            if a.effective_to is None or b.effective_from <= a.effective_to:
                raise UniverseError("%s: %s has overlapping membership periods (from %s and from %s)"
                                    % (path, sym, a.effective_from, b.effective_from))
    return Universe(name or path, rows)
