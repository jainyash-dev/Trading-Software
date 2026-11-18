"""R-12: NSE's PREVCLOSE is unadjusted on an ex-date, so a split never shows as a PREVCLOSE break.

SYNTHETIC legacy bhavcopy files shaped like real sessions (the TATASTEEL 1:10 split of
2022-07-28, cm28JUL2022bhav.csv.zip: PREVCLOSE 959.4, open 98.1, close 100.35; bonus,
demerger and rights shapes from recorded 2021-2025 events). They prove the code path, not
the historical files. The real-file evidence is ED-50 (55 of 55 events).
"""

import datetime
import os
import shutil
import tempfile
import unittest

import _research as R
from nse.research import corporate_actions as ca, marketdata, models as m, scanner

D = datetime.date
CAL = R.WeekdayCalendar()
MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


class _Files(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def files(self, bars, symbol="TATASTEEL", start=D(2022, 7, 26)):
        """bars: [(open, high, low, close, prevclose)], one per weekday from start."""
        from nse.research.deps import bhavcopy as bc
        paths = []
        for d, (o, h, lo, c, pc) in zip(R.weekdays(start, len(bars)), bars):
            stamp = "%02d-%s-%04d" % (d.day, MON[d.month - 1], d.year)
            path = os.path.join(self.tmp, "cm%02d%s%04dbhav.csv" % (d.day, MON[d.month - 1], d.year))
            with open(path, "w", newline="") as fh:
                fh.write(",".join(bc.LEGACY_HEADER) + "\n")
                fh.write("%s,EQ,%s,%s,%s,%s,%s,%s,1000,100000,%s,10,INE081A01012,\n"
                         % (symbol, o, h, lo, c, c, pc, stamp))
            paths.append(path)
        return bc.load_many(paths)


# (open, high, low, close, prevclose): the ex-date prints the unadjusted prior close
TATASTEEL_SPLIT = [("950", "962", "948", "949.5", "945"), ("951", "963", "950", "959.4", "949.5"),
                   ("98.1", "101", "97", "100.35", "959.4"), ("103", "109.3", "102.15", "107.6", "100.35")]
BONUS_1_1 = [("1950", "1970", "1940", "1964.1", "1950"), ("985", "990", "975", "982", "1964.1")]
DEMERGER_LARGE = [("4900", "4940", "4890", "4928.15", "4900"), ("2450", "2520", "2400", "2480", "4928.15")]
DEMERGER_SMALL = [("2840", "2850", "2830", "2841.85", "2830"), ("2580", "2620", "2560", "2600", "2841.85")]
RIGHTS = [("1220", "1230", "1215", "1223.6", "1218"), ("1216", "1225", "1205", "1210", "1223.6")]
ORDINARY = [("100", "101", "99", "100", "99.5"), ("98", "99", "97", "98.5", "100")]


class Detection(_Files):
    def test_the_tatasteel_split_leaves_prevclose_intact_and_is_caught_by_the_price_screen(self):
        files = self.files(TATASTEEL_SPLIT)
        self.assertEqual(ca.prevclose_discontinuities(files, "TATASTEEL"), [])     # the R-12 blind spot
        [g] = ca.price_scale_gaps(files, "TATASTEEL")
        self.assertEqual((g["date"], g["last_close"], g["low"], g["high"]), (D(2022, 7, 28), "959.4", "97", "101"))
        inp = marketdata.from_bhavcopy(files, "TATASTEEL")
        [f] = [f for f in inp.findings if f.code == ca.PRICE_SCALE_GAP]
        self.assertEqual(f.date, D(2022, 7, 28))
        self.assertEqual(f.extra["last_date"], "2022-07-27")
        self.assertNotIn("PREVCLOSE_DISCONTINUITY", [x.code for x in inp.findings])

    def test_raw_ohlc_is_not_adjusted(self):
        inp = marketdata.from_bhavcopy(self.files(TATASTEEL_SPLIT), "TATASTEEL")
        self.assertEqual([round(c.close, 2) for c in inp.candles], [949.5, 959.4, 100.35, 107.6])

    def test_bonus_and_large_demerger_are_caught(self):
        for bars in (BONUS_1_1, DEMERGER_LARGE):
            files = self.files(bars, symbol="SYN")
            self.assertEqual(ca.prevclose_discontinuities(files, "SYN"), [])
            self.assertEqual(len(ca.price_scale_gaps(files, "SYN")), 1)

    def test_a_small_demerger_or_rights_issue_is_below_the_screen(self):
        # documented limitation: these are visible only through a recorded action (see Gate0)
        for bars in (DEMERGER_SMALL, RIGHTS, ORDINARY):
            self.assertEqual(ca.price_scale_gaps(self.files(bars, symbol="SYN"), "SYN"), [])

    def test_band_edges(self):
        self.assertTrue(ca.price_scale_gap("100", "70", "84.99"))
        self.assertFalse(ca.price_scale_gap("100", "70", "85"))
        self.assertTrue(ca.price_scale_gap("100", "117.65", "130"))
        self.assertFalse(ca.price_scale_gap("100", "117.6", "130"))
        self.assertTrue(ca.price_scale_gap("0", "1", "2"))


def _gap(day, ratio=0.104):
    return marketdata.Finding("SYN", marketdata.WARNING, ca.PRICE_SCALE_GAP, "synthetic", date=day,
                              extra={"ratio": ratio, "file": "x", "last_date": (day - datetime.timedelta(1)).isoformat()})


class Gate0(unittest.TestCase):
    """The scanner holds G0 so an unexplained scale break cannot pass into an actionable result."""

    def setUp(self):
        self.cs = R.long_mit_candles()
        self.cfg = dict(as_of=self.cs[-1].end, calendar=CAL, risk_per_trade=1000.0)

    def _candidate(self, findings, **cfg):
        res = scanner.scan([marketdata.DailyInput("SYN", self.cs, {}, [], findings)],
                           scanner.ScanConfig(**dict(self.cfg, **cfg)))
        [c] = res.symbols[0].candidates
        return c, res.symbols[0]

    def test_an_unrecorded_split_inside_the_history_holds_g0(self):
        c, _ = self._candidate([_gap(D(2022, 5, 2))])
        self.assertEqual((c.gate("G0").outcome, c.status), (m.MANUAL, m.MANUAL_REVIEW))
        self.assertIn("G0:PRICE_DISCONTINUITY_IN_HISTORY", c.manual_review)
        self.assertNotEqual(c.status, m.ACTIONABLE)

    def test_it_holds_g0_even_with_verified_coverage_for_the_symbol(self):
        # the R-12 hole: a non-empty verified response that omits the split clears the coverage check
        start, end = self.cs[0].start.date(), self.cs[-1].end.date()
        c, _ = self._candidate([_gap(D(2022, 5, 2))], corporate_actions=[],
                               corporate_action_coverage={"SYN": [(start - datetime.timedelta(400), end)]})
        self.assertNotIn("G0:CORPORATE_ACTION_COVERAGE_UNVERIFIED", c.manual_review)
        self.assertIn("G0:PRICE_DISCONTINUITY_IN_HISTORY", c.manual_review)
        self.assertEqual(c.gate("G0").outcome, m.MANUAL)

    def test_without_the_gap_that_configuration_does_not_hold_g0_for_a_discontinuity(self):
        start, end = self.cs[0].start.date(), self.cs[-1].end.date()
        c, _ = self._candidate([], corporate_actions=[],
                               corporate_action_coverage={"SYN": [(start - datetime.timedelta(400), end)]})
        self.assertNotIn("G0:PRICE_DISCONTINUITY_IN_HISTORY", c.manual_review)

    def test_recorded_split_bonus_rights_and_demerger_hold_g0_once(self):
        start, end = self.cs[0].start.date(), self.cs[-1].end.date()
        cov = {"SYN": [(start - datetime.timedelta(400), end)]}
        for action, ratio in (("SPLIT", (1, 10)), ("BONUS", (1, 2)), ("RIGHTS", (0, 0)), ("DEMERGER", (0, 0))):
            act = ca.Action("SYN", D(2022, 5, 2), action, ratio[0], ratio[1], True, "SYNTHETIC")
            findings = [_gap(D(2022, 5, 2))] if action in ("SPLIT", "BONUS") else []
            c, sym = self._candidate(findings, corporate_actions=[act], corporate_action_coverage=cov)
            self.assertEqual(c.gate("G0").outcome, m.MANUAL, action)
            self.assertIn("G0:CORPORATE_ACTION_IN_HISTORY", c.manual_review, action)
            self.assertNotIn("G0:PRICE_DISCONTINUITY_IN_HISTORY", c.manual_review, action)
            if findings:
                self.assertIn("PRICE_SCALE_GAP_AT_RECORDED_ACTION", [f["code"] for f in sym.findings])

    def test_a_gap_after_as_of_is_not_read(self):
        c, _ = self._candidate([_gap(D(2030, 1, 1))])
        self.assertNotIn("G0:PRICE_DISCONTINUITY_IN_HISTORY", c.manual_review)


SPLIT_5_1 = [("1000", "1010", "990", "1000", "995"), ("201", "205", "197", "200", "1000")]
BONUS_1_2 = [("600", "606", "594", "600", "598"), ("402", "406", "396", "400", "600")]   # factor 2/3
SMALL_MOVE = [("500", "505", "495", "500", "498"), ("470", "478", "468", "472", "500")]  # -5.6%, no event
LARGE_MOVE = [("500", "505", "495", "500", "498"), ("400", "410", "398", "402", "500")]  # -20% band move


class MoreDetection(_Files):
    def test_split_5_1_and_bonus_1_2_are_caught(self):
        for bars in (SPLIT_5_1, BONUS_1_2):
            files = self.files(bars, symbol="SYN")
            self.assertEqual(ca.prevclose_discontinuities(files, "SYN"), [])
            self.assertEqual(len(ca.price_scale_gaps(files, "SYN")), 1)

    def test_an_ordinary_small_market_move_is_not_flagged(self):
        self.assertEqual(ca.price_scale_gaps(self.files(SMALL_MOVE, symbol="SYN"), "SYN"), [])

    def test_a_large_market_move_is_flagged_and_never_called_a_corporate_action(self):
        # fail closed by design: a 20% band move is held for review (ADANIENSOL 2024-11-21 shape)
        inp = marketdata.from_bhavcopy(self.files(LARGE_MOVE, symbol="SYN"), "SYN")
        [f] = [f for f in inp.findings if f.code == ca.PRICE_SCALE_GAP]
        self.assertNotIn("SPLIT", f.detail.upper().replace("PRICE-SCALE", ""))
        self.assertIn("is not adjusted", f.detail)

    def test_consecutive_event_sessions_each_get_a_finding(self):
        bars = [("1000", "1010", "990", "1000", "995"), ("100", "102", "98", "100", "1000"),
                ("10", "10.2", "9.8", "10", "100")]
        gaps = ca.price_scale_gaps(self.files(bars, symbol="SYN"), "SYN")
        self.assertEqual([g["date"] for g in gaps], [D(2022, 7, 27), D(2022, 7, 28)])


class UserCsv(unittest.TestCase):
    """R-12: a user CSV goes through the same screen as an official archive."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def csv(self, rows, name="SYN.csv"):
        path = os.path.join(self.tmp, name)
        with open(path, "w") as fh:
            fh.write("date,open,high,low,close,volume\n")
            for d, o, h, lo, c in rows:
                fh.write("%s,%s,%s,%s,%s,1000\n" % (d, o, h, lo, c))
        return path

    def test_a_scale_break_in_a_user_csv_is_a_finding(self):
        path = self.csv([("2022-07-26", 950, 962, 948, 949.5), ("2022-07-27", 951, 963, 950, 959.4),
                         ("2022-07-28", 98.1, 101, 97, 100.35)])
        for adjustment in ("UNKNOWN", "NONE", "ADJUSTED"):
            inp = marketdata.from_csv(path, "SYN", price_adjustment=adjustment)
            [f] = [f for f in inp.findings if f.code == ca.PRICE_SCALE_GAP]
            self.assertEqual((f.date, f.extra["last_date"]), (D(2022, 7, 28), "2022-07-27"))
            self.assertEqual([round(c.close, 2) for c in inp.candles], [949.5, 959.4, 100.35])   # raw, unadjusted

    def test_an_ordinary_user_csv_has_no_finding(self):
        path = self.csv([("2022-07-26", 500, 505, 495, 500), ("2022-07-27", 470, 478, 468, 472)])
        self.assertEqual([f for f in marketdata.from_csv(path, "SYN").findings if f.code == ca.PRICE_SCALE_GAP], [])

    def test_a_user_csv_scale_break_holds_g0_in_the_scanner(self):
        cs = R.long_mit_candles()
        rows = [(c.start.date().isoformat(), c.open, c.high, c.low, c.close) for c in cs]
        i = next(k for k, r in enumerate(rows) if r[0] >= "2022-05-02")
        rows = rows[:i] + [(d, o / 10, h / 10, lo / 10, c / 10) for d, o, h, lo, c in rows[i:]]
        inp = marketdata.from_csv(self.csv(rows), "SYN")
        self.assertTrue([f for f in inp.findings if f.code == ca.PRICE_SCALE_GAP])
        res = scanner.scan([inp], scanner.ScanConfig(as_of=cs[-1].end, calendar=CAL, risk_per_trade=1000.0))
        for c in res.symbols[0].candidates:
            self.assertEqual(c.gate("G0").outcome, m.MANUAL)
            self.assertIn("G0:PRICE_DISCONTINUITY_IN_HISTORY", c.manual_review)
            self.assertNotEqual(c.status, m.ACTIONABLE)


class RecordedEvidenceEdges(Gate0):
    def test_an_action_recorded_on_the_wrong_date_does_not_explain_the_gap(self):
        start, end = self.cs[0].start.date(), self.cs[-1].end.date()
        act = ca.Action("SYN", D(2022, 5, 9), "SPLIT", 1, 10, True, "SYNTHETIC")       # gap is on 2022-05-02
        c, sym = self._candidate([_gap(D(2022, 5, 2))], corporate_actions=[act],
                                 corporate_action_coverage={"SYN": [(start - datetime.timedelta(400), end)]})
        self.assertIn("G0:PRICE_DISCONTINUITY_IN_HISTORY", c.manual_review)
        self.assertNotIn("PRICE_SCALE_GAP_AT_RECORDED_ACTION", [f["code"] for f in sym.findings])

    def test_duplicate_recorded_events_still_hold_g0(self):
        start, end = self.cs[0].start.date(), self.cs[-1].end.date()
        acts = [ca.Action("SYN", D(2022, 5, 2), "SPLIT", 1, 10, True, "SYNTHETIC")] * 2
        c, _ = self._candidate([_gap(D(2022, 5, 2))], corporate_actions=acts,
                               corporate_action_coverage={"SYN": [(start - datetime.timedelta(400), end)]})
        self.assertEqual(c.gate("G0").outcome, m.MANUAL)
        self.assertIn("G0:CORPORATE_ACTION_IN_HISTORY", c.manual_review)

    def test_missing_corporate_action_evidence_holds_g0(self):
        c, _ = self._candidate([_gap(D(2022, 5, 2))])               # no file, no coverage
        self.assertIn("G0:CORPORATE_ACTION_COVERAGE_UNKNOWN", c.manual_review)
        self.assertIn("G0:PRICE_DISCONTINUITY_IN_HISTORY", c.manual_review)


if __name__ == "__main__":
    unittest.main()
