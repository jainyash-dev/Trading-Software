"""Data readiness (inventory), corporate actions and zone reference comparison.
SYNTHETIC inputs except RealInventory, which reads the local official files (git-ignored)."""

import csv
import datetime
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
        self.assertEqual(inv["problems"], [])
        self.assertEqual(inv["eod_files"]["archives_loaded"], 62)
        self.assertEqual(inv["eod_files"]["runs"][0], {"from": "2022-01-03", "to": "2022-03-31", "sessions": 61})
        self.assertTrue(inv["history"]["D"]["ready"])
        self.assertFalse(inv["history"]["W"]["ready"])          # 55 weeks are not held
        self.assertFalse(inv["ready_for_full_scan"])
        self.assertEqual(inv["files_on_non_trading_days"], [])
        self.assertIn(2019, inv["acquisition"]["calendar"]["missing_years"])
        self.assertEqual(inv["symbols"]["INFY"]["files_with_eq_row"], 62)


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
        self.write(["SYN,2023-11-20,SPLIT,1,5,SYNTHETIC TEST ROW,x.pdf,%s,2026-10-29,\n" % ("a" * 64),
                    "SYN,2022-05-02,DIVIDEND,,,,,,2026-10-29,\n"])
        acts = ca.load(self.path)
        self.assertEqual([(a.action, a.verified) for a in acts], [("DIVIDEND", False), ("SPLIT", True)])
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
        self.assertEqual(c.status, m.ACTIONABLE)
        self.assertEqual(c.gate("G0").outcome, m.PASS)


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
        for d, c, pc in zip(R.weekdays(D(2025, 1, 6), len(closes)), closes, prevs):
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
        self.assertEqual((x["date"], x["last_close"], x["prev_close"], x["ratio"]), (D(2025, 1, 8), "102", "51", 0.5))
        inp = marketdata.from_bhavcopy(files, "SYN")
        [f] = [f for f in inp.findings if f.code == "PREVCLOSE_DISCONTINUITY"]
        self.assertEqual((f.date, f.extra["ratio"]), (D(2025, 1, 8), 0.5))
        self.assertEqual(ca.prevclose_discontinuities(self.files(["100", "102"], ["99", "100"]), "SYN"), [])

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
        self.assertEqual(c.status, m.ACTIONABLE)


class RealDiscontinuities(unittest.TestCase):
    def test_q1_2022_files(self):
        import glob
        from nse.research.deps import bhavcopy as bc
        zips = sorted(glob.glob(os.path.join(ROOT, "nse", "data", "eod", "raw", "cm*2022bhav.csv.zip")))
        require_local(len(zips) >= 61, "the 61 Q1 2022 bhavcopy archives in nse/data/eod/raw/")
        files = bc.load_many(zips, bc.read_manifest(os.path.join(ROOT, "nse", "data", "eod", "manifest.csv")))
        self.assertEqual(ca.prevclose_discontinuities(files, "INFY"), [])
        [x] = ca.prevclose_discontinuities(files, "SETFGOLD")       # the only one found in these files
        self.assertEqual(x["date"], D(2022, 1, 6))


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
        self.assertEqual((inv["history"]["WINDOW"]["sessions_needed"], inv["missing_sessions"]["count"]), (1233, 1171))
        self.assertEqual(len(inv["excluded_sessions"]["dates"]), 7)
        self.assertEqual(inv["files_on_non_trading_days"], [])

    def test_runner_required_window(self):
        from nse.validation import run_all
        self.assertEqual(run_all.check_local_data((D(2022, 1, 3), D(2022, 3, 31)))["status"], run_all.PASS)
        bad = run_all.check_local_data((D(2022, 1, 3), D(2022, 4, 29)))
        self.assertEqual(bad["status"], run_all.FAIL)
        self.assertGreater(bad["details"]["required_window"]["missing_sessions"], 0)

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
        zips = sorted(glob.glob(os.path.join(ROOT, "nse", "data", "eod", "raw", "cm*2022bhav.csv.zip")))
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
            "SYN,EQ,10,11,9,10.5,10.5,10,1000,10000,06-JAN-2025,10,INE000A01019,\n"
        self.zip = os.path.join(self.tmp, "cm06JAN2025bhav.csv.zip")
        with zipfile.ZipFile(self.zip, "w") as z:
            z.writestr("cm06JAN2025bhav.csv", body)

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
