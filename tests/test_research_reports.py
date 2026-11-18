"""Reports, data-quality checks and the universe loader (SYNTHETIC inputs)."""

import csv
import datetime
import hashlib
import io
import json
import os
import shutil
import tempfile
import unittest

import _research as R
from nse.research import marketdata, models as m, readiness, reports, scanner, universe

D = datetime.date


def write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


class DataQuality(unittest.TestCase):
    def test_bad_rows_are_errors_and_are_never_repaired(self):
        rows = [(D(2025, 1, 6), 10.0, 11.0, 9.0, 10.5, "l2"), (D(2025, 1, 6), 10.0, 11.0, 9.0, 10.5, "l3"),
                (D(2025, 1, 3), 10.0, 11.0, 9.0, 10.5, "l4"), (D(2025, 1, 7), 10.0, 9.5, 9.0, 10.5, "l5"),
                (D(2025, 1, 8), 0.0, 11.0, 0.0, 10.5, "l6"), (D(2025, 1, 11), 10.0, 11.0, 9.0, 10.5, "l7"),
                (D(2025, 1, 13), float("nan"), 11.0, 9.0, 10.5, "l8")]
        codes = [(f.severity, f.code) for f in marketdata.check_rows("X", rows)]
        for want in [("ERROR", "DUPLICATE_DATE"), ("ERROR", "OUT_OF_ORDER"), ("ERROR", "OHLC_INCONSISTENT"),
                     ("ERROR", "NON_POSITIVE_PRICE"), ("WARNING", "WEEKEND_ROW"), ("ERROR", "NON_NUMERIC_PRICE")]:
            self.assertIn(want, codes)

    def test_csv_errors_stop_the_symbol_from_their_date_on(self):
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "abc.csv")
            write(p, "date,open,high,low,close\n2025-01-06,10,11,9,10.5\n2025-01-06,10,11,9,10.5\n")
            inp = marketdata.from_csv(p)
            self.assertEqual(inp.symbol, "ABC")
            self.assertEqual([(f.code, f.date) for f in inp.errors], [("DUPLICATE_DATE", D(2025, 1, 6))])
            res = scanner.scan([inp], scanner.ScanConfig(as_of=R.DT(2025, 1, 6, 15, 30)))
            self.assertEqual(res.symbols[0].status, scanner.SYMBOL_DATA_INSUFFICIENT)
            self.assertEqual(res.symbols[0].candidates, [])
            self.assertEqual(inp.findings_at(D(2025, 1, 3)), [f for f in inp.findings if f.date is None])
            write(p, "day,o,h,l,c\n")
            self.assertEqual([f.code for f in marketdata.from_csv(p).errors], ["BAD_HEADER"])
            write(p, "date,open,high,low,close\n2025-01-06,10,11,9,10.5\n")
            ok = marketdata.from_csv(p)
            self.assertEqual(len(ok.candles), 1)
            self.assertIn(m.PRICE_ADJUSTMENT_UNKNOWN, ok.limitations)
            self.assertEqual(len(ok.provenance["sha256"]), 64)
        finally:
            shutil.rmtree(tmp)


class Universe(unittest.TestCase):
    HEADER = ",".join(universe.COLUMNS) + "\n"

    def test_point_in_time_membership(self):
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "u.csv")
            sha = {}
            for name in ("x.pdf", "y.pdf"):
                write(os.path.join(tmp, name), "SYNTHETIC " + name)
                sha[name] = hashlib.sha256(("SYNTHETIC " + name).encode("utf-8")).hexdigest()
            write(p, self.HEADER +
                  "AAA,EQ,,NIFTY 100,2020-01-01,2022-06-30,NSE Indices notice X,x.pdf,%s,2026-10-29,\n" % sha["x.pdf"] +
                  "BBB,EQ,,NIFTY 100,2022-07-01,,NSE Indices notice Y,y.pdf,%s,2026-10-29,\n" % sha["y.pdf"] +
                  "CCC,EQ,,NIFTY 100,2020-01-01,,,,,2026-10-29,unsourced\n")
            u = universe.load(p)
            self.assertEqual([r.symbol for r in u.members(D(2022, 6, 30))], ["AAA", "CCC"])
            self.assertEqual([r.symbol for r in u.members(D(2022, 7, 1))], ["BBB", "CCC"])
            self.assertEqual(u.limitations(D(2022, 7, 1)), [m.UNIVERSE_UNVERIFIED])      # CCC has no source
            u.rows = [r for r in u.rows if r.symbol != "CCC"]
            self.assertEqual(u.limitations(D(2022, 7, 1)), [])
            # a hash string that does not match its file no longer verifies the row (audit 2026-11-06)
            write(os.path.join(tmp, "y.pdf"), "edited after recording")
            self.assertEqual(universe.load(p).limitations(D(2022, 7, 1)), [m.UNIVERSE_UNVERIFIED])
            write(p, "symbol\nAAA\n")
            with self.assertRaises(universe.UniverseError):
                universe.load(p)
        finally:
            shutil.rmtree(tmp)

    def test_a_date_with_no_member_is_never_a_verified_universe(self):
        # PROMPT-01 audit: before a file's first period members() is empty and all([]) made
        # the universe look verified; unknown membership is UNIVERSE_UNVERIFIED
        u = universe.Universe("NIFTY 100", [universe.Membership("AAA", "EQ", D(2021, 1, 1), None, True, "SYNTHETIC")])
        self.assertEqual(u.limitations(D(2021, 6, 1)), [])                       # a verified member
        self.assertEqual(u.limitations(D(2018, 6, 1)), [m.MEMBERSHIP_BEFORE_PROVISIONAL_WINDOW,
                                                       m.UNIVERSE_UNVERIFIED])   # D59, and no member yet
        self.assertNotIn(m.MEMBERSHIP_BEFORE_PROVISIONAL_WINDOW, u.limitations(universe.PROVISIONAL_MEMBERSHIP_START))
        self.assertIn(m.MEMBERSHIP_BEFORE_PROVISIONAL_WINDOW,
                      u.limitations(universe.PROVISIONAL_MEMBERSHIP_START - datetime.timedelta(days=1)))
        self.assertNotIn(m.MEMBERSHIP_BEFORE_PROVISIONAL_WINDOW,
                         universe.adhoc(["AAA"]).limitations(D(2016, 1, 1)))

    def test_adhoc_universe_is_unverified_and_non_members_are_reported(self):
        u = universe.adhoc(["aaa", "AAA", " bbb "])
        self.assertEqual([r.symbol for r in u.rows], ["AAA", "BBB"])
        self.assertEqual(u.limitations(D(2025, 1, 1)), [m.UNIVERSE_UNVERIFIED])
        cs = R.random_walk(1, 300)
        res = scanner.scan([R.daily_input("ZZZ", cs)], scanner.ScanConfig(as_of=cs[-1].end), universe=u)
        status = {s.symbol: s.status for s in res.symbols}
        self.assertEqual(status["ZZZ"], scanner.SYMBOL_NOT_IN_UNIVERSE)
        # members without any input are reported, never dropped (survivorship, 2026-11-08)
        self.assertEqual((status["AAA"], status["BBB"]), (scanner.SYMBOL_DATA_INSUFFICIENT,) * 2)
        self.assertTrue(res.symbols[0].reasons[0].startswith("NO_INPUT_FOR_UNIVERSE_MEMBER"))
        self.assertEqual([s.symbol for s in res.symbols], ["AAA", "BBB", "ZZZ"])
        self.assertIn(m.UNIVERSE_UNVERIFIED, res.limitations)

    def test_overlapping_membership_periods_are_refused(self):
        import tempfile
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "u.csv")
            with open(path, "w") as fh:
                fh.write(",".join(universe.COLUMNS) + "\n")
                fh.write("AAA,EQ,,NIFTY 100,2022-01-01,2022-06-30,,,,,SYNTHETIC\n")
                fh.write("AAA,EQ,,NIFTY 100,2022-06-30,,,,,,SYNTHETIC\n")   # shares 30 Jun (inclusive ends)
            with self.assertRaisesRegex(universe.UniverseError, "overlapping"):
                universe.load(path)
            with open(path, "w") as fh:
                fh.write(",".join(universe.COLUMNS) + "\n")
                fh.write("AAA,EQ,,NIFTY 100,2022-01-01,2022-06-29,,,,,SYNTHETIC\n")
                fh.write("AAA,EQ,,NIFTY 100,2022-06-30,,,,,,SYNTHETIC\n")
            self.assertEqual(len(universe.load(path).members(D(2022, 6, 30))), 1)
        finally:
            shutil.rmtree(tmp)

    def test_scan_level_limitations_reach_every_candidate_csv_row(self):
        # audit 2026-11-06 (Agent 6 #6): candidates.csv rows used to omit UNIVERSE_UNVERIFIED
        cs = R.long_mit_candles()
        cfg = scanner.ScanConfig(as_of=cs[-1].end, calendar=R.WeekdayCalendar(), risk_per_trade=1000.0)
        res = scanner.scan([R.daily_input("SYN", cs)], cfg, universe=universe.adhoc(["SYN"]))
        rows = reports.candidate_rows(res)
        self.assertTrue(rows)
        for r in rows:
            self.assertIn(m.UNIVERSE_UNVERIFIED, r["limitations"])
        self.assertIn(m.UNIVERSE_UNVERIFIED, reports.candidates_csv(res))


class Serialisation(unittest.TestCase):
    def setUp(self):
        cs = R.random_walk(8, 430)
        cfg = scanner.ScanConfig(as_of=cs[-1].end, calendar=R.WeekdayCalendar(), calendar_label="TEST",
                                 generated_at="test-label")
        self.res = scanner.scan([R.daily_input("SYN", cs)], cfg)

    def test_json_round_trip_keeps_every_status_and_gate(self):
        back = json.loads(reports.to_json(self.res))
        self.assertEqual(back["generated_at"], "test-label")
        self.assertEqual(back["as_of"], self.res.as_of)
        got = [(c["zone"]["zone_id"], c["status"], [g["outcome"] for g in c["gates"]])
               for s in back["symbols"] for c in s["candidates"]]
        want = [(c.zone["zone_id"], c.status, [g.outcome for g in c.gates]) for c in self.res.candidates()]
        self.assertEqual(got, want)
        self.assertTrue(want)

    def test_csv_columns_and_reconciliation(self):
        rows = list(csv.DictReader(io.StringIO(reports.candidates_csv(self.res))))
        self.assertEqual(tuple(rows[0].keys()), reports.CANDIDATE_COLUMNS)
        self.assertEqual(len(rows), len(self.res.candidates()))
        summ = reports.summary(self.res)
        self.assertEqual(sum(summ["candidate_status_counts"].values()), summ["candidate_records"])
        self.assertEqual(summ["symbols_processed"], 1)
        fresh = list(csv.DictReader(io.StringIO(reports.fresh_zones_csv(self.res))))
        self.assertEqual(len(fresh), summ["fresh_zone_records"])
        self.assertTrue(all(r["side"] == "supply" and r["zone_level"] == "context: not a candidate"
                            or r["side"] == "demand" for r in fresh))

    def test_reports_are_byte_identical_across_runs(self):
        cs = R.random_walk(8, 430)
        cfg = scanner.ScanConfig(as_of=cs[-1].end, calendar=R.WeekdayCalendar(), calendar_label="TEST",
                                 generated_at="test-label")
        again = scanner.scan([R.daily_input("SYN", cs)], cfg)
        for fn in (reports.to_json, reports.candidates_csv, reports.fresh_zones_csv, reports.data_quality_csv,
                   reports.blocked_zones_csv):
            self.assertEqual(fn(self.res), fn(again), fn.__name__)

    def test_readiness_rows_carry_every_state(self):
        for row in readiness.report():
            for k in readiness.STATE_KEYS:
                self.assertIn(k, row, row["id"])
        ids = [r["id"] for r in readiness.report()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_m1_approvals_are_removed_from_open_readiness_decisions(self):
        rows = {r["id"]: r for r in readiness.report()}
        self.assertEqual(rows["trend_sma_clock"]["requires_human_decision"], [])  # R2
        self.assertEqual(rows["location_curve"]["requires_human_decision"], [])
        self.assertFalse(rows["location_curve"]["reference_validated"])
        self.assertFalse(rows["location_curve"]["externally_validated"])
        self.assertTrue(any("P-LOC-2" in item and "not externally validated" in item
                            for item in rows["location_curve"]["limits"]))
        self.assertEqual(rows["coinciding"]["requires_human_decision"],
                         ["Aggressive entry criteria, including achievement (RB 1843-1847, 1854-1855)"])
        self.assertIn("wholly above HTF demand is Aggressive", rows["coinciding"]["limits"][0])


if __name__ == "__main__":
    unittest.main()
