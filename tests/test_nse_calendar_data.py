"""Tests of the REAL calendar tables in nse/data/calendar/ (B17), as opposed to the
synthetic fixtures in test_nse_calendar.py.

The expected rows below are a second, independent transcription of the official NSE
circulars (CMTR50560, CMTR54023, CMTR54757, CMTR59124; text-extracted and checked on
the rendered pages, 2026-10-28). Any edit to events.csv that disagrees with the printed
circulars fails here.

The circular PDFs are local only (git-ignored, D31), so tests that need their hashes
are skipped when the files are absent.
"""

import csv
import datetime
import os
import unittest

from _load import load, ROOT

cal_mod = load(os.path.join("nse", "calendar"), "nse_calendar")
mtf = load(os.path.join("nse", "mtf-freshness"), "mtf_freshness")
D = datetime.date

CAL_DIR = os.path.join(ROOT, "nse", "data", "calendar")
CIRCULARS = os.path.join(CAL_DIR, "circulars")
MANIFEST = os.path.join(ROOT, "nse", "data", "eod", "manifest.csv")

# date: (printed day, printed description)
HOLIDAYS_2022 = {   # NSE/CMTR/50560: 13 weekday rows (p.1) + 5 Saturday/Sunday rows
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
}
HOLIDAYS_2023 = {   # NSE/CMTR/54757: 15 weekday rows (p.1) + 4 Saturday/Sunday rows (p.2)
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
}
# Muhurat "Normal Market" rows of NSE/CMTR/54023 and NSE/CMTR/59124
MUHURAT = {D(2022, 10, 24): ("NSE/CMTR/54023", "18:15", "19:15"),
           D(2023, 11, 12): ("NSE/CMTR/59124", "18:15", "19:15")}
# Bakri Id 2023: printed 28 June; reportedly moved to 29 June, amendment not obtained
BAKRI_ID_2023 = (D(2023, 6, 28), D(2023, 6, 29))

SOURCE_FILES = {
    "NSE/CMTR/41180": "CMTR41180.pdf",
    "NSE/CMTR/50560": "NSE_CMTR_50560_2022_trading_holidays.pdf.pdf",
    "NSE/CMTR/54023": "CMTR54023.pdf",
    "NSE/CMTR/54757": "CMTR54757.pdf",
    "NSE/CMTR/59124": "CMTR59124.pdf",
}
HAVE_CIRCULARS = all(os.path.isfile(os.path.join(CIRCULARS, f)) for f in SOURCE_FILES.values())


def read(name):
    with open(os.path.join(CAL_DIR, name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def holidays_from(rows, ref):
    return {D.fromisoformat(r["date"]): r for r in rows if r["event"] == "HOLIDAY" and r["source_ref"] == ref}


class Tables(unittest.TestCase):
    """Checks on the committed CSVs alone; they run without the PDFs."""

    def setUp(self):
        self.sources = read("sources.csv")
        self.events = read("events.csv")

    def test_tables_parse_under_the_loader_schema(self):
        c = cal_mod.NseCalendar.load(CAL_DIR)
        self.assertEqual(sorted(c.sources), sorted(SOURCE_FILES))
        self.assertEqual(len(c.events), 19 + 21)

    def test_2022_holidays_match_the_circular(self):
        rows = holidays_from(self.events, "NSE/CMTR/50560")
        self.assertEqual(sorted(rows), sorted(HOLIDAYS_2022))
        self.assertEqual(sum(d.weekday() < 5 for d in rows), 13)
        self.assertEqual(sum(d.weekday() >= 5 for d in rows), 5)
        for d, (day, desc) in HOLIDAYS_2022.items():
            self.assertEqual(d.strftime("%A"), day, d)            # printed day agrees with the date
            self.assertEqual(rows[d]["description"], desc, d)
            self.assertEqual(rows[d]["status"], "CONFIRMED", d)

    def test_2023_holidays_match_the_circular(self):
        printed = holidays_from(self.events, "NSE/CMTR/54757")
        self.assertEqual(sorted(printed), sorted(HOLIDAYS_2023))       # 29 June is not attributed to it
        self.assertEqual(sum(d.weekday() < 5 for d in printed), 15)
        self.assertEqual(sum(d.weekday() >= 5 for d in printed), 4)
        for d, (day, desc) in HOLIDAYS_2023.items():
            self.assertEqual(d.strftime("%A"), day, d)
            self.assertEqual(printed[d]["description"], desc, d)

    def test_bakri_id_2023_stays_unresolved_without_an_amendment(self):
        unresolved = sorted(D.fromisoformat(r["date"]) for r in self.events if r["status"] == "UNRESOLVED")
        self.assertEqual(unresolved, list(BAKRI_ID_2023))
        rows = {r["date"]: r for r in self.events if r["status"] == "UNRESOLVED"}
        self.assertEqual(rows["2023-06-28"]["source_ref"], "NSE/CMTR/54757")    # printed there
        self.assertEqual(rows["2023-06-29"]["source_ref"], "")                  # printed in no circular held
        self.assertIn("No registered source", rows["2023-06-29"]["note"])
        for r in rows.values():
            self.assertEqual(r["event"], "HOLIDAY")
            self.assertRegex(r["note"], r"amending circular (has not been obtained or verified|is obtained and verified)")
        # if an amendment is ever registered, this test must be revisited with it
        self.assertFalse([s for s in self.sources if s["kind"] == "AMENDMENT"])

    def test_muhurat_sessions_come_from_their_session_notices(self):
        kinds = {s["source_ref"]: s["kind"] for s in self.sources}
        rows = {D.fromisoformat(r["date"]): r for r in self.events if r["event"] == "MUHURAT_SESSION"}
        self.assertEqual(sorted(rows), sorted(MUHURAT))
        for d, (ref, start, end) in MUHURAT.items():
            r = rows[d]
            self.assertEqual((r["source_ref"], r["session_start"], r["session_end"], r["status"]),
                             (ref, start, end, "CONFIRMED"))
            self.assertEqual(kinds[ref], "SESSION_NOTICE")
            self.assertIn("D30", r["note"])
            # the regular session that day is a holiday in the base circular
            self.assertTrue(any(h["date"] == r["date"] and h["event"] == "HOLIDAY" for h in self.events))

    def test_provenance_fields(self):
        by = {s["source_ref"]: s for s in self.sources}
        self.assertEqual({k: v["file_name"] for k, v in by.items()}, SOURCE_FILES)
        # decision 2026-10-28: the supplied copy's download date is not known; never inferred
        self.assertEqual(by["NSE/CMTR/50560"]["downloaded_on"], cal_mod.DOWNLOAD_DATE_UNKNOWN)
        self.assertEqual(by["NSE/CMTR/50560"]["url"], "https://archives.nseindia.com/content/circulars/CMTR50560.pdf")
        for ref, s in by.items():
            number = ref.split("/")[-1]
            self.assertRegex(s["url"], r"^https://(nsearchives|archives)\.nseindia\.com/content/circulars/CMTR%s\.pdf$"
                             % number)
            self.assertRegex(s["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(sorted((s["applicable_year"], s["kind"]) for s in self.sources if s["kind"] == "BASE"),
                         [("2022", "BASE"), ("2023", "BASE")])

    def test_every_event_cites_a_source_for_its_own_year(self):
        years = {s["source_ref"]: int(s["applicable_year"]) for s in self.sources}
        unsourced = [r["date"] for r in self.events if not r["source_ref"]]
        self.assertEqual(unsourced, ["2023-06-29"])          # only the unresolved Bakri Id date
        for r in self.events:
            if r["source_ref"]:
                self.assertEqual(D.fromisoformat(r["date"]).year, years[r["source_ref"]], r["date"])


@unittest.skipUnless(HAVE_CIRCULARS, "official NSE circulars are local only (nse/data/calendar/circulars/ is git-ignored)")
class RealCalendar(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cal = cal_mod.NseCalendar.load(CAL_DIR)

    def test_every_circular_is_hash_verified(self):
        self.assertEqual({r: s.file_status for r, s in self.cal.sources.items()},
                         {r: cal_mod.VERIFIED for r in SOURCE_FILES})
        self.assertEqual(self.cal.covered_years, [2022, 2023])
        self.assertIsNone(self.cal.sources["NSE/CMTR/50560"].downloaded_on)

    def test_years_without_a_base_circular_are_not_covered(self):
        for d in (D(2021, 12, 31), D(2024, 1, 1)):
            with self.assertRaises(cal_mod.CalendarCoverageError):
                self.cal.session_type(d)

    def test_session_types(self):
        cases = {
            D(2022, 3, 31): cal_mod.NORMAL,
            D(2022, 11, 8): cal_mod.HOLIDAY,
            D(2022, 10, 26): cal_mod.HOLIDAY,
            D(2022, 10, 24): cal_mod.EXCLUDED_MUHURAT,     # D30: flagged, never a normal candle
            D(2023, 11, 12): cal_mod.EXCLUDED_MUHURAT,
            D(2023, 6, 27): cal_mod.NORMAL,
            D(2023, 6, 30): cal_mod.NORMAL,
        }
        for d, st in cases.items():
            self.assertEqual(self.cal.session_type(d), st, d)
        self.assertFalse(self.cal.is_trading_day(D(2022, 10, 24)))
        self.assertTrue(self.cal.is_excluded_session(D(2022, 10, 24)))
        self.assertEqual(sorted(self.cal.flagged_dates()), sorted(MUHURAT))

    def test_bakri_id_2023_dates_refuse_to_answer(self):
        for d in BAKRI_ID_2023:
            with self.assertRaises(cal_mod.CalendarAmbiguityError):
                self.cal.session_type(d)
            with self.assertRaises(cal_mod.CalendarAmbiguityError):
                self.cal.is_trading_day(d)
            with self.assertRaises(cal_mod.CalendarAmbiguityError):
                self.cal.is_excluded_session(d)

    def test_bakri_id_2023_dates_are_never_reconciled_as_normal(self):
        # whether or not an EOD file exists, neither date counts as a trading or closed day
        start, end = BAKRI_ID_2023
        for eod in (set(), {start}, {end}, set(BAKRI_ID_2023)):
            r = cal_mod.reconcile(self.cal, eod, start, end)
            self.assertEqual(r.unresolved, list(BAKRI_ID_2023), eod)
            self.assertEqual((r.missing_eod_on_trading_day, r.eod_on_closed_day), ([], []), eod)
            self.assertFalse(r.clean)

    def test_q1_2022_reconciles_with_the_eod_manifest(self):
        with open(MANIFEST, newline="", encoding="utf-8") as fh:
            eod = {D.fromisoformat(r["trade_date"]) for r in csv.DictReader(fh) if r["kind"] == "ARCHIVE"}
        start, end = D(2022, 1, 3), D(2022, 3, 31)
        r = cal_mod.reconcile(self.cal, eod, start, end)
        self.assertTrue(r.clean, r)
        self.assertEqual(len([d for d in eod if start <= d <= end]), 61)
        self.assertEqual(self.cal.session_type(D(2023, 12, 29)), cal_mod.NORMAL)   # the B18 sample date
        weekday_holidays = [d for d in HOLIDAYS_2022 if d <= D(2022, 3, 31) and d.weekday() < 5]
        self.assertEqual(sorted(weekday_holidays), [D(2022, 1, 26), D(2022, 3, 1), D(2022, 3, 18)])
        self.assertFalse(set(weekday_holidays) & eod)

    def test_muhurat_candle_is_excluded_from_construction(self):
        # D30/D33: a candle on the Muhurat date never enters a higher-timeframe candle
        days = [D(2022, 10, 24), D(2022, 10, 25), D(2022, 10, 27), D(2022, 10, 28)]   # 26th: holiday
        cs = [mtf.TimedCandle(datetime.datetime.combine(d, mtf.SESSION_OPEN),
                              datetime.datetime.combine(d, mtf.SESSION_CLOSE), 100, 101, 99, 100)
              for d in days]
        s = mtf.replay(cs, "D", htf=("W",), as_of=datetime.datetime(2022, 10, 28, 15, 30), calendar=self.cal)
        self.assertEqual([(x.date, x.classification) for x in s.excluded_candles],
                         [(D(2022, 10, 24), cal_mod.EXCLUDED_MUHURAT)])
        self.assertEqual(s.data_gaps, [])
        self.assertEqual(s.unresolved_calendar_dates, [])

    def test_bakri_id_week_is_set_aside_not_guessed(self):
        # D39: the ambiguous dates are handled per date and truncate the affected week
        days = [D(2023, 6, 26), D(2023, 6, 27), D(2023, 6, 28), D(2023, 6, 30)]
        cs = [mtf.TimedCandle(datetime.datetime.combine(d, mtf.SESSION_OPEN),
                              datetime.datetime.combine(d, mtf.SESSION_CLOSE), 100, 101, 99, 100)
              for d in days]
        s = mtf.replay(cs, "D", htf=("W",), as_of=datetime.datetime(2023, 6, 30, 15, 30), calendar=self.cal)
        self.assertEqual([(x.date, x.classification) for x in s.excluded_candles],
                         [(D(2023, 6, 28), mtf.CALENDAR_UNRESOLVED)])
        self.assertEqual(s.unresolved_calendar_dates, list(BAKRI_ID_2023))
        self.assertEqual(s.series["W"].truncated_at, "2023-W26")


if __name__ == "__main__":
    unittest.main()
