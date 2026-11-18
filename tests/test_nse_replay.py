"""nse/eod replay adapter and reference comparison. All bhavcopy files and reference rows
here are SYNTHETIC test inputs, not market data and not TradingView output. The real INFY
samples are exercised only to show what the two local dates can and cannot support.
"""

import datetime
import os
import shutil
import tempfile
import unittest
from decimal import Decimal

from _load import ROOT, load, require_local

bc = load(os.path.join("nse", "eod"), "nse_bhavcopy")
rp = load(os.path.join("nse", "eod"), "nse_replay")
rf = load(os.path.join("nse", "eod"), "nse_reference")
D = datetime.date

HEADER = ",".join(bc.LEGACY_HEADER)
MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
# a DBR shaped like the Zone Engine's own test: leg-in, base, leg-out, strong follow-through
DBR = [("100", "101", "99", "100"), ("100", "100.5", "94", "95"), ("95", "96", "94.5", "95.2"),
       ("95.5", "102", "95.3", "101.5"), ("101.5", "105", "101", "104.5"), ("104.5", "105", "103", "104")]
WEEK = [D(2024, 1, 8) + datetime.timedelta(days=i) for i in range(5)] + [D(2024, 1, 15)]


def stamp(d):
    return "%02d-%s-%04d" % (d.day, MON[d.month - 1], d.year)


def row(d, o, h, l, c, symbol="AAAA", series="EQ"):
    return "%s,%s,%s,%s,%s,%s,%s,%s,1000,100000,%s,10,INE000A01019," % (symbol, series, o, h, l, c, c, o, stamp(d))


class Files(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="nse-replay-test-")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def bhav(self, d, *rows):
        path = os.path.join(self.dir, "cm%02d%s%04dbhav.csv" % (d.day, MON[d.month - 1], d.year))
        with open(path, "w", newline="") as fh:
            fh.write(HEADER + "\n" + "".join(r + "\n" for r in rows))
        return path

    def dbr_files(self, skip=()):
        return bc.load_many([self.bhav(d, row(d, *p)) for d, p in zip(WEEK, DBR) if d not in skip])

    def write_ref(self, name, header, lines):
        path = os.path.join(self.dir, name)
        with open(path, "w", newline="") as fh:
            fh.write(",".join(header) + "\n" + "".join(l + "\n" for l in lines))
        return path


class DailySeries(Files):
    def test_exact_decimals_and_source_per_bar(self):
        s = rp.daily_series(self.dbr_files(), "AAAA")
        self.assertEqual([b.trade_date for b in s.bars], WEEK)
        b = s.bars[2]
        self.assertEqual((b.open, b.high, b.low, b.close), (Decimal("95"), Decimal("96"), Decimal("94.5"), Decimal("95.2")))
        for bar in s.bars:                                           # 95.0 == Decimal("95"), so check the type
            self.assertTrue(all(type(v) is Decimal for v in (bar.open, bar.high, bar.low, bar.close)))
        self.assertEqual(b.source_file, "cm10JAN2024bhav.csv")
        self.assertEqual(len(b.source_sha256), 64)
        self.assertEqual((s.price_adjustment, s.warnings), ("NONE", [rp.CORPORATE_ACTIONS_UNVERIFIED]))
        self.assertEqual([x["provenance_status"] for x in s.sources], ["NO_MANIFEST"] * 6)

    def test_absent_rows_are_listed_never_filled(self):
        d0, d1 = WEEK[0], WEEK[1]
        files = bc.load_many([self.bhav(d0, row(d0, *DBR[0])),
                              self.bhav(d1, row(d1, *DBR[1], symbol="BBBB"), row(d1, *DBR[1], series="BE"))])
        s = rp.daily_series(files, "AAAA")
        self.assertEqual([b.trade_date for b in s.bars], [d0])        # no bar invented for d1
        self.assertEqual((s.missing_dates, s.other_series_dates), ([d1], [d1]))

    def test_missing_files_are_not_bars_and_dates_stay_ordered(self):
        s = rp.daily_series(self.dbr_files(skip=(WEEK[2],)), "AAAA")
        self.assertNotIn(WEEK[2], [b.trade_date for b in s.bars])     # no file: no bar, no fill
        self.assertEqual(s.missing_dates, [])                         # absence of a file is not reported here

    def test_bad_inputs_are_refused(self):
        files = self.dbr_files()
        for bad in ([], list(reversed(files)), [files[0], files[0]]):
            with self.subTest(n=len(bad)):
                with self.assertRaises(rp.ReplayInputError):
                    rp.daily_series(bad, "AAAA")
        with self.assertRaises(rp.ReplayInputError):
            rp.replay_symbol(files, "ZZZZ", assume_regular_session=True)


class SessionAssumption(Files):
    def test_candles_need_the_session_assumption_explicitly(self):
        s = rp.daily_series(self.dbr_files(), "AAAA")
        with self.assertRaises(rp.ReplayInputError):
            rp.timed_candles(s)
        with self.assertRaises(rp.ReplayInputError):
            rp.replay_symbol(self.dbr_files(), "AAAA")
        c = rp.timed_candles(s, assume_regular_session=True)[0]
        self.assertEqual((c.start.time(), c.end.time()), (datetime.time(9, 15), datetime.time(15, 30)))


class Replay(Files):
    def test_replay_runs_the_existing_engine_and_records_its_caveats(self):
        r = rp.replay_symbol(self.dbr_files(), "AAAA", htf=("D",), assume_regular_session=True)
        self.assertIn("D:demand-2-3", r.snapshot.zones)                 # the engine's own DBR zone
        self.assertEqual(r.warnings, [rp.CORPORATE_ACTIONS_UNVERIFIED, rp.SESSION_TIMES_ASSUMED, rp.CALENDAR_UNVALIDATED])
        self.assertIn(rp.CALENDAR_UNVALIDATED, r.snapshot.limitations)
        self.assertEqual(r.engine_numeric, "float (mtf_freshness.TimedCandle)")

    def test_a_missing_file_is_a_gap_for_the_orchestrator_not_a_filled_bar(self):
        r = rp.replay_symbol(self.dbr_files(skip=(WEEK[4],)), "AAAA", htf=("D",), assume_regular_session=True)
        self.assertIn(WEEK[4], [g.date for g in r.snapshot.data_gaps])
        self.assertFalse(any(z.usable_as_fresh_context for z in r.snapshot.zones.values()))

    def test_too_few_bars_are_flagged(self):
        r = rp.replay_symbol(self.dbr_files()[:2], "AAAA", htf=("D",), assume_regular_session=True)
        self.assertIn(rp.INSUFFICIENT_DAILY_BARS, r.warnings)
        self.assertEqual(r.snapshot.zones, {})


def ohlc_line(tf, d, o, h, l, c, adj=("OFF", "OFF"), symbol="AAAA", src=("TRADINGVIEW_MANUAL", "", "")):
    return ",".join([symbol, "NSE", tf, d.isoformat(), o, h, l, c, src[0], src[1], src[2], "Asia/Kolkata",
                     adj[0], adj[1], "2026-10-28", "synthetic"])


SHOT = ("YAHOO_FINANCE_SCREENSHOT", "synthetic_screenshot_1.png", "a" * 64)    # a test name and hash only


class ReferenceFormat(Files):
    def test_templates_match_the_reader(self):
        for name, cols in (("ohlc_reference.template.csv", rf.OHLC_REFERENCE_COLUMNS),
                           ("zone_reference.template.csv", rf.ZONE_REFERENCE_COLUMNS)):
            with open(os.path.join(ROOT, "nse", "data", "reference", name)) as fh:
                self.assertEqual(fh.read(), ",".join(cols) + "\n")    # header only: no expected values

    def test_bad_reference_rows_are_refused(self):
        good = ohlc_line("D", WEEK[0], "100", "101", "99", "100")
        bad_rows = [good.replace(",NSE,", ",BSE,"), good.replace(",D,", ",H,"), good.replace(",100,101,", ",x,101,"),
                    good.replace("Asia/Kolkata", ""), good.replace(",OFF,OFF,", ",MAYBE,OFF,"),
                    good.replace("TRADINGVIEW_MANUAL", "TRADINGVIEW_EXPORT")]   # export without file and hash
        for line in bad_rows:
            with self.subTest(line=line):
                with self.assertRaises(rf.ReferenceFormatError):
                    rf.read_ohlc_reference(self.write_ref("r.csv", rf.OHLC_REFERENCE_COLUMNS, [line]))
        with self.assertRaises(rf.ReferenceFormatError):
            rf.read_ohlc_reference(self.write_ref("r.csv", ("symbol", "close"), []))
        with self.assertRaises(rf.ReferenceFormatError):
            rf.read_zone_reference(self.write_ref("z.csv", ("symbol",), []))


class CompareOhlc(Files):
    def compare(self, lines, skip=(), tolerance=Decimal("0"), calendar=None):
        refs = rf.read_ohlc_reference(self.write_ref("r.csv", rf.OHLC_REFERENCE_COLUMNS, lines))
        r = rp.replay_symbol(self.dbr_files(skip), "AAAA", htf=("D", "W"), assume_regular_session=True, calendar=calendar)
        return {(c.timeframe, c.bar_date): c for c in rf.compare_ohlc(refs, r, tolerance)}

    def test_daily_match_mismatch_and_classification(self):
        res = self.compare([ohlc_line("D", WEEK[0], *DBR[0]),
                            ohlc_line("D", WEEK[1], "100", "100.5", "94", "95.05"),                   # close differs
                            ohlc_line("D", WEEK[2], "95", "96", "94.5", "95.25", adj=("ON", "OFF")),  # adjusted chart
                            ohlc_line("D", WEEK[3], *DBR[3])], skip=(WEEK[3],))
        self.assertEqual((res[("D", WEEK[0])].status, res[("D", WEEK[0])].max_abs_diff), (rf.MATCH, Decimal("0")))
        self.assertEqual((res[("D", WEEK[1])].status, res[("D", WEEK[1])].classification), (rf.MISMATCH, rf.DATA_MISMATCH))
        self.assertEqual(res[("D", WEEK[1])].max_abs_diff, Decimal("0.05"))
        self.assertEqual(res[("D", WEEK[2])].classification, rf.METHODOLOGY_AMBIGUITY)
        self.assertEqual((res[("D", WEEK[3])].status, res[("D", WEEK[3])].classification), (rf.NO_ACTUAL, rf.INSUFFICIENT_EVIDENCE))

    def test_tolerance_is_explicit(self):
        res = self.compare([ohlc_line("D", WEEK[1], "100", "100.5", "94", "95.05")], tolerance=Decimal("0.05"))
        self.assertEqual((res[("D", WEEK[1])].status, res[("D", WEEK[1])].tolerance), (rf.MATCH, Decimal("0.05")))

    def test_htf_rows_are_blocked_without_a_validated_calendar(self):
        res = self.compare([ohlc_line("W", WEEK[0], "100", "105", "94", "104.5")])
        c = res[("W", WEEK[0])]
        self.assertEqual((c.status, c.classification, c.period), (rf.BLOCKED, rf.INSUFFICIENT_EVIDENCE, "2024-W02"))

    def test_weekly_construction_mismatch_needs_matching_daily_references(self):
        cal = type("Cal", (), {"is_trading_day": lambda self, d: d.weekday() < 5})()
        daily = [ohlc_line("D", d, *p) for d, p in zip(WEEK[:5], DBR[:5])]
        wrong_week = ohlc_line("W", WEEK[0], "100", "105", "94", "104")             # true week closes 104.5
        res = self.compare(daily + [wrong_week], calendar=cal)
        self.assertEqual(res[("W", WEEK[0])].classification, rf.CANDLE_CONSTRUCTION_MISMATCH)
        res = self.compare(daily[:2] + [wrong_week], calendar=cal)                   # daily evidence incomplete
        self.assertEqual(res[("W", WEEK[0])].classification, rf.INSUFFICIENT_EVIDENCE)
        res = self.compare(daily + [ohlc_line("W", WEEK[0], "100", "105", "94", "104.5")], calendar=cal)
        self.assertEqual(res[("W", WEEK[0])].status, rf.MATCH)

    def test_reference_for_another_symbol_is_refused(self):
        with self.assertRaises(rf.ReferenceFormatError):
            self.compare([ohlc_line("D", WEEK[0], *DBR[0], symbol="BBBB")])


class ScreenshotProvenance(Files):
    """Screenshot-derived references (e.g. Yahoo Finance) must name the image and its SHA-256,
    and keep their own source label: they are not TradingView data."""

    def read(self, line):
        return rf.read_ohlc_reference(self.write_ref("r.csv", rf.OHLC_REFERENCE_COLUMNS, [line]))

    def test_screenshot_rows_need_the_image_name_and_hash(self):
        for label, src in (("no file, no hash", (SHOT[0], "", "")), ("no hash", (SHOT[0], SHOT[1], "")),
                           ("no file", (SHOT[0], "", SHOT[2])), ("bad hash", (SHOT[0], SHOT[1], "1234"))):
            with self.subTest(label):
                with self.assertRaises(rf.ReferenceFormatError):
                    self.read(ohlc_line("D", WEEK[0], *DBR[0], src=src))
        ref = self.read(ohlc_line("D", WEEK[0], *DBR[0], src=SHOT))[0]
        self.assertEqual((ref.source, ref.export_file, ref.export_sha256), SHOT)

    def test_tradingview_sources_still_work(self):
        self.assertEqual(self.read(ohlc_line("D", WEEK[0], *DBR[0]))[0].source, "TRADINGVIEW_MANUAL")
        export = ("TRADINGVIEW_EXPORT", "D.csv", "b" * 64)
        self.assertEqual(self.read(ohlc_line("D", WEEK[0], *DBR[0], src=export))[0].source, "TRADINGVIEW_EXPORT")

    def test_screenshots_cannot_be_zone_references(self):
        zone = ",".join(["AAAA", "NSE", "D", "max_base=5", "demand", "DBR", "2024-01-10", "2024-01-11", "95.2", "94",
                         "7/7", "NO", "", "", SHOT[0], "Asia/Kolkata", "OFF", "OFF", "2026-10-28", "synthetic"])
        with self.assertRaises(rf.ReferenceFormatError):
            rf.read_zone_reference(self.write_ref("z.csv", rf.ZONE_REFERENCE_COLUMNS, [zone]))

    def test_each_comparison_names_its_reference_source(self):
        refs = rf.read_ohlc_reference(self.write_ref("r.csv", rf.OHLC_REFERENCE_COLUMNS,
                                                     [ohlc_line("D", WEEK[0], *DBR[0], src=SHOT)]))
        r = rp.replay_symbol(self.dbr_files(), "AAAA", htf=("D",), assume_regular_session=True)
        c = [x for x in rf.compare_ohlc(refs, r) if x.bar_date == WEEK[0]][0]
        self.assertEqual((c.status, c.source), (rf.MATCH, "YAHOO_FINANCE_SCREENSHOT"))


class Coverage(Files):
    """A replayed bar without a reference row is reported, so partial coverage is never
    mistaken for complete coverage."""

    def results(self, days):
        lines = [ohlc_line("D", d, *p) for d, p in zip(WEEK, DBR) if d in days]
        refs = rf.read_ohlc_reference(self.write_ref("r.csv", rf.OHLC_REFERENCE_COLUMNS, lines))
        return rf.compare_ohlc(refs, rp.replay_symbol(self.dbr_files(), "AAAA", htf=("D",), assume_regular_session=True))

    def test_bar_without_a_reference_is_no_reference(self):
        res = self.results(WEEK[:5])                                    # the 6th bar has no reference
        missing = [c for c in res if c.status == rf.NO_REFERENCE]
        self.assertEqual([(c.timeframe, c.bar_date, c.classification) for c in missing],
                         [("D", WEEK[5], rf.INSUFFICIENT_EVIDENCE)])
        self.assertIsNone(missing[0].expected)
        s = rf.coverage_summary(res)
        self.assertEqual((s["complete"], s["counts"][rf.MATCH], s["counts"][rf.NO_REFERENCE]), (False, 5, 1))
        self.assertEqual(s["no_reference"], [("D", WEEK[5])])

    def test_complete_only_when_every_bar_has_a_matching_reference(self):
        self.assertTrue(rf.coverage_summary(self.results(WEEK))["complete"])
        lines = [ohlc_line("D", d, *p) for d, p in zip(WEEK, DBR)]
        lines[2] = ohlc_line("D", WEEK[2], "95", "96", "94.5", "95.25")  # one mismatch
        refs = rf.read_ohlc_reference(self.write_ref("r.csv", rf.OHLC_REFERENCE_COLUMNS, lines))
        res = rf.compare_ohlc(refs, rp.replay_symbol(self.dbr_files(), "AAAA", htf=("D",), assume_regular_session=True))
        self.assertFalse(rf.coverage_summary(res)["complete"])

    def test_no_references_at_all_is_not_complete(self):
        s = rf.coverage_summary(self.results([]))
        self.assertEqual((s["complete"], s["counts"][rf.NO_REFERENCE]), (False, 6))
        self.assertFalse(rf.coverage_summary([])["complete"])         # nothing compared is not complete


RAW = os.path.join(ROOT, "nse", "data", "eod", "raw")
MANIFEST = os.path.join(ROOT, "nse", "data", "eod", "manifest.csv")
ZIPS = [os.path.join(RAW, n) for n in ("cm03JAN2022bhav.csv.zip", "cm29DEC2023bhav.csv.zip")]
CAL_DIR = os.path.join(ROOT, "nse", "data", "calendar")
INFY_REFERENCE = os.path.join(ROOT, "nse", "data", "reference", "INFY", "ohlc_reference.csv")
cal_mod = load(os.path.join("nse", "calendar"), "nse_calendar")


class RealInfySamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_local(all(os.path.isfile(p) for p in ZIPS), "real NSE samples in nse/data/eod/raw/ (git-ignored)")

    def test_two_dates_give_two_bars_and_no_usable_replay(self):
        r = rp.replay_symbol(bc.load_many(ZIPS, MANIFEST), "INFY", htf=("D", "W", "M"), assume_regular_session=True)
        self.assertEqual([(b.trade_date, str(b.close)) for b in r.daily.bars],
                         [(D(2022, 1, 3), "1898.45"), (D(2023, 12, 29), "1542.9")])
        self.assertEqual([s["provenance_status"] for s in r.daily.sources], ["USER_CONFIRMED", "USER_CONFIRMED"])
        self.assertIn(rp.INSUFFICIENT_DAILY_BARS, r.warnings)
        self.assertEqual(r.snapshot.zones, {})


class RealInfyQ1Of2022(unittest.TestCase):
    """End to end on real data: the 61 official Q1 2022 bhavcopies, the official calendar,
    the orchestrator and the recorded Yahoo Finance reference (61 daily rows). Yahoo
    republishes exchange data, so a match is a transcription and pipeline check, not an
    independent validation; no TradingView reference exists yet (B8, B10)."""

    @classmethod
    def setUpClass(cls):
        records = [r for r in bc.read_manifest(MANIFEST) if r["kind"] == "ARCHIVE"
                   and D(2022, 1, 3) <= D.fromisoformat(r["trade_date"]) <= D(2022, 3, 31)]
        require_local(len(records) == 61, "nse/data/eod/manifest.csv lists %d of the 61 Q1 2022 archives" % len(records))
        paths = [os.path.join(RAW, r["file_name"]) for r in records]
        missing = [os.path.basename(p) for p in paths if not os.path.isfile(p)]
        require_local(not missing, "Q1 2022 archives in nse/data/eod/raw/ (git-ignored): %d missing" % len(missing))
        require_local(os.path.isfile(INFY_REFERENCE), "nse/data/reference/INFY/ohlc_reference.csv")
        cls.cal = cal_mod.NseCalendar.load(CAL_DIR)
        require_local(2022 in cls.cal.covered_years, "a hash-verified 2022 base circular in nse/data/calendar/circulars/")
        files = bc.load_many(sorted(paths), MANIFEST)
        cls.result = rp.replay_symbol(files, "INFY", htf=("D", "W", "M"), calendar=cls.cal, assume_regular_session=True)
        cls.refs = rf.read_ohlc_reference(INFY_REFERENCE)

    def test_every_session_has_a_bar_and_the_calendar_sees_no_gap(self):
        r = self.result
        self.assertEqual((len(r.daily.bars), r.daily.missing_dates), (61, []))
        self.assertNotIn(rp.CALENDAR_UNVALIDATED, r.warnings)
        snap = r.snapshot
        self.assertTrue(snap.calendar_validated)
        self.assertEqual((snap.data_gaps, snap.excluded_candles, snap.unresolved_calendar_dates), ([], [], []))

    def test_daily_bars_match_all_61_reference_rows(self):
        results = rf.compare_ohlc(self.refs, self.result)
        summary = rf.coverage_summary(results)
        self.assertTrue(summary["complete"], summary)
        self.assertEqual(summary["counts"][rf.MATCH], 61)

    def test_holiday_weeks_and_month_ends_aggregate_only_their_sessions(self):
        # weekly and monthly candles recomputed here from the reference rows, not from the engine
        ref = {r.bar_date: r for r in self.refs if r.timeframe == "D"}
        series = {tf: {c.period_key: c for c in self.result.snapshot.series[tf].candles} for tf in ("W", "M")}
        for tf, key, first, last in (("W", "2022-W04", D(2022, 1, 24), D(2022, 1, 28)),   # 26 Jan holiday
                                     ("W", "2022-W09", D(2022, 2, 28), D(2022, 3, 4)),    # 1 Mar holiday
                                     ("W", "2022-W11", D(2022, 3, 14), D(2022, 3, 18)),   # 18 Mar holiday
                                     ("M", "2022-03", D(2022, 3, 1), D(2022, 3, 31))):    # 1 Mar holiday, 31 Mar close
            days = sorted(d for d in ref if first <= d <= last)
            c = series[tf][key]
            expect = (ref[days[0]].open, max(ref[d].high for d in days), min(ref[d].low for d in days), ref[days[-1]].close)
            got = tuple(Decimal(str(x)) for x in (c.open, c.high, c.low, c.close))
            self.assertEqual(got, expect, key)
            self.assertEqual(len(days), 4 if tf == "W" else 21, key)   # March: 23 weekdays - 2 holidays
        # the week of 28 Mar-1 Apr is not complete on 31 Mar, so it is not a candle yet
        self.assertNotIn("2022-W13", series["W"])


if __name__ == "__main__":
    unittest.main()
