"""End-to-end: candles -> data checks -> Zone Engine -> MTF overlay -> TDA -> G0-G8 ->
results -> JSON/CSV reports, through the REAL replay (mtf_freshness.replay) and scanner.

Synthetic classes use SYNTHETIC candles and a weekday test calendar (not an NSE
calendar). RealNseQ1Of2022 runs official NSE bhavcopies (git-ignored, D31) with the
official calendar; it proves the pipeline runs on real files, not that any decision is
right: the history is one quarter, so nothing can reach ACTIONABLE.
"""

import csv
import glob
import io
import json
import os
import shutil
import tempfile
import unittest

import _research as R
from _load import ROOT, require_local
from nse.research import cli, models as m, reports, scanner
from nse.research.deps import mtf

RAW = os.path.join(ROOT, "nse", "data", "eod", "raw")
MANIFEST = os.path.join(ROOT, "nse", "data", "eod", "manifest.csv")
CAL = os.path.join(ROOT, "nse", "data", "calendar")


def run(candles, days, calendar=None, as_of_index=-1, symbol="SYN"):
    cfg = scanner.ScanConfig(as_of=R.DT.combine(days[as_of_index], mtf.SESSION_CLOSE),
                             calendar=calendar or R.WeekdayCalendar(), calendar_label="TEST_WEEKDAYS")
    return scanner.scan([R.daily_input(symbol, candles)], cfg)


class SyntheticPipeline(unittest.TestCase):
    def test_fresh_zone_flows_through_every_gate(self):
        days, cs = R.dbr_candles()
        res = run(cs, days)
        s = res.symbols[0]
        self.assertEqual(s.status, scanner.SYMBOL_EVALUATED)
        [c] = s.candidates
        self.assertEqual(c.zone["proximal"], R.DBR_PL)
        self.assertEqual([g.gate for g in c.gates], list(m.GATES))
        self.assertEqual((c.gate("G1").outcome, c.gate("G2").outcome), (m.PASS, m.PASS))
        # three months of history: no curve, no trend, no Q/HY/Y -> never actionable
        self.assertEqual(c.status, m.STATUS_DATA_INSUFFICIENT)
        self.assertEqual(c.gate("G4").outcome, m.MANUAL)
        self.assertIn("TREND_INSUFFICIENT_HISTORY", c.gate("G4").manual_review)

    def test_candidates_are_exactly_the_overlay_kept_zones(self):
        for seed in range(6):
            cs = R.random_walk(seed, 420)
            days = [c.start.date() for c in cs]
            res = run(cs, days)
            snap = mtf.replay(cs, "D", htf=scanner.HTF, as_of=res_as_of(res), calendar=R.WeekdayCalendar())
            kept = [a.zone.id for a in snap.eligible_after_overlay("D")[0]]
            kept += [a.zone.id for a in snap.manual_review_after_overlay("D")[0]]
            got = [c.zone["zone_id"] for c in res.symbols[0].candidates]
            self.assertEqual(sorted(got), sorted(kept), seed)

    def test_tested_zone_leaves_the_candidates_and_the_fresh_zone_report(self):
        days, cs = R.dbr_candles(touch_on=50)
        s = run(cs, days).symbols[0]
        self.assertEqual(s.candidates, [])
        self.assertEqual(s.status, scanner.SYMBOL_NO_EXECUTION_ZONE)
        # on a daily base the engine sees the daily touch itself, so the zone is never
        # engine-eligible; the overlay agrees, and neither report lists it as fresh
        snap = mtf.replay(cs, "D", htf=scanner.HTF, calendar=R.WeekdayCalendar())
        [st] = [z for z in snap.zones.values() if z.tf == "D" and z.side == "demand" and z.proximal == R.DBR_PL]
        self.assertEqual(st.status, mtf.TESTED)
        self.assertNotIn(st.zone_id, [z["zone_id"] for z in s.fresh_zones if z["tf"] == "D"])
        self.assertEqual(s.blocked_zones, [])

    def test_a_missing_session_never_reads_as_fresh(self):
        days, cs = R.dbr_candles(skip=(50,))
        s = run(cs, days).symbols[0]
        self.assertEqual(s.status, scanner.SYMBOL_DATA_INSUFFICIENT)       # D series ends at the gap
        self.assertTrue(all(c.status != m.ACTIONABLE for c in s.candidates))
        self.assertTrue(any(f["code"] == "MISSING_SESSION" for f in s.findings))

    def test_data_errors_stop_before_the_replay(self):
        from nse.research import marketdata
        inp = marketdata.DailyInput("BAD", [], {}, [], [marketdata.Finding("BAD", marketdata.ERROR, "DUPLICATE_DATE", "x")])
        res = scanner.scan([inp], scanner.ScanConfig(as_of=R.AS_OF))
        self.assertEqual(res.symbols[0].status, scanner.SYMBOL_DATA_INSUFFICIENT)

    def test_reports_reconcile_with_the_records(self):
        cs = R.random_walk(3, 420)
        res = run(cs, [c.start.date() for c in cs])
        out = tempfile.mkdtemp()
        try:
            names = reports.write_all(res, out)
            self.assertEqual(names, ["blocked_zones.csv", "candidates.csv", "data_quality.csv", "fresh_zones.csv",
                                     "readiness.json", "scan.json", "summary.json"])
            with open(os.path.join(out, "summary.json")) as fh:
                summ = json.load(fh)
            with open(os.path.join(out, "candidates.csv")) as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(summ["candidate_records"], len(rows), len(res.candidates()))
            counts = {}
            for r in rows:
                counts[r["status"]] = counts.get(r["status"], 0) + 1
            self.assertEqual(summ["candidate_status_counts"], counts)
            for r, c in zip(rows, sorted(res.candidates(), key=lambda c: (c.zone["created_time"], c.zone["zone_id"]))):
                self.assertEqual((r["zone_id"], r["status"]), (c.zone["zone_id"], c.status))
                self.assertEqual([r[g] for g in m.GATES], [g.outcome for g in c.gates])
        finally:
            shutil.rmtree(out)


def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def read_json(path):
    return json.loads(read_text(path))


def res_as_of(res):
    import datetime
    return datetime.datetime.fromisoformat(res.as_of)


class Cli(unittest.TestCase):
    def test_csv_input_scan_writes_every_report(self):
        tmp = tempfile.mkdtemp()
        try:
            data = os.path.join(tmp, "in")
            os.makedirs(data)
            cs = R.random_walk(5, 300)
            with open(os.path.join(data, "SYNA.csv"), "w") as fh:
                fh.write("date,open,high,low,close\n")
                for c in cs:
                    fh.write("%s,%s,%s,%s,%s\n" % (c.start.date(), c.open, c.high, c.low, c.close))
            out = os.path.join(tmp, "out")
            buf = io.StringIO()
            import contextlib
            with contextlib.redirect_stdout(buf):
                code = cli.main(["scan", "--as-of", str(cs[-1].start.date()), "--csv-dir", data, "--out", out])
            self.assertEqual(code, 0)
            summ = read_json(os.path.join(out, "summary.json"))
            self.assertIn(m.CALENDAR_UNVALIDATED, summ["limitations"])
            self.assertIn(m.UNIVERSE_UNVERIFIED, summ["limitations"])
            self.assertIn("PRICE_ADJUSTMENT_UNKNOWN", read_text(os.path.join(out, "data_quality.csv")))
            # without a calendar, no candidate can pass G0 (D28)
            rows = list(csv.DictReader(io.StringIO(read_text(os.path.join(out, "candidates.csv")))))
            self.assertTrue(rows)
            for r in rows:
                self.assertNotEqual(r["status"], m.ACTIONABLE)
                self.assertEqual(r["G0"], m.MANUAL)
        finally:
            shutil.rmtree(tmp)

    def test_wit_scan_is_blocked_without_reading_data(self):
        tmp = tempfile.mkdtemp()
        try:
            import contextlib
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(["scan", "--as-of", "2025-01-10", "--trade-type", "WIT-125", "--symbols", "AAA",
                                 "--csv-dir", tmp, "--out", os.path.join(tmp, "o")])
            self.assertEqual(code, 0)
            summ = read_json(os.path.join(tmp, "o", "summary.json"))
            self.assertEqual((summ["symbol_status_counts"], summ["candidate_records"]), ({"BLOCKED": 1}, 0))
        finally:
            shutil.rmtree(tmp)

    def test_bad_input_is_exit_code_2(self):
        import contextlib
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["scan", "--as-of", "not-a-date", "--csv-dir", ".", "--out", "x"]), 2)


class RealNseQ1Of2022(unittest.TestCase):
    """Official NSE files (local, git-ignored). Proves the pipeline runs on real data and
    reports honestly; it validates no trading decision."""

    @classmethod
    def setUpClass(cls):
        zips = sorted(glob.glob(os.path.join(RAW, "cm*MAR2022bhav.csv.zip")))
        require_local(len(zips) >= 20, "March 2022 bhavcopy archives in nse/data/eod/raw/")
        require_local(os.path.isdir(os.path.join(CAL, "circulars")), "calendar circulars in nse/data/calendar/circulars/")

    def test_infy_scan_through_the_cli(self):
        tmp = tempfile.mkdtemp()
        try:
            import contextlib
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(["scan", "--as-of", "2022-03-31", "--symbols", "INFY,TCS",
                                 "--bhavcopy-dir", RAW, "--manifest", MANIFEST, "--calendar", CAL, "--out", tmp])
            self.assertEqual(code, 0)
            scan = read_json(os.path.join(tmp, "scan.json"))
            self.assertEqual([s["symbol"] for s in scan["symbols"]], ["INFY", "TCS"])
            for s in scan["symbols"]:
                # the label describes the loaded dataset (MP1: legacy to 2024-07-05, UDiFF after)
                self.assertIn("NSE_CM_BHAVCOPY_LEGACY", s["provenance"]["source"].split("+"))
                self.assertIn(m.CORPORATE_ACTIONS_UNVERIFIED, s["limitations"])
                for c in s["candidates"]:
                    self.assertNotEqual(c["status"], m.ACTIONABLE)
                    self.assertEqual(c["zone"]["overlay_status"], mtf.FRESH)
                    self.assertEqual(c["zone"]["test_count"], 0)
                ids = [z["zone_id"] for z in s["fresh_zones"] if z["tf"] == "D"]
                for c in s["candidates"]:
                    self.assertIn(c["zone"]["zone_id"], ids)
            self.assertNotIn(m.CALENDAR_UNVALIDATED, scan["limitations"])
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
