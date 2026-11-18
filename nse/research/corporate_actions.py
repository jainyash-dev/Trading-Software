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
import hashlib
import json
import os
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction

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


PRICE_SCALE_GAP = "PRICE_SCALE_GAP"
# R-12: a step whose whole session range lies more than this far from the last close is a
# possible price-scale break. A screen only: it names no event and no ratio.
SCALE_GAP_BAND = Decimal("0.15")


def price_scale_gap(prior_close, low, high, band=SCALE_GAP_BAND):
    """True when [low, high] lies wholly outside (1 - band, 1 / (1 - band)) x prior_close."""
    prior_close, low, high = Decimal(str(prior_close)), Decimal(str(low)), Decimal(str(high))
    if prior_close <= 0:
        return True
    return high < prior_close * (1 - band) or low > prior_close / (1 - band)


def price_scale_gaps(files, symbol, series="EQ"):
    """[{date, last_close, low, high, ratio, last_file, file, last_date}] where the session's
    whole range is outside SCALE_GAP_BAND of the symbol's last held close (R-12).

    NSE prints the unadjusted prior close on an ex-date (55 of 55 recorded 2021-2025 events,
    ED-50), so prevclose_discontinuities() never sees a split or bonus. This screen looks at
    prices instead. A hit is not a corporate action and is never used as a ratio."""
    out = []
    last = None
    for f in files:
        hit = [r for r in f.rows if r.symbol == symbol and r.series == series]
        if not hit:
            continue
        r = hit[0]
        if last is not None and price_scale_gap(last[0], r.low, r.high):
            out.append({"date": f.trade_date, "last_close": str(last[0]), "low": str(r.low), "high": str(r.high),
                        "ratio": round(float(r.close / last[0]), 6) if last[0] else None,
                        "last_file": last[1], "file": f.source.file_name, "last_date": last[2]})
        last = (r.close, f.source.file_name, f.trade_date)
    return out


def prevclose_discontinuities(files, symbol, series="EQ"):
    """[{date, last_close, prev_close, ratio, last_file, file}] where a row's PREVCLOSE differs
    from the symbol's last close in the files given (files in date order, nse_bhavcopy).

    This does not detect a split or bonus: NSE prints the unadjusted prior close on the
    ex-date, so the chain stays intact across one (R-12, ED-50). Use price_scale_gaps()."""
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


MAX_RATIO_TERM = 10000   # ED-57: engineering bound; a share-ratio term above this is treated as unreadable
_PLAIN_DECIMAL = re.compile(r"\d+(?:\.\d+)?\Z")


def face_value_ratio(kind, old_text, new_text):
    """ED-57: exact share ratio for a face-value change, or None (fail closed).

    old_text/new_text are the face values exactly as printed ("5", "2", "2.5"). They are read
    with Decimal and Fraction, never float. SPLIT needs old > new; CONSOLIDATION needs
    new > old. Returns (kind, ratio_from, ratio_to) as old:new share counts in lowest terms:
    SPLIT 10->2 is (1, 5), SPLIT 5->2 is (2, 5), CONSOLIDATION 1->10 is (10, 1)."""
    if not (isinstance(old_text, str) and isinstance(new_text, str)):
        return None
    old_text, new_text = old_text.strip(), new_text.strip()
    if not (_PLAIN_DECIMAL.match(old_text) and _PLAIN_DECIMAL.match(new_text)):
        return None           # no exponent, sign, Infinity or NaN: only digits with one optional point
    try:
        old = Fraction(Decimal(old_text))
        new = Fraction(Decimal(new_text))
    except (InvalidOperation, ValueError, TypeError, OverflowError):
        return None
    if old <= 0 or new <= 0:
        return None
    if kind == "SPLIT":
        factor = old / new
        row = (kind, factor.denominator, factor.numerator)
    elif kind == "CONSOLIDATION":
        factor = new / old
        row = (kind, factor.numerator, factor.denominator)
    else:
        return None
    if factor <= 1 or row[1] > MAX_RATIO_TERM or row[2] > MAX_RATIO_TERM:
        return None
    return row


def _part_row(part):
    """(action, ratio_from, ratio_to) for one subject part, or (None, reason)."""
    m_ = _BONUS.match(part)
    if m_:                                         # "Bonus a:b": a new shares for every b held
        a, b = int(m_.group(1)), int(m_.group(2))
        if a > 0 and b > 0:
            return "BONUS", b, a + b
    m_ = _FV.match(part)                           # whole part: a combined event is never half-read
    if m_:
        kind = "SPLIT" if m_.group(1).lower() == "split" else "CONSOLIDATION"
        got = face_value_ratio(kind, m_.group(2), m_.group(3))
        if got is not None:
            return got
    m_ = _FV_ABBR.match(part)
    if m_:
        got = face_value_ratio("SPLIT", m_.group(1), m_.group(2))
        if got is not None:
            return got
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


# Evidence tiers (owner decision D62, DECISION_LOG.md). Response
# integrity (the bytes are the response that was saved, it is not empty, and it parsed)
# is not response completeness (the API listed every event in the window).
#   CA_COMPLETENESS_VERIFIED          two independent sources plus reconciliation prove the
#                                     window complete (D66). No such register is on file today.
#   CA_RESPONSE_PRESENT_NOT_COMPLETE  hash-verified, non-empty, no unparsed price subject,
#                                     and the symbol-date passed the EOD and price-continuity
#                                     checks. Exploratory research only: it does not pass the
#                                     corporate-action gate, does not enter the certified
#                                     universe, and keeps CORPORATE_ACTIONS_UNVERIFIED.
#   CORPORATE_ACTIONS_UNVERIFIED      everything else (models.CORPORATE_ACTIONS_UNVERIFIED).
# A PREVCLOSE check is never evidence of completeness: NSE prints the unadjusted prior
# close on an ex-date (ED-50).
CA_COMPLETENESS_VERIFIED = "CA_COMPLETENESS_VERIFIED"
CA_RESPONSE_PRESENT_NOT_COMPLETE = "CA_RESPONSE_PRESENT_NOT_COMPLETE"
CA_UNVERIFIED = m.CORPORATE_ACTIONS_UNVERIFIED
_INTEGRITY_STATUSES = (COVERED_WITH_VERIFIED_EVENTS, RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED)


def evidence_tier(body_status, price_integrity_passed, completeness_proved=False):
    """The evidence tier of one symbol-date. CA_COMPLETENESS_VERIFIED only when the caller
    holds a completeness-register window for it (load_completeness) and the saved response
    is hash-verified with no unparsed price subject. A saved response never proves its own
    completeness, and an integrity or price check cannot."""
    if completeness_proved is True and body_status in _INTEGRITY_STATUSES + (EMPTY_RESPONSE,):
        return CA_COMPLETENESS_VERIFIED
    if body_status in _INTEGRITY_STATUSES and price_integrity_passed is True:
        return CA_RESPONSE_PRESENT_NOT_COMPLETE
    return CA_UNVERIFIED


# Completeness register (D62 tiers + D66 / OD-CA-1 Option A).
# A window is complete only when TWO independent official sources are held and hash-verified,
# reconciled event-by-event, and a USER_APPROVED decision names both source hashes and the
# reconciliation record for that exact symbol and window. A single source never proves
# completeness. No such file exists today, so nothing passes the corporate-action gate.
# A saved API response is never a completeness source.
COMPLETENESS_COLUMNS = (
    "symbol", "from_date", "to_date",
    "source_a", "source_a_file", "source_a_sha256",
    "source_b", "source_b_file", "source_b_sha256",
    "reconciliation_file", "reconciliation_sha256",
    "owner_decision", "recorded_on", "notes",
)
_OWNER_DECISION = re.compile(r"D\d+\Z")
_LOG_HEADING = re.compile(r"^### (D\d+)\.")
_LOG_STATUS = re.compile(r"^- \*\*Status:\*\* `([A-Z_]+)`")
RECONCILIATION_SCHEMA = "gtf.ca_reconciliation.v1"
RECONCILIATION_OK = "RECONCILED"
EVENT_MATCH = "MATCH"
EVENT_EQUIVALENT = "EQUIVALENT"  # differently represented, explicitly reconciled
_EVENT_OK = frozenset((EVENT_MATCH, EVENT_EQUIVALENT))


def owner_decision_status(decision_log):
    """{decision id: status} read from DECISION_LOG.md: the first `**Status:**` line under each
    `### D<n>.` heading. A missing file gives {} (review M-4)."""
    out, current = {}, None
    if not decision_log or not os.path.isfile(decision_log):
        return out
    with open(decision_log, encoding="utf-8") as fh:
        for line in fh:
            h = _LOG_HEADING.match(line)
            if h:
                current = h.group(1)
                continue
            s = _LOG_STATUS.match(line)
            if s and current and current not in out:
                out[current] = s.group(1)
    return out


# D66 marker. The legacy single-hash marker `- **Completeness source accepted:**` never qualifies.
COMPLETENESS_ACCEPTANCE_MARKER = "- **Completeness window accepted:**"
_ACCEPTED_ITEM = re.compile(
    r"^([0-9a-f]{64})\s+([0-9a-f]{64})\s+([0-9a-f]{64})\s+([A-Z0-9&_-]+)\s+"
    r"(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})$"
)


def completeness_decisions(decision_log):
    """{decision id: {(frozenset({sha_a, sha_b}), recon_sha, SYMBOL, from, to)}} accepted under
    D66. USER_APPROVED only. Marker items name both source hashes and the reconciliation hash
    for one symbol/window. Source-hash order in the item is irrelevant (frozenset). A single
    hash, the legacy single-source marker, USER_STATED/PROPOSED, or a mismatch never qualifies."""
    status = owner_decision_status(decision_log)
    out, current = {}, None
    if not decision_log or not os.path.isfile(decision_log):
        return out
    with open(decision_log, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                h = _LOG_HEADING.match(line)
                current = h.group(1) if h else None
                continue
            if current and line.startswith(COMPLETENESS_ACCEPTANCE_MARKER):
                for item in line[len(COMPLETENESS_ACCEPTANCE_MARKER):].split(";"):
                    hit = _ACCEPTED_ITEM.match(item.strip())
                    if not hit:
                        continue
                    sha_a, sha_b, recon, sym, a, b = hit.groups()
                    if sha_a == sha_b:
                        continue  # independence: two distinct source hashes required
                    out.setdefault(current, set()).add((frozenset((sha_a, sha_b)), recon, sym, a, b))
    return {d: items for d, items in out.items() if status.get(d) == "USER_APPROVED"}


def _is_saved_api_response(csv_path, source_file, api_hashes=frozenset()):
    """True when the cited source is a saved corporate-action API response: by name or location,
    by its bytes matching a saved response, or by its content having the API's shape (review R-3).

    Shape detection is independent of subject completeness: a JSON list of objects that carry
    `exDate`, or an empty JSON list `[]`, counts as API-shaped even when `subject` is missing."""
    path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(csv_path)), source_file))
    name = os.path.basename(path)
    if name.startswith("ca_") and name.endswith(".json") or os.sep + "raw" + os.sep in path:
        return True
    if not os.path.isfile(path):
        return False
    with open(path, "rb") as fh:
        data = fh.read()
    if hashlib.sha256(data).hexdigest() in api_hashes:
        return True
    try:
        text = data.decode("utf-8")
        parsed = json.loads(text)
    except (UnicodeDecodeError, ValueError, TypeError):
        return False
    if isinstance(parsed, list) and parsed == []:
        return True
    if not isinstance(parsed, list) or not parsed:
        return False
    if all(isinstance(e, dict) and "exDate" in e for e in parsed):
        return True
    body = _parsed_body(text)
    return bool(body) and all("exDate" in e for e in body)


def _resolve_beside(csv_path, relative):
    path = (relative or "").strip()
    if not path:
        return ""
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.abspath(csv_path)), path)
    return os.path.normpath(path)


def sources_independent(csv_path, file_a, sha_a, file_b, sha_b, api_hashes=frozenset()):
    """True when two cited sources are distinct hash-verified non-API files (D66 independence)."""
    sha_a = (sha_a or "").strip().lower()
    sha_b = (sha_b or "").strip().lower()
    if len(sha_a) != 64 or len(sha_b) != 64 or sha_a == sha_b:
        return False
    if _is_saved_api_response(csv_path, file_a, api_hashes) or _is_saved_api_response(csv_path, file_b, api_hashes):
        return False
    path_a = _resolve_beside(csv_path, file_a)
    path_b = _resolve_beside(csv_path, file_b)
    if not (os.path.isfile(path_a) and os.path.isfile(path_b)):
        return False
    if os.path.samefile(path_a, path_b):
        return False
    with open(path_a, "rb") as fh:
        data_a = fh.read()
    with open(path_b, "rb") as fh:
        data_b = fh.read()
    if data_a == data_b:
        return False
    return (hashlib.sha256(data_a).hexdigest() == sha_a
            and hashlib.sha256(data_b).hexdigest() == sha_b)


def event_key(action, ex_date, ratio_from="", ratio_to=""):
    """Canonical event identity for reconciliation (type, ex-date, ratio terms)."""
    rf = ("" if ratio_from in (None, "") else str(ratio_from).strip())
    rt = ("" if ratio_to in (None, "") else str(ratio_to).strip())
    ratio = ("%s:%s" % (rf, rt)) if (rf or rt) else ""
    return "%s|%s|%s" % ((action or "").strip().upper(), str(ex_date).strip(), ratio)


def reconcile_event_keys(keys_a, keys_b):
    """Event-by-event compare. Returns {matched, only_a, only_b}. Any only_* is unresolved."""
    a, b = set(keys_a or ()), set(keys_b or ())
    return {"matched": sorted(a & b), "only_a": sorted(a - b), "only_b": sorted(b - a)}


def load_reconciliation(path, symbol, from_date, to_date, sha_a, sha_b, expected_sha):
    """Load and validate a D66 reconciliation record. Returns the object or None if invalid.

    Required: schema gtf.ca_reconciliation.v1, status RECONCILED, empty unresolved, every event
    MATCH or EQUIVALENT, symbol/window/source hashes agree, file hashes to expected_sha."""
    if not path or not os.path.isfile(path) or len((expected_sha or "").strip()) != 64:
        return None
    with open(path, "rb") as fh:
        raw = fh.read()
    if hashlib.sha256(raw).hexdigest() != (expected_sha or "").strip().lower():
        return None
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, TypeError):
        return None
    if not isinstance(body, dict):
        return None
    if body.get("schema") != RECONCILIATION_SCHEMA:
        return None
    if body.get("status") != RECONCILIATION_OK:
        return None
    if body.get("unresolved") not in ([], None):
        return None
    if (body.get("symbol") or "").strip().upper() != (symbol or "").strip().upper():
        return None
    if (body.get("from_date"), body.get("to_date")) != (from_date, to_date):
        return None
    cited = frozenset(((body.get("source_a_sha256") or "").strip().lower(),
                       (body.get("source_b_sha256") or "").strip().lower()))
    if cited != frozenset(((sha_a or "").strip().lower(), (sha_b or "").strip().lower())):
        return None
    events = body.get("events")
    if not isinstance(events, list):
        return None
    # D66: event-by-event reconciliation. An empty events list is not a reconciliation unless
    # the record explicitly declares an empty window (both sources agree there are no events).
    empty_window = body.get("empty_window") is True
    if not events and not empty_window:
        return None
    if empty_window and events:
        return None
    for ev in events:
        if not isinstance(ev, dict):
            return None
        if (ev.get("status") or "").strip().upper() not in _EVENT_OK:
            return None
        if not (ev.get("key") or "").strip():
            return None
    return body


def load_completeness(path, accepted=None, api_hashes=frozenset()):
    """{symbol: [(from_date, to_date, owner_decision, recon_file)]} of proved-complete windows.

    D66: a row counts only when both independent sources hash-verify, neither is a saved API
    response, the reconciliation record validates with no unresolved conflict, and `accepted`
    (from completeness_decisions) names exactly (frozenset({sha_a, sha_b}), recon_sha, symbol,
    from, to) under a USER_APPROVED decision. A single source never counts. Without `accepted`
    no row counts. A malformed header or date is refused."""
    out = {}
    if not path or not os.path.isfile(path):
        return out
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != COMPLETENESS_COLUMNS:
            raise CorporateActionError("%s: header must be exactly %s" % (path, ",".join(COMPLETENESS_COLUMNS)))
        for i, r in enumerate(reader, 2):
            try:
                a = datetime.date.fromisoformat(r["from_date"].strip())
                b = datetime.date.fromisoformat(r["to_date"].strip())
            except ValueError:
                raise CorporateActionError("%s line %d: dates must be YYYY-MM-DD" % (path, i))
            if b < a:
                raise CorporateActionError("%s line %d: to_date before from_date" % (path, i))
            decision = (r["owner_decision"] or "").strip()
            sym = r["symbol"].strip().upper()
            sha_a = (r["source_a_sha256"] or "").strip().lower()
            sha_b = (r["source_b_sha256"] or "").strip().lower()
            recon_sha = (r["reconciliation_sha256"] or "").strip().lower()
            item = (frozenset((sha_a, sha_b)), recon_sha, sym, r["from_date"].strip(), r["to_date"].strip())
            if not _OWNER_DECISION.match(decision) or item not in (accepted or {}).get(decision, ()):
                continue
            if not sources_independent(path, r["source_a_file"], sha_a, r["source_b_file"], sha_b, api_hashes):
                continue
            if not m.source_verified(path, r["source_a"], r["source_a_file"], sha_a):
                continue
            if not m.source_verified(path, r["source_b"], r["source_b_file"], sha_b):
                continue
            recon_rel = (r["reconciliation_file"] or "").strip()
            recon_path = _resolve_beside(path, recon_rel)
            if load_reconciliation(recon_path, sym, r["from_date"].strip(), r["to_date"].strip(),
                                   sha_a, sha_b, recon_sha) is None:
                continue
            out.setdefault(sym, []).append((a, b, decision, recon_rel))
    return out


def completeness_proved(register, symbol, day):
    """True when one register window of symbol contains day."""
    return any(a <= day <= b for a, b, _, _ in (register or {}).get(symbol, []))


MALFORMED_RESPONSE = "MALFORMED_RESPONSE"


def _parsed_body(text):
    """The saved body as a list of event dicts, [] for an empty list, or None when it is not
    a JSON list of objects that each carry a text `subject` (review M-1)."""
    try:
        body = json.loads(text)
    except (TypeError, ValueError):
        return None
    if not isinstance(body, list):
        return None
    if any(not isinstance(e, dict) or not isinstance(e.get("subject"), str) or not e["subject"].strip()
           for e in body):
        return None
    return body


def _harmless_subject(subject):
    """True when the parser reads every part of the subject as a dividend or a known non-price
    event (from_nse_json's own rule); anything else could carry a price-scale change."""
    rows = _subject_rows(" ".join((subject or "").split()))
    return rows is not None and all(action == "DIVIDEND" for action, _, _ in rows)


def unreadable_price_entries(text):
    """Review N-3, N-3b: entries of a parsed body that from_nse_json drops without a row (series
    not exactly "EQ", or an ex-date that does not read as DD-Mon-YYYY exactly as saved) and whose
    subject is not harmless. Uses the parser's own predicates, unstripped, so nothing a parser
    would drop can vanish from the count. The caller adds them to the unparsed count."""
    events = _parsed_body(text) or []
    n = 0
    for e in events:
        dropped = e.get("series") != "EQ"
        if not dropped:
            try:
                datetime.datetime.strptime(e["exDate"], "%d-%b-%Y")
            except (KeyError, TypeError, ValueError):
                dropped = True
        if dropped and not _harmless_subject(e["subject"]):
            n += 1
    return n


def empty_api_body(text):
    """True when the saved response parses as an empty JSON list. That is not proof of no events."""
    return _parsed_body(text) == []


def response_status(body, parsed_price_events=0, unparsed_price_events=0):
    """Classify one saved response. An empty list is never 'no events'.

    A non-empty response is not proof that the API returned every event. Parsed
    price events are recorded. They do not by themselves authorise a price adjustment.
    """
    if body is None:
        return MISSING_COVERAGE
    events = _parsed_body(body)
    if events is None:
        return MALFORMED_RESPONSE                    # an error page or a non-list never counts (M-1)
    if not events:
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
