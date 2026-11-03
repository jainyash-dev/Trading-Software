"""Corporate-action records and their effect on a scan (B7). Interface only: no adjustment
method is chosen, because none is approved.

File format (CSV, exact header):
    symbol,ex_date,action,ratio_from,ratio_to,source,source_file,source_sha256,recorded_on,notes
action is one of PRICE_ACTIONS (they change the price scale) or DIVIDEND (recorded, not
treated as a price-scale event here). ratio_from:ratio_to is the share ratio, e.g. a 1:5
split is 1,5; a 1:1 bonus is 1,2 (one held becomes two). A row without source and a 64-hex
source_sha256 is UNVERIFIED.

Effect on a scan (scanner.ScanConfig.corporate_actions):
  - a price-scale action of the symbol with ex_date inside the replayed history and on or
    before as_of means the unadjusted series mixes two price scales: zones, breaches and
    trends across it are unreliable. G0 becomes MANUAL (CORPORATE_ACTION_IN_HISTORY) and
    the action is listed. Nothing is adjusted.
  - actions dated after as_of are ignored (point in time).
  - without a file, every result keeps CORPORATE_ACTIONS_UNVERIFIED, as before.

Independent of any file, prevclose_discontinuities() compares each bhavcopy row's PREVCLOSE
with the symbol's last close in the files held. NSE publishes PREVCLOSE with each row; a
difference (exact Decimal comparison, no tolerance) means the exchange's reference price
changed between sessions, as it does on the ex-date of a split or bonus. It is a detector,
not an explanation: the event type is never inferred. In the 61 official Q1 2022 files it
fires once in 99,288 consecutive pairs (SETFGOLD, 2022-01-06, ratio about 0.0101), which is a
local finding, not a verified corporate action.
"""

import csv
import datetime
import re
from dataclasses import dataclass

COLUMNS = ("symbol", "ex_date", "action", "ratio_from", "ratio_to", "source", "source_file", "source_sha256",
           "recorded_on", "notes")
PRICE_ACTIONS = ("SPLIT", "BONUS", "RIGHTS", "CONSOLIDATION", "DEMERGER", "MERGER")
ACTIONS = PRICE_ACTIONS + ("DIVIDEND",)
CORPORATE_ACTION_IN_HISTORY = "CORPORATE_ACTION_IN_HISTORY"
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class CorporateActionError(ValueError):
    pass


@dataclass(frozen=True)
class Action:
    symbol: str
    ex_date: datetime.date
    action: str
    ratio_from: float
    ratio_to: float
    verified: bool
    source: str

    def to_dict(self):
        return {"symbol": self.symbol, "ex_date": self.ex_date.isoformat(), "action": self.action,
                "ratio": "%g:%g" % (self.ratio_from, self.ratio_to), "verified": self.verified, "source": self.source}


def load(path):
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise CorporateActionError("%s: header must be exactly %s" % (path, ",".join(COLUMNS)))
        out = []
        for i, r in enumerate(reader, 2):
            where = "%s line %d" % (path, i)
            try:
                ex = datetime.date.fromisoformat(r["ex_date"].strip())
            except ValueError:
                raise CorporateActionError("%s: ex_date must be YYYY-MM-DD" % where)
            if r["action"] not in ACTIONS:
                raise CorporateActionError("%s: action must be one of %s" % (where, ", ".join(ACTIONS)))
            try:
                a, b = float(r["ratio_from"] or 0), float(r["ratio_to"] or 0)
            except ValueError:
                raise CorporateActionError("%s: ratios must be numbers" % where)
            if r["action"] in ("SPLIT", "BONUS", "CONSOLIDATION") and (a <= 0 or b <= 0):
                raise CorporateActionError("%s: %s needs a positive ratio" % (where, r["action"]))
            verified = bool(r["source"].strip()) and bool(_SHA.match(r["source_sha256"].strip().lower()))
            out.append(Action(r["symbol"].strip().upper(), ex, r["action"], a, b, verified, r["source"].strip()))
    return sorted(out, key=lambda x: (x.symbol, x.ex_date, x.action))


def in_history(actions, symbol, first_date, as_of_date):
    """Price-scale actions of symbol with first_date < ex_date <= as_of_date (point in time)."""
    return [a for a in actions if a.symbol == symbol and a.action in PRICE_ACTIONS
            and first_date < a.ex_date <= as_of_date]


PRICE_DISCONTINUITY_IN_HISTORY = "PRICE_DISCONTINUITY_IN_HISTORY"


def prevclose_discontinuities(files, symbol, series="EQ"):
    """[{date, last_close, prev_close, ratio, last_file, file}] where a row's PREVCLOSE differs
    from the symbol's last close in the files given (files in date order, nse_bhavcopy)."""
    out = []
    last = None
    for f in files:
        hit = [r for r in f.rows if r.symbol == symbol and r.series == series]
        if not hit:
            continue
        r = hit[0]
        if last is not None and r.prev_close != last[0]:
            out.append({"date": f.trade_date, "last_close": str(last[0]), "prev_close": str(r.prev_close),
                        "ratio": round(float(r.prev_close / last[0]), 6) if last[0] else None,
                        "last_file": last[1], "file": f.source.file_name})
        last = (r.close, f.source.file_name)
    return out
