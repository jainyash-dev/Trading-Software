"""Data readiness (inventory), corporate actions and zone reference comparison.
SYNTHETIC inputs except RealInventory, which reads the local official files (git-ignored)."""

import datetime
import hashlib
import os
import shutil
import tempfile
import unittest
from decimal import Decimal

import _research as R
from _load import ROOT, require_local
from nse.research import corporate_actions as ca, inventory, models as m, refcheck, scanner
from nse.research.deps import mtf, reference

D = datetime.date
CAL = R.WeekdayCalendar()
# the four 2016-2019 Dhanteras dates: UNRESOLVED until owner decision D58 (CAL-2 option A)
DHANTERAS = ("2016-10-28", "2017-10-17", "2018-11-05", "2019-10-25")


def unresolved_calendar_dates(*dates):
    """Make the real calendar answer the given dates as an UNRESOLVED row would (raise
    CalendarAmbiguityError), so the fail-closed rules stay tested now that the real tables
    have no UNRESOLVED row (D58). Every other date is answered from the real tables."""
    from unittest import mock
    from nse.research.deps import calendar as cal_mod
    real = cal_mod.NseCalendar.session_type
    marked = set(dates)

    def session_type(self, d):
        if d in marked:
            raise cal_mod.CalendarAmbiguityError("%s: injected UNRESOLVED (test)" % d)
        return real(self, d)
    return mock.patch.object(cal_mod.NseCalendar, "session_type", session_type)


class RequiredHistory(unittest.TestCase):
    def test_required_start_counts_completed_periods_only(self):
        req = inventory.required_start(D(2024, 1, 31))
        self.assertEqual(req["Y"], D(2021, 1, 1))          # 2021, 2022, 2023 completed; 2024 in progress
        self.assertEqual(req["HY"], D(2022, 7, 1))
        self.assertEqual(req["Q"], D(2023, 4, 1))           # Q2, Q3, Q4 2023
        self.assertEqual(req["M"], D(2023, 10, 1))
        self.assertEqual(req["W"], D(2024, 1, 29) - datetime.timedelta(weeks=55))
        self.assertEqual(req["M_context"], D(2019, 6, 1))

    def test_ranges_merge_only_neighbouring_sessions(self):
        days = [D(2025, 1, 6), D(2025, 1, 7), D(2025, 1, 10), D(2025, 2, 3)]
        self.assertEqual(inventory._ranges(days),
                         [{"from": "2025-01-06", "to": "2025-01-10", "sessions": 3},
                          {"from": "2025-02-03", "to": "2025-02-03", "sessions": 1}])


class RealInventory(unittest.TestCase):
    def test_local_files_against_the_official_calendar(self):
        raw = os.path.join(ROOT, "nse", "data", "eod", "raw")
        require_local(os.path.isdir(os.path.join(ROOT, "nse", "data", "calendar", "circulars")),
                      "calendar circulars in nse/data/calendar/circulars/")
        require_local(os.path.isdir(raw) and len(os.listdir(raw)) >= 60, "EOD archives in nse/data/eod/raw/")
        inv = inventory.inventory(raw, os.path.join(ROOT, "nse", "data", "eod", "manifest.csv"),
                                  os.path.join(ROOT, "nse", "data", "calendar"), D(2022, 3, 31), ["INFY"])
        # re-pinned 2026-11-09 after the D55 backfill: 2,478 archives 2016-2025 (2,466 trading
        # days, including the four Dhanteras dates confirmed by D58, plus 12 excluded sessions);
        # runs break at holidays
        self.assertEqual(inv["problems"], [])
        self.assertEqual(inv["eod_files"]["archives_loaded"], 2478)
        self.assertEqual(inv["eod_files"]["runs"][0], {"from": "2016-01-01", "to": "2016-03-23", "sessions": 57})
        for tf in ("D", "W", "M", "Q", "HY"):                   # HY from 2020-07-01: held since D55
            self.assertTrue(inv["history"][tf]["ready"], tf)
        # re-pinned 2026-11-10 after owner decision D58 (CAL-2 option A): the four Dhanteras
        # dates are confirmed regular sessions, so the M_context (from 2017-08-01) and Y ranges
        # contain no UNRESOLVED date and are ready. History coverage only: not DATA_READY.
        # (The blocking rule itself, ED-31, is tested on injected dates in UnresolvedDateScope.)
        for tf in ("M_context", "Y"):
            self.assertEqual(inv["history"][tf]["unresolved_dates"], 0, tf)
            self.assertTrue(inv["history"][tf]["ready"], tf)
        self.assertTrue(inv["ready_for_full_scan"])
        self.assertEqual(inv["files_on_non_trading_days"], [])
        self.assertEqual(inv["acquisition"]["calendar"]["missing_years"], [])     # 2019 covered since D48
        self.assertEqual(inv["symbols"]["INFY"]["files_with_eq_row"], 2478)


CA_HEADER = ",".join(ca.COLUMNS) + "\n"


class CorporateActions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "ca.csv")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, rows):
        with open(self.path, "w") as fh:
            fh.write(CA_HEADER + "".join(rows))

    def test_loader_validates(self):
        with open(os.path.join(self.tmp, "x.pdf"), "wb") as fh:
            fh.write(b"SYNTHETIC notice")
        sha = hashlib.sha256(b"SYNTHETIC notice").hexdigest()
        self.write(["SYN,2023-11-20,SPLIT,1,5,SYNTHETIC TEST ROW,x.pdf,%s,2026-10-29,\n" % sha,
                    "SYN,2022-05-02,DIVIDEND,,,,,,2026-10-29,\n"])
        acts = ca.load(self.path)
        self.assertEqual([(a.action, a.verified) for a in acts], [("DIVIDEND", False), ("SPLIT", True)])
        # a well-formed hash that does not match the file, or a missing file, is not provenance
        for f, h in (("x.pdf", "a" * 64), ("absent.pdf", sha)):
            self.write(["SYN,2023-11-20,SPLIT,1,5,SYNTHETIC TEST ROW,%s,%s,2026-10-29,\n" % (f, h)])
            self.assertEqual([a.verified for a in ca.load(self.path)], [False])
        for bad in ("SYN,2023-13-01,SPLIT,1,5,,,,2026-10-29,\n", "SYN,2023-11-20,MAGIC,1,5,,,,2026-10-29,\n",
                    "SYN,2023-11-20,SPLIT,0,5,,,,2026-10-29,\n"):
            self.write([bad])
            with self.assertRaises(ca.CorporateActionError):
                ca.load(self.path)

    def test_a_split_inside_the_history_holds_the_candidate_and_is_point_in_time(self):
        self.write(["SYN,2023-11-20,SPLIT,1,5,SYNTHETIC TEST ROW,x.pdf,%s,2026-10-29,\n" % ("a" * 64),
                    "SYN,2030-01-01,BONUS,1,2,SYNTHETIC TEST ROW,x.pdf,%s,2026-10-29,\n" % ("a" * 64),
                    "SYN,2023-11-21,DIVIDEND,,,,,,2026-10-29,\n"])
        acts = ca.load(self.path)
        cs = R.long_mit_candles()
        cfg = scanner.ScanConfig(as_of=cs[-1].end, calendar=CAL, risk_per_trade=1000.0, corporate_actions=acts)
        [c] = scanner.scan([R.daily_input("SYN", cs)], cfg).symbols[0].candidates
        self.assertEqual((c.gate("G0").outcome, c.status), (m.MANUAL, m.MANUAL_REVIEW))
        self.assertIn("G0:CORPORATE_ACTION_IN_HISTORY", c.manual_review)
        self.assertNotIn("2030", " ".join(c.gate("G0").reasons))               # the future bonus is unknown at T
        before = cs[[i for i, x in enumerate(cs) if x.start.date() >= D(2023, 11, 20)][0] - 1].end
        early = scanner.scan([R.daily_input("SYN", cs)], scanner.ScanConfig(as_of=before, calendar=CAL,
                                                                           corporate_actions=acts))
        for c in early.candidates():
            self.assertNotIn("G0:CORPORATE_ACTION_IN_HISTORY", c.manual_review)

    def test_no_file_keeps_the_limitation(self):
        cs = R.long_mit_candles()
        [c] = scanner.scan([R.daily_input("SYN", cs)], scanner.ScanConfig(as_of=cs[-1].end, calendar=CAL,
                                                                          risk_per_trade=1000.0)).symbols[0].candidates
        self.assertEqual(c.gate("G0").outcome, m.MANUAL)
        self.assertIn("G0:CORPORATE_ACTION_COVERAGE_UNKNOWN", c.manual_review)
        self.assertNotEqual(c.status, m.ACTIONABLE)


class PrevcloseDiscontinuity(unittest.TestCase):
    """SYNTHETIC legacy bhavcopy files: PREVCLOSE follows the last close except on one day."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def files(self, closes, prevs):
        from nse.research.deps import bhavcopy as bc
        mon = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
        paths = []
        for d, c, pc in zip(R.weekdays(D(2024, 1, 8), len(closes)), closes, prevs):
            stamp = "%02d-%s-%04d" % (d.day, mon[d.month - 1], d.year)
            path = os.path.join(self.tmp, "cm%02d%s%04dbhav.csv" % (d.day, mon[d.month - 1], d.year))
            with open(path, "w", newline="") as fh:
                fh.write(",".join(bc.LEGACY_HEADER) + "\n")
                fh.write("SYN,EQ,%s,%s,%s,%s,%s,%s,1000,100000,%s,10,INE000A01019,\n" % (c, c, c, c, c, pc, stamp))
            paths.append(path)
        return bc.load_many(paths)

    def test_detected_dated_and_restricting(self):
        from nse.research import marketdata
        files = self.files(["100", "102", "51.5", "52"], ["99", "100", "51", "51.5"])   # 102 -> 51 on day 3
        [x] = ca.prevclose_discontinuities(files, "SYN")
        self.assertEqual((x["date"], x["last_close"], x["prev_close"], x["ratio"]), (D(2024, 1, 10), "102", "51", 0.5))
        inp = marketdata.from_bhavcopy(files, "SYN")
        [f] = [f for f in inp.findings if f.code == "PREVCLOSE_DISCONTINUITY"]
        self.assertEqual((f.date, f.extra["ratio"]), (D(2024, 1, 10), 0.5))
        self.assertEqual(ca.prevclose_discontinuities(self.files(["100", "102"], ["99", "100"]), "SYN"), [])
        self.assertEqual(x["weekdays_between"], 0)
        self.assertIn("possible unadjusted corporate action", f.detail)

    def test_a_comparison_across_missing_files_is_not_called_a_corporate_action(self):
        # audit 2026-11-06 (Agent 5): the held files skip two weekdays; the change may be the gap
        from nse.research import marketdata
        files = self.files(["100", "102", "51.5", "52"], ["99", "100", "51", "51.5"])
        files = files[:2] + files[3:]                    # drop the 102 -> 51 day; compare across it
        [x] = ca.prevclose_discontinuities(files, "SYN")
        self.assertEqual(x["weekdays_between"], 1)
        [f] = [f for f in marketdata.from_bhavcopy(files, "SYN").findings if f.code == "PREVCLOSE_DISCONTINUITY"]
        self.assertIn("a corporate action is not established", f.detail)
        self.assertEqual(f.extra["weekdays_between"], 1)

    def test_a_discontinuity_inside_the_history_holds_g0_and_a_later_one_does_not(self):
        from nse.research import marketdata
        cs = R.long_mit_candles()
        inside = marketdata.Finding("SYN", marketdata.WARNING, "PREVCLOSE_DISCONTINUITY", "synthetic",
                                    date=D(2022, 5, 2), extra={"ratio": 0.5, "file": "x"})
        after = marketdata.Finding("SYN", marketdata.WARNING, "PREVCLOSE_DISCONTINUITY", "synthetic",
                                   date=D(2030, 1, 1), extra={"ratio": 0.5, "file": "y"})
        cfg = scanner.ScanConfig(as_of=cs[-1].end, calendar=CAL, risk_per_trade=1000.0)
        [c] = scanner.scan([marketdata.DailyInput("SYN", cs, {}, [], [inside])], cfg).symbols[0].candidates
        self.assertEqual((c.gate("G0").outcome, c.status), (m.MANUAL, m.MANUAL_REVIEW))
        self.assertIn("G0:PRICE_DISCONTINUITY_IN_HISTORY", c.manual_review)
        [c] = scanner.scan([marketdata.DailyInput("SYN", cs, {}, [], [after])], cfg).symbols[0].candidates
        self.assertNotIn("G0:PRICE_DISCONTINUITY_IN_HISTORY", c.manual_review)
        self.assertIn("G0:CORPORATE_ACTION_COVERAGE_UNKNOWN", c.manual_review)


class RealDiscontinuities(unittest.TestCase):
    def test_q1_2022_files(self):
        import glob
        from nse.research.deps import bhavcopy as bc
        # Q1 2022 only, as the name says (MP1: the raw folder now holds 2021-2025)
        zips = sorted(p for p in glob.glob(os.path.join(ROOT, "nse", "data", "eod", "raw", "cm*2022bhav.csv.zip"))
                      if bc.name_info(os.path.basename(p))[0] <= D(2022, 3, 31))
        require_local(len(zips) >= 61, "the 61 Q1 2022 bhavcopy archives in nse/data/eod/raw/")
        files = bc.load_many(zips, bc.read_manifest(os.path.join(ROOT, "nse", "data", "eod", "manifest.csv")))
        self.assertEqual(ca.prevclose_discontinuities(files, "INFY"), [])
        [x] = ca.prevclose_discontinuities(files, "SETFGOLD")       # the only one found in these files
        self.assertEqual(x["date"], D(2022, 1, 6))

    def test_muhurat_sessions_leave_a_detected_discontinuity(self):
        # MP1 real-data finding (owner question DQ-1): NSE publishes no bhavcopy for a Muhurat
        # session, so the next PREVCLOSE is the Muhurat close. Across the Sunday session of
        # 2023-11-12 no weekday separates the held files. The detector reports it and G0 is
        # MANUAL (fail-closed); it is not treated as explained.
        from nse.research.deps import bhavcopy as bc
        raw = os.path.join(ROOT, "nse", "data", "eod", "raw")
        names = ["cm10NOV2023bhav.csv.zip", "cm13NOV2023bhav.csv.zip"]
        require_local(all(os.path.isfile(os.path.join(raw, n)) for n in names), "Nov 2023 archives")
        files = bc.load_many([os.path.join(raw, n) for n in names],
                             bc.read_manifest(os.path.join(ROOT, "nse", "data", "eod", "manifest.csv")))
        [x] = ca.prevclose_discontinuities(files, "INFY")
        self.assertEqual((x["date"], x["weekdays_between"]), (D(2023, 11, 13), 0))


class RealWindow(unittest.TestCase):
    def setUp(self):
        require_local(os.path.isdir(os.path.join(ROOT, "nse", "data", "calendar", "circulars")),
                      "calendar circulars in nse/data/calendar/circulars/")
        require_local(len(os.listdir(os.path.join(ROOT, "nse", "data", "eod", "raw"))) >= 60,
                      "EOD archives in nse/data/eod/raw/")

    def test_inventory_window_counts_sessions_from_the_calendar(self):
        inv = inventory.inventory(os.path.join(ROOT, "nse", "data", "eod", "raw"),
                                  os.path.join(ROOT, "nse", "data", "eod", "manifest.csv"),
                                  os.path.join(ROOT, "nse", "data", "calendar"), D(2025, 12, 31),
                                  window_start=D(2021, 1, 1))
        # re-pinned after the D47 backfill: every 2021-2025 trading day is held (was 1,171 missing)
        self.assertEqual((inv["history"]["WINDOW"]["sessions_needed"], inv["missing_sessions"]["count"]), (1233, 0))
        self.assertEqual(len(inv["excluded_sessions"]["dates"]), 7)
        self.assertEqual(inv["files_on_non_trading_days"], [])

    def test_runner_required_window(self):
        from nse.validation import run_all
        self.assertEqual(run_all.check_local_data((D(2022, 1, 3), D(2022, 3, 31)))["status"], run_all.PASS)
        # re-pinned after the D55 backfill: December 2020 is held now; a window reaching before
        # the calendar (2015) must fail, and so must one containing an UNRESOLVED date (D54)
        self.assertEqual(run_all.check_local_data((D(2020, 12, 1), D(2021, 1, 29)))["status"], run_all.PASS)
        bad = run_all.check_local_data((D(2015, 12, 1), D(2016, 1, 29)))
        self.assertEqual(bad["status"], run_all.FAIL)
        self.assertEqual(bad["details"]["required_window"]["outside_calendar_coverage"], 23)
        # D58 (CAL-2 option A): 2016-10-28 is a confirmed regular session, so October 2016 passes
        cal2 = run_all.check_local_data((D(2016, 10, 3), D(2016, 10, 31)))
        self.assertEqual((cal2["status"], cal2["details"]["required_window"]["unresolved"]), (run_all.PASS, []))
        # ...and a window that contains an UNRESOLVED date still fails (D54 rule, ED-42)
        with unresolved_calendar_dates(D(2016, 10, 28)):
            bad = run_all.check_local_data((D(2016, 10, 3), D(2016, 10, 31)))
        self.assertEqual((bad["status"], bad["details"]["required_window"]["unresolved"]), (run_all.FAIL, ["2016-10-28"]))

    def test_unresolved_dates_outside_a_window_do_not_fail_it(self):
        # D54 / ED-42: an UNRESOLVED date never blocks unrelated readiness; it is listed per
        # month as information, never as a calendar-vs-EOD disagreement. Since D58 the real
        # tables have none, so one is injected; the real October 2016 lists nothing.
        from nse.validation import run_all
        out = run_all.check_local_data()
        self.assertEqual(out["status"], run_all.PASS, out["problems"])
        self.assertNotIn("unresolved", out["details"]["reconciliation"]["2016-10"].get("info", {}))
        with unresolved_calendar_dates(D(2016, 10, 28)):
            out = run_all.check_local_data()
        self.assertEqual(out["status"], run_all.PASS, out["problems"])
        self.assertEqual(out["details"]["reconciliation"]["2016-10"]["info"]["unresolved"], ["2016-10-28"])
        self.assertEqual(out["details"]["reconciliation"]["2016-10"]["issues"], {})

    def test_a_file_on_an_excluded_session_is_information_not_a_problem(self):
        from unittest import mock
        from nse.research.deps import calendar as cal_mod
        from nse.validation import run_all
        real = cal_mod.reconcile

        def with_muhurat(cal, dates, start, end):
            r = real(cal, dates, start, end)
            if start.month == 2:
                r.eod_on_excluded_session.append(D(2022, 2, 15))     # injected for the test
            return r
        with mock.patch.object(cal_mod, "reconcile", with_muhurat):
            out = run_all.check_local_data()
        self.assertEqual(out["status"], run_all.PASS)
        self.assertEqual(out["details"]["reconciliation"]["2022-02"]["info"],
                         {"eod_on_excluded_session": ["2022-02-15"]})


class QuarterlyReference(unittest.TestCase):
    """The recorded INFY daily reference (Yahoo Finance screenshots: republished exchange data,
    not independent) aggregated to Q1 2022 must equal the replayed Quarterly candle."""

    def test_q_rows_are_compared(self):
        import glob
        from nse.research.deps import bhavcopy as bc, replay_mod
        ref = os.path.join(ROOT, "nse", "data", "reference", "INFY", "ohlc_reference.csv")
        # Q1 2022 only (MP1: the raw folder now holds 2021-2025)
        zips = sorted(p for p in glob.glob(os.path.join(ROOT, "nse", "data", "eod", "raw", "cm*2022bhav.csv.zip"))
                      if bc.name_info(os.path.basename(p))[0] <= D(2022, 3, 31))
        require_local(len(zips) >= 61 and os.path.isfile(ref), "Q1 2022 archives and the INFY reference")
        require_local(os.path.isdir(os.path.join(ROOT, "nse", "data", "calendar", "circulars")), "calendar circulars")
        from nse.research.deps import calendar as cal_mod
        rows = [r for r in reference.read_ohlc_reference(ref) if r.timeframe == "D"]
        self.assertEqual(len(rows), 61)
        files = bc.load_many(zips, bc.read_manifest(os.path.join(ROOT, "nse", "data", "eod", "manifest.csv")))
        rp = replay_mod.replay_symbol(files, "INFY", htf=("D", "Q"), assume_regular_session=True,
                                      calendar=cal_mod.NseCalendar.load(os.path.join(ROOT, "nse", "data", "calendar")))
        rows.sort(key=lambda r: r.bar_date)
        q = dict(open=rows[0].open, high=max(r.high for r in rows), low=min(r.low for r in rows), close=rows[-1].close)
        import dataclasses
        qref = dataclasses.replace(rows[0], timeframe="Q", bar_date=D(2022, 1, 3), **q)
        res = reference.compare_ohlc(rows + [qref], rp)
        [qc] = [c for c in res if c.timeframe == "Q"]
        self.assertEqual((qc.status, qc.period), (reference.MATCH, "2022-Q1"))
        wrong = dataclasses.replace(qref, close=q["close"] + 1)
        [qc] = [c for c in reference.compare_ohlc(rows + [wrong], rp) if c.timeframe == "Q"]
        # the recorded rows do not state adjustment OFF/OFF, so a difference is never called a data error
        adjusted = not (qref.adjust_dividends == "OFF" and qref.adjust_splits == "OFF")
        self.assertEqual((qc.status, qc.classification),
                         (reference.MISMATCH, reference.METHODOLOGY_AMBIGUITY if adjusted
                          else reference.CANDLE_CONSTRUCTION_MISMATCH))

    def test_zone_rows_refuse_quarterly(self):
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "z.csv")
            with open(path, "w") as fh:
                fh.write(",".join(reference.ZONE_REFERENCE_COLUMNS) + "\n" +
                         zone_row("2024-01-17", "159.94", "157.92", tf="Q"))
            with self.assertRaises(reference.ReferenceFormatError):
                reference.read_zone_reference(path)
        finally:
            shutil.rmtree(tmp)


class ManifestRows(unittest.TestCase):
    """SYNTHETIC archive in a temporary folder; the real manifest is never touched."""

    def setUp(self):
        import zipfile
        from nse.research.deps import bhavcopy as bc
        self.tmp = tempfile.mkdtemp()
        self.manifest = os.path.join(self.tmp, "manifest.csv")
        with open(self.manifest, "w") as fh:
            fh.write(",".join(bc.MANIFEST_COLUMNS) + "\n")
        body = ",".join(bc.LEGACY_HEADER) + "\n" + \
            "SYN,EQ,10,11,9,10.5,10.5,10,1000,10000,08-JAN-2024,10,INE000A01019,\n"
        self.zip = os.path.join(self.tmp, "cm08JAN2024bhav.csv.zip")
        with zipfile.ZipFile(self.zip, "w") as z:
            z.writestr("cm08JAN2024bhav.csv", body)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_rows_make_the_strict_loader_accept_the_file(self):
        from nse.research import manifest_tool as mt
        from nse.research.deps import bhavcopy as bc
        with self.assertRaises(bc.ProvenanceError):
            bc.load_many([self.zip], self.manifest)
        rows = mt.rows_for([self.zip], self.manifest, "SYNTHETIC TEST", "UNKNOWN", "TEST_ONLY")
        self.assertEqual([r["kind"] for r in rows], ["ARCHIVE", "ARCHIVE_MEMBER"])
        self.assertEqual(rows[1]["provenance_status"], "TEST_ONLY_VIA_ARCHIVE")
        mt.append(self.manifest, rows)
        [f] = bc.load_many([self.zip], self.manifest)
        self.assertEqual(f.provenance["downloaded_on"], "UNKNOWN")
        with self.assertRaises(mt.ManifestError):                         # never twice
            mt.rows_for([self.zip], self.manifest, "x", "2026-10-29", "TEST_ONLY")

    def test_what_only_the_user_knows_is_required(self):
        from nse.research import manifest_tool as mt
        for args in (("", "2026-10-29", "S"), ("page", "yesterday", "S"), ("page", "2026-10-29", "")):
            with self.assertRaises(mt.ManifestError):
                mt.rows_for([self.zip], self.manifest, *args)


class TrendReference(unittest.TestCase):
    """Expected SMA 50 values come from the input candles grouped by ISO week here, not from
    the engine's weekly candles. SYNTHETIC history; the rows are not TradingView readings."""

    def test_weekly_sma_matches_and_short_history_is_no_actual(self):
        cs = R.long_mit_candles()
        snap = mtf.replay(cs, "D", htf=scanner.HTF, calendar=CAL)
        weeks = {}
        for c in cs:
            weeks.setdefault(c.start.date().isocalendar()[:2], []).append(c)
        closes = [v[-1].close for k, v in sorted(weeks.items())][:-1]          # the last week is in progress
        expected = Decimal(str(sum(closes[-50:]) / 50)).quantize(Decimal("0.0001"))
        friday = sorted(weeks.items())[-2][1][-1].start.date()
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "trend.csv")

            def write(*rows):
                with open(path, "w") as fh:
                    fh.write(",".join(refcheck.TREND_COLUMNS) + "\n")
                    for d, v in rows:
                        fh.write("SYN,NSE,W,%s,%s,TRADINGVIEW_MANUAL,,,Asia/Kolkata,OFF,OFF,2026-10-29,SYNTHETIC\n" % (d, v))
            write((friday.isoformat(), str(expected)), (cs[5].start.date().isoformat(), "200.0000"))
            out = refcheck.compare_trend(refcheck.read_trend_reference(path), snap)
            self.assertEqual([r["status"] for r in out["results"]], [refcheck.MATCH, refcheck.NO_ACTUAL])
            write((friday.isoformat(), str(expected + Decimal("0.5"))))
            [r] = refcheck.compare_trend(refcheck.read_trend_reference(path), snap)["results"]
            self.assertEqual((r["status"], r["classification"]), (refcheck.MISMATCH, refcheck.INSUFFICIENT_EVIDENCE))
        finally:
            shutil.rmtree(tmp)


ZONE_HEADER = ",".join(reference.ZONE_REFERENCE_COLUMNS) + "\n"


def zone_row(created, pl, dl, tested="NO", first_test="", invalidated="", side="demand", pattern="DBR", tf="D"):
    return ("SYN,NSE,%s,max base 5,%s,%s,,%s,%s,%s,7/7,%s,%s,%s,TRADINGVIEW_MANUAL,Asia/Kolkata,OFF,OFF,2026-10-29,"
            "SYNTHETIC TEST ROW (hand-derived from the fixture inputs, not a TradingView reading)\n"
            % (tf, side, pattern, created, pl, dl, tested, first_test, invalidated))


class ZoneReference(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cs = R.long_mit_candles()
        self.snap = mtf.replay(self.cs, "D", htf=scanner.HTF, calendar=CAL)
        legout = [c for c in self.cs if c.close == round(101.5 * R.LONG_K, 2)][0]
        self.created = legout.start.date().isoformat()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def compare(self, rows, **kw):
        path = os.path.join(self.tmp, "zone_reference.csv")
        with open(path, "w") as fh:
            fh.write(ZONE_HEADER + "".join(rows))
        return refcheck.compare_zones(reference.read_zone_reference(path), self.snap, **kw)

    def test_hand_derived_reference_matches(self):
        out = self.compare([zone_row(self.created, "159.94", "157.92")])
        [r] = out["results"]
        self.assertEqual((r["status"], out["complete"]), (refcheck.MATCH, True))

    def test_a_disagreement_is_reported_not_resolved(self):
        out = self.compare([zone_row(self.created, "160.50", "157.92")])
        [r] = out["results"]
        self.assertEqual((r["status"], r["classification"]), (refcheck.MISMATCH, refcheck.INSUFFICIENT_EVIDENCE))
        self.assertEqual(r["differences"]["proximal"], ["160.50", "159.94"])
        self.assertFalse(out["complete"])
        self.assertEqual(self.compare([zone_row(self.created, "160.50", "157.92")], tolerance=Decimal("0.6"))
                         ["results"][0]["status"], refcheck.MATCH)
        self.assertEqual(self.compare([zone_row(self.created, "159.94", "157.92", tested="YES")])
                         ["results"][0]["differences"]["tested"], ["YES", "NO"])

    def test_missing_zone_and_unreferenced_zone_are_never_matches(self):
        last = self.cs[-1].start.date().isoformat()
        out = self.compare([zone_row("2024-01-02", "170.00", "165.00"), zone_row(last, "170.00", "165.00")])
        self.assertEqual([r["status"] for r in out["results"][:2]], [refcheck.NO_ACTUAL] * 2)
        self.assertIn(refcheck.NO_REFERENCE, [r["status"] for r in out["results"]])     # the real zone, unreferenced
        self.assertFalse(out["complete"])


if __name__ == "__main__":
    unittest.main()


class CorporateActionStoreD50(unittest.TestCase):
    """D50 (owner 2026-11-09): events and terms stored separately from raw prices, read from
    official subject text by exact patterns only. SYNTHETIC API-shaped JSON."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def convert(self, subjects):
        import json
        raw = os.path.join(self.tmp, "raw")
        os.makedirs(raw)
        path = os.path.join(raw, "ca.json")
        with open(path, "w") as fh:
            json.dump([{"symbol": "SYN", "series": "EQ", "isin": "INE000A01019", "exDate": "0%d-Jan-2024" % (i + 1),
                        "recDate": "", "subject": s} for i, s in enumerate(subjects)], fh)
        return ca.from_nse_json(path, self.tmp, "2026-11-09")

    def test_exact_patterns_give_terms(self):
        rows, unparsed, skipped = self.convert([
            " Bonus 3:2", "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share",
            "Face Value Consolidation - From Rs 1/- Per Share To Rs 10/- Per Share", " Rights 1:15 @ Premium Rs 1247",
            "Demerger", "Interim Dividend - Rs 7 Per Share", "Buyback"])
        got = [(r["action"], r["ratio_from"], r["ratio_to"]) for r in rows]
        self.assertEqual(got, [("BONUS", "2", "5"), ("SPLIT", "1", "5"), ("CONSOLIDATION", "10", "1"),
                               ("RIGHTS", "0", "0"), ("DEMERGER", "0", "0"), ("DIVIDEND", "0", "0")])
        self.assertEqual(unparsed, [])
        self.assertEqual([s["subject"] for s in skipped], ["Buyback"])
        self.assertIn("subject: Bonus 3:2", rows[0]["notes"])

    def test_combined_or_unclear_price_events_are_never_guessed(self):
        rows, unparsed, _ = self.convert(["Bonus 1:1 And Face Value Split (Sub-Division) - From Rs 10/- Per Share To "
                                          "Rs 5/- Per Share", "Scheme Of Arrangement", "Face Value Split (Sub-Division) "
                                          "- From Rs 10/- Per Share To Rs 3/- Per Share", "Bonus issue",
                                          "Rights 1:5 @ Premium Rs 100 And Bonus 1:1"])     # QA: anchored
        # D56: never guessed and never silent: each unclear subject is one UNPARSED_PRICE_EVENT.
        # ED-57 (D67): "From Rs 10 To Rs 3" states its terms in full; it is read exactly as
        # SPLIT 3:10 (old:new share count), not guessed. The other four stay unparsed.
        self.assertEqual([(r["action"], r["ratio_from"], r["ratio_to"]) for r in rows],
                         [("UNPARSED_PRICE_EVENT", "0", "0"), ("UNPARSED_PRICE_EVENT", "0", "0"),
                          ("SPLIT", "3", "10"),
                          ("UNPARSED_PRICE_EVENT", "0", "0"), ("UNPARSED_PRICE_EVENT", "0", "0")])
        self.assertIn("UNPARSED_PRICE_EVENT", ca.PRICE_ACTIONS)
        self.assertEqual(len(unparsed), 4)

    def test_official_variants_and_combined_subjects(self):
        rows, unparsed, skipped = self.convert([
            "Face Value Split (Sub-Division) - From Rs 2/- Per Share To Re 1/- Per Share",
            "Face Value Split From Rs 10 To Re 2", "Face Value Split (Sub-Division) - From Rs10/- Per Share To Re 1/- Per Share",
            "Rights 1:10 @ Prem Rs 197/- Per Share", "Bonus 1:1 /Dividend- Rs 29",
            "Bonus 1:1/Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share",
            "Annual General Meeting/Dividend - Rs 2.50 Per Share/Bonus 1:10 (Revised)"])
        got = [(r["ex_date"], r["action"], r["ratio_from"], r["ratio_to"]) for r in rows]
        self.assertEqual(got, [("2024-01-01", "SPLIT", "1", "2"), ("2024-01-02", "SPLIT", "1", "5"),
                               ("2024-01-03", "SPLIT", "1", "10"), ("2024-01-04", "RIGHTS", "0", "0"),
                               ("2024-01-05", "BONUS", "1", "2"), ("2024-01-05", "DIVIDEND", "0", "0"),
                               ("2024-01-06", "BONUS", "1", "2"), ("2024-01-06", "SPLIT", "1", "5"),
                               ("2024-01-07", "UNPARSED_PRICE_EVENT", "0", "0")])
        self.assertEqual([u["subject"][-17:] for u in unparsed], ["Bonus 1:10 (Revised)"[-17:]])

    def test_abbreviated_splits_and_unknown_subjects_are_never_skipped(self):
        # regression (D56 audit, 2026-11-09): NSE's "Fv Splt Frm Rs 10 To Re 1" (JSWSTEEL, ex
        # 04-Jan-2017) was read as "no price event" and dropped. Only known non-price subjects
        # are skipped now; anything unrecognised is an UNPARSED_PRICE_EVENT (G0 MANUAL).
        rows, unparsed, skipped = self.convert([
            "Fv Splt Frm Rs 10 To Re 1", "Fv Splt Frm Rs 10 To Rs 3", "Int Div Rs 5 Per Sh", "Interimdividend - Rs 2",
            "Annnual General Meeting/ Annula General Meeting/Annul General Meeting", "Buy-Back Of Shares", "Annual General Meeting (Book Closure Date Revised)",
            "Capital Restructuring", "Annual General Meeting/ Change In Registrar And Transfer Agent"])
        got = [(r["ex_date"], r["action"], r["ratio_from"], r["ratio_to"]) for r in rows]
        # ED-57 (D67): "Fv Splt Frm Rs 10 To Rs 3" is read exactly as SPLIT 3:10 (was unparsed);
        # it is still never skipped. "Capital Restructuring" stays unparsed.
        self.assertEqual(got, [("2024-01-01", "SPLIT", "1", "10"), ("2024-01-02", "SPLIT", "3", "10"),
                               ("2024-01-03", "DIVIDEND", "0", "0"), ("2024-01-04", "DIVIDEND", "0", "0"),
                               ("2024-01-08", "UNPARSED_PRICE_EVENT", "0", "0")])
        self.assertEqual([u["subject"] for u in unparsed], ["Capital Restructuring"])
        self.assertEqual(len(skipped), 4)

    def test_split_wording_with_div_is_never_a_dividend(self):
        # QA 2026-11-09: "Sub Division" / "Sub Div" matched the dividend spelling "\bdiv"
        rows, unparsed, _ = self.convert(["Sub Division Of Equity Shares From Rs 10 To Re 1", "Sub Div Frm Rs 10 To Re 1",
                                          "Dividend - Rs 2 / Sub Division", "Divestment of undertaking",
                                          "Annual General Meeting/Div-Rs 3 Per Share"])
        self.assertEqual([r["action"] for r in rows], ["UNPARSED_PRICE_EVENT"] * 4 + ["DIVIDEND"])
        self.assertEqual(len(unparsed), 4)

    def test_rows_load_verified_and_prices_are_never_adjusted(self):
        rows, _, _ = self.convert([" Bonus 1:1"])
        [a] = ca.load(ca.write(rows, os.path.join(self.tmp, "actions.csv")))
        self.assertEqual((a.action, a.ratio_from, a.ratio_to, a.verified), ("BONUS", 1.0, 2.0, True))
        import nse.research.marketdata as md
        self.assertFalse(any(n for n in dir(md) if "adjust" in n.lower() and callable(getattr(md, n))))


class UnresolvedDateScope(unittest.TestCase):
    """An unresolved calendar date blocks only the timeframes whose required range contains it
    (MP1, ED-31). Real calendar, no EOD files. The four 2016-2019 Dhanteras dates were the real
    UNRESOLVED rows until D58 confirmed them; the same four dates are injected as UNRESOLVED."""

    def test_scope_by_required_range(self):
        require_local(os.path.isdir(os.path.join(ROOT, "nse", "data", "calendar", "circulars")),
                      "calendar circulars in nse/data/calendar/circulars/")
        empty = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, empty, True)
        cal_dir = os.path.join(ROOT, "nse", "data", "calendar")
        real = inventory.inventory(empty, None, cal_dir, D(2020, 3, 31))["history"]
        self.assertEqual([tf for tf, h in real.items() if h["unresolved_dates"]], [])     # D58: none left
        with unresolved_calendar_dates(*(D.fromisoformat(d) for d in DHANTERAS)):
            inv = inventory.inventory(empty, None, cal_dir, D(2020, 3, 31))
        hist = inv["history"]
        self.assertEqual(hist["D"]["unresolved_dates"], 0)              # last few sessions: none
        unresolved_in_y = [d for d in DHANTERAS if d >= hist["Y"]["from"]]
        self.assertEqual(hist["Y"]["unresolved_dates"], len(unresolved_in_y))
        self.assertGreater(len(unresolved_in_y), 0)
        self.assertFalse(hist["Y"]["ready"])                            # still blocked where it applies


class ExcludedSessionD52(unittest.TestCase):
    """D52 (owner 2026-11-09): a PREVCLOSE discontinuity across a calendar-confirmed excluded
    session without an EOD file is explained only with every safeguard met. SYNTHETIC candles
    (tests/_research.py) and a fake calendar naming one weekday as an excluded session."""
    BEFORE = D(2023, 6, 14)          # before the candidate zone forms (2024-01-15)
    INSIDE = D(2024, 1, 24)          # inside the candidate zone's span

    class Cal(R.WeekdayCalendar):
        def __init__(self, excluded=(), unresolved=()):
            super().__init__()
            self.excluded, self.unresolved = set(excluded), set(unresolved)

        def session_type(self, d):
            from nse.research.deps import calendar as cal_mod
            if d in self.unresolved:
                raise cal_mod.CalendarAmbiguityError("%s: SYNTHETIC unresolved" % d)
            if d in self.excluded:
                return cal_mod.EXCLUDED_MUHURAT
            return cal_mod.WEEKEND if d.weekday() >= 5 else cal_mod.NORMAL

        @property
        def UNRESOLVED_ERRORS(self):                                   # as NseCalendar declares it
            from nse.research.deps import calendar as cal_mod
            return (cal_mod.CalendarAmbiguityError,)

        def is_trading_day(self, d):                                   # raises for UNRESOLVED, as NseCalendar
            from nse.research.deps import calendar as cal_mod
            return self.session_type(d) == cal_mod.NORMAL

        def is_excluded_session(self, d):
            return d in self.excluded

    def run_scan(self, gap, calendar, coverage=True, actions=(), extra_missing=()):
        from nse.research import marketdata
        drop = {gap} | set(extra_missing)
        cs = [c for c in R.long_mit_candles() if c.start.date() not in drop]       # no candle for the gap
        before = max(c.start.date() for c in cs if c.start.date() < gap)
        after = min(c.start.date() for c in cs if c.start.date() > gap)
        f = marketdata.Finding("SYN", marketdata.WARNING, "PREVCLOSE_DISCONTINUITY", "SYNTHETIC", date=after,
                               extra={"ratio": 1.01, "file": "x", "weekdays_between": 0, "last_date": before.isoformat()})
        cov = {"SYN": [(D(2016, 1, 1), D(2025, 12, 31))]} if coverage else None
        cfg = scanner.ScanConfig(as_of=cs[-1].end, calendar=calendar, risk_per_trade=1000.0,
                                 corporate_actions=list(actions), corporate_action_coverage=cov)
        res = scanner.scan([marketdata.DailyInput("SYN", cs, {}, [], [f])], cfg).symbols[0]
        return res, cs

    def test_confirmed_excluded_session_is_explained_and_never_a_corporate_action(self):
        res, cs = self.run_scan(self.BEFORE, self.Cal(excluded=[self.BEFORE]))
        [c] = res.candidates
        self.assertNotIn("G0:PRICE_DISCONTINUITY_IN_HISTORY", c.manual_review)
        self.assertNotIn("G0:CORPORATE_ACTION_IN_HISTORY", c.manual_review)
        codes = [f["code"] for f in res.findings]
        self.assertIn("PREVCLOSE_EXPLAINED_BY_EXCLUDED_SESSION", codes)
        self.assertIn("PREVCLOSE_DISCONTINUITY", codes)                     # the detection itself is kept
        self.assertIn(m.EXCLUDED_SESSION_UNOBSERVED, res.limitations)       # the missing-session marker
        self.assertNotIn(self.BEFORE, [x.start.date() for x in cs])         # no candle is fabricated

    def test_an_unconfirmed_session_is_not_explained(self):
        # unresolved: the rule refuses (test_an_unresolved_gap_is_never_explained_directly); in
        # a scan the history starts after that date (ED-44), so nothing is explained either
        res, _ = self.run_scan(self.BEFORE, self.Cal(unresolved=[self.BEFORE]))
        self.assertNotIn("PREVCLOSE_EXPLAINED_BY_EXCLUDED_SESSION", [f["code"] for f in res.findings])
        self.assertIn(m.HISTORY_STARTS_AFTER_UNRESOLVED_DATE, res.limitations)
        res, _ = self.run_scan(self.BEFORE, R.WeekdayCalendar(closed=[self.BEFORE]))   # closed, not excluded
        for c in res.candidates:
            self.assertIn("G0:PRICE_DISCONTINUITY_IN_HISTORY", c.manual_review)

    def test_without_verified_corporate_action_coverage_it_stays_a_possible_action(self):
        res, _ = self.run_scan(self.BEFORE, self.Cal(excluded=[self.BEFORE]), coverage=False)
        [c] = res.candidates
        self.assertIn("G0:PRICE_DISCONTINUITY_IN_HISTORY", c.manual_review)

    def test_a_genuine_corporate_action_in_the_gap_is_never_explained_away(self):
        bonus = ca.Action("SYN", self.BEFORE + datetime.timedelta(days=1), "BONUS", 1.0, 2.0, True, "SYNTHETIC")
        res, _ = self.run_scan(self.BEFORE, self.Cal(excluded=[self.BEFORE]), actions=[bonus])
        [c] = res.candidates
        self.assertIn("G0:PRICE_DISCONTINUITY_IN_HISTORY", c.manual_review)
        self.assertIn("G0:CORPORATE_ACTION_IN_HISTORY", c.manual_review)

    def explained(self, cal, between, extra=None, actions=(), held_without_row=frozenset()):
        # the rule itself, on a gap last..next (QA: a scan-level test could pass with no candidates)
        from nse.research import marketdata
        last, nxt = between
        f = marketdata.Finding("SYN", marketdata.WARNING, "PREVCLOSE_DISCONTINUITY", "SYNTHETIC", date=nxt,
                               extra={"last_date": last.isoformat()})
        cfg = scanner.ScanConfig(as_of=datetime.datetime(2025, 1, 1, 15, 30), calendar=cal,
                                 corporate_actions=list(actions),
                                 corporate_action_coverage={"SYN": [(D(2016, 1, 1), D(2025, 12, 31))]})
        if extra:
            cfg = extra(cfg)
        return scanner._explained_by_excluded_session(f, "SYN", cfg, held_without_row)

    def test_a_missing_trading_day_in_the_gap_is_not_explained(self):
        cal = self.Cal(excluded=[self.BEFORE])
        nxt = self.BEFORE + datetime.timedelta(days=1)                     # a normal weekday with no file
        self.assertTrue(self.explained(cal, (self.BEFORE - datetime.timedelta(days=1), nxt)))
        self.assertIsNone(self.explained(cal, (self.BEFORE - datetime.timedelta(days=1), nxt + datetime.timedelta(days=1))))
        res, _ = self.run_scan(self.BEFORE, cal, extra_missing=[nxt])
        for c in res.candidates:
            self.assertIn("G0:PRICE_DISCONTINUITY_IN_HISTORY", c.manual_review)

    def test_an_unresolved_gap_is_never_explained_directly(self):
        gap = (self.BEFORE - datetime.timedelta(days=1), self.BEFORE + datetime.timedelta(days=1))
        self.assertIsNone(self.explained(self.Cal(unresolved=[self.BEFORE]), gap))

    def test_history_starts_after_the_last_unresolved_date(self):
        # D54 / ED-44: an UNRESOLVED date ends every series (L10); a later scan replays from the
        # first session after it instead of being DATA_INSUFFICIENT, and says so (dated)
        from nse.research import marketdata
        cs = R.long_mit_candles()
        cfg = scanner.ScanConfig(as_of=cs[-1].end, calendar=self.Cal(unresolved=[self.BEFORE]), risk_per_trade=1000.0)
        res = scanner.scan([marketdata.DailyInput("SYN", cs, {}, [], [])], cfg).symbols[0]
        self.assertIn(m.HISTORY_STARTS_AFTER_UNRESOLVED_DATE, res.limitations)
        [f] = [f for f in res.findings if f["code"] == m.HISTORY_STARTS_AFTER_UNRESOLVED_DATE]
        self.assertEqual(f["date"], self.BEFORE.isoformat())
        self.assertNotEqual(res.status, scanner.SYMBOL_DATA_INSUFFICIENT, res.reasons)
        self.assertTrue(res.candidates)
        for c in res.candidates:
            self.assertNotEqual(c.status, m.ACTIONABLE)                     # never promoted by the cut
        # an earlier as_of (before the unresolved date) is unchanged by it (prefix invariance)
        early = [c for c in cs if c.start.date() < self.BEFORE]
        cfg_e = scanner.ScanConfig(as_of=early[-1].end, calendar=self.Cal(unresolved=[self.BEFORE]))
        res_e = scanner.scan([marketdata.DailyInput("SYN", early, {}, [], [])], cfg_e).symbols[0]
        self.assertNotIn(m.HISTORY_STARTS_AFTER_UNRESOLVED_DATE, res_e.limitations)

    def test_a_held_file_or_absent_records_are_never_explained(self):
        # QA 2026-11-09: a file held for the session (the symbol absent from it) is not
        # "no EOD file"; coverage without the action records proves nothing
        import dataclasses
        cal = self.Cal(excluded=[self.BEFORE])
        gap = (self.BEFORE - datetime.timedelta(days=1), self.BEFORE + datetime.timedelta(days=1))
        self.assertTrue(self.explained(cal, gap))
        self.assertIsNone(self.explained(cal, gap, held_without_row=frozenset([self.BEFORE])))
        self.assertIsNone(self.explained(cal, gap, extra=lambda c: dataclasses.replace(c, corporate_actions=None)))

    def test_an_unobserved_excluded_session_inside_the_zone_span_makes_g1_manual(self):
        # D33: an excluded session that reaches a zone makes it manual; with no file its price
        # action is unknown, so freshness across it cannot be confirmed (sequence-dependent)
        res, _ = self.run_scan(self.INSIDE, self.Cal(excluded=[self.INSIDE]))
        [c] = res.candidates
        self.assertEqual(c.gate("G1").outcome, m.MANUAL)
        self.assertIn("G1:" + m.EXCLUDED_SESSION_UNOBSERVED, c.manual_review)
        self.assertNotEqual(c.status, m.ACTIONABLE)


class ExternalComparisonRunner(unittest.TestCase):
    """The runner compares supplied rows. It does not invent observations and it does not
    certify T-005. SYNTHETIC rows are not TradingView readings."""

    def _replay(self):
        from nse.research.deps import replay_mod
        bar = replay_mod.DailyBar(D(2024, 1, 8), Decimal("10"), Decimal("11"), Decimal("9"), Decimal("10"),
                                  1, "synthetic.csv", "a" * 64, 2)
        daily = replay_mod.DailySeries("SYN", "EQ", [bar], [], [], [])
        snap = type("S", (), {"calendar_validated": True, "series": {}})()
        return type("R", (), {"symbol": "SYN", "daily": daily, "snapshot": snap})()

    def _ohlc(self, path, close, source, adjust="OFF", tf="D"):
        sha = "" if source == "TRADINGVIEW_MANUAL" else "b" * 64
        evidence = "" if source == "TRADINGVIEW_MANUAL" else "export.csv"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(",".join(reference.OHLC_REFERENCE_COLUMNS) + "\n")
            fh.write("SYN,NSE,%s,2024-01-08,10,11,9,%s,%s,%s,%s,Asia/Kolkata,%s,%s,2026-11-10,synthetic\n"
                     % (tf, close, source, evidence, sha, adjust, adjust))

    def test_no_reference_file_stays_pending(self):
        report = refcheck.external_comparison_report(self._replay())
        self.assertEqual(report["status"], refcheck.PENDING_EXTERNAL_EVIDENCE)
        self.assertFalse(report["certifies_external_validation"])
        self.assertFalse(report["t005_closed"])
        self.assertEqual(report["ohlc"]["results"], [])

    def test_duplicate_bar_is_refused(self):
        row = type("O", (), {"line": 2, "timeframe": "D", "bar_date": D(2024, 1, 8)})()
        other = type("O", (), {"line": 4, "timeframe": "D", "bar_date": D(2024, 1, 8)})()
        with self.assertRaises(ValueError) as caught:
            refcheck.reject_duplicate_observations([row, other], lambda r: (r.timeframe, r.bar_date), "OHLC observation")
        self.assertIn("duplicate", str(caught.exception))

    def test_wrong_timeframe_and_unsupported_source_are_refused(self):
        tmp = tempfile.mkdtemp()
        try:
            bad_tf = os.path.join(tmp, "zone.csv")
            with open(bad_tf, "w", encoding="utf-8") as fh:
                fh.write(",".join(reference.ZONE_REFERENCE_COLUMNS) + "\n")
                fh.write("SYN,NSE,Q,settings,demand,DBR,,2024-01-08,10,9,7/7,NO,,,TRADINGVIEW_MANUAL,"
                         "Asia/Kolkata,OFF,OFF,2026-11-10,synthetic\n")
            with self.assertRaises(reference.ReferenceFormatError):
                reference.read_zone_reference(bad_tf)
            bad_src = os.path.join(tmp, "ohlc.csv")
            self._ohlc(bad_src, "10", "BROKER_EXPORT")
            with self.assertRaises(reference.ReferenceFormatError):
                reference.read_ohlc_reference(bad_src)
        finally:
            shutil.rmtree(tmp)

    def test_unknown_adjustment_is_not_certified_and_a_mismatch_stays_a_mismatch(self):
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "ohlc.csv")
            self._ohlc(path, "99", "TRADINGVIEW_MANUAL", adjust="UNKNOWN")
            rows = reference.read_ohlc_reference(path)
            report = refcheck.external_comparison_report(self._replay(), ohlc_rows=rows)
            self.assertEqual(report["status"], refcheck.COMPARED_NOT_CERTIFIED)
            self.assertFalse(report["t005_closed"])
            self.assertFalse(report["certifies_external_validation"])
            [row] = [r for r in report["ohlc"]["results"] if r["status"] != reference.NO_REFERENCE]
            self.assertEqual((row["status"], row["classification"]),
                             (reference.MISMATCH, reference.METHODOLOGY_AMBIGUITY))
        finally:
            shutil.rmtree(tmp)

    def test_a_yahoo_match_is_not_tradingview_validation(self):
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "ohlc.csv")
            self._ohlc(path, "10", "YAHOO_FINANCE_SCREENSHOT")
            rows = reference.read_ohlc_reference(path)
            report = refcheck.external_comparison_report(self._replay(), ohlc_rows=rows)
            self.assertTrue(report["yahoo_is_not_tradingview"])
            self.assertFalse(report["certifies_external_validation"])
            self.assertFalse(report["t005_closed"])
        finally:
            shutil.rmtree(tmp)
