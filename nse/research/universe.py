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
import re
from dataclasses import dataclass
from typing import List, Optional

from nse.research import models as m

COLUMNS = ("symbol", "series", "isin", "index_name", "effective_from", "effective_to", "source",
           "source_file", "source_sha256", "recorded_on", "notes")
_SHA = re.compile(r"[0-9a-f]{64}\Z")


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

    def limitations(self, as_of_date):
        if self.adhoc or not all(r.verified for r in self.members(as_of_date)):
            return [m.UNIVERSE_UNVERIFIED]
        return []


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
            verified = bool(r["source"].strip()) and bool(_SHA.match(r["source_sha256"].strip().lower()))
            rows.append(Membership(r["symbol"].strip().upper(), r["series"].strip() or "EQ", start, end,
                                   verified, r["source"].strip()))
    return Universe(name or path, rows)
