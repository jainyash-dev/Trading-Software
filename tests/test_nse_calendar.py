"""nse/calendar tests. Every file here is SYNTHETIC: the "circulars" are placeholder
bytes and the events are invented test rows, not a transcription of real NSE
circulars. Real data is added only after the user places the official PDFs.
"""

import csv
import datetime
import hashlib
import os
import shutil
import tempfile
import unittest

from _load import load

cal_mod = load(os.path.join("nse", "calendar"), "nse_calendar")
mtf = load(os.path.join("nse", "mtf-freshness"), "mtf_freshness")
D = datetime.date


def write_csv(path, columns, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(columns)
        for r in rows:
            w.writerow([r.get(c, "") for c in columns])


class Fixture(object):
    """A temporary calendar folder: circulars/, sources.csv, events.csv."""

    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="nse-cal-test-")
        os.mkdir(os.path.join(self.dir, "circulars"))
        self.sources = []
        self.events = []

    def circular(self, ref, kind, year, content=None, hash_override=None, write=True):
        name = ref.replace("/", "_") + ".pdf"
        data = content if content is not None else ("placeholder for %s" % ref).encode()
        if write:
            with open(os.path.join(self.dir, "circulars", name), "wb") as fh:
                fh.write(data)
        self.sources.append({
            "source_ref": ref, "kind": kind, "applicable_year": str(year), "doc_date": "%d-12-01" % (year - 1),
            "title": "Trading holidays for the calendar year %d" % year, "file_name": name,
            "sha256": hash_override or hashlib.sha256(data).hexdigest(), "downloaded_on": "2026-10-26",
            "url": "https://example.invalid/%s" % name})
        return self

    def event(self, date, event, ref, start="", end="", status="CONFIRMED", note="", description="test"):
        self.events.append({"date": date, "event": event, "description": description,
                            "session_start": start, "session_end": end, "source_ref": ref,
                            "status": status, "note": note})
        return self

    def load(self):
        write_csv(os.path.join(self.dir, "sources.csv"), cal_mod.SOURCE_COLUMNS, self.sources)
        write_csv(os.path.join(self.dir, "events.csv"), cal_mod.EVENT_COLUMNS, self.events)
        return cal_mod.NseCalendar.load(self.dir)

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()
        self.addCleanup(self.f.close)


class Provenance(Base):
    def test_verified_base_circular_covers_its_year(self):
        c = self.f.circular("T/BASE/2024", "BASE", 2024).load()
        self.assertEqual(c.covered_years, [2024])
        self.assertEqual(c.sources["T/BASE/2024"].file_status, cal_mod.VERIFIED)
        self.assertTrue(c.is_trading_day(D(2024, 3, 4)))

    def test_missing_file_leaves_the_year_uncovered(self):
        c = self.f.circular("T/BASE/2024", "BASE", 2024, write=False).load()
        self.assertEqual(c.covered_years, [])
        self.assertEqual(c.sources["T/BASE/2024"].file_status, cal_mod.MISSING_FILE)
        with self.assertRaises(cal_mod.CalendarCoverageError):
            c.is_trading_day(D(2024, 3, 4))

    def test_hash_mismatch_leaves_the_year_uncovered(self):
        c = self.f.circular("T/BASE/2024", "BASE", 2024, hash_override="0" * 64).load()
        self.assertEqual(c.sources["T/BASE/2024"].file_status, cal_mod.HASH_MISMATCH)
        with self.assertRaises(cal_mod.CalendarCoverageError):
            c.session_type(D(2024, 3, 4))

    def test_no_weekday_fallback_outside_covered_years(self):
        c = self.f.circular("T/BASE/2024", "BASE", 2024).load()
        with self.assertRaises(cal_mod.CalendarCoverageError):
            c.is_trading_day(D(2025, 3, 4))

    def test_event_from_an_unverified_amendment_is_not_trusted(self):
        c = (self.f.circular("T/BASE/2024", "BASE", 2024)
             .circular("T/AMEND/2024", "AMENDMENT", 2024, write=False)
             .event("2024-05-20", "HOLIDAY", "T/AMEND/2024").load())
        self.assertEqual([s.source_ref for s in c.unverified_sources], ["T/AMEND/2024"])
        with self.assertRaises(cal_mod.CalendarAmbiguityError):
            c.is_trading_day(D(2024, 5, 20))
        self.assertTrue(c.is_trading_day(D(2024, 5, 21)))     # other dates unaffected


class SessionTypes(Base):
    def cal(self):
        return (self.f.circular("T/BASE/2024", "BASE", 2024)
                .event("2024-03-25", "HOLIDAY", "T/BASE/2024")
                .event("2024-11-01", "HOLIDAY", "T/BASE/2024", description="Diwali")
                .event("2024-11-01", "MUHURAT_SESSION", "T/BASE/2024", "18:00", "19:00")
                .event("2024-01-20", "SPECIAL_SESSION", "T/BASE/2024", "09:15", "15:30")
                .event("2024-03-02", "SHORTENED_SESSION", "T/BASE/2024", "09:15", "10:00")
                .event("2024-05-18", "SPECIAL_SESSION", "T/BASE/2024", "09:15", "12:40")
                .load())

    def test_each_kind_of_day(self):
        c = self.cal()
        cases = {
            D(2024, 3, 4): (cal_mod.NORMAL, True),
            D(2024, 3, 9): (cal_mod.WEEKEND, False),
            D(2024, 3, 25): (cal_mod.HOLIDAY, False),
            D(2024, 11, 1): (cal_mod.EXCLUDED_MUHURAT, False),     # flagged, never a normal candle
            D(2024, 1, 20): (cal_mod.NORMAL_SPECIAL, True),        # Saturday on regular hours
            D(2024, 3, 2): (cal_mod.EXCLUDED_SHORTENED, False),
            D(2024, 5, 18): (cal_mod.EXCLUDED_SHORTENED, False),   # special, but not regular hours
        }
        for d, (st, trading) in cases.items():
            self.assertEqual(c.session_type(d), st, d)
            self.assertEqual(c.is_trading_day(d), trading, d)
        self.assertTrue(c.is_excluded_session(D(2024, 11, 1)))
        self.assertEqual(sorted(c.flagged_dates()), [D(2024, 1, 20), D(2024, 3, 2), D(2024, 5, 18), D(2024, 11, 1)])

    def test_unresolved_rows_raise_instead_of_guessing(self):
        c = (self.f.circular("T/BASE/2024", "BASE", 2024)
             .event("2024-11-20", "HOLIDAY", "T/BASE/2024", status="UNRESOLVED",
                    note="sources disagree on full vs partial closure").load())
        with self.assertRaises(cal_mod.CalendarAmbiguityError):
            c.is_trading_day(D(2024, 11, 20))


class Validation(Base):
    def test_rejects_malformed_tables(self):
        bad = [
            lambda f: f.event("2024-13-01", "HOLIDAY", "T/BASE/2024"),
            lambda f: f.event("2024-03-25", "CLOSED", "T/BASE/2024"),
            lambda f: f.event("2024-03-25", "HOLIDAY", "T/NOPE/2024"),
            lambda f: f.event("2024-03-25", "HOLIDAY", "T/BASE/2024", "09:15", "15:30"),
            lambda f: f.event("2024-01-20", "SPECIAL_SESSION", "T/BASE/2024", "15:30", "09:15"),
            lambda f: f.event("2024-01-20", "SPECIAL_SESSION", "T/BASE/2024", "9am", "3pm"),
            lambda f: f.event("2024-11-20", "HOLIDAY", "T/BASE/2024", status="UNRESOLVED"),   # no note
            lambda f: f.event("2024-03-25", "HOLIDAY", "T/BASE/2024").event("2024-03-25", "HOLIDAY", "T/BASE/2024"),
            lambda f: f.event("2024-01-22", "HOLIDAY", "T/BASE/2024")
                       .event("2024-01-22", "SPECIAL_SESSION", "T/BASE/2024", "09:15", "15:30"),
        ]
        for i, add in enumerate(bad):
            f = Fixture()
            try:
                add(f.circular("T/BASE/2024", "BASE", 2024))
                with self.assertRaises(cal_mod.CalendarError, msg=str(i)):
                    f.load()
            finally:
                f.close()

    def test_rejects_wrong_header(self):
        self.f.circular("T/BASE/2024", "BASE", 2024)
        write_csv(os.path.join(self.f.dir, "sources.csv"), cal_mod.SOURCE_COLUMNS, self.f.sources)
        with open(os.path.join(self.f.dir, "events.csv"), "w", encoding="utf-8") as fh:
            fh.write("date,event\n2024-03-25,HOLIDAY\n")
        with self.assertRaises(cal_mod.CalendarError):
            cal_mod.NseCalendar.load(self.f.dir)

    def test_conflict_is_allowed_once_marked_unresolved(self):
        c = (self.f.circular("T/BASE/2024", "BASE", 2024)
             .event("2024-01-22", "HOLIDAY", "T/BASE/2024")
             .event("2024-01-22", "SPECIAL_SESSION", "T/BASE/2024", status="UNRESOLVED", note="contradiction")
             .load())
        with self.assertRaises(cal_mod.CalendarAmbiguityError):
            c.session_type(D(2024, 1, 22))


class Reconcile(Base):
    def test_every_disagreement_is_reported(self):
        c = (self.f.circular("T/BASE/2024", "BASE", 2024)
             .event("2024-03-25", "HOLIDAY", "T/BASE/2024")
             .event("2024-03-29", "HOLIDAY", "T/BASE/2024")
             .event("2024-03-30", "SHORTENED_SESSION", "T/BASE/2024", "09:15", "10:00")
             .event("2024-03-27", "HOLIDAY", "T/BASE/2024", status="UNRESOLVED", note="unclear").load())
        start, end = D(2024, 3, 25), D(2024, 3, 31)
        eod = {D(2024, 3, 25),               # file on a holiday: calendar or data is wrong
               D(2024, 3, 26),               # normal, fine
               D(2024, 3, 30),               # shortened session: expected, flagged only
               D(2024, 3, 31)}               # Sunday with a file: unlisted session?
        r = cal_mod.reconcile(c, eod, start, end)
        self.assertEqual(r.eod_on_closed_day, [D(2024, 3, 25), D(2024, 3, 31)])
        self.assertEqual(r.missing_eod_on_trading_day, [D(2024, 3, 28)])
        self.assertEqual(r.eod_on_excluded_session, [D(2024, 3, 30)])
        self.assertEqual(r.unresolved, [D(2024, 3, 27)])
        self.assertFalse(r.clean)

    def test_clean_when_everything_agrees(self):
        c = self.f.circular("T/BASE/2024", "BASE", 2024).event("2024-03-29", "HOLIDAY", "T/BASE/2024").load()
        eod = {D(2024, 3, 25), D(2024, 3, 26), D(2024, 3, 27), D(2024, 3, 28)}
        r = cal_mod.reconcile(c, eod, D(2024, 3, 25), D(2024, 3, 31))
        self.assertTrue(r.clean)

    def test_dates_outside_coverage_are_reported(self):
        c = self.f.circular("T/BASE/2024", "BASE", 2024).load()
        r = cal_mod.reconcile(c, {D(2025, 1, 1)}, D(2024, 12, 31), D(2025, 1, 2))
        self.assertEqual(r.outside_coverage, [D(2025, 1, 1), D(2025, 1, 2)])
        self.assertFalse(r.clean)


class OrchestratorIntegration(Base):
    def test_validated_calendar_drives_the_orchestrator(self):
        c = (self.f.circular("T/BASE/2025", "BASE", 2025)
             .event("2025-02-14", "HOLIDAY", "T/BASE/2025").load())
        days = [D(2025, 2, 10) + datetime.timedelta(days=i) for i in range(4)]   # Mon-Thu; Fri holiday
        cs = [mtf.TimedCandle(datetime.datetime.combine(d, datetime.time(9, 15)),
                              datetime.datetime.combine(d, datetime.time(15, 30)), 100, 101, 99, 100)
              for d in days]
        s = mtf.replay(cs, "D", htf=("W",), as_of=datetime.datetime(2025, 2, 13, 15, 30), calendar=c)
        self.assertTrue(s.calendar_validated)
        self.assertNotIn(mtf.CALENDAR_UNVALIDATED, s.limitations)
        self.assertEqual(s.data_gaps, [])
        self.assertEqual(s.series["W"].candles[-1].known_at, datetime.datetime(2025, 2, 13, 15, 30))

    def test_uncovered_year_stops_the_orchestrator(self):
        c = self.f.circular("T/BASE/2025", "BASE", 2025).load()
        cs = [mtf.TimedCandle(datetime.datetime(2024, 12, 30, 9, 15), datetime.datetime(2024, 12, 30, 15, 30),
                              100, 101, 99, 100)]
        with self.assertRaises(cal_mod.CalendarCoverageError):
            mtf.replay(cs, "D", htf=("W",), calendar=c)


if __name__ == "__main__":
    unittest.main()
