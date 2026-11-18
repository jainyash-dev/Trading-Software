"""Offline EOD acquisition: the owner downloads NSE end-of-day files, this module verifies
and ingests them (D31: local files only; nothing here fetches, schedules or contacts a
broker, D10, D17).

  Provider / LocalInboxProvider   where a session's downloaded files are found
  detect_format(path)             LEGACY_BHAVCOPY | UDIFF_BHAVCOPY | UNKNOWN
  plan(calendar, start, end, manifest_path, raw_dir) -> rows, one per session
  ingest(paths, raw_dir, manifest_path, quarantine_dir, ledger_path, ...) -> outcomes
  daily_update(session_date, provider, calendar, ...) -> one status (+ alert)
  coverage(plan_rows) -> counts, first/last held date, missing sessions

Rules:
  - Two verified formats are ingested, as archives only: the legacy bhavcopy
    (cmDDMMMYYYYbhav.csv.zip) and the UDiFF bhavcopy (BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000
    .csv.zip), EOD_FORMAT_EVIDENCE.md sections 5 and 9. Format detection is a triage label
    only; acceptance is the strict nse_bhavcopy parse, which accepts only the verified
    schema versions. A verified file in the format NOT selected for its trade date
    (nse_bhavcopy.selected_format, ED-20: legacy up to 2024-07-05, UDiFF from 2024-07-08)
    is quarantined with FORMAT_NOT_SELECTED_FOR_DATE, so one session never has two sources.
  - Source files are copied, never moved or deleted. A held raw file is never
    overwritten: a second file for a held session with a different SHA-256 is a revision
    and is quarantined (REVISED_FILE_QUARANTINED) for the owner to judge.
  - Quarantine = a copy in quarantine_dir named <sha256>_<name> plus a
    <sha256>_<name>.reason.json record. Nothing quarantined is used by any scan.
  - Manifest rows come from manifest_tool.rows_for (strict parse, sizes and hashes from
    the bytes); what only the owner knows (source page, download date, provenance status)
    is passed in, never inferred, and never from a file's modification time.
  - Every outcome is appended to a JSONL ledger, one object per line, sorted keys, with
    the caller's recorded_at (the clock is never read). The ledger is append-only.
  - Without a calendar a weekday is only a CANDIDATE session (CALENDAR_UNVALIDATED): it
    is never called expected or missing. A date the calendar cannot answer for is
    labelled the same way; an unresolved calendar date is CALENDAR_AMBIGUOUS (D39). A
    Muhurat or shortened session is EXCLUDED_SESSION: not required (D30, D33).
  - plan() is a pure function of the local files, so re-running it after more files
    arrive resumes the backfill; nothing is cached.

Adding a licensed data provider later (owner approval required, D17, D31): subclass
Provider and implement list_available(session_date) so that it returns paths of files
ALREADY ON LOCAL DISK, in the provider's own delivery folder, plus the provenance
(source page, download date, status) the owner records for ingest(). Its files then pass
the same detect_format / strict parse / quarantine path as a manual download. A provider
must not add network code to nse/ (tests/test_repo.py forbids it) and must not deliver a
format other than the two verified archive formats.
"""

import datetime
import hashlib
import json
import os
import shutil
import sys
import zipfile

from nse.research import manifest_tool
from nse.research.deps import bhavcopy, calendar as cal_mod, EOD_MANIFEST, EOD_RAW_DIR

# formats (detect_format)
LEGACY_BHAVCOPY = "LEGACY_BHAVCOPY"
UDIFF_BHAVCOPY = "UDIFF_BHAVCOPY"
UDIFF_UNVERIFIED = UDIFF_BHAVCOPY            # former name, kept for callers and old ledger readers
UNKNOWN = "UNKNOWN"
UDIFF_LEADING_COLUMNS = ("TradDt", "BizDt", "Sgmt")    # first columns of a UDiFF CM bhavcopy

# plan statuses
HELD = "HELD"
MISSING = "MISSING"
HASH_MISMATCH = "HASH_MISMATCH"
NOT_IN_MANIFEST = "NOT_IN_MANIFEST"
PLAN_STATUSES = (HELD, MISSING, HASH_MISMATCH, NOT_IN_MANIFEST)

# calendar labels on plan rows
EXPECTED = "EXPECTED"                          # the calendar says the session trades
CALENDAR_UNVALIDATED = "CALENDAR_UNVALIDATED"  # weekday, no calendar answer: a candidate only
CALENDAR_AMBIGUOUS = "CALENDAR_AMBIGUOUS"      # the calendar has an unresolved event
EXCLUDED_SESSION = "EXCLUDED_SESSION"          # Muhurat / shortened: not required (D30, D33)
CLOSED_DAY = "CLOSED_DAY"                      # holiday or weekend that nevertheless has a file

# ingestion outcomes
INGESTED = "INGESTED"
DUPLICATE = "DUPLICATE"
QUARANTINED = "QUARANTINED"
REVISED_FILE_QUARANTINED = "REVISED_FILE_QUARANTINED"
SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"

# quarantine reasons
FORMAT_UNVERIFIED_B18 = "FORMAT_UNVERIFIED_B18"   # used before ED-20; appears only in old ledgers
FORMAT_NOT_SELECTED_FOR_DATE = "FORMAT_NOT_SELECTED_FOR_DATE"
FORMAT_UNKNOWN = "FORMAT_UNKNOWN"
PARSE_FAILED = "PARSE_FAILED"
NOT_AN_ARCHIVE = "NOT_AN_ARCHIVE"
REVISION_OF_HELD_SESSION = "REVISION_OF_HELD_SESSION"
RAW_NAME_CONFLICT = "RAW_NAME_CONFLICT"

# daily_update statuses
NOT_A_TRADING_SESSION = "NOT_A_TRADING_SESSION"
FILE_NOT_YET_AVAILABLE = "FILE_NOT_YET_AVAILABLE"
SESSION_MISSING_ALERT = "SESSION_MISSING_ALERT"
ALREADY_HELD = "ALREADY_HELD"                  # session held and no new file offered

_MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
_HEADER_PEEK = 4096


class AcquisitionError(ValueError):
    """A usage or input error; nothing was ingested by the failing call."""


def legacy_name(session_date):
    """cmDDMMMYYYYbhav.csv.zip, the legacy archive name for a date."""
    return "cm%02d%s%04dbhav.csv.zip" % (session_date.day, _MONTHS[session_date.month - 1], session_date.year)


def expected_name(session_date):
    """The archive name NSE serves for the format selected for this date (ED-20)."""
    return bhavcopy.official_name(session_date)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --- providers --------------------------------------------------------------------------

class Provider(object):
    """Where the files for a session are found. list_available returns LOCAL paths only;
    see the module docstring for how a licensed provider would plug in."""
    name = "abstract"
    kind = "abstract"

    def list_available(self, session_date):
        raise NotImplementedError


class LocalInboxProvider(Provider):
    """A folder the owner downloads into. A session's file is the archive named by the NSE
    convention for the format selected for that date; any other file is not offered."""
    name = "local_inbox"
    kind = "LOCAL_FILES"

    def __init__(self, inbox_dir):
        self.inbox_dir = inbox_dir

    def list_available(self, session_date):
        path = os.path.join(self.inbox_dir, expected_name(session_date))
        return [path] if os.path.isfile(path) else []


# --- format detection -------------------------------------------------------------------

def _header_format(first_line):
    text = first_line.decode("utf-8", "replace").lstrip("﻿").rstrip("\r\n")
    cols = tuple(c.strip() for c in text.split(","))
    if cols in (bhavcopy.LEGACY_HEADER, bhavcopy.LEGACY_HEADER_13):     # 13 columns: ED-38, strict parse decides
        return LEGACY_BHAVCOPY
    if cols[:len(UDIFF_LEADING_COLUMNS)] == UDIFF_LEADING_COLUMNS:
        return UDIFF_BHAVCOPY
    return UNKNOWN


def detect_format(path):
    """Triage label from the CSV header (inside the zip, if it is one). Tolerant on purpose
    (BOM, CR, spaces): a legacy file with such a defect is labelled legacy and then refused
    by the strict parse with the loader's own message."""
    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as z:
                infos = z.infolist()
                if len(infos) != 1:
                    return UNKNOWN
                with z.open(infos[0]) as fh:
                    return _header_format(fh.readline(_HEADER_PEEK))
        with open(path, "rb") as fh:
            return _header_format(fh.readline(_HEADER_PEEK))
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError):
        return UNKNOWN


# --- manifest state ---------------------------------------------------------------------

def _held_archives(manifest_path):
    """ARCHIVE rows of the manifest, by trade date."""
    by_date = {}
    for r in bhavcopy.read_manifest(manifest_path):
        if r["kind"] == "ARCHIVE":
            by_date.setdefault(r["trade_date"], []).append(r)
    return by_date


def _session_label(calendar, d):
    """(label, detail) for one date. A calendar that cannot answer never yields EXPECTED."""
    if calendar is None:
        return (CALENDAR_UNVALIDATED, "no calendar") if d.weekday() < 5 else (None, "weekend")
    try:
        if calendar.is_trading_day(d):
            return EXPECTED, ""
        excluded = getattr(calendar, "is_excluded_session", None)
        if excluded is not None and excluded(d):
            return EXCLUDED_SESSION, "Muhurat or shortened session"
        return CLOSED_DAY, "calendar: not a trading day"
    except cal_mod.CalendarCoverageError as e:
        return (CALENDAR_UNVALIDATED, str(e)) if d.weekday() < 5 else (None, "weekend")
    except cal_mod.CalendarAmbiguityError as e:
        return CALENDAR_AMBIGUOUS, str(e)


def _file_status(d, held, raw_dir):
    """(status, file_name, detail) for one date from the manifest and the raw folder."""
    name = expected_name(d)
    path = os.path.join(raw_dir, name)
    records = held.get(d.isoformat(), [])
    present = os.path.isfile(path)
    if not records:
        if present:
            return NOT_IN_MANIFEST, name, "raw file present without an ARCHIVE manifest record"
        return MISSING, name, ""
    if len(records) != 1:
        return HASH_MISMATCH, name, "%d ARCHIVE manifest records for one date" % len(records)
    rec = records[0]
    rpath = os.path.join(raw_dir, rec["file_name"])
    if not os.path.isfile(rpath):
        return MISSING, rec["file_name"], "manifest record present, raw file absent"
    if sha256_file(rpath) != rec["sha256"]:
        return HASH_MISMATCH, rec["file_name"], "raw file SHA-256 differs from the manifest"
    return HELD, rec["file_name"], ""


def plan(calendar, start, end, manifest_path, raw_dir):
    """One row per session in [start, end]: what is held and what is still needed.
    Closed days appear only when a file or manifest record exists for them."""
    if start > end:
        raise AcquisitionError("start %s is after end %s" % (start, end))
    held = _held_archives(manifest_path)
    rows, d = [], start
    while d <= end:
        label, why = _session_label(calendar, d)
        status, name, detail = _file_status(d, held, raw_dir)
        if label in (None, CLOSED_DAY):
            label = CLOSED_DAY
            if status == MISSING and not held.get(d.isoformat()):
                d += datetime.timedelta(days=1)
                continue                     # a closed day with no file: nothing to report
        rows.append({"session_date": d.isoformat(), "calendar_status": label, "calendar_detail": why,
                     "status": status, "file_name": name, "detail": detail,
                     "format": bhavcopy.selected_format(d), "url": bhavcopy.official_url(d)})
        d += datetime.timedelta(days=1)
    return rows


def coverage(plan_rows):
    """Counts and gaps. Only EXPECTED sessions can be missing; CALENDAR_UNVALIDATED
    weekdays without a file are listed separately as unconfirmed candidates."""
    by_status, by_cal = {}, {}
    for r in plan_rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        by_cal[r["calendar_status"]] = by_cal.get(r["calendar_status"], 0) + 1
    held = sorted(r["session_date"] for r in plan_rows if r["status"] == HELD)
    pick = lambda st, cal: sorted(r["session_date"] for r in plan_rows
                                  if r["status"] == st and r["calendar_status"] == cal)
    return {
        "counts_by_status": dict(sorted(by_status.items())),
        "counts_by_calendar_status": dict(sorted(by_cal.items())),
        "first_held": held[0] if held else None,
        "last_held": held[-1] if held else None,
        "missing_sessions": pick(MISSING, EXPECTED),
        "missing_candidate_weekdays_calendar_unvalidated": pick(MISSING, CALENDAR_UNVALIDATED),
        "missing_on_ambiguous_dates": pick(MISSING, CALENDAR_AMBIGUOUS),
        "hash_mismatch": sorted(r["session_date"] for r in plan_rows if r["status"] == HASH_MISMATCH),
        "not_in_manifest": sorted(r["session_date"] for r in plan_rows if r["status"] == NOT_IN_MANIFEST),
        "files_on_closed_days": sorted(r["session_date"] for r in plan_rows
                                       if r["calendar_status"] == CLOSED_DAY),
        "complete": not (pick(MISSING, EXPECTED) or by_status.get(HASH_MISMATCH)
                         or by_status.get(NOT_IN_MANIFEST) or by_cal.get(CALENDAR_UNVALIDATED)
                         or by_cal.get(CALENDAR_AMBIGUOUS)),
    }


# --- ledger -----------------------------------------------------------------------------

def _dumps(obj):
    return json.dumps(obj, sort_keys=True)


def append_ledger(ledger_path, entry):
    parent = os.path.dirname(os.path.abspath(ledger_path))
    os.makedirs(parent, exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(_dumps(entry) + "\n")


def read_ledger(ledger_path):
    if not os.path.isfile(ledger_path):
        return []
    out = []
    with open(ledger_path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError as e:
                    raise AcquisitionError("%s line %d: not JSON (%s)" % (ledger_path, i, e))
    return out


# --- ingestion --------------------------------------------------------------------------

def _quarantine(src, name, sha, quarantine_dir, record):
    """Copy src into quarantine_dir with its reason record; an existing copy of the same
    bytes is left as it is (its first record stands)."""
    os.makedirs(quarantine_dir, exist_ok=True)
    dest = os.path.join(quarantine_dir, "%s_%s" % (sha, name))
    if not os.path.exists(dest):
        shutil.copyfile(src, dest)
        with open(dest + ".reason.json", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(record, sort_keys=True, indent=1) + "\n")
    return dest


def _copy_verified(src, dest, sha):
    tmp = dest + ".partial"
    shutil.copyfile(src, tmp)
    if sha256_file(tmp) != sha:
        os.remove(tmp)
        raise AcquisitionError("%s: copy does not match the source SHA-256" % src)
    os.replace(tmp, dest)


def ingest(paths, raw_dir, manifest_path, quarantine_dir, ledger_path, source_page, downloaded_on,
           provenance_status, recorded_at):
    """Verify and ingest local files, in sorted path order. Returns one outcome dict per
    path (also appended to the ledger). Order of checks per file: present, SHA-256 already
    held (DUPLICATE), format (UDiFF / unknown quarantined), legacy archive name, strict
    parse (failure quarantined with the loader's error), revision of a held session
    (quarantined), name clash in raw_dir, then copy + manifest rows."""
    if not str(recorded_at or "").strip():
        raise AcquisitionError("recorded_at is required (the clock is never read)")
    manifest_tool.rows_for([], manifest_path, source_page, downloaded_on, provenance_status)  # validates
    out = []
    for src in sorted(paths, key=lambda p: (os.path.basename(p), p)):
        res = _ingest_one(src, raw_dir, manifest_path, quarantine_dir, source_page, downloaded_on,
                          provenance_status, recorded_at)
        append_ledger(ledger_path, res)
        out.append(res)
    return out


def _ingest_one(src, raw_dir, manifest_path, quarantine_dir, source_page, downloaded_on,
                provenance_status, recorded_at):
    name = os.path.basename(src)
    res = {"event": "INGEST", "recorded_at": recorded_at, "source_path": src, "file_name": name,
           "sha256": None, "size_bytes": None, "format": None, "session_date": None,
           "outcome": None, "reason": None, "detail": "", "raw_path": None, "quarantine_path": None,
           "source_page": source_page, "downloaded_on": downloaded_on, "provenance_status": provenance_status}
    if not os.path.isfile(src):
        res.update(outcome=SOURCE_NOT_FOUND, reason=SOURCE_NOT_FOUND, detail="no such file")
        return res
    sha = sha256_file(src)
    res.update(sha256=sha, size_bytes=os.path.getsize(src))
    held = _held_archives(manifest_path)
    for d, recs in sorted(held.items()):
        for r in recs:
            if r["sha256"] == sha:
                res.update(outcome=DUPLICATE, session_date=d,
                           detail="identical bytes already held as %s" % r["file_name"])
                return res

    def quarantine(outcome, reason, detail, **extra):
        rec = {"file_name": name, "sha256": sha, "reason": reason, "detail": detail,
               "recorded_at": recorded_at, "source_path": src}
        rec.update(extra)
        res.update(outcome=outcome, reason=reason, detail=detail,
                   quarantine_path=_quarantine(src, name, sha, quarantine_dir, rec))
        return res

    fmt = detect_format(src)
    res["format"] = fmt
    if fmt == UNKNOWN:
        return quarantine(QUARANTINED, FORMAT_UNKNOWN, "header is neither legacy bhavcopy nor UDiFF")
    if not name.endswith(".csv.zip"):
        return quarantine(QUARANTINED, NOT_AN_ARCHIVE,
                          "only official .csv.zip archives are ingested (manifest ARCHIVE rows)")
    try:
        f = bhavcopy.load(src)                       # strict: raises on any deviation
    except bhavcopy.BhavcopyError as e:
        return quarantine(QUARANTINED, PARSE_FAILED, "%s: %s" % (type(e).__name__, e))
    d = f.trade_date.isoformat()
    res["session_date"] = d
    res["schema_version"] = f.schema_version
    selected = bhavcopy.selected_format(f.trade_date)
    if f.format != selected:
        return quarantine(QUARANTINED, FORMAT_NOT_SELECTED_FOR_DATE,
                          "%s is a verified %s file, but %s is the selected source for %s (ED-20); "
                          "kept for cross-checking only" % (name, f.format, selected, d), session_date=d)
    if held.get(d):
        h = held[d][0]
        return quarantine(REVISED_FILE_QUARANTINED, REVISION_OF_HELD_SESSION,
                          "session %s already held as %s with SHA-256 %s; the held file is kept"
                          % (d, h["file_name"], h["sha256"]), held_sha256=h["sha256"], session_date=d)
    os.makedirs(raw_dir, exist_ok=True)
    dest = os.path.join(raw_dir, name)
    preexisting = os.path.exists(dest)
    if preexisting and sha256_file(dest) != sha:
        return quarantine(QUARANTINED, RAW_NAME_CONFLICT,
                          "%s exists in the raw folder with different bytes and no manifest record" % name,
                          session_date=d)
    try:
        rows = manifest_tool.rows_for([src], manifest_path, source_page, downloaded_on, provenance_status)
    except manifest_tool.ManifestError as e:
        return quarantine(QUARANTINED, PARSE_FAILED, "manifest: %s" % e, session_date=d)
    if not preexisting:
        _copy_verified(src, dest, sha)
    manifest_tool.append(manifest_path, rows)
    res.update(outcome=INGESTED, raw_path=dest,
               detail="raw file was already present; manifest rows added" if preexisting else "")
    return res


# --- daily update -----------------------------------------------------------------------

def _attempts(ledger_path, session_date):
    return sum(1 for e in read_ledger(ledger_path)
               if e.get("event") == "DAILY_UPDATE" and e.get("session_date") == session_date
               and e.get("status") in (FILE_NOT_YET_AVAILABLE, SESSION_MISSING_ALERT))


def daily_update(session_date, provider, calendar, raw_dir, manifest_path, quarantine_dir, ledger_path,
                 source_page, downloaded_on, provenance_status, recorded_at, max_attempts):
    """One scheduler-ready step for one session (cron calls the CLI; no daemon here).
    Returns {"status", "alert", ...}; the status is also appended to the ledger."""
    if not isinstance(max_attempts, int) or max_attempts < 1:
        raise AcquisitionError("max_attempts must be a whole number >= 1")
    if not str(recorded_at or "").strip():
        raise AcquisitionError("recorded_at is required (the clock is never read)")
    d = session_date.isoformat()
    label, why = _session_label(calendar, session_date)
    out = {"event": "DAILY_UPDATE", "session_date": d, "recorded_at": recorded_at, "provider": provider.name,
           "provider_kind": provider.kind, "calendar_status": label or CLOSED_DAY, "calendar_detail": why,
           "status": None, "alert": None, "attempt": None, "max_attempts": max_attempts, "results": [],
           "outcome_if_expected": None}

    def alert(kind, reason):
        return {"alert": kind, "session_date": d, "reason": reason, "recorded_at": recorded_at}

    if label in (None, CLOSED_DAY, EXCLUDED_SESSION):
        out["status"] = NOT_A_TRADING_SESSION
        append_ledger(ledger_path, out)
        return out
    files = provider.list_available(session_date)
    if files:
        out["results"] = ingest(files, raw_dir, manifest_path, quarantine_dir, ledger_path, source_page,
                                downloaded_on, provenance_status, recorded_at)
        outcomes = set(r["outcome"] for r in out["results"])
        bad = [r for r in out["results"] if r["outcome"] in (QUARANTINED, REVISED_FILE_QUARANTINED, SOURCE_NOT_FOUND)]
        if INGESTED in outcomes:
            status = INGESTED
        elif bad:
            status = QUARANTINED
        else:
            status = DUPLICATE
        if bad:
            out["alert"] = alert("QUALITY_FAILURE", "; ".join("%s: %s" % (r["file_name"], r["reason"]) for r in bad))
    else:
        st, _, _ = _file_status(session_date, _held_archives(manifest_path), raw_dir)
        if st == HELD:
            status = ALREADY_HELD
        else:
            out["attempt"] = _attempts(ledger_path, d) + 1
            status = SESSION_MISSING_ALERT if out["attempt"] >= max_attempts else FILE_NOT_YET_AVAILABLE
            if status == SESSION_MISSING_ALERT:
                out["alert"] = alert("SESSION_MISSING", "no file after %d attempts" % out["attempt"])
    if label != EXPECTED:
        # without a calendar answer the session is not known to be expected: the files
        # offered are still verified and ingested, but nothing is called missing
        out["outcome_if_expected"] = status
        status = CALENDAR_UNVALIDATED
        if out["alert"] and out["alert"]["alert"] == "SESSION_MISSING":
            out["alert"] = None
    out["status"] = status
    ledger_entry = dict(out)
    ledger_entry["results"] = [r["outcome"] for r in out["results"]]
    append_ledger(ledger_path, ledger_entry)
    return out


# --- command line -----------------------------------------------------------------------

def _date(text):
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise AcquisitionError("%r is not YYYY-MM-DD" % text)


def _calendar(folder):
    if not folder:
        return None
    try:
        return cal_mod.NseCalendar.load(folder)
    except (cal_mod.CalendarError, OSError) as e:
        raise AcquisitionError("calendar not loadable: %s" % e)


def _emit(obj, out_path):
    text = json.dumps(obj, sort_keys=True, indent=1) + "\n"
    print(text, end="")
    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)


def _guard(fn):
    def run(args):
        try:
            return fn(args)
        except (AcquisitionError, manifest_tool.ManifestError, bhavcopy.BhavcopyError, OSError) as e:
            sys.stderr.write("error: %s\n" % e)
            return 2
    return run


@_guard
def cmd_plan(args):
    rows = plan(_calendar(args.calendar), _date(args.start), _date(args.end), args.manifest, args.raw_dir)
    cov = coverage(rows)
    _emit({"calendar": args.calendar or CALENDAR_UNVALIDATED, "coverage": cov, "rows": rows}, args.out)
    return 1 if cov["hash_mismatch"] else 0


@_guard
def cmd_coverage(args):
    cov = coverage(plan(_calendar(args.calendar), _date(args.start), _date(args.end), args.manifest, args.raw_dir))
    _emit(dict(cov, calendar=args.calendar or CALENDAR_UNVALIDATED), args.out)
    return 1 if cov["hash_mismatch"] else 0


@_guard
def cmd_ingest(args):
    res = ingest(args.files, args.raw_dir, args.manifest, args.quarantine_dir, args.ledger, args.source_page,
                 args.downloaded_on, args.provenance_status, args.recorded_at)
    _emit({"results": res}, args.out)
    return 1 if any(r["outcome"] not in (INGESTED, DUPLICATE) for r in res) else 0


@_guard
def cmd_daily(args):
    res = daily_update(_date(args.session_date), LocalInboxProvider(args.inbox), _calendar(args.calendar),
                       args.raw_dir, args.manifest, args.quarantine_dir, args.ledger, args.source_page,
                       args.downloaded_on, args.provenance_status, args.recorded_at, args.max_attempts)
    _emit(res, args.out)
    return 1 if res["alert"] else 0


def _common(p, ingest_args):
    p.add_argument("--manifest", default=EOD_MANIFEST)
    p.add_argument("--raw-dir", default=EOD_RAW_DIR)
    if ingest_args:
        p.add_argument("--quarantine-dir", required=True, help="refused files are copied here with a reason")
        p.add_argument("--ledger", required=True, help="append-only JSONL ledger")
        p.add_argument("--source-page", required=True, help="the page the files came from, as you recorded it")
        p.add_argument("--downloaded-on", required=True, help="YYYY-MM-DD or UNKNOWN (never a file time)")
        p.add_argument("--provenance-status", required=True, help="e.g. USER_CONFIRMED")
        p.add_argument("--recorded-at", required=True, help="label written to the ledger; no clock is read")
    p.add_argument("--out", help="also write the JSON here")


def add_commands(subparsers):
    p = subparsers.add_parser("acquire-plan", help="per-session backfill plan from local EOD files (resumable)")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--calendar", help="calendar folder; omitted -> weekdays are CALENDAR_UNVALIDATED candidates")
    _common(p, False)
    p.set_defaults(func=cmd_plan)
    c = subparsers.add_parser("acquire-coverage", help="coverage counts and missing sessions")
    c.add_argument("--start", required=True)
    c.add_argument("--end", required=True)
    c.add_argument("--calendar")
    _common(c, False)
    c.set_defaults(func=cmd_coverage)
    i = subparsers.add_parser("acquire-ingest", help="verify, quarantine or ingest downloaded EOD files (copies only)")
    i.add_argument("files", nargs="+")
    _common(i, True)
    i.set_defaults(func=cmd_ingest)
    u = subparsers.add_parser("daily-update", help="one session from a local inbox folder (cron-ready)")
    u.add_argument("--session-date", required=True)
    u.add_argument("--inbox", required=True, help="folder the owner downloads into")
    u.add_argument("--calendar", help="calendar folder; omitted -> CALENDAR_UNVALIDATED")
    u.add_argument("--max-attempts", type=int, required=True, help="no-file attempts before SESSION_MISSING_ALERT")
    _common(u, True)
    u.set_defaults(func=cmd_daily)
