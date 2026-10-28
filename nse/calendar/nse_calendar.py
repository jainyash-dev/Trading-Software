#!/usr/bin/env python3
"""NSE capital-market trading calendar, built only from local files. Standard library only.

Resolves blocker B17 once the official circulars are in place. Nothing is fetched:
the user downloads the NSE circulars, a person transcribes their dates into
events.csv, and this module checks every circular's SHA-256 against sources.csv
before trusting a year.

Two files (formats below), normally in nse/data/calendar/:

sources.csv   one row per circular
    source_ref       e.g. NSE/CMTR/59722
    kind             BASE (the year's holiday circular) | AMENDMENT | SESSION_NOTICE
    applicable_year  e.g. 2024
    doc_date         date printed on the circular, YYYY-MM-DD
    title            subject line of the circular
    file_name        the PDF, relative to the circulars/ folder
    sha256           hash of that file
    downloaded_on    YYYY-MM-DD, or UNKNOWN when the download date was not recorded
                     (never inferred from a file's modification time)
    url              where it was downloaded from (provenance only; never fetched)

events.csv    one row per dated event
    date             YYYY-MM-DD
    event            HOLIDAY | SPECIAL_SESSION | MUHURAT_SESSION | SHORTENED_SESSION
    description      as printed in the circular
    session_start    HH:MM, required for session events
    session_end      HH:MM, required for session events
    source_ref       must exist in sources.csv. Only an UNRESOLVED row may leave it
                     empty: a date blocked on evidence that is not yet a registered
                     circular (the note says what that evidence is)
    status           CONFIRMED | UNRESOLVED
    note             free text (e.g. why a row is UNRESOLVED)

Rules (user decisions, 2026-10-26; DECISION_LOG D29-D32):
  - A year is usable only if its BASE circular file is present and its hash matches.
    Asking about any other date raises CalendarCoverageError: no weekday fallback.
  - A date with an UNRESOLVED row raises CalendarAmbiguityError: never guessed.
  - MUHURAT_SESSION and SHORTENED_SESSION days are flagged and EXCLUDED from normal
    candle construction until a documented rule is approved.
  - A SPECIAL_SESSION held on the regular 09:15-15:30 hours (e.g. a budget Saturday)
    is a normal trading day, flagged as special. Any other hours count as shortened.

reconcile() compares the calendar with the set of dates that actually have an NSE
end-of-day file. Every disagreement is reported; none is silently resolved.
"""

import csv
import datetime
import hashlib
import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

REGULAR_OPEN = "09:15"
REGULAR_CLOSE = "15:30"

KINDS = ("BASE", "AMENDMENT", "SESSION_NOTICE")
EVENTS = ("HOLIDAY", "SPECIAL_SESSION", "MUHURAT_SESSION", "SHORTENED_SESSION")
STATUSES = ("CONFIRMED", "UNRESOLVED")
SOURCE_COLUMNS = ("source_ref", "kind", "applicable_year", "doc_date", "title", "file_name",
                  "sha256", "downloaded_on", "url")
EVENT_COLUMNS = ("date", "event", "description", "session_start", "session_end",
                 "source_ref", "status", "note")

# session types returned by session_type()
WEEKEND = "WEEKEND"
HOLIDAY = "HOLIDAY"
NORMAL = "NORMAL"
NORMAL_SPECIAL = "NORMAL_SPECIAL"             # special day on regular hours
EXCLUDED_MUHURAT = "EXCLUDED_MUHURAT"
EXCLUDED_SHORTENED = "EXCLUDED_SHORTENED"

DOWNLOAD_DATE_UNKNOWN = "UNKNOWN"             # sources.csv downloaded_on, as in the EOD manifest

VERIFIED = "VERIFIED"
MISSING_FILE = "MISSING_FILE"
HASH_MISMATCH = "HASH_MISMATCH"


class CalendarError(ValueError):
    pass


class CalendarCoverageError(CalendarError):
    """The date's year has no verified BASE circular."""


class CalendarAmbiguityError(CalendarError):
    """The date has an UNRESOLVED event."""


@dataclass(frozen=True)
class Source:
    source_ref: str
    kind: str
    applicable_year: int
    doc_date: datetime.date
    title: str
    file_name: str
    sha256: str
    downloaded_on: Optional[datetime.date]     # None when recorded as UNKNOWN
    url: str
    file_status: str


@dataclass(frozen=True)
class Event:
    date: datetime.date
    event: str
    description: str
    session_start: str
    session_end: str
    source_ref: str
    status: str
    note: str


@dataclass
class Reconciliation:
    eod_on_closed_day: List[datetime.date] = field(default_factory=list)      # file exists, calendar closed
    missing_eod_on_trading_day: List[datetime.date] = field(default_factory=list)
    eod_on_excluded_session: List[datetime.date] = field(default_factory=list)  # expected: flagged only
    outside_coverage: List[datetime.date] = field(default_factory=list)
    unresolved: List[datetime.date] = field(default_factory=list)

    @property
    def clean(self):
        return not (self.eod_on_closed_day or self.missing_eod_on_trading_day
                    or self.outside_coverage or self.unresolved)


def _date(text, what):
    try:
        return datetime.date.fromisoformat(text.strip())
    except ValueError:
        raise CalendarError("%s: %r is not a YYYY-MM-DD date" % (what, text))


def _hhmm(text, what):
    try:
        datetime.datetime.strptime(text.strip(), "%H:%M")
    except ValueError:
        raise CalendarError("%s: %r is not HH:MM" % (what, text))
    return text.strip()


def _rows(path, columns):
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != columns:
            raise CalendarError("%s: header must be exactly %s" % (os.path.basename(path), ",".join(columns)))
        return [dict(r) for r in reader]


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


class NseCalendar(object):
    # Errors that concern ONE date and that a caller may handle per date (audit L10,
    # option B): an UNRESOLVED row or an event from an unverified source. A year without
    # a verified BASE circular (CalendarCoverageError) is a setup error and stays fatal.
    UNRESOLVED_ERRORS = (CalendarAmbiguityError,)

    def __init__(self, sources, events):
        self.sources = {s.source_ref: s for s in sources}
        self.events = sorted(events, key=lambda e: (e.date, e.event))
        self.by_date = {}
        for e in self.events:
            self.by_date.setdefault(e.date, []).append(e)
        self.covered_years = sorted(set(
            s.applicable_year for s in sources if s.kind == "BASE" and s.file_status == VERIFIED))
        self.unverified_sources = [s for s in sources if s.file_status != VERIFIED]

    @classmethod
    def load(cls, folder, circulars_folder=None):
        """Read sources.csv and events.csv from folder; hash-check every circular."""
        circ = circulars_folder or os.path.join(folder, "circulars")
        sources = []
        seen = set()
        for i, r in enumerate(_rows(os.path.join(folder, "sources.csv"), SOURCE_COLUMNS), 2):
            ref = r["source_ref"].strip()
            if not ref or ref in seen:
                raise CalendarError("sources.csv line %d: missing or duplicate source_ref %r" % (i, ref))
            seen.add(ref)
            if r["kind"] not in KINDS:
                raise CalendarError("sources.csv line %d: kind must be one of %s" % (i, ", ".join(KINDS)))
            path = os.path.join(circ, r["file_name"])
            if not r["file_name"] or not os.path.isfile(path):
                status = MISSING_FILE
            elif sha256_of(path) != r["sha256"].strip().lower():
                status = HASH_MISMATCH
            else:
                status = VERIFIED
            downloaded = (None if r["downloaded_on"].strip() == DOWNLOAD_DATE_UNKNOWN
                          else _date(r["downloaded_on"], "sources.csv line %d downloaded_on" % i))
            sources.append(Source(ref, r["kind"], int(r["applicable_year"]),
                                  _date(r["doc_date"], "sources.csv line %d doc_date" % i),
                                  r["title"], r["file_name"], r["sha256"].strip().lower(),
                                  downloaded, r["url"], status))
        events = []
        for i, r in enumerate(_rows(os.path.join(folder, "events.csv"), EVENT_COLUMNS), 2):
            where = "events.csv line %d" % i
            d = _date(r["date"], where + " date")
            if r["event"] not in EVENTS:
                raise CalendarError("%s: event must be one of %s" % (where, ", ".join(EVENTS)))
            if r["status"] not in STATUSES:
                raise CalendarError("%s: status must be CONFIRMED or UNRESOLVED" % where)
            if r["source_ref"] not in seen and not (r["source_ref"] == "" and r["status"] == "UNRESOLVED"):
                raise CalendarError("%s: source_ref %r is not in sources.csv (only an UNRESOLVED row may "
                                    "leave it empty)" % (where, r["source_ref"]))
            start, end = r["session_start"].strip(), r["session_end"].strip()
            if r["event"] == "HOLIDAY":
                if start or end:
                    raise CalendarError("%s: a HOLIDAY has no session times" % where)
            elif r["status"] == "CONFIRMED":
                start, end = _hhmm(start, where + " session_start"), _hhmm(end, where + " session_end")
                if not start < end:
                    raise CalendarError("%s: session_start must be before session_end" % where)
            if r["status"] == "UNRESOLVED" and not r["note"].strip():
                raise CalendarError("%s: an UNRESOLVED row must say why in note" % where)
            events.append(Event(d, r["event"], r["description"], start, end, r["source_ref"],
                                r["status"], r["note"]))
        _check_conflicts(events)
        return cls(sources, events)

    # queries ---------------------------------------------------------------------

    def _covered(self, d):
        if d.year not in self.covered_years:
            raise CalendarCoverageError("%s: no verified BASE circular for %d" % (d, d.year))

    def session_type(self, d):
        self._covered(d)
        evs = self.by_date.get(d, [])
        if any(e.status == "UNRESOLVED" for e in evs):
            raise CalendarAmbiguityError("%s: unresolved calendar event (%s)"
                                         % (d, "; ".join(e.note for e in evs if e.status == "UNRESOLVED")))
        unverified = [e.source_ref for e in evs
                      if e.source_ref and self.sources[e.source_ref].file_status != VERIFIED]
        if unverified:
            raise CalendarAmbiguityError("%s: event source not verified (%s)" % (d, ", ".join(unverified)))
        kinds = set(e.event for e in evs)
        if "MUHURAT_SESSION" in kinds:
            return EXCLUDED_MUHURAT
        if "SHORTENED_SESSION" in kinds:
            return EXCLUDED_SHORTENED
        if "SPECIAL_SESSION" in kinds:
            sp = [e for e in evs if e.event == "SPECIAL_SESSION"][0]
            regular = sp.session_start == REGULAR_OPEN and sp.session_end == REGULAR_CLOSE
            return NORMAL_SPECIAL if regular else EXCLUDED_SHORTENED
        if "HOLIDAY" in kinds:
            return HOLIDAY
        return WEEKEND if d.weekday() >= 5 else NORMAL

    def is_trading_day(self, d):
        """True only for days whose candles take part in normal construction."""
        return self.session_type(d) in (NORMAL, NORMAL_SPECIAL)

    def is_excluded_session(self, d):
        return self.session_type(d) in (EXCLUDED_MUHURAT, EXCLUDED_SHORTENED)

    def flagged_dates(self):
        """Every special, Muhurat or shortened date, with its events (for review)."""
        return {d: evs for d, evs in self.by_date.items()
                if any(e.event != "HOLIDAY" for e in evs)}


def _check_conflicts(events):
    by = {}
    for e in events:
        by.setdefault(e.date, []).append(e)
    for d, evs in by.items():
        kinds = [e.event for e in evs]
        if len(kinds) != len(set(kinds)):
            raise CalendarError("%s: duplicate %s rows" % (d, ", ".join(sorted(kinds))))
        # a holiday may coexist with a Muhurat session (Diwali); with a special or shortened
        # session the circulars contradict each other unless a row is UNRESOLVED
        if "HOLIDAY" in kinds and ({"SPECIAL_SESSION", "SHORTENED_SESSION"} & set(kinds)):
            if not any(e.status == "UNRESOLVED" for e in evs):
                raise CalendarError("%s: HOLIDAY and a trading session on the same date; "
                                    "mark the conflicting row UNRESOLVED with a note" % d)


def reconcile(calendar, eod_dates, start, end):
    """Compare calendar days in [start, end] with the dates that have an EOD file."""
    eod = set(eod_dates)
    r = Reconciliation()
    d = start
    while d <= end:
        try:
            st = calendar.session_type(d)
        except CalendarCoverageError:
            if d in eod or d.weekday() < 5:
                r.outside_coverage.append(d)
            d += datetime.timedelta(days=1)
            continue
        except CalendarAmbiguityError:
            r.unresolved.append(d)
            d += datetime.timedelta(days=1)
            continue
        has = d in eod
        if st in (NORMAL, NORMAL_SPECIAL) and not has:
            r.missing_eod_on_trading_day.append(d)
        elif st in (WEEKEND, HOLIDAY) and has:
            r.eod_on_closed_day.append(d)
        elif st in (EXCLUDED_MUHURAT, EXCLUDED_SHORTENED) and has:
            r.eod_on_excluded_session.append(d)
        d += datetime.timedelta(days=1)
    return r
