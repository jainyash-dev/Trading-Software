"""nse/research/confluence.py: the spec 5.3 X/14 display. It is information only (spec 5.1,
D4): sector and RSI/Stochastic are NOT_EVALUATED (never 0), EMA 20 / crossover / gap are
PROVISIONAL with their manual conditions, and no gate or status may depend on it."""

import datetime
import unittest
from unittest import mock

import _research as R
from nse.research import confluence, models as m, scanner
from nse.research.deps import mtf


class Ema(unittest.TestCase):
    def test_sma_seed_then_exponential(self):
        vals = [float(v) for v in range(1, 25)]           # 1..24
        e = confluence.ema_series(vals, 20)
        self.assertEqual(e[:19], [None] * 19)
        self.assertAlmostEqual(e[19], 10.5)               # mean of 1..20
        a = 2.0 / 21
        self.assertAlmostEqual(e[20], a * 21 + (1 - a) * 10.5)

    def test_short_series_has_no_ema(self):
        self.assertEqual(confluence.ema_series([1.0] * 19, 20), [None] * 19)

    def test_part_e_boundaries_rb_1027_1033(self):
        self.assertEqual([confluence.part_e(x) for x in (6.5, 7, 8, 9, 10, 11, 12, 14)],
                         ["Reject", "Minimum Acceptable", "Good", "Good", "Very Strong", "Very Strong",
                          "Exceptional", "Exceptional"])


class HtfEma(unittest.TestCase):
    def snap(self):
        b = R.SnapBuilder()
        b.add_series("W", [100.0] * 30)              # EMA 20 = 100: inside a 95-105 zone
        b.add_series("M", [200.0] * 30)              # outside
        b.add_series("Q", [100.0] * 5)               # too short: not counted, reason given
        b.add_series("HY", [100.0] * 30, truncated_at=b.as_of)
        return b.build()

    def test_counts_only_known_emas_inside_the_zone(self):
        pts, rows = confluence.htf_ema20(self.snap(), ["W", "M", "Q", "HY", "Y"], 95.0, 105.0)
        self.assertEqual(pts, 1)
        by = {r["tf"]: r for r in rows}
        self.assertIs(by["W"]["inside_zone"], True)
        self.assertIs(by["M"]["inside_zone"], False)
        for tf in ("Q", "HY", "Y"):                  # unknown is never a point
            self.assertIsNone(by[tf]["inside_zone"], tf)
            self.assertTrue(by[tf]["reason"], tf)

    def test_capped_at_two(self):
        b = R.SnapBuilder()
        for tf in ("W", "M", "Q"):
            b.add_series(tf, [100.0] * 30)
        pts, _ = confluence.htf_ema20(b.build(), ["W", "M", "Q"], 95.0, 105.0)
        self.assertEqual(pts, 2)


class Crossover(unittest.TestCase):
    def candles(self, closes):
        days = R.weekdays(datetime.date(2024, 1, 1), len(closes))
        return [R.candle(d, c, c, c, c) for d, c in zip(days, closes)]

    def test_golden_cross_inside_zone_after_creation_counts(self):
        closes = [110.0 - 0.2 * i for i in range(60)] + [98.0 + 0.6 * i for i in range(30)]
        cs = self.candles(closes)
        pts, ev = confluence.crossover(cs, 10, 90.0, 120.0)
        self.assertEqual(pts, 1, ev)
        pts, ev = confluence.crossover(cs, 10, 200.0, 210.0)   # cross outside the zone
        self.assertEqual(pts, 0)

    def test_not_enough_history(self):
        pts, ev = confluence.crossover(self.candles([100.0] * 30), 5, 90.0, 110.0)
        self.assertEqual(pts, 0)
        self.assertIn("EMA 50", ev["reason"])


class OnTheRealPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candles = R.long_mit_candles()
        cfg = scanner.ScanConfig(as_of=cls.candles[-1].end, calendar=R.WeekdayCalendar(),
                                 calendar_label="TEST_WEEKDAYS", risk_per_trade=1000.0)
        cls.cfg = cfg
        cls.res = scanner.scan([R.daily_input("SYN", cls.candles)], cfg)

    def test_display_states_and_bounds(self):
        [c] = self.res.candidates()
        s = c.zone["pre_entry_score"]
        st = {i["factor"]: i["state"] for i in s["items"]}
        self.assertEqual(st["sector"], confluence.NOT_EVALUATED)
        self.assertEqual(st["rsi_stochastic"], confluence.NOT_EVALUATED)
        for f in ("htf_ema20", "crossover", "gap"):
            self.assertEqual(st[f], confluence.PROVISIONAL)
        self.assertEqual(s["items"][0]["points"], 7.0)
        self.assertEqual(s["upper_bound"], s["evaluated"] + 3)       # sector 2 + RSI 1 not evaluated
        self.assertLessEqual(s["upper_bound"], 14)
        self.assertIn("information only", s["note"])

    def test_no_gate_or_status_depends_on_the_score(self):
        weird = {"items": [], "evaluated": 0, "upper_bound": 0, "display": "x", "part_e_evaluated": "Reject",
                 "part_e_upper_bound": "Reject", "note": ""}
        with mock.patch.object(confluence, "score14", return_value=weird):
            other = scanner.scan([R.daily_input("SYN", self.candles)], self.cfg)
        a, b = self.res.candidates(), other.candidates()
        self.assertEqual([(c.status, [g.outcome for g in c.gates], [g.reasons for g in c.gates]) for c in a],
                         [(c.status, [g.outcome for g in c.gates], [g.reasons for g in c.gates]) for c in b])
        self.assertEqual(a[0].status, m.ACTIONABLE)

    def test_prefix_invariant(self):
        later = R.extend(self.candles, [(110.0, 110.5, 109.5, 110.0)] * 3)
        cfg = scanner.ScanConfig(as_of=self.candles[-1].end, calendar=R.WeekdayCalendar(),
                                 calendar_label="TEST_WEEKDAYS", risk_per_trade=1000.0)
        again = scanner.scan([R.daily_input("SYN", later)], cfg)
        self.assertEqual(self.res.candidates()[0].zone["pre_entry_score"],
                         again.candidates()[0].zone["pre_entry_score"])



class CrossoverPreExistingZone(unittest.TestCase):
    """RB 570: the cross counts only inside a PRE-EXISTING zone (audit 2026-11-02)."""

    def candles(self, closes):
        days = R.weekdays(datetime.date(2024, 1, 1), len(closes))
        return [R.candle(d, c, c, c, c) for d, c in zip(days, closes)]

    def _cross_index(self, cs):
        closes = [c.close for c in cs]
        f, s = confluence.ema_series(closes, 20), confluence.ema_series(closes, 50)
        return [i for i in range(1, len(cs)) if None not in (f[i], s[i], f[i - 1], s[i - 1])
                and f[i - 1] <= s[i - 1] and f[i] > s[i]][0]

    def test_cross_on_or_before_the_creation_bar_does_not_count(self):
        closes = [110.0 - 0.2 * i for i in range(60)] + [98.0 + 0.6 * i for i in range(30)]
        cs = self.candles(closes)
        k = self._cross_index(cs)
        self.assertEqual(confluence.crossover(cs, k, 90.0, 120.0)[0], 0)        # created on the cross bar
        self.assertEqual(confluence.crossover(cs, k + 5, 90.0, 120.0)[0], 0)    # created after the cross
        self.assertEqual(confluence.crossover(cs, k - 1, 90.0, 120.0)[0], 1)    # pre-existing zone

if __name__ == "__main__":
    unittest.main()
