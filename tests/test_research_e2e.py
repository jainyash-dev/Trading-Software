"""End-to-end through the REAL pipeline on a long SYNTHETIC history (tests/_research.py
long_mit_candles): DailyInput -> mtf_freshness.replay (real Zone Engine and overlay on
D, W, M, Q, HY, Y) -> top-down -> G0-G8 -> reports and CLI. Nothing is mocked.

The prices are synthetic and say nothing about any market. They exist so that every gate
is decided by evidence the engine computed itself, including one candidate that passes
every automated gate and still carries the manual checklist.
"""

import contextlib
import csv
import datetime
import io
import json
import os
import shutil
import tempfile
import unittest

import _research as R
from nse.research import cli, models as m, reports, scanner
from nse.research.deps import mtf

CAL = R.WeekdayCalendar()


def scan(candles, as_of=None, trade_type=m.MIT, calendar=CAL, risk=1000.0):
    cfg = scanner.ScanConfig(as_of=as_of or candles[-1].end, trade_type=trade_type, calendar=calendar,
                             calendar_label="TEST_WEEKDAYS", risk_per_trade=risk,
                             corporate_action_coverage=R.verified_ca("SYN"))
    return scanner.scan([R.daily_input("SYN", candles)], cfg).symbols[0]


def outcomes(c):
    return {g.gate: g.outcome for g in c.gates}


def the_zone(s):
    return [c for c in s.candidates if c.zone["proximal"] == R.LONG_PL]


class Reference(unittest.TestCase):
    """Scenario 1 and 9: a fully evaluated fresh demand zone that still needs a person."""

    @classmethod
    def setUpClass(cls):
        cls.candles = R.long_mit_candles()
        cls.s = scan(cls.candles)

    def test_the_only_candidate_passes_every_automated_gate(self):
        [c] = self.s.candidates
        self.assertEqual((c.zone["proximal"], c.zone["distal"]), (R.LONG_PL, R.LONG_DL))
        self.assertEqual(c.status, m.ACTIONABLE)
        self.assertEqual(set(outcomes(c).values()), {m.PASS})

    def test_each_gate_passed_on_engine_evidence(self):
        [c] = self.s.candidates
        g3 = c.gate("G3").evidence
        self.assertEqual(g3["position_at_price"], ["LOC"])
        self.assertEqual(g3["bottom"]["tf"], "M")
        self.assertEqual(g3["top"]["side"], "supply")
        self.assertEqual(g3["skipped_tested_boundaries"], [c.gate("G6").evidence["htf_zone"]["zone_id"]])
        g4 = c.gate("G4").evidence["gate"]
        self.assertEqual((g4["tf"], g4["position"]), ("W", "12 o'clock"))
        self.assertEqual((g4["rulebook_label"], g4["readings"]), ("Extreme Uptrend", ["STRONG_UP"]))
        g6 = c.gate("G6").evidence
        self.assertEqual((g6["class"], g6["htf_zone"]["tf"], g6["htf_zone"]["freshness"]), ("COINCIDING", "M", "TESTED"))
        g7 = c.gate("G7").evidence
        self.assertEqual((g7["target"]["tf"], g7["rr"]["status"]), ("W", "PASS_ALL"))
        self.assertGreaterEqual(g7["rr"]["rr"][0], 2.0)
        # every TDA timeframe was available, so EC1 passed on data, not by default
        self.assertEqual([r["series"]["status"] for r in self.s.tda], ["AVAILABLE"] * 6)

    def test_manual_checks_and_limitations_survive_every_export(self):
        [c] = self.s.candidates
        self.assertEqual([x["code"] for x in c.manual_checks], [x[0] for x in m.CHECKLIST])
        tmp = tempfile.mkdtemp()
        try:
            res = scanner.scan([R.daily_input("SYN", self.candles)],
                               scanner.ScanConfig(as_of=self.candles[-1].end, calendar=CAL, risk_per_trade=1000.0,
                                                  corporate_action_coverage=R.verified_ca("SYN")))
            reports.write_all(res, tmp)
            with open(os.path.join(tmp, "candidates.csv"), encoding="utf-8") as fh:
                [row] = list(csv.DictReader(fh))
            self.assertEqual(row["status"], m.ACTIONABLE)
            self.assertIn("Extreme Uptrend", row["trend_gate"])
            for code, _, _ in m.CHECKLIST:
                self.assertIn(code, row["manual_checks"])
            self.assertIn(m.NOT_EXTERNALLY_VALIDATED, row["limitations"])
            with open(os.path.join(tmp, "summary.json"), encoding="utf-8") as fh:
                self.assertIn("No status approves a trade", json.load(fh)["note"])
        finally:
            shutil.rmtree(tmp)


class Exclusions(unittest.TestCase):
    def test_tested_zone_is_excluded_from_then_on(self):
        base = R.long_mit_candles()
        touched = R.extend(base, [(176.0, 176.5, 159.5, 170.0), (170.0, 171.0, 169.0, 170.5)])   # low 159.5 <= PL
        s = scan(touched)
        self.assertEqual(the_zone(s), [])
        snap = mtf.replay(touched, "D", htf=scanner.HTF, calendar=CAL)
        [st] = [z for z in snap.zones.values() if z.tf == "D" and z.proximal == R.LONG_PL]
        self.assertEqual(st.status, mtf.TESTED)
        self.assertNotIn(st.zone_id, [z["zone_id"] for z in s.fresh_zones if z["tf"] == "D"])
        # the earlier scan, re-run with the touch in the data, is unchanged (scenario 10)
        self.assertEqual(reports.to_dict(scanner.scan([R.daily_input("SYN", touched)],
                                                      scanner.ScanConfig(as_of=base[-1].end, calendar=CAL))),
                         reports.to_dict(scanner.scan([R.daily_input("SYN", base)],
                                                      scanner.ScanConfig(as_of=base[-1].end, calendar=CAL))))

    def test_invalidated_zone_is_excluded(self):
        broken = R.extend(R.long_mit_candles(), [(176.0, 176.0, 150.0, 151.0)])   # close below DL 157.92
        s = scan(broken)
        self.assertEqual(the_zone(s), [])
        snap = mtf.replay(broken, "D", htf=scanner.HTF, calendar=CAL)
        [st] = [z for z in snap.zones.values() if z.tf == "D" and z.proximal == R.LONG_PL]
        self.assertEqual(st.status, mtf.INVALIDATED)
        for c in s.candidates:
            self.assertNotEqual(c.status, m.ACTIONABLE)


class Restrictions(unittest.TestCase):
    def test_missing_higher_timeframe_history(self):
        # scenario 4: from 2022-06 the Yearly series is too short (MANUAL); from 2023-02 Half-yearly too
        y = R.only({"candidates": the_zone(scan(R.long_mit_candles(start=datetime.date(2022, 6, 1))))})
        self.assertEqual(y.gate("G5").outcome, m.MANUAL)
        self.assertIn("HTF_EVIDENCE_INSUFFICIENT_HISTORY_Y", " ".join(y.gate("G5").reasons))
        hy = R.only({"candidates": the_zone(scan(R.long_mit_candles(start=datetime.date(2023, 2, 1))))})
        self.assertEqual((hy.gate("G5").outcome, hy.status), (m.DATA_INSUFFICIENT, m.STATUS_DATA_INSUFFICIENT))
        self.assertEqual(hy.gate("G4").outcome, m.MANUAL)                     # 53 of 55 weekly candles
        self.assertIn("TREND_INSUFFICIENT_HISTORY", hy.gate("G4").manual_review)

    def test_incomplete_data_stops_the_symbol(self):
        # scenario 5: a missing session after the zone formed (calendar says it traded)
        cs = R.long_mit_candles()
        gap = cs[:-3] + cs[-2:]
        s = scan(gap)
        self.assertEqual(s.status, scanner.SYMBOL_DATA_INSUFFICIENT)
        self.assertTrue(all(c.status != m.ACTIONABLE for c in s.candidates))
        self.assertIn("MISSING_SESSION", [f["code"] for f in s.findings])

    def test_aggressive_zone_stays_distinct_from_coinciding(self):
        # Scenario 6: the D zone is wholly above the Monthly demand range.
        [c] = the_zone_k(1.75)
        self.assertEqual(c.status, m.MANUAL_REVIEW)
        # D43: a Pine-only Weekly supply (PL 184.91) is within 10% of ENTRY_MAX 168.6, so G5 is
        # MANUAL as well; it never FAILs G5 and never clears it
        self.assertEqual({g: o for g, o in outcomes(c).items() if o != m.PASS}, {"G5": m.MANUAL, "G6": m.MANUAL})
        self.assertIn("G5:PINE_ONLY_ZONE_REVIEW", c.manual_review)
        self.assertEqual(c.gate("G6").evidence["class"], "AGGRESSIVE")
        self.assertIn("G6:AGGRESSIVE_ENTRY_REVIEW", c.manual_review)

    def test_higher_timeframe_conflict(self):
        # scenario 7: the Weekly supply is within 10% of the entry maximum but not of the PL
        cs = R.long_mit_candles(k=1.79, tail_step=1.0, tail_wick=.002)
        [c] = [x for x in scan(cs).candidates if x.zone["proximal"] == round(95.2 * 1.79, 2)]
        g5 = c.gate("G5")
        self.assertEqual(g5.outcome, m.MANUAL)
        self.assertEqual(g5.evidence["findings"][0]["zone"]["tf"], "W")
        self.assertEqual(g5.evidence["findings"][0]["bands"]["ENTRY_MAX"], "WITHIN_10")
        self.assertNotEqual(c.status, m.ACTIONABLE)

    def test_no_calendar_is_never_actionable(self):
        [c] = the_zone(scan(R.long_mit_candles(), calendar=None))
        self.assertEqual((c.gate("G0").outcome, c.status), (m.MANUAL, m.MANUAL_REVIEW))

    def test_no_risk_per_trade_is_never_actionable(self):
        [c] = the_zone(scan(R.long_mit_candles(), risk=None))
        self.assertEqual(c.status, m.MANUAL_REVIEW)
        self.assertIn("G8:EC7_POSITION_SIZE", c.manual_review)


def the_zone_k(k):
    pl = round(95.2 * k, 2)
    return [c for c in scan(R.long_mit_candles(k=k)).candidates if c.zone["proximal"] == pl]


class History(unittest.TestCase):
    def test_appending_future_candles_never_changes_an_earlier_scan(self):
        base = R.long_mit_candles()
        later = R.extend(base, [(180.0, 181.0, 150.0, 151.0)] + [(151.0, 152.0, 150.0, 151.0)] * 10)
        for t in (base[-1].end, base[-8].end, base[-200].end):
            a = scanner.scan([R.daily_input("SYN", base)], scanner.ScanConfig(as_of=t, calendar=CAL))
            b = scanner.scan([R.daily_input("SYN", later)], scanner.ScanConfig(as_of=t, calendar=CAL))
            self.assertEqual(reports.to_dict(a), reports.to_dict(b), t)

    def test_before_the_leg_out_closes_there_is_no_candidate(self):
        cs = R.long_mit_candles()
        legout = [i for i, c in enumerate(cs) if c.close == round(101.5 * R.LONG_K, 2)][0]
        s = scan(cs, as_of=cs[legout - 1].end)
        self.assertEqual(the_zone(s), [])
        # on the leg-out day the zone exists with one explosive candle: 6/7, not a candidate
        self.assertEqual(the_zone(scan(cs, as_of=cs[legout].end)), [])
        snap = mtf.replay(cs, "D", htf=scanner.HTF, as_of=cs[legout].end, calendar=CAL)
        [a] = [a for a in snap.series["D"].engine.assessments if a.zone.proximal == R.LONG_PL]
        self.assertEqual(a.score.core, 6.0)
        [row] = [z for z in scan(cs, as_of=cs[legout].end).fresh_zones if z["zone_id"] == a.zone.id]
        self.assertIn("LEGOUT_WINDOW_OPEN: 0 of 3", row["zone_level"])     # audit M1, report only
        # the follow-through candle (a second explosive candle, RB 728) completes 7/7
        self.assertEqual(len(the_zone(scan(cs, as_of=cs[legout + 1].end))), 1)
        # a scan in the middle of that day's session still cannot see it
        noon = datetime.datetime.combine(cs[legout + 1].start.date(), datetime.time(12, 0))
        self.assertEqual(the_zone(scan(cs, as_of=noon)), [])

    def test_scan_history_tracks_the_zone_through_its_life(self):
        cs = R.extend(R.long_mit_candles(), [(176.0, 176.5, 159.5, 170.0)])
        cfg = scanner.ScanConfig(as_of=cs[0].end, calendar=CAL, risk_per_trade=1000.0)
        hist = scanner.scan_history([R.daily_input("SYN", cs)], [cs[-3].end, cs[-2].end, cs[-1].end], cfg)
        self.assertEqual([len(the_zone(h.symbols[0])) for h in hist], [1, 1, 0])


class WitIsBlocked(unittest.TestCase):
    def test_wit_never_produces_output_on_the_same_data(self):
        for tt in (m.WIT_75, m.WIT_125):
            s = scan(R.long_mit_candles(), trade_type=tt)
            self.assertEqual((s.status, s.candidates, s.fresh_zones), (scanner.SYMBOL_BLOCKED, [], []))


class CliEndToEnd(unittest.TestCase):
    def test_csv_input_through_the_cli_reaches_the_same_decision(self):
        tmp = tempfile.mkdtemp()
        try:
            cs = R.long_mit_candles()
            data = os.path.join(tmp, "in")
            os.makedirs(data)
            with open(os.path.join(data, "SYN.csv"), "w", encoding="utf-8") as fh:
                fh.write("date,open,high,low,close\n")
                for c in cs:
                    fh.write("%s,%s,%s,%s,%s\n" % (c.start.date(), c.open, c.high, c.low, c.close))
            out = os.path.join(tmp, "out")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["scan", "--as-of", str(cs[-1].start.date()), "--csv-dir", data,
                                           "--price-adjustment", "NONE", "--risk-per-trade", "1000", "--out", out]), 0)
            with open(os.path.join(out, "candidates.csv"), encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            # without a calendar (P-CAL-1) the same zone stops at G0 MANUAL: the CLI never upgrades it
            [row] = [r for r in rows if float(r["proximal"]) == R.LONG_PL]
            self.assertEqual((row["G0"], row["status"]), (m.MANUAL, m.MANUAL_REVIEW))
            self.assertEqual([row[g] for g in m.GATES[1:]], [m.PASS] * 8)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
