"""Tests of the REAL calendar tables in nse/data/calendar/ (B17), as opposed to the
synthetic fixtures in test_nse_calendar.py.

The expected rows below are a second, independent transcription of the official NSE
circulars registered in sources.csv (text-extracted and checked on the rendered pages,
2026-10-28). Any edit to events.csv that disagrees with the printed circulars fails here.

The circular files are local only (git-ignored, D31), and so are the raw EOD files.
Tests that need them call require_local: they skip with a PREREQUISITE MISSING reason
in a normal run and fail in an acceptance run (NSE_PHASE1_ACCEPTANCE=1).
"""

import csv
import datetime
import os
import unittest

from _load import load, require_local, ROOT

cal_mod = load(os.path.join("nse", "calendar"), "nse_calendar")
mtf = load(os.path.join("nse", "mtf-freshness"), "mtf_freshness")
D = datetime.date

CAL_DIR = os.path.join(ROOT, "nse", "data", "calendar")
CIRCULARS = os.path.join(CAL_DIR, "circulars")
MANIFEST = os.path.join(ROOT, "nse", "data", "eod", "manifest.csv")

# Base circulars: date -> (printed day, printed description); (weekday rows, weekend rows)
BASE_HOLIDAYS = {
    "NSE/CMTR/46623": ({   # 2021: 14 weekday rows + 5 Saturday/Sunday rows, one page
        D(2021, 1, 26): ("Tuesday", "Republic Day"),
        D(2021, 3, 11): ("Thursday", "Mahashivratri"),
        D(2021, 3, 29): ("Monday", "Holi"),
        D(2021, 4, 2): ("Friday", "Good Friday"),
        D(2021, 4, 14): ("Wednesday", "Dr.Baba Saheb Ambedkar Jayanti"),
        D(2021, 4, 21): ("Wednesday", "Ram Navami"),
        D(2021, 5, 13): ("Thursday", "Id-Ul-Fitr (Ramzan ID)"),
        D(2021, 7, 21): ("Wednesday", "Bakri Id"),
        D(2021, 8, 19): ("Thursday", "Moharram"),
        D(2021, 9, 10): ("Friday", "Ganesh Chaturthi"),
        D(2021, 10, 15): ("Friday", "Dussehra"),
        D(2021, 11, 4): ("Thursday", "Diwali-Laxmi Pujan*"),
        D(2021, 11, 5): ("Friday", "Diwali-Balipratipada"),
        D(2021, 11, 19): ("Friday", "Gurunanak Jayanti"),
        D(2021, 4, 25): ("Sunday", "Mahavir Jayanti"),
        D(2021, 5, 1): ("Saturday", "Maharashtra Day"),
        D(2021, 8, 15): ("Sunday", "Independence Day"),
        D(2021, 10, 2): ("Saturday", "Mahatma Gandhi Jayanti"),
        D(2021, 12, 25): ("Saturday", "Christmas"),
    }, (14, 5)),
    "NSE/CMTR/50560": ({   # 2022: 13 + 5
        D(2022, 1, 26): ("Wednesday", "Republic Day"),
        D(2022, 3, 1): ("Tuesday", "Mahashivratri"),
        D(2022, 3, 18): ("Friday", "Holi"),
        D(2022, 4, 14): ("Thursday", "Dr. Baba Saheb Ambedkar Jayanti/Mahavir Jayanti"),
        D(2022, 4, 15): ("Friday", "Good Friday"),
        D(2022, 5, 3): ("Tuesday", "Id-Ul-Fitr (Ramzan ID)"),
        D(2022, 8, 9): ("Tuesday", "Moharram"),
        D(2022, 8, 15): ("Monday", "Independence Day"),
        D(2022, 8, 31): ("Wednesday", "Ganesh Chaturthi"),
        D(2022, 10, 5): ("Wednesday", "Dussehra"),
        D(2022, 10, 24): ("Monday", "Diwali-Laxmi Pujan*"),
        D(2022, 10, 26): ("Wednesday", "Diwali-Balipratipada"),
        D(2022, 11, 8): ("Tuesday", "Gurunanak Jayanti"),
        D(2022, 4, 10): ("Sunday", "Ram Navami"),
        D(2022, 5, 1): ("Sunday", "Maharashtra Day"),
        D(2022, 7, 10): ("Sunday", "Bakri Id"),
        D(2022, 10, 2): ("Sunday", "Mahatma Gandhi Jayanti"),
        D(2022, 12, 25): ("Sunday", "Christmas"),
    }, (13, 5)),
    "NSE/CMTR/54757": ({   # 2023: 15 + 4 (28 June later moved by NSE/CMTR/57285)
        D(2023, 1, 26): ("Thursday", "Republic Day"),
        D(2023, 3, 7): ("Tuesday", "Holi"),
        D(2023, 3, 30): ("Thursday", "Ram Navami"),
        D(2023, 4, 4): ("Tuesday", "Mahavir Jayanti"),
        D(2023, 4, 7): ("Friday", "Good Friday"),
        D(2023, 4, 14): ("Friday", "Dr. Baba Saheb Ambedkar Jayanti"),
        D(2023, 5, 1): ("Monday", "Maharashtra Day"),
        D(2023, 6, 28): ("Wednesday", "Bakri Id"),
        D(2023, 8, 15): ("Tuesday", "Independence Day"),
        D(2023, 9, 19): ("Tuesday", "Ganesh Chaturthi"),
        D(2023, 10, 2): ("Monday", "Mahatma Gandhi Jayanti"),
        D(2023, 10, 24): ("Tuesday", "Dussehra"),
        D(2023, 11, 14): ("Tuesday", "Diwali-Balipratipada"),
        D(2023, 11, 27): ("Monday", "Gurunanak Jayanti"),
        D(2023, 12, 25): ("Monday", "Christmas"),
        D(2023, 2, 18): ("Saturday", "Mahashivratri"),
        D(2023, 4, 22): ("Saturday", "Id-Ul-Fitr (Ramzan ID)"),
        D(2023, 7, 29): ("Saturday", "Moharram"),
        D(2023, 11, 12): ("Sunday", "Diwali-Laxmi Pujan*"),
    }, (15, 4)),
    "NSE/CMTR/59722": ({   # 2024: 14 + 5
        D(2024, 1, 26): ("Friday", "Republic Day"),
        D(2024, 3, 8): ("Friday", "Mahashivratri"),
        D(2024, 3, 25): ("Monday", "Holi"),
        D(2024, 3, 29): ("Friday", "Good Friday"),
        D(2024, 4, 11): ("Thursday", "Id-Ul-Fitr (Ramadan Eid)"),
        D(2024, 4, 17): ("Wednesday", "Shri Ram Navmi"),
        D(2024, 5, 1): ("Wednesday", "Maharashtra Day"),
        D(2024, 6, 17): ("Monday", "Bakri Id"),
        D(2024, 7, 17): ("Wednesday", "Moharram"),
        D(2024, 8, 15): ("Thursday", "Independence Day/Parsi New Year"),
        D(2024, 10, 2): ("Wednesday", "Mahatma Gandhi Jayanti"),
        D(2024, 11, 1): ("Friday", "Diwali Laxmi Pujan*"),
        D(2024, 11, 15): ("Friday", "Gurunanak Jayanti"),
        D(2024, 12, 25): ("Wednesday", "Christmas"),
        D(2024, 4, 14): ("Sunday", "Dr. Baba Saheb Ambedkar Jayanti"),
        D(2024, 4, 21): ("Sunday", "Shri Mahavir Jayanti"),
        D(2024, 9, 7): ("Saturday", "Ganesh Chaturthi"),
        D(2024, 10, 12): ("Saturday", "Dussehra"),
        D(2024, 11, 2): ("Saturday", "Diwali-Balipratipada"),
    }, (14, 5)),
    "NSE/CMTR/65587": ({   # 2025: 14 + 4
        D(2025, 2, 26): ("Wednesday", "Mahashivratri"),
        D(2025, 3, 14): ("Friday", "Holi"),
        D(2025, 3, 31): ("Monday", "Id-Ul-Fitr (Ramadan Eid)"),
        D(2025, 4, 10): ("Thursday", "Shri Mahavir Jayanti"),
        D(2025, 4, 14): ("Monday", "Dr. Baba Saheb Ambedkar Jayanti"),
        D(2025, 4, 18): ("Friday", "Good Friday"),
        D(2025, 5, 1): ("Thursday", "Maharashtra Day"),
        D(2025, 8, 15): ("Friday", "Independence Day"),
        D(2025, 8, 27): ("Wednesday", "Ganesh Chaturthi"),
        D(2025, 10, 2): ("Thursday", "Mahatma Gandhi Jayanti/Dussehra"),
        D(2025, 10, 21): ("Tuesday", "Diwali Laxmi Pujan*"),
        D(2025, 10, 22): ("Wednesday", "Diwali-Balipratipada"),
        D(2025, 11, 5): ("Wednesday", "Prakash Gurpurb Sri Guru Nanak Dev"),
        D(2025, 12, 25): ("Thursday", "Christmas"),
        D(2025, 1, 26): ("Sunday", "Republic Day"),
        D(2025, 4, 6): ("Sunday", "Shri Ram Navami"),
        D(2025, 6, 7): ("Saturday", "Bakri Id"),
        D(2025, 7, 6): ("Sunday", "Muharram"),
    }, (14, 4)),
}
# Amendments: holidays they add, and base-circular holidays they remove
AMENDMENT_HOLIDAYS = {
    D(2023, 6, 29): ("NSE/CMTR/57285", "Thursday"),     # moved from 2023-06-28
    D(2024, 1, 22): ("NSE/CMTR/60338", "Monday"),
    D(2024, 5, 20): ("NSE/CMTR/61518", "Monday"),
    D(2024, 11, 20): ("NSE/CMTR/64960", "Wednesday"),
}
REMOVED_BY_AMENDMENT = {D(2023, 6, 28): "NSE/CMTR/57285"}
# Session rows: (date, event) -> (source, session_start, session_end, expected session_type)
SESSIONS = {
    (D(2021, 11, 4), "MUHURAT_SESSION"): ("NSE/CMTR/50050", "18:15", "19:15", cal_mod.EXCLUDED_MUHURAT),
    (D(2022, 10, 24), "MUHURAT_SESSION"): ("NSE/CMTR/54023", "18:15", "19:15", cal_mod.EXCLUDED_MUHURAT),
    (D(2023, 11, 12), "MUHURAT_SESSION"): ("NSE/CMTR/59124", "18:15", "19:15", cal_mod.EXCLUDED_MUHURAT),
    (D(2024, 11, 1), "MUHURAT_SESSION"): ("NSE/CMTR/64628", "18:00", "19:00", cal_mod.EXCLUDED_MUHURAT),
    (D(2025, 10, 21), "MUHURAT_SESSION"): ("NSE/CMTR/70319", "13:45", "14:45", cal_mod.EXCLUDED_MUHURAT),
    (D(2024, 1, 20), "SPECIAL_SESSION"): ("NSE/MSD/60340", "09:15", "15:30", cal_mod.NORMAL_SPECIAL),
    (D(2025, 2, 1), "SPECIAL_SESSION"): ("NSE/CMTR/65729", "09:15", "15:30", cal_mod.NORMAL_SPECIAL),
    (D(2024, 3, 2), "SHORTENED_SESSION"): ("NSE/MSD/60677", "09:15", "12:30", cal_mod.EXCLUDED_SHORTENED),
    (D(2024, 5, 18), "SHORTENED_SESSION"): ("NSE/MSD/61893", "09:15", "12:30", cal_mod.EXCLUDED_SHORTENED),
}
SOURCE_FILES = {
    "NSE/CMTR/41180": "CMTR41180.pdf",
    "NSE/CMTR/46623": "CMTR46623.pdf",
    "NSE/CMTR/50050": "CMTR50050.pdf",
    "NSE/CMTR/50560": "NSE_CMTR_50560_2022_trading_holidays.pdf.pdf",
    "NSE/CMTR/54023": "CMTR54023.pdf",
    "NSE/CMTR/54757": "CMTR54757.pdf",
    "NSE/CMTR/57285": "CMTR57285.zip",
    "NSE/CMTR/59124": "CMTR59124.pdf",
    "NSE/CMTR/59722": "CMTR59722.pdf",
    "NSE/CMTR/60338": "CMTR60338.zip",
    "NSE/MSD/60340": "MSD60340.pdf",
    "NSE/MSD/60677": "MSD60677.pdf",
    "NSE/CMTR/61518": "CMTR61518.pdf",
    "NSE/MSD/61893": "MSD61893.pdf",
    "NSE/CMTR/64628": "CMTR64628.pdf",
    "NSE/CMTR/64960": "CMTR64960.pdf",
    "NSE/CMTR/65587": "CMTR65587.pdf",
    "NSE/CMTR/65729": "CMTR65729.pdf",
    "NSE/CMTR/70319": "CMTR70319.pdf",
}
Q1_2022 = (D(2022, 1, 3), D(2022, 3, 31))
Q1_2022_EOD_FILES = 61


def read(name):
    with open(os.path.join(CAL_DIR, name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def holidays_from(rows, ref):
    return {D.fromisoformat(r["date"]): r for r in rows if r["event"] == "HOLIDAY" and r["source_ref"] == ref}


def daily(days, closes=None):
    closes = closes or [100] * len(days)
    return [mtf.TimedCandle(datetime.datetime.combine(d, mtf.SESSION_OPEN), datetime.datetime.combine(d, mtf.SESSION_CLOSE),
                            c, c + 1, c - 1, c) for d, c in zip(days, closes)]


class Tables(unittest.TestCase):
    """Checks on the committed CSVs alone; they run without the circular files."""

    def setUp(self):
        self.sources = read("sources.csv")
        self.events = read("events.csv")

    def test_tables_parse_under_the_loader_schema(self):
        c = cal_mod.NseCalendar.load(CAL_DIR)
        self.assertEqual(sorted(c.sources), sorted(SOURCE_FILES))
        expected = sum(len(h) for h, _ in BASE_HOLIDAYS.values()) - len(REMOVED_BY_AMENDMENT) \
            + len(AMENDMENT_HOLIDAYS) + len(SESSIONS)
        self.assertEqual(len(c.events), expected)
        self.assertEqual(expected, 105)

    def test_base_holidays_match_each_circular(self):
        for ref, (printed, (weekday_rows, weekend_rows)) in BASE_HOLIDAYS.items():
            self.assertEqual(sum(d.weekday() < 5 for d in printed), weekday_rows, ref)
            self.assertEqual(sum(d.weekday() >= 5 for d in printed), weekend_rows, ref)
            rows = holidays_from(self.events, ref)
            self.assertEqual(sorted(rows), sorted(d for d in printed if d not in REMOVED_BY_AMENDMENT), ref)
            for d, (day, desc) in printed.items():
                self.assertEqual(d.strftime("%A"), day, d)            # printed day agrees with the date
                if d in rows:
                    self.assertEqual((rows[d]["description"], rows[d]["status"]), (desc, "CONFIRMED"), d)

    def test_amendments_add_and_move_holidays(self):
        kinds = {s["source_ref"]: s["kind"] for s in self.sources}
        for d, (ref, day) in AMENDMENT_HOLIDAYS.items():
            self.assertEqual(d.strftime("%A"), day, d)
            [row] = [r for r in self.events if r["date"] == d.isoformat()]
            self.assertEqual((row["event"], row["source_ref"], row["status"], kinds[ref]),
                             ("HOLIDAY", ref, "CONFIRMED", "AMENDMENT"), d)
        # 2023 Bakri Id: printed for 28 June in 54757, moved to 29 June by 57285
        for d in REMOVED_BY_AMENDMENT:
            self.assertFalse([r for r in self.events if r["date"] == d.isoformat()], d)
        note = [r for r in self.events if r["date"] == "2023-06-29"][0]["note"]
        self.assertIn("NSE/CMTR/54757", note)
        self.assertIn("2023-06-28", note)

    def test_no_row_is_unresolved_or_unsourced(self):
        self.assertEqual([r["date"] for r in self.events if r["status"] != "CONFIRMED"], [])
        self.assertEqual([r["date"] for r in self.events if not r["source_ref"]], [])

    def test_session_rows_match_their_notices(self):
        kinds = {s["source_ref"]: s["kind"] for s in self.sources}
        rows = {(D.fromisoformat(r["date"]), r["event"]): r for r in self.events if r["event"] != "HOLIDAY"}
        self.assertEqual(sorted(rows), sorted(SESSIONS))
        for key, (ref, start, end, _) in SESSIONS.items():
            r = rows[key]
            self.assertEqual((r["source_ref"], r["session_start"], r["session_end"], r["status"]),
                             (ref, start, end, "CONFIRMED"), key)
            self.assertEqual(kinds[ref], "SESSION_NOTICE", key)
            if key[1] in ("MUHURAT_SESSION", "SHORTENED_SESSION"):
                self.assertIn("D30", r["note"], key)
            if key[1] == "MUHURAT_SESSION":       # the regular session that day is a base holiday
                self.assertTrue(any(h["date"] == r["date"] and h["event"] == "HOLIDAY" for h in self.events), key)

    def test_hours_not_printed_by_their_own_source_are_marked(self):
        # Checked 2026-10-28 against the extracted text of every cited circular: only the
        # 20 Jan 2024 row carries times its source does not print ("as per regular market
        # timings"); they come from NSE/CMTR/41180, whose normal-hours status is provisional.
        [row] = [r for r in self.events if r["date"] == "2024-01-20"]
        self.assertIn("prints no times", row["note"])
        self.assertIn("NSE/CMTR/41180", row["note"])
        # the DR-switch rows span two printed windows; their notes must say so
        for d in ("2024-03-02", "2024-05-18"):
            [row] = [r for r in self.events if r["date"] == d]
            self.assertIn("not one continuous session", row["note"], d)

    def test_provenance_fields(self):
        by = {s["source_ref"]: s for s in self.sources}
        self.assertEqual({k: v["file_name"] for k, v in by.items()}, SOURCE_FILES)
        # decision 2026-10-28: the supplied copy's download date is not known; never inferred
        self.assertEqual(by["NSE/CMTR/50560"]["downloaded_on"], cal_mod.DOWNLOAD_DATE_UNKNOWN)
        self.assertEqual(by["NSE/CMTR/50560"]["url"], "https://archives.nseindia.com/content/circulars/CMTR50560.pdf")
        for ref, s in by.items():
            series, number = ref.split("/")[1:]
            if ref != "NSE/CMTR/50560":       # every other file keeps the name NSE serves
                self.assertTrue(s["url"].endswith("/" + s["file_name"]), ref)
                self.assertEqual(s["file_name"].rsplit(".", 1)[0], series + number, ref)
            self.assertRegex(s["url"], r"^https://(nsearchives|archives)\.nseindia\.com/content/circulars/%s%s\.(pdf|zip)$"
                             % (series, number))
            self.assertRegex(s["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(sorted(s["applicable_year"] for s in self.sources if s["kind"] == "BASE"),
                         ["2021", "2022", "2023", "2024", "2025"])     # the whole D29 window

    def test_every_event_cites_a_source_for_its_own_year(self):
        years = {s["source_ref"]: int(s["applicable_year"]) for s in self.sources}
        for r in self.events:
            self.assertEqual(D.fromisoformat(r["date"]).year, years[r["source_ref"]], r["date"])


class RealCalendar(unittest.TestCase):
    """Needs the git-ignored circular files, because the loader hash-checks every one."""

    @classmethod
    def setUpClass(cls):
        missing = [f for f in SOURCE_FILES.values() if not os.path.isfile(os.path.join(CIRCULARS, f))]
        require_local(not missing, "official NSE circulars in nse/data/calendar/circulars/ (git-ignored): %s"
                      % ", ".join(missing))
        cls.cal = cal_mod.NseCalendar.load(CAL_DIR)

    def test_every_circular_is_hash_verified(self):
        self.assertEqual({r: s.file_status for r, s in self.cal.sources.items()},
                         {r: cal_mod.VERIFIED for r in SOURCE_FILES})
        self.assertEqual(self.cal.covered_years, [2021, 2022, 2023, 2024, 2025])
        self.assertIsNone(self.cal.sources["NSE/CMTR/50560"].downloaded_on)

    def test_years_outside_the_d29_window_are_not_covered(self):
        for d in (D(2020, 12, 31), D(2026, 1, 1)):
            with self.assertRaises(cal_mod.CalendarCoverageError):
                self.cal.session_type(d)

    def test_session_types(self):
        cases = {
            D(2022, 3, 31): cal_mod.NORMAL,
            D(2022, 11, 8): cal_mod.HOLIDAY,
            D(2022, 10, 26): cal_mod.HOLIDAY,
            D(2023, 6, 27): cal_mod.NORMAL,
            D(2023, 6, 30): cal_mod.NORMAL,
            D(2024, 1, 22): cal_mod.HOLIDAY,
            D(2024, 11, 20): cal_mod.HOLIDAY,
        }
        cases.update({d: st for (d, _), (_, _, _, st) in SESSIONS.items()})
        for d, st in cases.items():
            self.assertEqual(self.cal.session_type(d), st, d)
        self.assertEqual(sorted(self.cal.flagged_dates()), sorted(d for d, _ in SESSIONS))

    def test_bakri_id_2023_follows_the_amendment(self):
        self.assertEqual(self.cal.session_type(D(2023, 6, 28)), cal_mod.NORMAL)
        self.assertTrue(self.cal.is_trading_day(D(2023, 6, 28)))
        self.assertEqual(self.cal.session_type(D(2023, 6, 29)), cal_mod.HOLIDAY)
        r = cal_mod.reconcile(self.cal, {D(2023, 6, 28)}, D(2023, 6, 28), D(2023, 6, 29))
        self.assertTrue(r.clean, r)
        r = cal_mod.reconcile(self.cal, {D(2023, 6, 29)}, D(2023, 6, 28), D(2023, 6, 29))
        self.assertEqual((r.missing_eod_on_trading_day, r.eod_on_closed_day), ([D(2023, 6, 28)], [D(2023, 6, 29)]))

    def test_q1_2022_reconciles_with_the_eod_manifest(self):
        # The manifest is the record of which official EOD files exist. Its Q1 rows are a
        # data prerequisite: without them, missing rows would look like missing sessions.
        with open(MANIFEST, newline="", encoding="utf-8") as fh:
            eod = {D.fromisoformat(r["trade_date"]) for r in csv.DictReader(fh) if r["kind"] == "ARCHIVE"}
        start, end = Q1_2022
        q1 = [d for d in eod if start <= d <= end]
        require_local(len(q1) == Q1_2022_EOD_FILES, "nse/data/eod/manifest.csv lists %d of the %d Q1 2022 EOD "
                      "archives (the Q1 manifest rows are not in this checkout)" % (len(q1), Q1_2022_EOD_FILES))
        r = cal_mod.reconcile(self.cal, eod, start, end)
        self.assertTrue(r.clean, r)
        self.assertEqual(self.cal.session_type(D(2023, 12, 29)), cal_mod.NORMAL)   # the B18 sample date
        weekday_holidays = [d for d in BASE_HOLIDAYS["NSE/CMTR/50560"][0] if d <= end and d.weekday() < 5]
        self.assertEqual(sorted(weekday_holidays), [D(2022, 1, 26), D(2022, 3, 1), D(2022, 3, 18)])
        self.assertFalse(set(weekday_holidays) & eod)

    def test_muhurat_candle_is_excluded_from_construction(self):
        # D30/D33: a candle on the Muhurat date never enters a higher-timeframe candle
        days = [D(2022, 10, 24), D(2022, 10, 25), D(2022, 10, 27), D(2022, 10, 28)]   # 26th: holiday
        s = mtf.replay(daily(days), "D", htf=("W",), as_of=datetime.datetime(2022, 10, 28, 15, 30), calendar=self.cal)
        self.assertEqual([(x.date, x.classification) for x in s.excluded_candles],
                         [(D(2022, 10, 24), cal_mod.EXCLUDED_MUHURAT)])
        self.assertEqual(s.data_gaps, [])
        self.assertEqual(s.unresolved_calendar_dates, [])

    def test_muhurat_inside_regular_clock_hours_is_still_excluded(self):
        # 2025's session (13:45-14:45) lies inside 09:15-15:30, so only the calendar can tell
        day = D(2025, 10, 21)
        cs = [mtf.TimedCandle(datetime.datetime.combine(day, datetime.time(13, 0)),
                              datetime.datetime.combine(day, datetime.time(14, 15)), 100, 101, 99, 100)]
        s = mtf.replay(cs, "75m", htf=("D",), as_of=datetime.datetime(2025, 10, 21, 15, 30), calendar=self.cal)
        self.assertEqual([(x.date, x.classification) for x in s.excluded_candles], [(day, cal_mod.EXCLUDED_MUHURAT)])

    def test_regular_hours_special_saturday_is_a_normal_session(self):
        # D30 provisional rule: 1 Feb 2025 (Union Budget) on 09:15-15:30 counts as a session
        days = [D(2025, 1, 27) + datetime.timedelta(days=i) for i in range(6)]          # Mon-Sat
        s = mtf.replay(daily(days, [100, 101, 102, 103, 104, 110]), "D", htf=("W",),
                       as_of=datetime.datetime(2025, 2, 1, 15, 30), calendar=self.cal)
        self.assertEqual(s.excluded_candles, [])
        self.assertEqual(s.data_gaps, [])
        week = s.series["W"].candles[-1]
        self.assertEqual((week.period_key, week.close, week.high), ("2025-W05", 110, 111))

    def test_disaster_recovery_session_is_excluded_as_shortened(self):
        days = [D(2024, 2, 26) + datetime.timedelta(days=i) for i in range(6)]          # Mon-Sat 2 Mar
        s = mtf.replay(daily(days), "D", htf=("W",), as_of=datetime.datetime(2024, 3, 2, 15, 30), calendar=self.cal)
        self.assertEqual([(x.date, x.classification) for x in s.excluded_candles],
                         [(D(2024, 3, 2), cal_mod.EXCLUDED_SHORTENED)])
        self.assertEqual(s.data_gaps, [])

    def test_bakri_id_week_is_complete_after_the_amendment(self):
        days = [D(2023, 6, 26), D(2023, 6, 27), D(2023, 6, 28), D(2023, 6, 30)]          # 29th: holiday
        s = mtf.replay(daily(days), "D", htf=("W",), as_of=datetime.datetime(2023, 6, 30, 15, 30), calendar=self.cal)
        self.assertEqual((s.excluded_candles, s.data_gaps, s.unresolved_calendar_dates), ([], [], []))
        self.assertIsNone(s.series["W"].truncated_at)
        self.assertEqual(s.series["W"].candles[-1].period_key, "2023-W26")


if __name__ == "__main__":
    unittest.main()
