"""Point-in-time Nifty 100 membership from a dated baseline and reconstitution events
(D1; B11; nse/docs/REAL_DATA_READINESS.md section 5).

No constituent list is built in. Two transcribed files, each row citing the official
document it comes from, convert into universe rows (universe.COLUMNS) that universe.load
reads:

    nifty100_baseline.csv  index_name,as_of_date,symbol,isin,series,source,source_doc_id,
                           source_file,source_sha256,recorded_on,notes
    nifty100_changes.csv   event_id,index_name,announcement_date,effective_date,action,symbol,
                           isin,series,replaces_isin,reason,source,source_doc_id,source_file,
                           source_sha256,recorded_on,notes

Date semantics (all inclusive):
  as_of_date      a date on which the listed baseline composition was in force. Membership
                  is only claimed from as_of_date; nothing before it is inferred.
  effective_date  the FIRST date on which the new composition is in force. An ADD is a
                  member from effective_date; a REMOVE is a member up to and including
                  effective_date - 1 day (calendar day, not session).
How a notice's wording (for example "effective from X (close of trading on X-1)") maps to
effective_date is an evidence decision recorded per row in `notes` by whoever transcribes
the notice (REAL_DATA_READINESS section 5, open interpretation). The converter never reads
free text; it trusts effective_date as transcribed.

The converter rolls forward only: the baseline must be the earliest composition, and a
change dated on or before the baseline as_of_date is refused. Rolling backward from a
later snapshot is not supported.

Validation collects every problem and then raises MembershipError listing all of them;
nothing is ever partially converted. Row and structure errors are checked first; the
membership walk (ADD not already a member, REMOVE a member, exactly N members after every
effective date) runs only when the rows themselves are valid, so its messages are not
noise from a malformed row.

Symbol changes (RENAME): a member whose symbol changes keeps its seat. A RENAME row gives
the member's ISIN and its NEW symbol, effective from the first session under the new
symbol (the NSE symbol-change date). The period under the old symbol ends the day before;
a period under the new symbol starts that day. The count is unchanged and the row is not
part of the ADD / REMOVE balance. The ISIN must already be a member.

ISIN changes (ISIN_CHANGE): a member whose ISIN changes (e.g. at a face-value split) keeps
its seat. The row gives the NEW isin, the member's symbol and, in replaces_isin, the old ISIN
that must be a member; the old period ends the day before, a new one starts. Count unchanged.

Member-count exceptions (ED-22): official data is not always N members. The NSE Indices
release of 17 Aug 2023 has six NIFTY 100 inclusions against five exclusions (the Tata
Motors DVR was added as a separate security), so the index held 101 securities from
29 Sep 2023. A count other than N, and an event whose ADD and REMOVE counts differ, are
accepted only for an effective date declared in count_exceptions ({date: count}, each
taken from the cited release), and the count must then equal the declared one exactly.
Every exception used is listed in the report. An undeclared deviation is still refused:
it usually means a transcription omission.

Provenance: each row is verified with models.source_verified relative to its own CSV's
folder (D31). A membership period is verified only when the row that starts it, the row
that ends it (if any) and its identity check (if instrument records are given) all are.
An unverified period is written with an empty source_sha256 (the transcribed hash is
kept in notes), so universe.load reads it as unverified and the scan carries
UNIVERSE_UNVERIFIED.

Human review gate (D49, D53, owner 2026-11-09; scopes in ED-48), row by row: every baseline,
change and count-exception row has a key (baseline:<symbol>:<isin>, change:<event_id>:
<action>:<symbol>:<isin>, exception:<date>) and the SHA-256 of its exact field values. The
review file holds one row per key. `decision` is the full membership-row approval: ACCEPTED
or REJECTED, with the reviewer, the date and the row hash the reviewer saw. A period is
verified only when its source verifies, the row that starts it and the row that ends it
(if any) are ACCEPTED with a matching hash, every count exception the conversion uses
passes the count gate, and its identity check (if records are given) is clear.

Two further columns do not approve a period (ED-48). `count_approval` APPROVED on an
exception row passes only the count gate. `mapping_approval` APPROVED on a change row
records a symbol add or remove and is never read by the period gate. An older review file
without those columns still means what it meant: `decision` ACCEPTED is full row approval,
and on an exception row that is also the count gate. Nothing copies an existing ACCEPTED
into the new columns. Editing a transcription row voids that row's approval. Agents never
write an ACCEPTED decision.
"""

import csv
import datetime
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from nse.research import instruments, models as m, universe

BASELINE_COLUMNS = ("index_name", "as_of_date", "symbol", "isin", "series", "source", "source_doc_id",
                    "source_file", "source_sha256", "recorded_on", "notes")
CHANGES_COLUMNS = ("event_id", "index_name", "announcement_date", "effective_date", "action", "symbol", "isin",
                   "series", "replaces_isin", "reason", "source", "source_doc_id", "source_file", "source_sha256",
                   "recorded_on", "notes")
ADD, REMOVE, RENAME, ISIN_CHANGE = "ADD", "REMOVE", "RENAME", "ISIN_CHANGE"
ACTIONS = (ADD, REMOVE, RENAME, ISIN_CHANGE)
REASONS = ("RECONSTITUTION", "CORPORATE_ACTION", "OTHER")
DEFAULT_MEMBERS = 100                                  # Nifty 100 (D1)
# The six-column file is the D53 review. The two scope columns are ED-48 and are optional
# on read, so an older file is not rewritten into a new meaning.
LEGACY_REVIEW_COLUMNS = ("row_key", "row_sha256", "decision", "reviewer", "reviewed_on", "notes")
SCOPE_COLUMNS = ("count_approval", "mapping_approval")
REVIEW_COLUMNS = LEGACY_REVIEW_COLUMNS + SCOPE_COLUMNS
ACCEPTED, REJECTED = "ACCEPTED", "REJECTED"
APPROVED = "APPROVED"                              # scope columns only; never a period decision
_SCOPE_VALUES = (APPROVED, REJECTED)
_ISIN = re.compile(r"IN[A-Z0-9]{10}\Z")                # as instruments and nse_bhavcopy check it
_DAY = datetime.timedelta(days=1)


class MembershipError(ValueError):
    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("%d problem(s):\n  %s" % (len(self.problems), "\n  ".join(self.problems)))


@dataclass(frozen=True)
class _Row:
    where: str                       # "file line n"
    kind: str                        # "BASELINE", ADD or REMOVE
    event_id: str
    index_name: str
    date: datetime.date              # as_of_date or effective_date
    announced: Optional[datetime.date]
    symbol: str
    isin: str
    series: str
    replaces_isin: str
    reason: str
    source: str
    source_doc_id: str
    source_file: str                 # absolute when given, else ""
    source_sha256: str
    recorded_on: str
    notes: str
    verified: bool
    key: str = ""                    # review key (module docstring)
    row_sha: str = ""                # SHA-256 of the row's field values, in file order


def _row_sha(values):
    import hashlib
    return hashlib.sha256("\x1f".join(v if v is not None else "" for v in values).encode("utf-8")).hexdigest()


@dataclass
class _Period:
    start: _Row
    end: Optional[_Row] = None
    identity: List[dict] = field(default_factory=list)

    @property
    def verified(self):
        return self.start.verified and (self.end is None or self.end.verified) and not self.identity


@dataclass
class Conversion:
    rows: List[Dict[str, str]]       # universe.COLUMNS, source_file absolute (write() relativises)
    report: dict


def _iso(value, where, name, problems, required=True):
    value = (value or "").strip()
    if not value and not required:
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        problems.append("%s: %s %r is not an ISO date (YYYY-MM-DD)" % (where, name, value))
        return None


def _read(path, columns, problems):
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != columns:
            problems.append("%s: header must be exactly %s" % (path, ",".join(columns)))
            return []
        return [(i, r) for i, r in enumerate(reader, 2)]


def _common(path, i, r, kind, event_id, date, announced, problems):
    where = "%s line %d" % (path, i)
    symbol, isin = r["symbol"].strip().upper(), r["isin"].strip().upper()
    if not symbol:
        problems.append("%s: empty symbol" % where)
    if not _ISIN.match(isin):
        problems.append("%s: isin %r is not IN + 10 letters or digits" % (where, isin))
    if r["recorded_on"].strip():
        _iso(r["recorded_on"], where, "recorded_on", problems)
    src_file = r["source_file"].strip()
    if src_file and not os.path.isabs(src_file):
        src_file = os.path.join(os.path.dirname(os.path.abspath(path)), src_file)
    key = ("baseline:%s:%s" % (symbol, isin) if kind == "BASELINE"
           else "change:%s:%s:%s:%s" % (event_id, kind, symbol, isin))
    return _Row(where, kind, event_id, r["index_name"].strip(), date, announced, symbol, isin,
                r["series"].strip() or "EQ", r.get("replaces_isin", "").strip().upper(), r.get("reason", "").strip(),
                r["source"].strip(), r["source_doc_id"].strip(), src_file, r["source_sha256"].strip().lower(),
                r["recorded_on"].strip(), r["notes"].strip(),
                m.source_verified(path, r["source"], r["source_file"], r["source_sha256"]),
                key, _row_sha(r.values()))


def _baseline(path, problems):
    out = []
    for i, r in _read(path, BASELINE_COLUMNS, problems):
        d = _iso(r["as_of_date"], "%s line %d" % (path, i), "as_of_date", problems)
        out.append(_common(path, i, r, "BASELINE", "", d, None, problems))
    return out


def _changes(path, problems):
    out = []
    for i, r in _read(path, CHANGES_COLUMNS, problems):
        where = "%s line %d" % (path, i)
        eff = _iso(r["effective_date"], where, "effective_date", problems)
        ann = _iso(r["announcement_date"], where, "announcement_date", problems)
        if eff and ann and ann > eff:
            problems.append("%s: announcement_date %s is after effective_date %s" % (where, ann, eff))
        action = r["action"].strip()
        if action not in ACTIONS:
            problems.append("%s: action %r must be one of %s" % (where, action, ", ".join(ACTIONS)))
        if r["reason"].strip() not in REASONS:
            problems.append("%s: reason %r must be one of %s" % (where, r["reason"].strip(), ", ".join(REASONS)))
        if not r["event_id"].strip():
            problems.append("%s: empty event_id" % where)
        out.append(_common(path, i, r, action, r["event_id"].strip(), eff, ann, problems))
    return out


def _structure(base, changes, problems, count_exceptions=()):
    """Checks that need no membership walk; returns {event_id: [rows]} in file order."""
    names = sorted(set(r.index_name for r in base + changes))
    if len(names) != 1:
        problems.append("index_name must be one value throughout, found %s" % (names or "none"))
    if not base:
        problems.append("baseline has no rows")
    dates = sorted(set(r.date for r in base if r.date))
    if len(dates) > 1:
        problems.append("baseline must be one dated snapshot, found as_of_date %s"
                        % ", ".join(d.isoformat() for d in dates))
    for attr in ("isin", "symbol"):
        seen = {}
        for r in base:
            key = getattr(r, attr)
            if key in seen:
                problems.append("%s: duplicate %s %s in the baseline (also %s)" % (r.where, attr, key, seen[key]))
            seen.setdefault(key, r.where)
    as_of = dates[-1] if dates else None
    events = {}
    for r in changes:
        events.setdefault(r.event_id, []).append(r)
        if as_of and r.date and r.date <= as_of:
            problems.append("%s: effective_date %s is on or before the baseline as_of_date %s; the "
                            "converter rolls forward only" % (r.where, r.date, as_of))
    for eid, rows in sorted(events.items()):
        effs = sorted(set(r.date for r in rows if r.date))
        if len(effs) > 1:
            problems.append("event %s: one effective_date per event, found %s"
                            % (eid, ", ".join(d.isoformat() for d in effs)))
        adds = [r for r in rows if r.kind == ADD]
        removes = [r for r in rows if r.kind == REMOVE]
        if len(adds) != len(removes) and not (effs and effs[0] in count_exceptions):
            problems.append("event %s: %d ADD and %d REMOVE rows; the counts must be equal"
                            % (eid, len(adds), len(removes)))
        out_isins = set(r.isin for r in removes)
        for r in rows:
            if r.kind != ISIN_CHANGE and r.replaces_isin and r.replaces_isin not in out_isins:
                problems.append("%s: replaces_isin %s is not a REMOVE in event %s" % (r.where, r.replaces_isin, eid))
        seen = {}
        for r in rows:
            if r.isin in seen:
                problems.append("%s: isin %s appears twice in event %s (also %s)" % (r.where, r.isin, eid, seen[r.isin]))
            seen.setdefault(r.isin, r.where)
    return as_of, events


def _identity(period, records):
    """Findings for a period whose ISIN does not resolve via instruments at its start date."""
    r = period.start
    res = instruments.resolve(records, r.symbol, r.date)
    base = {"isin": r.isin, "symbol": r.symbol, "date": r.date.isoformat(), "row": r.where}
    if res["status"] != instruments.RESOLVED:
        return [dict(base, code=instruments.UNKNOWN_INSTRUMENT, detail=res["reason"])]
    if res["isin"] != r.isin:
        return [dict(base, code=instruments.ISIN_RECORD_MISMATCH,
                     detail="instrument records give %s for %s on %s" % (res["isin"], r.symbol, r.date))]
    if not res["verified"]:
        # an identity resting on an unverified record is not evidence (unknown is never PASS)
        return [dict(base, code=instruments.UNVERIFIED, detail="identity record(s) unverified: lines %s"
                     % ", ".join(str(n) for n in res["records"]))]
    return []


def _describe(r, role):
    if r.kind == "BASELINE":
        text = "%s: baseline as of %s" % (role, r.date)
    else:
        text = "%s: event %s %s %s announced %s" % (role, r.event_id, r.kind, r.reason, r.announced)
        if r.replaces_isin:
            text += " replacing %s" % r.replaces_isin
    if r.source_doc_id:
        text += " doc %s" % r.source_doc_id
    if not r.verified:
        text += " (source UNVERIFIED)"
    if r.notes:
        text += " [%s]" % r.notes
    return text


def _file_sha(path):
    import hashlib
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


COUNT_EXCEPTION_COLUMNS = ("effective_date", "members", "source_doc_id", "basis")


def load_count_exceptions(path):
    """{date: members} from a CSV (COUNT_EXCEPTION_COLUMNS); each row cites the release whose
    one-sided change gives that official count (ED-22, D49 "never force 100")."""
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != COUNT_EXCEPTION_COLUMNS:
            raise MembershipError(["%s: header must be exactly %s" % (path, ",".join(COUNT_EXCEPTION_COLUMNS))])
        out = {}
        for i, r in enumerate(reader, 2):
            if not r["source_doc_id"].strip() or not r["basis"].strip():
                raise MembershipError(["%s line %d: an exception needs its source document and basis" % (path, i)])
            day = datetime.date.fromisoformat(r["effective_date"])
            if day in out:
                raise MembershipError(["%s line %d: %s declared twice" % (path, i, day)])
            out[day] = int(r["members"])
    return out


def _exception_rows(path):
    """[(key, sha)] of a count-exceptions file, in file order."""
    with open(path, newline="", encoding="utf-8") as fh:
        return [("exception:%s" % r["effective_date"].strip(), _row_sha(r.values())) for r in csv.DictReader(fh)]


def review_template(baseline_path, changes_path=None, count_exceptions_path=None):
    """One review row per transcription row, decision empty, for the human reviewer."""
    problems = []
    rows = _baseline(baseline_path, problems) + (_changes(changes_path, problems) if changes_path else [])
    if problems:
        raise MembershipError(problems)
    keys = [(r.key, r.row_sha) for r in rows]
    if count_exceptions_path:
        keys += _exception_rows(count_exceptions_path)
    return [{"row_key": k, "row_sha256": h, "decision": "", "reviewer": "", "reviewed_on": "", "notes": "",
             "count_approval": "", "mapping_approval": ""}
            for k, h in keys]


def read_review(review_path):
    """({key: row}, problems). A blank row is skipped. A key may appear once.

    `decision` ACCEPTED or REJECTED is the full membership-row approval. `count_approval`
    belongs only on an exception row and `mapping_approval` only on a change row. Either
    scope uses APPROVED or REJECTED. Any filled approval needs a reviewer and an ISO date.
    A malformed row is reported and omitted, so it cannot approve anything."""
    if not review_path or not os.path.isfile(review_path):
        return {}, []
    out, problems = {}, []
    with open(review_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header = tuple(reader.fieldnames or ())
        if header == LEGACY_REVIEW_COLUMNS:
            scoped = False
        elif header == REVIEW_COLUMNS:
            scoped = True
        else:
            return {}, ["%s: header must be %s or %s" % (
                review_path, ",".join(LEGACY_REVIEW_COLUMNS), ",".join(REVIEW_COLUMNS))]
        for i, raw in enumerate(reader, 2):
            decision = (raw.get("decision") or "").strip()
            count_approval = (raw.get("count_approval") or "").strip() if scoped else ""
            mapping_approval = (raw.get("mapping_approval") or "").strip() if scoped else ""
            if not decision and not count_approval and not mapping_approval:
                continue
            where = "%s line %d" % (review_path, i)
            row_problems = []
            key = raw.get("row_key") or ""
            if decision and decision not in (ACCEPTED, REJECTED):
                row_problems.append("%s: decision must be ACCEPTED or REJECTED" % where)
            if count_approval and count_approval not in _SCOPE_VALUES:
                row_problems.append("%s: count_approval must be APPROVED or REJECTED" % where)
            if mapping_approval and mapping_approval not in _SCOPE_VALUES:
                row_problems.append("%s: mapping_approval must be APPROVED or REJECTED" % where)
            if count_approval and not key.startswith("exception:"):
                row_problems.append("%s: count_approval applies only to an exception row" % where)
            if mapping_approval and not key.startswith("change:"):
                row_problems.append("%s: mapping_approval applies only to a change row" % where)
            if not (raw.get("reviewer") or "").strip() or not _ISO_OK(raw.get("reviewed_on")):
                row_problems.append("%s: an approval needs a reviewer and an ISO reviewed_on date" % where)
            if key in out:
                row_problems.append("%s: %s decided twice" % (where, key))
            if row_problems:
                problems.extend(row_problems)
                continue
            stored = {column: raw.get(column, "") or "" for column in REVIEW_COLUMNS}
            stored["decision"] = decision
            stored["count_approval"] = count_approval
            stored["mapping_approval"] = mapping_approval
            out[key] = stored
    return out, problems


def _ISO_OK(text):
    try:
        datetime.date.fromisoformat(text)
        return True
    except (TypeError, ValueError):
        return False


def _out_row(p, reviewed=True):
    r = p.start
    notes = [_describe(r, "from")]
    if p.end is not None:
        notes.append(_describe(p.end, "to"))
    for f in p.identity:
        notes.append("identity %s: %s" % (f["code"], f["detail"]))
    sha = r.source_sha256
    if not p.verified:
        notes.append("UNVERIFIED period; transcribed source_sha256 %s withheld" % (sha or "(none)"))
        sha = ""
    elif not reviewed:
        notes.append("UNREVIEWED transcription (D49); source_sha256 %s withheld until human review" % sha)
        sha = ""
    return {"symbol": r.symbol, "series": r.series, "isin": r.isin, "index_name": r.index_name,
            "effective_from": r.date.isoformat(),
            "effective_to": (p.end.date - _DAY).isoformat() if p.end is not None else "",
            "source": r.source, "source_file": r.source_file, "source_sha256": sha, "recorded_on": r.recorded_on,
            "notes": "; ".join(notes)}


def convert(baseline_path, changes_path=None, expected_members=DEFAULT_MEMBERS, instrument_records=None,
            count_exceptions=None, review_path=None, count_exceptions_path=None):
    """Validate the baseline and changes files and return a Conversion (universe rows and a
    report), or raise MembershipError with every problem found. instrument_records is the
    output of instruments.load; when given, each period's ISIN must resolve at its start.
    count_exceptions: {date: member count} for effective dates whose official count is not
    expected_members (module docstring, ED-22). review_path: the human review file (D49);
    without an accepted review every period is unverified. count_exceptions_path: the file the
    exceptions came from; its hash is part of the review, and when given without
    count_exceptions it is loaded."""
    problems = []
    if count_exceptions is None and count_exceptions_path:
        count_exceptions = load_count_exceptions(count_exceptions_path)
    count_exceptions = dict(count_exceptions or {})
    base = _baseline(baseline_path, problems)
    changes = _changes(changes_path, problems) if changes_path else []
    as_of, events = _structure(base, changes, problems, count_exceptions)
    if problems:
        raise MembershipError(problems)

    open_periods = {r.isin: _Period(r) for r in base}
    closed = []
    counts = {as_of.isoformat(): len(open_periods)}
    exceptions_used = {}

    def check_count(day, label):
        want = count_exceptions.get(day, expected_members)
        if len(open_periods) != want:
            problems.append("%s %d members, expected %d%s" % (label, len(open_periods), want,
                                                              " (declared exception)" if day in count_exceptions else ""))
        elif day in count_exceptions:
            exceptions_used[day.isoformat()] = want

    check_count(as_of, "baseline as of %s has" % as_of)
    order = sorted(events, key=lambda e: (events[e][0].date, e))
    applied = []
    for n, eid in enumerate(order):
        rows = events[eid]
        before = set(open_periods)
        for r in rows:
            if r.kind == REMOVE and r.isin not in before:
                problems.append("%s: REMOVE %s (%s) is not a member before %s" % (r.where, r.isin, r.symbol, r.date))
            if r.kind == ADD and r.isin in before:
                problems.append("%s: ADD %s (%s) is already a member before %s" % (r.where, r.isin, r.symbol, r.date))
        for r in rows:
            if r.kind == REMOVE and r.isin in open_periods:
                p = open_periods.pop(r.isin)
                p.end = r
                closed.append(p)
                if r.date <= p.start.date:            # added and removed on the same day
                    problems.append("%s: REMOVE %s on %s leaves an empty period (member from %s)"
                                    % (r.where, r.isin, r.date, p.start.date))
        for r in rows:
            if r.kind == ISIN_CHANGE:
                if r.replaces_isin not in open_periods or r.isin in open_periods:
                    problems.append("%s: ISIN_CHANGE %s -> %s needs the old ISIN as a member and the new one not"
                                    % (r.where, r.replaces_isin, r.isin))
                    continue
                p = open_periods.pop(r.replaces_isin)
                p.end = r
                closed.append(p)
                open_periods[r.isin] = _Period(r)
        for r in rows:
            if r.kind == RENAME:
                if r.isin not in open_periods:
                    problems.append("%s: RENAME %s (%s) is not a member before %s" % (r.where, r.isin, r.symbol, r.date))
                    continue
                p = open_periods.pop(r.isin)
                if p.start.symbol == r.symbol:
                    problems.append("%s: RENAME %s to its current symbol %s" % (r.where, r.isin, r.symbol))
                p.end = r
                closed.append(p)
                open_periods[r.isin] = _Period(r)
        for r in rows:
            if r.kind == ADD and r.isin not in open_periods:
                open_periods[r.isin] = _Period(r)
        applied.append(eid)
        day = rows[0].date
        if n + 1 == len(order) or events[order[n + 1]][0].date != day:
            counts[day.isoformat()] = len(open_periods)
            check_count(day, "after effective_date %s:" % day)
            syms = {}
            for p in open_periods.values():
                if p.start.symbol in syms:
                    problems.append("after effective_date %s: symbol %s is held by %s and %s"
                                    % (day, p.start.symbol, syms[p.start.symbol], p.start.isin))
                syms.setdefault(p.start.symbol, p.start.isin)
    if problems:
        raise MembershipError(problems)

    periods = sorted(closed + list(open_periods.values()), key=lambda p: (p.start.symbol, p.start.date))
    findings = []
    if instrument_records is not None:
        for p in periods:
            p.identity = _identity(p, instrument_records)
            findings += p.identity
    decisions, review_problems = read_review(review_path)

    def _matches(key, sha):
        row = decisions.get(key)
        return row is not None and row["row_sha256"] == sha

    def accepted(key, sha):
        # Full membership-row approval. Scope columns are not consulted.
        return _matches(key, sha) and decisions[key]["decision"] == ACCEPTED

    def count_satisfied(key, sha):
        # The count gate only. An explicit REJECTED on either column fails closed.
        # A legacy ACCEPTED with a blank count_approval keeps its old meaning and is
        # not copied into count_approval.
        if not _matches(key, sha):
            return False
        row = decisions[key]
        if row["decision"] == REJECTED or row["count_approval"] == REJECTED:
            return False
        if row["count_approval"] == APPROVED:
            return True
        return row["count_approval"] == "" and row["decision"] == ACCEPTED

    used_exc = set(exceptions_used)
    exc_rows = [(k, h) for k, h in (_exception_rows(count_exceptions_path) if count_exceptions_path else [])
                if k.split(":", 1)[1] in used_exc]
    exceptions_ok = (not used_exc) or (bool(count_exceptions_path) and len(exc_rows) == len(used_exc)
                                       and all(count_satisfied(k, h) for k, h in exc_rows))
    period_ok = lambda p: (exceptions_ok and accepted(p.start.key, p.start.row_sha)
                           and (p.end is None or accepted(p.end.key, p.end.row_sha)))
    rows = [_out_row(p, period_ok(p)) for p in periods]
    all_rows = [(r.key, r.row_sha) for r in base + changes] + exc_rows
    stale = sorted(k for k, h in all_rows if k in decisions and decisions[k]["row_sha256"] != h)
    rejected = sorted(k for k, h in all_rows if k in decisions and decisions[k]["decision"] == REJECTED)
    n_acc = sum(1 for k, h in all_rows if accepted(k, h))

    def _scoped(field, prefix):
        return sorted(k for k, h in all_rows if k.startswith(prefix) and _matches(k, h)
                      and decisions[k][field] == APPROVED)

    review = {"status": "COMPLETE" if n_acc == len(all_rows) and not review_problems
              else ("NOT_REVIEWED" if not decisions else "INCOMPLETE"),
              "rows": len(all_rows), "accepted": n_acc, "rejected": rejected, "stale_hash": stale,
              "undecided": len(all_rows) - n_acc - len(rejected) - len(stale), "problems": review_problems,
              "count_exceptions_accepted": exceptions_ok,
              "count_approvals": _scoped("count_approval", "exception:"),
              "mapping_approvals": _scoped("mapping_approval", "change:")}
    unverified_rows = [{"row": r.where, "isin": r.isin, "symbol": r.symbol}
                       for r in base + changes if not r.verified]
    report = {"index_name": base[0].index_name, "baseline_as_of": as_of.isoformat(),
              "expected_members": expected_members, "members_by_date": counts, "events_applied": applied,
              "count_exceptions_used": exceptions_used,
              "periods": len(rows),
              "unverified_periods": sum(1 for p in periods if not (p.verified and period_ok(p))),
              "review": review,
              "unverified_rows": unverified_rows, "identity_findings": findings,
              "identity_checked": instrument_records is not None}
    return Conversion(rows, report)


def write(rows, path):
    """Write converted rows as a universe CSV (universe.load reads it). source_file is made
    relative to the output folder so the hash check still finds the cited document."""
    folder = os.path.dirname(os.path.abspath(path))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=universe.COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            out = dict(r)
            if out["source_file"] and os.path.isabs(out["source_file"]):
                try:
                    out["source_file"] = os.path.relpath(out["source_file"], folder)
                except ValueError:                     # another drive (Windows): keep it absolute
                    pass
            w.writerow(out)
    return path


NEEDS_OWNER_REVIEW = "NEEDS_OWNER_REVIEW"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
ACCEPT_RECOMMENDED = "ACCEPT_RECOMMENDED"
REJECT_RECOMMENDED = "REJECT_RECOMMENDED"


def owner_review_queue(review_path, packet_path):
    """Advisory queue for the 271 membership rows. It does not write the review file.

    A packet verdict and a matching hash are not a membership-period decision.
    Count and mapping approvals stay in their own columns. This function never
    returns ACCEPT_RECOMMENDED: accepting a period still needs the owner, and
    this queue does not re-read the cited PDF pages.
    """
    with open(review_path, newline="", encoding="utf-8") as fh:
        review = list(csv.DictReader(fh))
    with open(packet_path, newline="", encoding="utf-8") as fh:
        packet = {r["row_key"]: r for r in csv.DictReader(fh)}
    out = []
    for row in review:
        key = row["row_key"]
        prior = packet.get(key)
        verdict = (prior or {}).get("verifier_verdict", "")
        evidence = (prior or {}).get("evidence", "")
        if prior is None or prior.get("row_sha256") != row["row_sha256"]:
            recommendation = INSUFFICIENT_EVIDENCE
            why = "the advisory packet is missing or its hash does not match this review row"
        elif "DUMMY" in key or verdict == "INFERENCE":
            recommendation = INSUFFICIENT_EVIDENCE if verdict == "INFERENCE" else NEEDS_OWNER_REVIEW
            why = "placeholder or inferred ISIN; not a tradable instrument and not a membership-period approval"
        else:
            recommendation = NEEDS_OWNER_REVIEW
            why = ("row hash matches the advisory packet (%s); the period decision is still open"
                   % (verdict or "no verdict"))
        scope = []
        if row.get("count_approval"):
            scope.append("count_approval " + row["count_approval"])
        if row.get("mapping_approval"):
            scope.append("mapping_approval " + row["mapping_approval"])
        out.append({
            "row_key": key,
            "row_sha256": row["row_sha256"],
            "decision": row.get("decision", ""),
            "recorded_scope": "; ".join(scope),
            "packet_verdict": verdict,
            "evidence": evidence,
            "recommendation": recommendation,
            "why": why,
        })
    return out


def members_without_data(univ, available_symbols_by_date):
    """{date iso: [member symbols with no market data that day]} for each date given, so a
    historical member without an input file is reported instead of silently dropping out."""
    out = {}
    for d in sorted(available_symbols_by_date):
        have = set(s.upper() for s in available_symbols_by_date[d])
        missing = sorted(r.symbol for r in univ.members(d) if r.symbol not in have)
        if missing:
            out[d.isoformat()] = missing
    return out
