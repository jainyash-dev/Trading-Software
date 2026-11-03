"""Backtest infrastructure (nse/research/backtest.py). SYNTHETIC candles only; every
expected number below is computed by hand from the inputs in the test. Nothing here is a
performance result."""

import dataclasses
import datetime
import json
import unittest

import _research as R
from nse.research import backtest as bt, models as m, scanner, universe
from nse.research.deps import mtf

D = datetime.date
T0 = datetime.datetime(2025, 1, 3, 15, 30)


def model(**over):
    base = dict(entry="ENTRY_MAX", stop="NORMAL_WIDE", target="STRUCTURAL", statuses=(m.ACTIONABLE,),
                entry_expiry_sessions=5, cancel_if_target_first=False, gap_fill="AT_LEVEL", same_bar="STOP_FIRST",
                cost_pct_per_side=0.0, slippage_pct_per_side=0.0)
    base.update(over)
    return bt.ExecutionModel(**base)


def bars(rows, start=D(2025, 1, 6)):
    return [R.candle(d, *r) for d, r in zip(R.weekdays(start, len(rows)), rows)]


LEVELS = (100.0, 95.0, 110.0)      # entry, stop, target


class Model(unittest.TestCase):
    def test_nothing_has_a_default(self):
        # B9, B12: no execution assumption has a default. The only defaulted fields are the
        # optional portfolio rules (RB 2392), whose None means "not applied" and is listed as a
        # limitation (Portfolio.test_old_model_json_loads_and_lists_rules_not_applied).
        with self.assertRaises(TypeError):
            bt.ExecutionModel()
        assumptions = ("entry", "stop", "target", "statuses", "entry_expiry_sessions", "cancel_if_target_first",
                       "gap_fill", "same_bar", "cost_pct_per_side", "slippage_pct_per_side")
        for field in dataclasses.fields(bt.ExecutionModel):
            if field.name in assumptions:
                self.assertIs(field.default, dataclasses.MISSING, field.name)
            else:
                self.assertIn(field.name, ("monthly_trade_cap", "max_open_positions"))
                self.assertIsNone(field.default, field.name)
            self.assertIs(field.default_factory, dataclasses.MISSING, field.name)
        self.assertEqual(tuple(f.name for f in dataclasses.fields(bt.ExecutionModel))[:10], assumptions)

    def test_invalid_choices_are_refused(self):
        for bad in (dict(entry="MID"), dict(same_bar="RANDOM"), dict(statuses=()), dict(statuses=(m.REJECTED,)),
                    dict(statuses=(m.STATUS_DATA_INSUFFICIENT,)), dict(entry_expiry_sessions=0),
                    dict(cost_pct_per_side=-0.1), dict(slippage_pct_per_side=float("nan"))):
            with self.assertRaises(ValueError, msg=bad):
                model(**bad)


class Simulate(unittest.TestCase):
    def run_(self, rows, zone=None, **over):
        return bt.simulate(LEVELS, bars(rows), T0, model(**over), zone=zone)

    def test_fill_then_target(self):
        r = self.run_([(104, 105, 101, 103), (103, 103, 99, 101), (101, 111, 100, 110)])
        self.assertEqual((r["fill_price"], r["exit_price"], r["exit_reason"]), (100.0, 110.0, "TARGET"))
        self.assertEqual(bt.r_multiple(r, model()), 2.0)                       # (110 - 100) / (100 - 95)

    def test_fill_then_stop_and_gap_policies(self):
        r = self.run_([(103, 103, 99, 101), (96, 96, 90, 91)])
        self.assertEqual((r["exit_price"], r["exit_reason"]), (95.0, "STOP"))
        r = self.run_([(103, 103, 99, 101), (93, 94, 90, 91)], gap_fill="AT_OPEN")
        self.assertEqual(r["exit_price"], 93.0)                                 # opened through the stop
        self.assertEqual(bt.r_multiple(r, model()), -1.4)
        r = self.run_([(98, 99, 97, 98)], gap_fill="AT_OPEN")
        self.assertEqual(r["fill_price"], 98.0)                                 # opened below the limit

    def test_stop_loss_and_zone_invalidation_are_separate_events(self):
        zone = {"zone_id": "D1", "timeframe": "D", "side": "demand", "distal": 100.0}
        stop_only = self.run_([(103, 104, 99, 101), (101, 103, 94, 101)], zone=zone)
        self.assertEqual(stop_only["exit_reason"], "STOP")
        self.assertEqual([e["type"] for e in stop_only["trade_events"]], ["STOP_LOSS_HIT"])
        self.assertEqual(stop_only["zone_events"], [])  # low pierced DL, close recovered

        invalidation_only = self.run_([(103, 104, 99, 101), (101, 102, 97, 99)], zone=zone)
        self.assertEqual(invalidation_only["exit_reason"], "OPEN_AT_END_OF_DATA")
        self.assertEqual(invalidation_only["trade_events"], [])
        self.assertEqual([e["type"] for e in invalidation_only["zone_events"]], ["ZONE_INVALIDATED"])

        both = self.run_([(103, 104, 99, 101), (101, 103, 94, 99)], zone=zone)
        self.assertEqual(both["exit_reason"], "STOP")
        self.assertEqual([e["type"] for e in both["trade_events"]], ["STOP_LOSS_HIT"])
        self.assertEqual([e["type"] for e in both["zone_events"]], ["ZONE_INVALIDATED"])

    def test_wick_below_dl_without_close_or_sl_is_not_invalidation_or_stop(self):
        zone = {"zone_id": "D1", "timeframe": "D", "side": "demand", "distal": 100.0}
        rec = self.run_([(103, 104, 99, 101), (101, 103, 98, 101)], zone=zone)
        self.assertEqual(rec["exit_reason"], "OPEN_AT_END_OF_DATA")
        self.assertEqual(rec["trade_events"], [])
        self.assertEqual(rec["zone_events"], [])

    def test_gap_below_the_stop_on_the_fill_bar_exits_at_the_fill(self):
        r = self.run_([(93, 94, 90, 91)], gap_fill="AT_OPEN")
        self.assertEqual((r["fill_price"], r["exit_price"], r["exit_reason"]), (93.0, 93.0, "STOP"))

    def test_same_bar_policies(self):
        rows = [(103, 103, 99, 101), (100, 111, 94, 100)]
        self.assertEqual(self.run_(rows)["exit_reason"], "STOP")
        self.assertEqual(self.run_(rows, same_bar="TARGET_FIRST")["exit_reason"], "TARGET")
        self.assertEqual(self.run_(rows, same_bar="EXCLUDE")["exit_reason"], "EXCLUDED_SAME_BAR")
        fill_and_target = [(103, 111, 99, 105)]                                  # order unknown on the fill bar
        self.assertEqual(self.run_(fill_and_target)["exit_reason"], "OPEN_AT_END_OF_DATA")
        self.assertEqual(self.run_(fill_and_target, same_bar="TARGET_FIRST")["exit_reason"], "TARGET")
        self.assertEqual(self.run_(fill_and_target, same_bar="EXCLUDE")["exit_reason"], "EXCLUDED_SAME_BAR")

    def test_expiry_cancellation_and_end_of_data(self):
        self.assertEqual(self.run_([(104, 105, 101, 103)] * 6, entry_expiry_sessions=3)["exit_reason"], "EXPIRED")
        self.assertEqual(self.run_([(104, 112, 101, 103), (103, 103, 99, 101)],
                                   cancel_if_target_first=True)["exit_reason"], "CANCELLED_TARGET_FIRST")
        self.assertEqual(self.run_([(104, 105, 101, 103)])["exit_reason"], "OPEN_ORDER_AT_END_OF_DATA")
        self.assertEqual(self.run_([(103, 103, 99, 101)])["exit_reason"], "OPEN_AT_END_OF_DATA")

    def test_only_candles_after_the_signal_are_read(self):
        cs = bars([(103, 103, 99, 101), (101, 111, 100, 110)], start=D(2025, 1, 2))   # 2 Jan, 3 Jan
        r = bt.simulate(LEVELS, cs, T0, model())                                  # signal at 3 Jan close
        self.assertEqual(r["exit_reason"], "OPEN_ORDER_AT_END_OF_DATA")

    def test_costs(self):
        r = self.run_([(103, 103, 99, 101), (101, 111, 100, 110)])
        net = bt.r_multiple(r, model(cost_pct_per_side=0.1, slippage_pct_per_side=0.05))
        self.assertAlmostEqual(net, (110 * (1 - 0.0015) - 100 * (1 + 0.0015)) / 5, places=6)


class Metrics(unittest.TestCase):
    def test_hand_computed(self):
        trades = [{"r": 2.0, "exit_time": "2025-01-01", "symbol": "A", "zone_id": "1"},
                  {"r": -1.0, "exit_time": "2025-01-02", "symbol": "A", "zone_id": "2"},
                  {"r": -1.0, "exit_time": "2025-01-03", "symbol": "A", "zone_id": "3"},
                  {"r": 3.0, "exit_time": "2025-01-04", "symbol": "A", "zone_id": "4"},
                  {"r": None, "exit_time": None, "symbol": "A", "zone_id": "5"}]
        got = bt.metrics(trades)
        self.assertEqual(got, {"closed_trades": 4, "wins": 2, "losses": 2, "win_rate": 0.5, "expectancy_r": 0.75,
                               "total_r": 3.0, "max_drawdown_r": -2.0, "not_closed": 1, "excluded": 0})
        self.assertEqual(bt.metrics([])["expectancy_r"], None)


class EndToEnd(unittest.TestCase):
    """The long SYNTHETIC history, then candles that dip into the entry and run to the target."""

    def setUp(self):
        base = R.long_mit_candles()
        self.signal = base[-1].end
        # entry max 161.94 (PL 159.94 + 2), normal wide SL 155.8, target W supply PL
        self.candles = R.extend(base, [(175.0, 176.0, 161.5, 163.0), (163.0, 175.0, 162.0, 174.0),
                                       (174.0, 200.0, 173.0, 198.0)])
        self.cfg = scanner.ScanConfig(as_of=self.signal, calendar=R.WeekdayCalendar(), risk_per_trade=1000.0)

    def test_a_synthetic_trade_from_a_point_in_time_signal(self):
        res = bt.run([R.daily_input("SYN", self.candles)], [self.signal], self.cfg, model(entry_expiry_sessions=3))
        [t] = res["trades"]
        self.assertEqual((t["status"], t["exit_reason"]), (m.ACTIONABLE, "TARGET"))
        self.assertEqual(t["fill_price"], round(R.LONG_PL + 2.0, 4))
        self.assertGreater(t["r"], 2.0)
        self.assertIn("TRADER_STATE", t["manual_checks_pending"])
        self.assertIn(bt.NOT_PERFORMANCE_EVIDENCE, res["limitations"])
        self.assertIn(bt.SURVIVORSHIP_UNCONTROLLED, res["limitations"])
        self.assertEqual(bt.to_json(res), bt.to_json(bt.run([R.daily_input("SYN", self.candles)], [self.signal],
                                                            self.cfg, model(entry_expiry_sessions=3))))

    def test_a_trade_across_a_price_scale_event_is_excluded_not_counted(self):
        from nse.research import corporate_actions as ca
        target_day = self.candles[-1].start.date()
        act = ca.Action("SYN", target_day, "SPLIT", 1.0, 2.0, True, "SYNTHETIC TEST ROW")
        cfg = dataclasses.replace(self.cfg, corporate_actions=[act])
        res = bt.run([R.daily_input("SYN", self.candles)], [self.signal], cfg, model(entry_expiry_sessions=3))
        [t] = res["trades"]
        self.assertIsNone(t["r"])
        self.assertTrue(t["excluded_reason"].startswith("PRICE_SCALE_EVENT_DURING_TRADE"))
        self.assertEqual((res["metrics"]["ALL"]["closed_trades"], res["metrics"]["ALL"]["excluded"]), (0, 1))
        # an event after the exit does not touch the trade
        later = ca.Action("SYN", target_day + datetime.timedelta(days=30), "SPLIT", 1.0, 2.0, True, "SYNTHETIC")
        res = bt.run([R.daily_input("SYN", self.candles)], [self.signal],
                     dataclasses.replace(self.cfg, corporate_actions=[later]), model(entry_expiry_sessions=3))
        self.assertEqual(res["metrics"]["ALL"]["closed_trades"], 1)

    def test_statuses_not_selected_place_no_order(self):
        res = bt.run([R.daily_input("SYN", self.candles)], [self.signal], self.cfg,
                     model(statuses=(m.MANUAL_REVIEW,)))
        self.assertEqual(res["trades"], [])

    def test_a_zone_signals_once_and_segments_stay_separate(self):
        times = [self.signal, self.candles[-3].end]
        res = bt.run([R.daily_input("SYN", self.candles)], times, self.cfg, model(), split=self.signal)
        self.assertEqual(len(res["trades"]), 1)
        self.assertEqual(res["trades"][0]["segment"], "IN_SAMPLE")
        self.assertEqual(res["metrics"]["OUT_OF_SAMPLE"]["closed_trades"], 0)

    def test_history_respects_point_in_time_membership(self):
        u = universe.Universe("TEST", [universe.Membership("SYN", "EQ", D(2019, 1, 1), self.signal.date(), True, "t")])
        later = self.candles[-1].end
        hist = scanner.scan_history([R.daily_input("SYN", self.candles)], [self.signal, later], self.cfg, universe=u)
        self.assertEqual([h.symbols[0].status for h in hist], [scanner.SYMBOL_EVALUATED, scanner.SYMBOL_NOT_IN_UNIVERSE])


class Cli(unittest.TestCase):
    def test_backtest_command_needs_every_assumption(self):
        import contextlib
        import io
        import os
        import shutil
        import tempfile
        from nse.research import cli
        tmp = tempfile.mkdtemp()
        try:
            cs = R.extend(R.long_mit_candles(), [(175.0, 176.0, 161.5, 163.0), (174.0, 200.0, 173.0, 198.0)])
            data = os.path.join(tmp, "in")
            os.makedirs(data)
            with open(os.path.join(data, "SYN.csv"), "w") as fh:
                fh.write("date,open,high,low,close\n")
                for c in cs:
                    fh.write("%s,%s,%s,%s,%s\n" % (c.start.date(), c.open, c.high, c.low, c.close))
            spec = dataclasses.asdict(model(statuses=(m.MANUAL_REVIEW,)))     # no calendar: G0 MANUAL
            mpath = os.path.join(tmp, "model.json")
            with open(mpath, "w") as fh:
                json.dump(spec, fh)
            out = os.path.join(tmp, "bt.json")
            args = ["backtest", "--model", mpath, "--start", str(cs[-3].start.date()), "--end", str(cs[-3].start.date()),
                    "--symbols", "SYN", "--csv-dir", data, "--price-adjustment", "NONE", "--risk-per-trade", "1000",
                    "--out", out]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(args), 0)
            with open(out) as fh:
                res = json.load(fh)
            self.assertEqual([t["exit_reason"] for t in res["trades"]], ["TARGET"])
            self.assertIn(bt.NOT_PERFORMANCE_EVIDENCE, res["limitations"])
            del spec["same_bar"]
            with open(mpath, "w") as fh:
                json.dump(spec, fh)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(cli.main(args), 2)
            self.assertIn("same_bar", err.getvalue())
        finally:
            shutil.rmtree(tmp)



def closed(rs, start=D(2025, 1, 6)):
    """Closed trade records with the given R, exiting on consecutive weekdays."""
    return [{"r": r, "exit_time": "%sT15:30:00" % d, "symbol": "A", "zone_id": str(n), "exit_reason": "X"}
            for n, (d, r) in enumerate(zip(R.weekdays(start, len(rs)), rs))]


class ExtendedMetrics(unittest.TestCase):
    """Distribution metrics, computed by hand. r <= 0 is a loss (the metrics() convention)."""

    def test_hand_computed(self):
        got = bt.extended_metrics(closed([2.0, -1.0, -1.0, 3.0, -0.5, 0.5]))
        self.assertEqual(got["profit_factor"], 2.2)                    # (2 + 3 + 0.5) / |-1 - 1 - 0.5|
        self.assertEqual(got["avg_win_r"], round(5.5 / 3, 6))
        self.assertEqual(got["avg_loss_r"], round(-2.5 / 3, 6))
        self.assertEqual(got["max_consecutive_losses"], 2)
        self.assertEqual(got["median_r"], 0.0)                         # (-0.5 + 0.5) / 2
        self.assertEqual(got["r_distribution"], [{"bucket": "<=-1", "count": 2}, {"bucket": "(-1,0]", "count": 1},
                                                 {"bucket": "(0,1]", "count": 1}, {"bucket": "(1,2]", "count": 1},
                                                 {"bucket": "(2,3]", "count": 1}, {"bucket": ">3", "count": 0}])
        self.assertEqual(got["exit_reasons"], {"X": 6})
        self.assertEqual(got["sample_size_warning"], bt.SMALL_SAMPLE)
        base = bt.metrics(closed([2.0, -1.0, -1.0, 3.0, -0.5, 0.5]))
        self.assertEqual({k: got[k] for k in base}, base)             # metrics() itself is unchanged

    def test_bucket_edges_are_upper_inclusive(self):
        for r, label in ((-1.0, "<=-1"), (-1.000001, "<=-1"), (-0.999999, "(-1,0]"), (0.0, "(-1,0]"),
                         (1.0, "(0,1]"), (2.0, "(1,2]"), (3.0, "(2,3]"), (3.000001, ">3")):
            self.assertEqual(bt.r_bucket(r), label, r)

    def test_no_loss_gives_no_profit_factor_not_infinity(self):
        got = bt.extended_metrics(closed([1.0, 2.0]))
        self.assertEqual((got["profit_factor"], got["avg_loss_r"], got["max_consecutive_losses"]), (None, None, 0))
        got = bt.extended_metrics(closed([0.0, 1.0]))                  # a 0R loss: nothing to divide by
        self.assertEqual((got["losses"], got["profit_factor"]), (1, None))
        empty = bt.extended_metrics([])
        self.assertEqual((empty["median_r"], empty["avg_win_r"], empty["sample_size_warning"]),
                         (None, None, bt.SMALL_SAMPLE))

    def test_consecutive_losses_follow_exit_order_not_list_order(self):
        rows = closed([-1.0, 1.0, -1.0, -1.0, -1.0])
        self.assertEqual(bt.extended_metrics(list(reversed(rows)))["max_consecutive_losses"], 3)

    def test_small_sample_threshold_boundary(self):
        self.assertEqual(bt.SMALL_SAMPLE_THRESHOLD, 30)
        self.assertEqual(bt.extended_metrics(closed([1.0] * 29))["sample_size_warning"], bt.SMALL_SAMPLE)
        self.assertIsNone(bt.extended_metrics(closed([1.0] * 30))["sample_size_warning"])

    def test_assumption_events_are_counted(self):
        sim = Simulate()
        gap_entry = sim.run_([(98, 99, 97, 98)], gap_fill="AT_OPEN")
        self.assertEqual([e["type"] for e in gap_entry["assumption_events"]], ["GAP_THROUGH_ENTRY"])
        at_level = sim.run_([(98, 99, 97, 98)])                         # recorded whatever the policy
        self.assertEqual([e["policy"] for e in at_level["assumption_events"]], ["gap_fill=AT_LEVEL"])
        both = sim.run_([(103, 103, 99, 101), (100, 111, 94, 100)])
        self.assertEqual([(e["type"], e["kind"]) for e in both["assumption_events"]],
                         [("SAME_BAR_AMBIGUOUS", "STOP_AND_TARGET")])
        stop_gap = sim.run_([(103, 103, 99, 101), (93, 94, 90, 91)])
        self.assertEqual([e["type"] for e in stop_gap["assumption_events"]], ["GAP_THROUGH_STOP"])
        target_gap = sim.run_([(103, 103, 99, 101), (112, 113, 111, 112)])
        self.assertEqual([e["type"] for e in target_gap["assumption_events"]], ["GAP_THROUGH_TARGET"])
        clean = sim.run_([(103, 103, 99, 101), (101, 111, 100, 110)])
        self.assertEqual(clean["assumption_events"], [])
        got = bt.extended_metrics([gap_entry, both, stop_gap, target_gap, clean])
        self.assertEqual((got["same_bar_ambiguous_trades"], got["gap_fill_trades"]), (1, 3))
        self.assertEqual(got["assumption_event_counts"], {"GAP_THROUGH_ENTRY": 1, "SAME_BAR_AMBIGUOUS": 1,
                                                         "GAP_THROUGH_STOP": 1, "GAP_THROUGH_TARGET": 1})


def filled(sym, zone, signal, fill, exit_, r=1.0):
    return {"symbol": sym, "zone_id": zone, "signal_as_of": "%sT15:30:00" % signal,
            "fill_time": "%sT15:30:00" % fill, "fill_price": 100.0,
            "exit_time": None if exit_ is None else "%sT15:30:00" % exit_, "exit_price": 110.0,
            "exit_reason": "TARGET" if exit_ else "OPEN_AT_END_OF_DATA", "r": r if exit_ else None,
            "trade_events": [], "zone_events": [], "assumption_events": []}


class Portfolio(unittest.TestCase):
    """RB 2392, 2408: at most 10 trades a month, counted by fill month; concurrency."""

    def test_eleventh_fill_in_a_month_is_not_traded(self):
        days = R.weekdays(D(2025, 1, 1), 12)                          # 1-16 Jan, then 17 Jan
        trades = [filled("S%02d" % n, "Z", D(2024, 12, 31), d, d) for n, d in enumerate(days[:11])]
        trades.append(filled("FEB", "Z", D(2025, 1, 30), D(2025, 2, 3), D(2025, 2, 3)))
        bt.apply_portfolio_rules(trades, model(monthly_trade_cap=10))
        self.assertEqual([t["exit_reason"] for t in trades[:10]], ["TARGET"] * 10)
        eleventh = trades[10]
        self.assertEqual((eleventh["exit_reason"], eleventh["r"], eleventh["fill_time"]),
                         (bt.NOT_TRADED_MONTHLY_CAP, None, None))
        self.assertEqual(eleventh["not_traded"]["would_have"]["exit_reason"], "TARGET")
        self.assertEqual(eleventh["not_traded"]["fill_month"], "2025-01")
        self.assertEqual(trades[11]["exit_reason"], "TARGET")       # a new month: the count restarts
        self.assertEqual(bt.extended_metrics(trades)["closed_trades"], 11)

    def test_cap_order_is_fill_time_then_signal_then_symbol_then_zone(self):
        d1, d2 = D(2025, 1, 6), D(2025, 1, 7)
        late_signal_early_fill = filled("ZZZ", "1", D(2025, 1, 3), d1, d1)
        same_day = [filled("BBB", "1", D(2025, 1, 2), d2, d2), filled("AAA", "2", D(2025, 1, 2), d2, d2),
                    filled("AAA", "1", D(2025, 1, 2), d2, d2), filled("CCC", "1", D(2025, 1, 1), d2, d2)]
        trades = same_day + [late_signal_early_fill]
        bt.apply_portfolio_rules(trades, model(monthly_trade_cap=3))
        taken = [(t["symbol"], t["zone_id"]) for t in trades if t["exit_reason"] == "TARGET"]
        # a later fill never displaces an earlier one; on one bar: signal time, symbol, zone id
        self.assertEqual(sorted(taken), sorted([("ZZZ", "1"), ("CCC", "1"), ("AAA", "1")]))
        self.assertEqual([t["exit_reason"] for t in trades[:2]], [bt.NOT_TRADED_MONTHLY_CAP] * 2)

    def test_unfilled_orders_do_not_count(self):
        d = D(2025, 1, 6)
        expired = {"symbol": "A", "zone_id": "1", "signal_as_of": "2025-01-03T15:30:00", "fill_time": None,
                   "exit_reason": "EXPIRED", "r": None}
        trades = [expired, filled("B", "1", D(2025, 1, 3), d, d)]
        bt.apply_portfolio_rules(trades, model(monthly_trade_cap=1, max_open_positions=1))
        self.assertEqual([t["exit_reason"] for t in trades], ["EXPIRED", "TARGET"])

    def test_max_open_positions(self):
        d = R.weekdays(D(2025, 1, 6), 5)
        a = filled("A", "1", D(2025, 1, 3), d[0], d[2])
        b = filled("B", "1", D(2025, 1, 3), d[1], d[1])            # A still open
        c = filled("C", "1", D(2025, 1, 3), d[2], d[3])            # A exits on this bar: counted open
        e = filled("E", "1", D(2025, 1, 3), d[3], None)            # free slot; never closes
        f = filled("F", "1", D(2025, 1, 3), d[4], d[4])            # E holds the slot to the end
        trades = bt.apply_portfolio_rules([a, b, c, e, f], model(max_open_positions=1))
        self.assertEqual([t["exit_reason"] for t in trades],
                         ["TARGET", bt.NOT_TRADED_MAX_OPEN_POSITIONS, bt.NOT_TRADED_MAX_OPEN_POSITIONS,
                          "OPEN_AT_END_OF_DATA", bt.NOT_TRADED_MAX_OPEN_POSITIONS])

    def test_a_trade_refused_for_concurrency_does_not_use_the_monthly_cap(self):
        d = R.weekdays(D(2025, 1, 6), 3)
        trades = [filled("A", "1", D(2025, 1, 3), d[0], d[1]), filled("B", "1", D(2025, 1, 3), d[1], d[1]),
                  filled("C", "1", D(2025, 1, 3), d[2], d[2])]
        bt.apply_portfolio_rules(trades, model(max_open_positions=1, monthly_trade_cap=2))
        self.assertEqual([t["exit_reason"] for t in trades], ["TARGET", bt.NOT_TRADED_MAX_OPEN_POSITIONS, "TARGET"])

    def test_rules_left_at_none_change_nothing(self):
        d = R.weekdays(D(2025, 1, 6), 12)
        trades = [filled("S%02d" % n, "Z", D(2025, 1, 3), x, None) for n, x in enumerate(d)]
        self.assertEqual(bt.apply_portfolio_rules([dict(t) for t in trades], model()), trades)

    def test_invalid_rule_values_are_refused(self):
        for bad in (dict(monthly_trade_cap=0), dict(monthly_trade_cap=True), dict(monthly_trade_cap=1.5),
                    dict(max_open_positions=0), dict(max_open_positions="3")):
            with self.assertRaises(ValueError, msg=bad):
                model(**bad)

    def test_old_model_json_loads_and_lists_rules_not_applied(self):
        import os
        import shutil
        import tempfile
        tmp = tempfile.mkdtemp()
        try:
            spec = dataclasses.asdict(model())
            del spec["monthly_trade_cap"], spec["max_open_positions"]    # a file written before these fields
            path = os.path.join(tmp, "old.json")
            with open(path, "w") as fh:
                json.dump(spec, fh)
            old = bt.load_model(path)
            self.assertEqual((old.monthly_trade_cap, old.max_open_positions), (None, None))
            self.assertEqual(sorted(old.not_applied()),
                             [bt.MONTHLY_TRADE_CAP_NOT_ENFORCED, bt.PORTFOLIO_CONCURRENCY_NOT_MODELLED])
            del spec["gap_fill"]
            with open(path, "w") as fh:
                json.dump(spec, fh)
            with self.assertRaises(TypeError):                             # assumptions stay required
                bt.load_model(path)
        finally:
            shutil.rmtree(tmp)


class PortfolioEndToEnd(unittest.TestCase):
    """Two SYNTHETIC symbols with the same history signal and fill together."""

    def setUp(self):
        base = R.long_mit_candles()
        self.signal = base[-1].end
        self.candles = R.extend(base, [(175.0, 176.0, 161.5, 163.0), (163.0, 175.0, 162.0, 174.0),
                                       (174.0, 200.0, 173.0, 198.0)])
        self.cfg = scanner.ScanConfig(as_of=self.signal, calendar=R.WeekdayCalendar(), risk_per_trade=1000.0)
        self.inputs = [R.daily_input("BBB", self.candles), R.daily_input("AAA", self.candles)]

    def test_limitations_name_the_rules_not_applied(self):
        res = bt.run(self.inputs, [self.signal], self.cfg, model(entry_expiry_sessions=3))
        self.assertIn(bt.MONTHLY_TRADE_CAP_NOT_ENFORCED, res["limitations"])
        self.assertIn(bt.PORTFOLIO_CONCURRENCY_NOT_MODELLED, res["limitations"])
        self.assertEqual([t["exit_reason"] for t in res["trades"]], ["TARGET", "TARGET"])

    def test_monthly_cap(self):
        res = bt.run(self.inputs, [self.signal], self.cfg, model(entry_expiry_sessions=3, monthly_trade_cap=1))
        self.assertEqual([(t["symbol"], t["exit_reason"]) for t in res["trades"]],
                         [("AAA", "TARGET"), ("BBB", bt.NOT_TRADED_MONTHLY_CAP)])
        self.assertEqual(res["metrics"]["ALL"]["closed_trades"], 1)
        self.assertNotIn(bt.MONTHLY_TRADE_CAP_NOT_ENFORCED, res["limitations"])
        self.assertIn(bt.MONTHLY_CAP_SELECTION_BY_FILL_ORDER, res["limitations"])
        self.assertEqual(res["portfolio_rules"]["monthly_cap_counts"], "FILL_MONTH")

    def test_concurrency(self):
        res = bt.run(self.inputs, [self.signal], self.cfg, model(entry_expiry_sessions=3, max_open_positions=1))
        self.assertEqual([t["exit_reason"] for t in res["trades"]], ["TARGET", bt.NOT_TRADED_MAX_OPEN_POSITIONS])
        self.assertNotIn(bt.PORTFOLIO_CONCURRENCY_NOT_MODELLED, res["limitations"])


class SetupAttributes(unittest.TestCase):
    """Setup attributes come from the signal scan's own gate evidence (point in time)."""

    def setUp(self):
        base = R.long_mit_candles()
        self.signal = base[-1].end
        self.candles = R.extend(base, [(175.0, 176.0, 161.5, 163.0), (163.0, 175.0, 162.0, 174.0),
                                       (174.0, 200.0, 173.0, 198.0)])
        self.cfg = scanner.ScanConfig(as_of=self.signal, calendar=R.WeekdayCalendar(), risk_per_trade=1000.0)

    def test_recorded_from_the_signal_candidate(self):
        res = bt.run([R.daily_input("SYN", self.candles)], [self.signal], self.cfg, model(entry_expiry_sessions=3))
        [t] = res["trades"]
        [c] = scanner.scan([R.daily_input("SYN", self.candles)], self.cfg).candidates()
        self.assertEqual(t["setup"], bt.setup_attributes(c))
        self.assertEqual(t["setup"]["status"], m.ACTIONABLE)
        self.assertEqual(t["setup"]["pattern"], c.zone["pattern"])
        self.assertEqual(t["setup"]["location"], "+".join(c.gate("G3").evidence["position_at_price"]))
        self.assertEqual(t["setup"]["coinciding_class"], c.gate("G6").evidence["class"])
        self.assertEqual(t["setup"]["gate_outcomes"], {g.gate: g.outcome for g in c.gates})
        month = t["exit_time"][:7]
        self.assertEqual(res["breakdowns"]["exit_month"][month]["closed_trades"], 1)
        self.assertEqual(res["breakdowns"]["exit_year"][month[:4]]["closed_trades"], 1)
        self.assertEqual(res["breakdowns"]["pattern"][c.zone["pattern"]]["closed_trades"], 1)

    def test_later_candles_do_not_change_recorded_attributes(self):
        more = R.extend(self.candles, [(150.0, 151.0, 140.0, 141.0)] * 40)  # a later collapse
        a = bt.run([R.daily_input("SYN", self.candles)], [self.signal], self.cfg, model(entry_expiry_sessions=3))
        b = bt.run([R.daily_input("SYN", more)], [self.signal], self.cfg, model(entry_expiry_sessions=3))
        self.assertEqual(a["trades"][0]["setup"], b["trades"][0]["setup"])
        self.assertEqual(a["trades"][0]["signal_as_of"], b["trades"][0]["signal_as_of"])

    def test_missing_evidence_is_unknown(self):
        c = m.CandidateResult("X", m.MIT, "D", "2025-01-03T15:30:00", {}, [], m.MANUAL_REVIEW, [], [], [], [], [],
                              {}, [])
        got = bt.setup_attributes(c)
        for k in ("location", "trend_gate_label", "trend_gate_readings", "coinciding_class", "pattern", "core"):
            self.assertEqual(got[k], "UNKNOWN", k)


class WalkForward(unittest.TestCase):
    def setUp(self):
        base = R.long_mit_candles()
        self.signal = base[-1].end
        self.candles = R.extend(base, [(175.0, 176.0, 161.5, 163.0), (163.0, 175.0, 162.0, 174.0),
                                       (174.0, 200.0, 173.0, 198.0)])
        self.cfg = scanner.ScanConfig(as_of=self.signal, calendar=R.WeekdayCalendar(), risk_per_trade=1000.0)
        c1, c2, c3 = self.candles[-3:]
        self.fold = (self.signal, c2.end, c3.end, c3.end)

    def wf(self, candles):
        return bt.run_walk_forward([R.daily_input("SYN", candles)], [self.fold], self.cfg,
                                   model(entry_expiry_sessions=3))

    def test_a_segment_reads_nothing_after_its_window(self):
        res = self.wf(self.candles)
        seg = res["folds"][0]["IN"]
        [t] = seg["trades"]
        self.assertTrue(self.signal.isoformat() <= t["signal_as_of"] <= self.fold[1].isoformat())
        # the full data reach the target on the last bar (EndToEnd); IN ends one bar earlier
        self.assertEqual(t["exit_reason"], "OPEN_AT_END_OF_DATA")
        self.assertEqual(seg["window"], [self.fold[0].isoformat(), self.fold[1].isoformat()])
        changed = self.candles[:-1] + R.extend(self.candles[:-1], [(150.0, 151.0, 140.0, 141.0)])[-1:]
        self.assertEqual(bt.to_json(self.wf(changed)["folds"][0]["IN"]), bt.to_json(seg))
        self.assertEqual(res["pooled_out"]["signals"], len(res["folds"][0]["OUT"]["trades"]))
        self.assertIn(bt.NOT_PERFORMANCE_EVIDENCE, res["limitations"])
        self.assertIn("selects, optimises and ranks nothing", res["no_selection"])

    def test_fold_checks(self):
        a, b, c, d = self.fold
        for bad in ([], [(b, a, c, d)], [(a, b, b, d)], [(a, b, c)], [(a, b, c, d), (a, b, c, d)],
                    [(a.date(), b, c, d)]):
            with self.assertRaises(ValueError, msg=bad):
                bt.check_folds(bad)


def find_keys(obj, words):
    if isinstance(obj, dict):
        return [k for k in obj if any(w in k.lower() for w in words)] + \
               [x for v in obj.values() for x in find_keys(v, words)]
    if isinstance(obj, list):
        return [x for v in obj for x in find_keys(v, words)]
    return []


class Sensitivity(unittest.TestCase):
    def setUp(self):
        base = R.long_mit_candles()
        self.signal = base[-1].end
        self.candles = R.extend(base, [(175.0, 176.0, 161.5, 163.0), (163.0, 175.0, 162.0, 174.0),
                                       (174.0, 200.0, 173.0, 198.0)])
        self.cfg = scanner.ScanConfig(as_of=self.signal, calendar=R.WeekdayCalendar(), risk_per_trade=1000.0)
        self.models = [model(entry_expiry_sessions=3), model(entry_expiry_sessions=1, entry="ENTRY_MIN"),
                       model(entry_expiry_sessions=3, cost_pct_per_side=0.5)]

    def test_side_by_side_in_input_order_with_no_ranking(self):
        inputs = [R.daily_input("SYN", self.candles)]
        res = bt.run_sensitivity(inputs, [self.signal], self.cfg, self.models)
        self.assertEqual([r["model"] for r in res["runs"]], [dataclasses.asdict(x) for x in self.models])
        self.assertEqual([r["index"] for r in res["runs"]], [0, 1, 2])
        self.assertEqual(find_keys(res, ("best", "rank", "winner", "optim")), [])
        for r, x in zip(res["runs"], self.models):                     # the same signals as a single run
            self.assertEqual(r["metrics"], bt.run(inputs, [self.signal], self.cfg, x)["metrics"])
        rev = bt.run_sensitivity(inputs, [self.signal], self.cfg, list(reversed(self.models)))
        self.assertEqual([r["metrics"] for r in rev["runs"]], [r["metrics"] for r in reversed(res["runs"])])
        with self.assertRaises(ValueError):
            bt.run_sensitivity(inputs, [self.signal], self.cfg, [])


class ExtraCommands(unittest.TestCase):
    def setUp(self):
        import os
        import tempfile
        self.tmp = tempfile.mkdtemp()
        self.cs = R.extend(R.long_mit_candles(), [(175.0, 176.0, 161.5, 163.0), (174.0, 200.0, 173.0, 198.0)])
        self.data = os.path.join(self.tmp, "in")
        os.makedirs(self.data)
        with open(os.path.join(self.data, "SYN.csv"), "w") as fh:     # SYNTHETIC
            fh.write("date,open,high,low,close\n")
            for c in self.cs:
                fh.write("%s,%s,%s,%s,%s\n" % (c.start.date(), c.open, c.high, c.low, c.close))
        spec = dataclasses.asdict(model(statuses=(m.MANUAL_REVIEW,)))   # no calendar: G0 MANUAL
        del spec["monthly_trade_cap"], spec["max_open_positions"]
        self.mpath = self.write("model.json", spec)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def write(self, name, obj):
        import os
        path = os.path.join(self.tmp, name)
        with open(path, "w") as fh:
            json.dump(obj, fh)
        return path

    def call(self, argv):
        import argparse
        import contextlib
        import io
        p = argparse.ArgumentParser()
        sub = p.add_subparsers(dest="cmd")
        bt.add_commands(sub)
        args = p.parse_args(argv)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            code = args.func(args)
        return code, err.getvalue()

    def common(self, out):
        return ["--symbols", "SYN", "--csv-dir", self.data, "--price-adjustment", "NONE", "--risk-per-trade",
                "1000", "--out", out]

    def test_walk_forward_command(self):
        import os
        d = str(self.cs[-3].start.date())
        folds = self.write("folds.json", [{"in_start": d, "in_end": d, "out_start": str(self.cs[-2].start.date()),
                                           "out_end": str(self.cs[-1].start.date())}])
        out = os.path.join(self.tmp, "wf.json")
        self.assertEqual(self.call(["backtest-walk-forward", "--model", self.mpath, "--folds", folds]
                                   + self.common(out))[0], 0)
        with open(out) as fh:
            res = json.load(fh)
        self.assertEqual(len(res["folds"]), 1)
        self.assertIn(bt.MONTHLY_TRADE_CAP_NOT_ENFORCED, res["limitations"])
        bad = self.write("bad.json", [[d, d, d, d]])                  # IN not before OUT
        code, err = self.call(["backtest-walk-forward", "--model", self.mpath, "--folds", bad] + self.common(out))
        self.assertEqual(code, 2)
        self.assertIn("in_end < out_start", err)

    def test_sensitivity_command(self):
        import os
        spec2 = dataclasses.asdict(model(statuses=(m.MANUAL_REVIEW,), entry="ENTRY_MIN"))
        m2 = self.write("m2.json", spec2)
        out = os.path.join(self.tmp, "sens.json")
        d = str(self.cs[-3].start.date())
        argv = ["backtest-sensitivity", "--models", m2, self.mpath, "--start", d, "--end", d] + self.common(out)
        self.assertEqual(self.call(argv)[0], 0)
        with open(out) as fh:
            res = json.load(fh)
        self.assertEqual([r["model"]["entry"] for r in res["runs"]], ["ENTRY_MIN", "ENTRY_MAX"])
        self.assertEqual(find_keys(res, ("best", "rank")), [])
        spec2.pop("same_bar")
        self.write("m2.json", spec2)
        code, err = self.call(argv)
        self.assertEqual(code, 2)
        self.assertIn("same_bar", err)



class CapAuditRegressions(unittest.TestCase):
    """Rulebook audit 2026-11-02: the cap's counting basis and a cap above RB 2392's
    maximum of 10 are recorded limitations, never silent."""

    def test_counting_basis_recorded(self):
        lim = bt._limitations(model(monthly_trade_cap=10), None)
        self.assertIn(bt.MONTHLY_CAP_COUNTED_AT_FILL, lim)
        self.assertNotIn(bt.MONTHLY_CAP_ABOVE_RULEBOOK, lim)

    def test_cap_above_ten_is_labelled(self):
        self.assertIn(bt.MONTHLY_CAP_ABOVE_RULEBOOK, bt._limitations(model(monthly_trade_cap=11), None))

    def test_concurrency_is_not_cited_as_a_rule(self):
        src = bt._portfolio_rules(model())["sources"]
        self.assertEqual(src["max_open_positions"], ["user parameter (not a Rulebook rule)"])

if __name__ == "__main__":
    unittest.main()
