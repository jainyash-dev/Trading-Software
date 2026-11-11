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

Policy (D50, owner 2026-11-09): raw, unadjusted OHLC is canonical. Verified events and their
terms are stored separately (this file format). Nothing here or anywhere in the pipeline
adjusts a price; an adjusted series, if one is ever built, must be separate, traceable and
follow a documented adjustment policy, and unverified ratios are never used.

from_nse_json() converts a saved response of NSE's corporate-actions page (fields symbol,
series, isin, exDate, subject, ...) into rows of this format. Terms are read from the
official subject text by exact patterns only, part by part for combined subjects ("Bonus
1:1 / Dividend - Rs 29"). A subject with any price-type part that does not match a pattern is
returned as UNPARSED and stored as one UNPARSED_PRICE_EVENT (a price action: G0 MANUAL when
it falls inside a history); its terms are never guessed.
"""

import csv
import datetime
import os
import re
from dataclasses import dataclass

from nse.research import models as m

COLUMNS = ("symbol", "ex_date", "action", "ratio_from", "ratio_to", "source", "source_file", "source_sha256",
           "recorded_on", "notes")
PRICE_ACTIONS = ("SPLIT", "BONUS", "RIGHTS", "CONSOLIDATION", "DEMERGER", "MERGER",
                 "UNPARSED_PRICE_EVENT")    # an official price-type event whose terms are not read (D56): MANUAL
ACTIONS = PRICE_ACTIONS + ("DIVIDEND",)
CORPORATE_ACTION_IN_HISTORY = "CORPORATE_ACTION_IN_HISTORY"


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
            verified = m.source_verified(path, r["source"], r["source_file"], r["source_sha256"])
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
            # weekdays strictly between the two held files: sessions or holidays the files do not
            # show. With any, the comparison may span missing data, not a price-scale event.
            between = sum(1 for k in range(1, (f.trade_date - last[2]).days)
                          if (last[2] + datetime.timedelta(days=k)).weekday() < 5)
            out.append({"date": f.trade_date, "last_close": str(last[0]), "prev_close": str(r.prev_close),
                        "ratio": round(float(r.prev_close / last[0]), 6) if last[0] else None,
                        "last_file": last[1], "file": f.source.file_name, "weekdays_between": between,
                        "last_date": last[2]})
        last = (r.close, f.source.file_name, f.trade_date)
    return out


_RS = r"R[se]\.?\s*([\d.]+)\s*(?:/-)?"                 # "Rs 10/-", "Re 1", "Rs10", "Rs. 2"
_BONUS = re.compile(r"^\s*Bonus\s+(\d+)\s*:\s*(\d+)\s*$", re.I)
_FV = re.compile(r"^\s*Face\s+Value\s+(Split|Consolidation)(?:\s*\([^)]*\))?\s*-?\s*From\s+" + _RS +
                 r"(?:\s*Per\s+Share)?\s+To\s+" + _RS + r"(?:\s*Per\s+Share)?\s*$", re.I)
_RIGHTS = re.compile(r"^\s*Rights\s+(\d+)\s*:\s*(\d+)\s*@\s*Prem(?:ium)?\s+" + _RS + r"(?:\s*Per\s+Share)?\s*$", re.I)
_DEMERGER = re.compile(r"^\s*Demerger\s*$", re.I)
_DIVIDEND = re.compile(r"^\s*(?:Annual\s+General\s+Meeting\s*)?(?:Interim\s+|Final\s+|Special\s+)?Dividend\b", re.I)
_FV_ABBR = re.compile(r"^\s*Fv\s+Splt\s+Frm\s+" + _RS + r"\s+To\s+" + _RS + r"\s*$", re.I)  # "Fv Splt Frm Rs 10 To Re 1"
_PRICE_WORDS = re.compile(r"bonus|split|splt|sub-?division|consolidat|rights|demerg|merg|amalgamat|arrang|"
                          r"capital\s+reduction|reduction\s+of\s+capital|\bfv\b|face\s*value|sub\s*-?\s*div|divest", re.I)
_DIVIDEND_WORDS = re.compile(r"\bdiv\b|dividend|divdend|dividned|divided", re.I)   # "Int Div", "Interimdividend"
# the only subjects read as "no price event"; anything else unrecognised is UNPARSED (fail closed)
_NON_PRICE = re.compile(r"^\s*(?:an+u(?:al|la|l)\s+general\s+meeting|extra-?\s*ordinary\s+general\s+meeting|"
                        r"buy\s*-?\s*back(?:\s+of\s+shares?)?|change\s+in\s+registrar\s+and\s+transfer\s+agent)"
                        r"\s*(?:\([^)]*\))?\s*$", re.I)
_PARTS = re.compile(r"\s*/(?!-)\s*")                 # "A / B", never the "/-" of "Rs 10/-"


def _part_row(part):
    """(action, ratio_from, ratio_to) for one subject part, or (None, reason)."""
    m_ = _BONUS.match(part)
    if m_:                                         # "Bonus a:b": a new shares for every b held
        a, b = int(m_.group(1)), int(m_.group(2))
        if a > 0 and b > 0:
            return "BONUS", b, a + b
    m_ = _FV.match(part)                           # whole part: a combined event is never half-read
    if m_:
        old, new = float(m_.group(2)), float(m_.group(3))
        if old > 0 and new > 0:
            kind = "SPLIT" if m_.group(1).lower() == "split" else "CONSOLIDATION"
            r = old / new if kind == "SPLIT" else new / old
            if abs(r - round(r)) < 1e-9 and round(r) >= 1:
                return (kind, 1, round(r)) if kind == "SPLIT" else (kind, round(r), 1)
    m_ = _FV_ABBR.match(part)
    if m_:
        old, new = float(m_.group(1)), float(m_.group(2))
        if old > new > 0 and abs(old / new - round(old / new)) < 1e-9:
            return "SPLIT", 1, round(old / new)
    if _RIGHTS.match(part):
        return "RIGHTS", 0, 0                       # terms kept in notes; not a price-scale ratio
    if _DEMERGER.match(part):
        return "DEMERGER", 0, 0
    if _PRICE_WORDS.search(part):
        return None, "UNPARSED_PRICE_ACTION"
    if _DIVIDEND.match(part) or _DIVIDEND_WORDS.search(part):
        return "DIVIDEND", 0, 0
    if _NON_PRICE.match(part):
        return None, "NOT_A_PRICE_ACTION"
    return None, "UNPARSED_PRICE_ACTION"          # unrecognised: never silently "no event" (D56)


def _subject_rows(subject):
    """[(action, a, b)] for a subject, its parts read one by one; [] when nothing is a price or
    dividend event; None when any price-type part cannot be read (the whole subject is then one
    UNPARSED_PRICE_EVENT: nothing is half-read)."""
    out = []
    for part in [p for p in _PARTS.split(subject) if p.strip()]:
        got = _part_row(part)
        if got[0] is None:
            if got[1] == "UNPARSED_PRICE_ACTION":
                return None
            continue
        out.append(got)
    return out


def from_nse_json(json_path, out_csv_dir, recorded_on, symbol=None):
    """(rows, unparsed, skipped) for a saved NSE corporate-actions response. rows use COLUMNS,
    with source_file relative to out_csv_dir (where the CSV will be written) so
    models.source_verified can hash it. Only EQ rows; the subject is kept verbatim in notes."""
    import hashlib
    import json
    import os
    with open(json_path, "rb") as fh:
        data = fh.read()
    sha = hashlib.sha256(data).hexdigest()
    rel = os.path.relpath(json_path, out_csv_dir)
    rows, unparsed, skipped = [], [], []
    for r in json.loads(data.decode("utf-8")):
        if r.get("series") != "EQ" or (symbol and r.get("symbol") != symbol):
            continue
        subject = " ".join((r.get("subject") or "").split())
        try:
            ex = datetime.datetime.strptime(r["exDate"], "%d-%b-%Y").date()
        except (KeyError, ValueError):
            unparsed.append({"symbol": r.get("symbol"), "ex_date": r.get("exDate"), "subject": subject,
                             "reason": "ex-date not DD-Mon-YYYY"})
            continue
        got = _subject_rows(subject)
        if got is None:
            unparsed.append({"symbol": r["symbol"], "ex_date": ex.isoformat(), "subject": subject,
                             "reason": "UNPARSED_PRICE_ACTION"})
            got = [("UNPARSED_PRICE_EVENT", 0, 0)]       # kept as a price-type event: G0 MANUAL, never silent
        elif not got:
            skipped.append({"symbol": r["symbol"], "ex_date": ex.isoformat(), "subject": subject,
                            "reason": "NOT_A_PRICE_ACTION"})
            continue
        for action, a, b in got:
            rows.append({"symbol": r["symbol"], "ex_date": ex.isoformat(), "action": action, "ratio_from": str(a),
                         "ratio_to": str(b), "source": "NSE corporate actions (saved API response)",
                         "source_file": rel, "source_sha256": sha, "recorded_on": recorded_on,
                         "notes": "subject: %s; isin %s; record date %s"
                                  % (subject, r.get("isin", ""), r.get("recDate", ""))})
    return rows, unparsed, skipped


COVERAGE_COLUMNS = ("symbol", "from_date", "to_date", "source_file", "source_sha256", "rows", "retrieved_on", "notes")


EMPTY_RESPONSE = "EMPTY_RESPONSE_COMPLETENESS_UNKNOWN"
MISSING_COVERAGE = "MISSING_COVERAGE"
UNPARSED_EVENT = "UNPARSED_EVENT"
COVERED_WITH_VERIFIED_EVENTS = "COVERED_WITH_VERIFIED_EVENTS"
RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED = "RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED"


def empty_api_body(text):
    """True when the saved response is an empty JSON list. That is not proof of no events."""
    return (text or "").strip() == "[]"


def response_status(body, parsed_price_events=0, unparsed_price_events=0):
    """Classify one saved response. An empty list is never 'no events'.

    A non-empty response is not proof that the API returned every event. Parsed
    price events are recorded. They do not by themselves authorise a price adjustment.
    """
    if body is None:
        return MISSING_COVERAGE
    if empty_api_body(body):
        return EMPTY_RESPONSE
    if unparsed_price_events:
        return UNPARSED_EVENT
    if parsed_price_events:
        return COVERED_WITH_VERIFIED_EVENTS
    return RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED


def _source_text(csv_path, source_file):
    path = (source_file or "").strip()
    if not path:
        return None
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.abspath(csv_path)), path)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def load_coverage(path):
    """{symbol: [(from_date, to_date)]} of hash-verified responses that are not an empty list.

    A window counts only when its source file is held with the recorded SHA-256.
    A body of `[]` is kept on disk and is not a window: the API's completeness is
    not established, so an empty list is not evidence that nothing happened (D56).
    """
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != COVERAGE_COLUMNS:
            raise CorporateActionError("%s: header must be exactly %s" % (path, ",".join(COVERAGE_COLUMNS)))
        for r in reader:
            if not m.source_verified(path, "NSE corporate actions", r["source_file"], r["source_sha256"]):
                continue
            body = _source_text(path, r["source_file"])
            if body is None or empty_api_body(body):
                continue
            out.setdefault(r["symbol"].strip().upper(), []).append(
                (datetime.date.fromisoformat(r["from_date"]), datetime.date.fromisoformat(r["to_date"])))
    return out


def covered(coverage, symbol, start, end):
    """True when one verified window of symbol contains start..end."""
    return any(a <= start and end <= b for a, b in (coverage or {}).get(symbol, []))


def write(rows, path):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(COLUMNS), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return path
