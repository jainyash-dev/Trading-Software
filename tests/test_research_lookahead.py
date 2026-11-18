"""Point-in-time safety of the scanner (SYNTHETIC candles, weekday test calendar).

Prefix invariance: with the data through time T unchanged, adding later candles must not
change any decision made at T. Every comparison is of the full serialised scan, so any
field that leaked future information would show up.
"""

import datetime
import json
import unittest

import _research as R
from nse.research import reports, scanner
from nse.research.deps import mtf


def scan(candles, as_of, **kw):
    kw.setdefault("corporate_action_coverage", R.verified_ca("SYN"))
    cfg = scanner.ScanConfig(as_of=as_of, calendar=R.WeekdayCalendar(), calendar_label="TEST_WEEKDAYS", **kw)
    return scanner.scan([R.daily_input("SYN", candles)], cfg)


def without_as_of(x):
    if isinstance(x, dict):
        return {k: without_as_of(v) for k, v in x.items() if k not in ("as_of", "as_of_time")}
    if isinstance(x, list):
        return [without_as_of(v) for v in x]
    return x


def close_of(c):
    return c.end


class PrefixInvariance(unittest.TestCase):
    def test_later_candles_never_change_an_earlier_scan(self):
        for seed in (1, 7):
            cs = R.random_walk(seed, 520)
            for t in (300, 380, 455):
                as_of = close_of(cs[t])
                full = reports.to_dict(scan(cs, as_of))
                prefix = reports.to_dict(scan(cs[:t + 1], as_of))
                self.assertEqual(full, prefix, (seed, t))

    def test_a_future_touch_does_not_rewrite_the_past(self):
        days, cs = R.dbr_candles(touch_on=52)
        before = close_of(cs[50])
        early = scan(cs, before).symbols[0]
        self.assertEqual([c.zone["proximal"] for c in early.candidates], [R.DBR_PL])
        late = scan(cs, close_of(cs[-1])).symbols[0]
        self.assertEqual(late.candidates, [])
        # re-running the early as_of with the touch now in the data gives the same answer
        self.assertEqual(reports.to_dict(scan(cs, before)), reports.to_dict(scan(cs[:51], before)))

    def test_as_of_inside_a_session_ignores_that_days_candle(self):
        cs = R.random_walk(2, 400)
        noon = datetime.datetime.combine(cs[350].start.date(), datetime.time(12, 0))
        self.assertEqual(reports.to_dict(scan(cs, noon))["symbols"][0]["price"], cs[349].close)
        # identical apart from the as_of label itself
        self.assertEqual(without_as_of(reports.to_dict(scan(cs, noon))),
                         without_as_of(reports.to_dict(scan(cs[:350], close_of(cs[349])))))

    def test_trailing_incomplete_candle_is_ignored(self):
        cs = R.random_walk(4, 400)
        last = cs[-1]
        forming = mtf.TimedCandle(last.start, last.end, last.open, last.high, last.low, last.close, complete=False)
        a = reports.to_dict(scan(cs[:-1] + [forming], close_of(last)))
        self.assertNotEqual(a["symbols"][0]["price"], None)
        self.assertEqual(a["symbols"][0]["price"], cs[-2].close)


class FutureDataQuality(unittest.TestCase):
    """A defect in data dated after as_of says nothing about the data a decision at as_of
    used; one dated at or before as_of stops the symbol (G0)."""

    def _csv_scan(self, extra_row, as_of_index):
        import os
        import shutil
        import tempfile
        from nse.research import marketdata
        cs = R.random_walk(6, 400)
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "SYN.csv")
            with open(p, "w") as fh:
                fh.write("date,open,high,low,close\n")
                for i, c in enumerate(cs):
                    fh.write("%s,%s,%s,%s,%s\n" % (c.start.date(), c.open, c.high, c.low, c.close))
                    if extra_row is not None and i == extra_row:
                        fh.write("%s,%s,%s,%s,%s\n" % (c.start.date(), c.open, c.high, c.low, c.close))   # duplicate
            inp = marketdata.from_csv(p, price_adjustment="NONE")
        finally:
            shutil.rmtree(tmp)
        cfg = scanner.ScanConfig(as_of=cs[as_of_index].end, calendar=R.WeekdayCalendar(), calendar_label="T")
        return scanner.scan([inp], cfg)

    def test_a_future_duplicate_row_does_not_change_an_earlier_scan(self):
        clean = reports.to_dict(self._csv_scan(None, 350))
        dirty_later = reports.to_dict(self._csv_scan(380, 350))
        # the input files differ (row count, SHA-256); every decision and finding is the same
        for d in (clean, dirty_later):
            d["symbols"][0].pop("provenance")
        self.assertEqual(clean, dirty_later)
        self.assertEqual(clean["symbols"][0]["status"], scanner.SYMBOL_EVALUATED)

    def _bad_date_input(self, bad_after, swap_neighbours=False):
        import os
        import shutil
        import tempfile
        from nse.research import marketdata
        cs = R.random_walk(6, 400)
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "SYN.csv")
            with open(p, "w") as fh:
                fh.write("date,open,high,low,close\n")
                rows = list(cs)
                if swap_neighbours:                          # the rows around the bad one are out of order
                    rows[bad_after], rows[bad_after + 1] = rows[bad_after + 1], rows[bad_after]
                if bad_after < 0:
                    fh.write("2O24-13-45,1,1,1,1\n")
                for i, c in enumerate(rows):
                    fh.write("%s,%s,%s,%s,%s\n" % (c.start.date(), c.open, c.high, c.low, c.close))
                    if i == bad_after:
                        fh.write("2O24-13-45,1,1,1,1\n")     # unreadable date (letter O)
            return cs, marketdata.from_csv(p, price_adjustment="NONE")
        finally:
            shutil.rmtree(tmp)

    def _status(self, cs, inp, as_of_index):
        cfg = scanner.ScanConfig(as_of=cs[as_of_index].end, calendar=R.WeekdayCalendar(), calendar_label="T")
        return scanner.scan([inp], cfg).symbols[0]

    def test_d44_a_bad_date_row_is_bounded_by_its_neighbours(self):
        # D44: the unreadable row lies after row 380 in a file whose neighbours are in order, so
        # its true date is on or after row 380's date: a scan at row 350 is not contaminated
        cs, inp = self._bad_date_input(380)
        [f] = [f for f in inp.findings if f.code == "BAD_DATE"]
        self.assertEqual((f.date, f.verified, f.extra["bound"]), (cs[380].start.date(), False, "EARLIEST_POSSIBLE_DATE"))
        self.assertIn("ERROR_DATE_BOUND_INFERRED", [x.code for x in inp.findings])   # the inference is visible
        self.assertEqual(self._status(cs, inp, 350).status, scanner.SYMBOL_EVALUATED)
        # on the bound itself (it may be a duplicate of that date) and later: blocked
        for k in (380, 390):
            s = self._status(cs, inp, k)
            self.assertEqual(s.status, scanner.SYMBOL_DATA_INSUFFICIENT, k)
            self.assertTrue(any("BAD_DATE" in r for r in s.reasons), k)

    def test_d44_an_unbounded_bad_date_still_blocks_every_scan(self):
        # before the first valid row: no lower bound, so the impact cannot be bounded
        cs, inp = self._bad_date_input(-1)
        [f] = [f for f in inp.findings if f.code == "BAD_DATE"]
        self.assertEqual((f.date, f.extra["bound"]), (None, "UNBOUNDED"))
        self.assertEqual(self._status(cs, inp, 100).status, scanner.SYMBOL_DATA_INSUFFICIENT)
        # neighbours out of order: the file's order cannot bound it either
        cs, inp = self._bad_date_input(380, swap_neighbours=True)
        [f] = [f for f in inp.findings if f.code == "BAD_DATE"]
        self.assertEqual(f.date, None)
        self.assertEqual(self._status(cs, inp, 100).status, scanner.SYMBOL_DATA_INSUFFICIENT)

    def test_d44_a_file_out_of_order_elsewhere_cannot_bound_a_bad_date(self):
        # QA 2026-11-08 reproduction: in-order neighbours (01-09, 01-10) but a later row (01-03)
        # proves the file unsorted, so the lost row could be 01-02: the error stays unbounded
        import os
        import shutil
        import tempfile
        from nse.research import marketdata
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "SYN.csv")
            with open(p, "w") as fh:
                fh.write("date,open,high,low,close\n2024-01-01,1,1,1,1\n2024-01-09,1,1,1,1\nbad,1,1,1,1\n"
                         "2024-01-10,1,1,1,1\n2024-01-03,1,1,1,1\n")
            inp = marketdata.from_csv(p, price_adjustment="NONE")
        finally:
            shutil.rmtree(tmp)
        [f] = [f for f in inp.findings if f.code == "BAD_DATE"]
        self.assertEqual((f.date, f.extra["bound"]), (None, "UNBOUNDED"))
        self.assertTrue(any(x.code == "BAD_DATE" for x in inp.findings_at(datetime.date(2024, 1, 5))))
        self.assertNotIn("ERROR_DATE_BOUND_INFERRED", [x.code for x in inp.findings])

    def test_a_past_duplicate_row_stops_the_symbol(self):
        res = self._csv_scan(300, 350)
        self.assertEqual(res.symbols[0].status, scanner.SYMBOL_DATA_INSUFFICIENT)
        self.assertTrue(any("DUPLICATE_DATE" in r for r in res.symbols[0].reasons))


class Determinism(unittest.TestCase):
    def test_identical_inputs_identical_outputs(self):
        cs = R.random_walk(9, 450)
        a = reports.to_json(scan(cs, close_of(cs[-1])))
        b = reports.to_json(scan(list(cs), close_of(cs[-1])))
        self.assertEqual(a, b)
        self.assertIsNone(json.loads(a)["generated_at"])      # no clock is read

    def test_symbol_order_does_not_matter(self):
        a, b = R.random_walk(11, 400), R.random_walk(12, 400)
        cfg = scanner.ScanConfig(as_of=close_of(a[-1]), calendar=R.WeekdayCalendar())
        x = scanner.scan([R.daily_input("AAA", a), R.daily_input("BBB", b)], cfg)
        y = scanner.scan([R.daily_input("BBB", b), R.daily_input("AAA", a)], cfg)
        self.assertEqual(reports.to_json(x), reports.to_json(y))

    def test_history_scans_equal_single_scans(self):
        cs = R.random_walk(13, 420)
        times = [close_of(cs[i]) for i in (300, 360, 419)]
        cfg = scanner.ScanConfig(as_of=times[0], calendar=R.WeekdayCalendar(), calendar_label="TEST_WEEKDAYS",
                                 corporate_action_coverage=R.verified_ca("SYN"))
        hist = scanner.scan_history([R.daily_input("SYN", cs)], list(reversed(times)), cfg)
        self.assertEqual([h.as_of for h in hist], [t.isoformat() for t in times])
        for h, t in zip(hist, times):
            self.assertEqual(reports.to_dict(h), reports.to_dict(scan(cs, t)))

    def test_repeated_scans_never_reset_zone_history(self):
        days, cs = R.dbr_candles(touch_on=52)
        t = close_of(cs[-1])
        for _ in range(3):
            self.assertEqual(scan(cs, t).symbols[0].candidates, [])


if __name__ == "__main__":
    unittest.main()
