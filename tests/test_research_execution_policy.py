"""Owner execution policy (nse/research/execution_policy.py), D45 refusals and IST month
counting in the backtest. SYNTHETIC inputs; the cost figures below are made up for the test
and are not Zerodha's."""

import datetime
import json
import os
import shutil
import tempfile
import unittest

import _research as R
from nse.research import backtest as bt, charges, execution_policy as ep, models as m

D = datetime.date
SCHEDULE = ep.CostSchedule("TEST_BROKER", (
    ep.CostPeriod(D(2024, 1, 1), D(2024, 6, 30), "SYNTHETIC TEST SCHEDULE A", {"EQ_DELIVERY": 0.11}),
    ep.CostPeriod(D(2024, 7, 1), D(2024, 12, 31), "SYNTHETIC TEST SCHEDULE B", {"EQ_DELIVERY": 0.12}),
))


def grid(scenarios=(("ENTRY_MAX", "NORMAL_WIDE"),), start=D(2024, 2, 1), end=D(2024, 3, 1)):
    return ep.owner_grid(list(scenarios), (m.ACTIONABLE,), False, SCHEDULE, "EQ_DELIVERY", start, end)


class OwnerGrid(unittest.TestCase):
    def test_fixed_order_owner_values_and_no_selection(self):
        models, meta = grid((("ENTRY_MAX", "NORMAL_WIDE"), ("ENTRY_MIN", "EXCEPTIONAL_WIDE")))
        self.assertEqual(len(models), 2 * 3 * 2)
        self.assertEqual([lbl for lbl, _ in models[:6]],
                         ["ENTRY_MAX/NORMAL_WIDE/slip0.05/STOP_FIRST", "ENTRY_MAX/NORMAL_WIDE/slip0.05/EXCLUDE",
                          "ENTRY_MAX/NORMAL_WIDE/slip0.10/STOP_FIRST", "ENTRY_MAX/NORMAL_WIDE/slip0.10/EXCLUDE",
                          "ENTRY_MAX/NORMAL_WIDE/slip0.20/STOP_FIRST", "ENTRY_MAX/NORMAL_WIDE/slip0.20/EXCLUDE"])
        for _, x in models:
            self.assertEqual((x.gap_fill, x.entry_expiry_sessions, x.monthly_trade_cap, x.max_open_positions,
                              x.cost_pct_per_side), ("AT_OPEN", 10, 10, 10, 0.11))
        self.assertEqual(sorted(set(x.slippage_pct_per_side for _, x in models)), [0.05, 0.10, 0.20])
        self.assertEqual((meta["cost_source"], meta["flat_charges_modelled"]), ("SYNTHETIC TEST SCHEDULE A", False))
        self.assertNotIn("best", json.dumps(meta).lower())

    def test_scenarios_must_be_declared(self):
        with self.assertRaises(ValueError):
            grid(())
        with self.assertRaises(ValueError):
            grid((("ENTRY_MAX", "NORMAL_WIDE"), ("ENTRY_MAX", "NORMAL_WIDE")))


class CostSchedule(unittest.TestCase):
    def test_a_window_across_a_schedule_change_or_outside_it_is_refused(self):
        with self.assertRaisesRegex(ep.CostScheduleError, "split the window"):
            grid(start=D(2024, 6, 1), end=D(2024, 7, 15))
        with self.assertRaises(ep.CostScheduleError):
            grid(start=D(2023, 12, 1), end=D(2023, 12, 31))
        self.assertEqual(SCHEDULE.rate_for("EQ_DELIVERY", D(2024, 7, 1), D(2024, 12, 31))[0], 0.12)  # inclusive

    def test_an_unknown_instrument_has_no_default_rate(self):
        with self.assertRaisesRegex(ep.CostScheduleError, "no EQ_INTRADAY rate"):
            SCHEDULE.rate_for("EQ_INTRADAY", D(2024, 2, 1), D(2024, 2, 2))

    def test_invalid_schedules_are_refused(self):
        p = ep.CostPeriod(D(2024, 1, 1), D(2024, 6, 30), "S", {"EQ_DELIVERY": 0.1})
        for bad in (lambda: ep.CostSchedule("", (p,)), lambda: ep.CostSchedule("B", ()),
                    lambda: ep.CostSchedule("B", (p, ep.CostPeriod(D(2024, 6, 30), D(2024, 7, 30), "S", {}))),
                    lambda: ep.CostSchedule("B", (ep.CostPeriod(D(2024, 2, 1), D(2024, 1, 1), "S", {}),)),
                    lambda: ep.CostSchedule("B", (ep.CostPeriod(D(2024, 1, 1), D(2024, 2, 1), "", {}),)),
                    lambda: ep.CostSchedule("B", (ep.CostPeriod(D(2024, 1, 1), D(2024, 2, 1), "S",
                                                                {"EQ_DELIVERY": True}),))):
            with self.assertRaises(ep.CostScheduleError):
                bad()

    def test_load_from_file(self):
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "costs.json")
            with open(path, "w") as fh:
                json.dump({"broker": "TEST", "periods": [{"effective_from": "2024-01-01", "effective_to": "2024-12-31",
                                                          "source": "SYNTHETIC", "rates": {"EQ_DELIVERY": 0.1}}]}, fh)
            self.assertEqual(ep.load_cost_schedule(path).periods[0].rates, {"EQ_DELIVERY": 0.1})
            with open(path, "w") as fh:
                json.dump({"broker": "TEST", "periods": [{"effective_from": "2024-01-01"}]}, fh)
            with self.assertRaises(ep.CostScheduleError):
                ep.load_cost_schedule(path)
        finally:
            shutil.rmtree(tmp)


def trade(sym, fill, exit_=None):
    return {"symbol": sym, "zone_id": "Z", "signal_as_of": "2024-01-01T15:30:00", "fill_time": fill,
            "fill_price": 100.0, "exit_time": exit_, "exit_price": 110.0 if exit_ else None,
            "exit_reason": "TARGET" if exit_ else "OPEN_AT_END_OF_DATA", "r": 1.0 if exit_ else None,
            "trade_events": [], "zone_events": [], "assumption_events": []}


def model(**over):
    base = dict(entry="ENTRY_MAX", stop="NORMAL_WIDE", target="STRUCTURAL", statuses=(m.ACTIONABLE,),
                entry_expiry_sessions=10, cancel_if_target_first=False, gap_fill="AT_OPEN", same_bar="STOP_FIRST",
                cost_pct_per_side=0.0, slippage_pct_per_side=0.0)
    base.update(over)
    return bt.ExecutionModel(**base)


class IstMonth(unittest.TestCase):
    """D42, D46: the monthly cap counts the first fill time converted to IST."""

    def test_ist_month(self):
        utc = datetime.timezone.utc
        self.assertEqual(m.ist_month(datetime.datetime(2024, 1, 31, 18, 29, tzinfo=utc)), (2024, 1))   # 23:59 IST
        self.assertEqual(m.ist_month(datetime.datetime(2024, 1, 31, 18, 30, tzinfo=utc)), (2024, 2))   # 00:00 IST
        self.assertEqual(m.ist_month(datetime.datetime(2024, 1, 31, 23, 59)), (2024, 1))               # naive = IST

    def test_a_utc_fill_on_31_january_evening_counts_in_february_ist(self):
        # ten January fills in IST, then one at 2024-01-31T20:00Z (= 1 Feb 01:30 IST): it is
        # February's first trade, not January's eleventh
        jan = [trade("J%02d" % n, "2024-01-%02dT15:30:00+05:30" % (2 + n), "2024-01-%02dT15:30:00+05:30" % (2 + n))
               for n in range(10)]
        late = trade("LATE", "2024-01-31T20:00:00+00:00", "2024-01-31T21:00:00+00:00")
        out = bt.apply_portfolio_rules(jan + [late], model())
        self.assertEqual(out[-1]["exit_reason"], "TARGET")
        early = trade("EARLY", "2024-01-31T18:00:00+00:00", "2024-01-31T18:10:00+00:00")   # 23:30 IST: January
        out = bt.apply_portfolio_rules([dict(t) for t in jan] + [early], model())
        self.assertEqual((out[-1]["exit_reason"], out[-1]["not_traded"]["fill_month"]),
                         (bt.NOT_TRADED_MONTHLY_CAP, "2024-01"))

    def test_closing_a_position_frees_a_slot_but_not_a_monthly_trade(self):
        ts = ["2024-03-%02dT15:30:00" % d for d in range(1, 13)]
        trades = [trade("S%02d" % n, ts[n], ts[n]) for n in range(11)]    # each closes on its fill bar...
        trades = [dict(t, exit_time="2024-03-%02dT15:30:00" % (2 + n)) for n, t in enumerate(trades)]  # ...next day
        out = bt.apply_portfolio_rules(trades, model())
        self.assertEqual([t["exit_reason"] for t in out[:10]], ["TARGET"] * 10)
        self.assertEqual(out[10]["exit_reason"], bt.NOT_TRADED_MONTHLY_CAP)      # concurrency was free


class WalkForwardPooledCap(unittest.TestCase):
    """QA 2026-11-08: OUT windows that split one IST month share its 10-trade cap when pooled.
    Unit level: _segment is patched to return known trades (no real fold run)."""

    def test_two_folds_in_one_month_cannot_pool_more_than_ten_trades(self):
        from unittest import mock
        dt = datetime.datetime
        first = [dict(trade("A%02d" % n, "2024-03-%02dT15:30:00" % (1 + n), "2024-03-%02dT15:30:00" % (1 + n)),
                      zone_id="a%d" % n) for n in range(10)]
        second = [dict(trade("B%02d" % n, "2024-03-%02dT15:30:00" % (16 + n), "2024-03-%02dT15:30:00" % (16 + n)),
                       zone_id="b%d" % n) for n in range(10)]
        segs = iter([{"trades": []}, {"trades": first}, {"trades": []}, {"trades": second}])
        folds = [(dt(2024, 2, 1), dt(2024, 2, 28), dt(2024, 3, 1), dt(2024, 3, 15)),
                 (dt(2024, 2, 1), dt(2024, 2, 29), dt(2024, 3, 16), dt(2024, 3, 31))]
        cfg = mock.Mock(calendar=R.WeekdayCalendar())
        with mock.patch.object(bt, "_segment", side_effect=lambda *a, **k: next(segs)):
            res = bt.run_walk_forward([], folds, cfg, model())
        self.assertEqual(res["pooled_out"]["signals"], 20)
        self.assertEqual(res["pooled_out"]["metrics"]["closed_trades"], 10)
        self.assertEqual([t["exit_reason"] for t in second], ["TARGET"] * 10)   # per-fold records untouched


class ShortenedCalendar(R.WeekdayCalendar):
    """Weekday fixture plus declared session types (not an NSE calendar)."""

    def __init__(self, shortened=(), muhurat=()):
        super().__init__(closed=list(shortened) + list(muhurat))
        self.shortened, self.muhurat = set(shortened), set(muhurat)

    def session_type(self, d):
        if d in self.shortened:
            return "EXCLUDED_SHORTENED"
        if d in self.muhurat:
            return "EXCLUDED_MUHURAT"
        return "NORMAL" if self.is_trading_day(d) else "HOLIDAY"


class D40TwoWindowSessions(unittest.TestCase):
    """D40 (evidence resolution 2026-11-08): 2 Mar and 18 May 2024 were two-window primary/DR
    sessions. One trading date for expiry; their daily bar spans the break, so it never
    fills or exits a trade (D30); its high/low only show that nothing could have happened."""
    T0 = datetime.datetime(2025, 1, 3, 15, 30)
    LEVELS = (100.0, 95.0, 110.0)

    def bars(self, rows):
        return [R.candle(d, *r) for d, r in zip(R.weekdays(D(2025, 1, 6), len(rows)), rows)]

    def sim(self, rows, shortened_index, expiry=10, muhurat=False):
        cs = self.bars(rows)
        d = cs[shortened_index].start.date()
        cal = ShortenedCalendar(muhurat=[d]) if muhurat else ShortenedCalendar(shortened=[d])
        return bt.simulate(self.LEVELS, cs, self.T0, model(entry_expiry_sessions=expiry), calendar=cal)

    def test_an_untouched_two_window_session_counts_toward_expiry(self):
        # two sessions allowed: day 1 no fill, day 2 the two-window session (no touch) -> EXPIRED,
        # although day 3 would have filled
        r = self.sim([(104, 105, 101, 103), (104, 105, 102, 103), (101, 102, 99, 100)], 1, expiry=2)
        self.assertEqual(r["exit_reason"], "EXPIRED")
        self.assertIsNone(r["fill_time"])

    def test_a_two_window_session_reaching_the_entry_ends_the_record(self):
        r = self.sim([(104, 105, 101, 103), (101, 102, 99, 100), (101, 112, 100, 111)], 1)
        self.assertEqual((r["exit_reason"], r["fill_time"]), (bt.DATA_EXCLUDED_SESSION, None))

    def test_an_open_position_carries_over_an_untouched_two_window_session(self):
        r = self.sim([(101, 102, 99, 100), (101, 104, 97, 103), (104, 112, 103, 111)], 1)
        self.assertEqual((r["exit_reason"], r["exit_price"]), ("TARGET", 110.0))
        self.assertTrue(r["exit_time"].startswith(str(R.weekdays(D(2025, 1, 6), 3)[2])))

    def test_an_open_position_touching_a_level_on_a_two_window_session_ends_the_record(self):
        r = self.sim([(101, 102, 99, 100), (99, 100, 94, 96), (96, 112, 95, 111)], 1)
        self.assertEqual((r["exit_reason"], r["exit_price"]), (bt.DATA_EXCLUDED_SESSION, None))
        self.assertIsNone(bt.r_multiple(r, model()))

    def test_a_missing_bar_on_a_two_window_session_is_a_missing_session(self):
        cs = self.bars([(104, 105, 101, 103), (104, 105, 102, 103), (101, 102, 99, 100)])
        cal = ShortenedCalendar(shortened=[cs[1].start.date()])
        r = bt.simulate(self.LEVELS, [cs[0], cs[2]], self.T0, model(), calendar=cal)
        self.assertEqual(r["exit_reason"], bt.DATA_MISSING_SESSION)

    def test_a_muhurat_session_still_ends_the_record(self):
        r = self.sim([(104, 105, 101, 103), (104, 105, 102, 103), (101, 102, 99, 100)], 1, muhurat=True)
        self.assertEqual(r["exit_reason"], bt.DATA_EXCLUDED_SESSION)

    def test_revalidation_is_checked_before_a_two_window_session(self):
        # QA 2026-11-08: a setup already invalid is CANCELLED_SETUP_INVALID, not a data stop
        cs = self.bars([(104, 105, 101, 103), (101, 102, 99, 100), (101, 102, 99, 100)])
        cal = ShortenedCalendar(shortened=[cs[1].start.date()])
        r = bt.simulate(self.LEVELS, cs, self.T0, model(), calendar=cal,
                        revalidation=[(cs[0].end, False, "ZONE_NO_LONGER_A_CANDIDATE")])
        self.assertEqual(r["exit_reason"], bt.CANCELLED_SETUP_INVALID)

    def test_a_carried_over_two_window_session_records_the_skipped_zone_check(self):
        # QA 2026-11-08: the close beyond the DL on the two-window day is not applied as an
        # invalidation (the bar is not a candle, D30) but it is recorded, never silent
        cs = self.bars([(101, 102, 99, 100), (101, 101.5, 96, 96.5), (104, 112, 103, 111)])
        cal = ShortenedCalendar(shortened=[cs[1].start.date()])
        r = bt.simulate(self.LEVELS, cs, self.T0, model(), calendar=cal,
                        zone={"zone_id": "z", "timeframe": "D", "side": "demand", "distal": 97.0})
        self.assertEqual(r["exit_reason"], "TARGET")
        [ev] = [e for e in r["assumption_events"] if e["type"] == "SHORTENED_SESSION_CARRIED_OVER"]
        self.assertEqual((ev["zone_check"], ev["close_beyond_dl"]), ("NOT_APPLIED", True))

    def test_the_real_calendar_classifies_the_three_2024_saturdays(self):
        from nse.research.deps import calendar as cal_mod
        cal = cal_mod.NseCalendar.load(os.path.join(R.ROOT, "nse", "data", "calendar"))
        self.assertTrue(cal.is_trading_day(D(2024, 1, 20)))                       # NSE/MSD/60340
        self.assertEqual(cal.session_type(D(2024, 1, 20)), "NORMAL_SPECIAL")
        for d in (D(2024, 3, 2), D(2024, 5, 18)):                                  # NSE/MSD/60677, 61893
            self.assertEqual(cal.session_type(d), "EXCLUDED_SHORTENED", d)
            self.assertFalse(cal.is_trading_day(d), d)


class D45Refusals(unittest.TestCase):
    def test_limits_above_the_owner_policy_are_refused_not_labelled(self):
        for bad in (dict(max_open_positions=11), dict(max_open_positions=None), dict(monthly_trade_cap=11),
                    dict(monthly_trade_cap=None), dict(entry_expiry_sessions=11)):
            with self.assertRaisesRegex(ValueError, "owner limit|None", msg=bad):
                model(**bad)

    def test_stricter_limits_are_allowed(self):
        x = model(max_open_positions=5, monthly_trade_cap=3, entry_expiry_sessions=5)
        self.assertIn(bt.ENTRY_EXPIRY_NOT_OWNER_POLICY, bt._limitations(x, None, R.WeekdayCalendar()))

    def test_a_backtest_without_a_calendar_is_refused(self):
        from nse.research import scanner
        cs = R.long_mit_candles()
        cfg = scanner.ScanConfig(as_of=cs[-1].end, calendar=None, risk_per_trade=1000.0)
        with self.assertRaisesRegex(ValueError, "calendar"):
            bt.run([R.daily_input("SYN", cs)], [cs[-1].end], cfg, model())
        with self.assertRaisesRegex(ValueError, "calendar"):
            bt.run_sensitivity([R.daily_input("SYN", cs)], [cs[-1].end], cfg, [model()])


class ItemisedCharges(unittest.TestCase):
    """Synthetic rates only. The module stores none of its own."""

    def schedule(self, **extra):
        components = [
            {"code": "BROKERAGE", "BUY": {"model": "FLAT_RUPEES", "rupees": 20}, "SELL": {"model": "NONE"}},
            {"code": "STT", "BUY": {"model": "BPS_OF_VALUE", "bps": 10}, "SELL": {"model": "BPS_OF_VALUE", "bps": 10}},
            {"code": "EXCHANGE", "BUY": {"model": "NONE"}, "SELL": {"model": "NONE"}},
            {"code": "SEBI", "BUY": {"model": "NONE"}, "SELL": {"model": "NONE"}},
            {"code": "STAMP", "BUY": {"model": "FLAT_RUPEES", "rupees": 1}, "SELL": {"model": "NONE"}},
            {"code": "GST", "model": "PERCENT_OF_COMPONENTS", "percent": 18, "of": ["BROKERAGE", "EXCHANGE", "SEBI"]},
            {"code": "OTHER", "BUY": {"model": "NONE"}, "SELL": {"model": "NONE"}},
        ]
        body = {
            "source": "SYNTHETIC schedule for the test. Not a statutory or broker tariff.",
            "effective_from": "2024-01-01",
            "effective_to": "2024-12-31",
            "components": components,
        }
        body.update(extra)
        return body

    def test_buy_and_sell_differ_and_gst_is_not_charged_twice(self):
        buy = charges.quote(self.schedule(), side="BUY", quantity=1, price=100, trade_date=D(2024, 2, 1))
        sell = charges.quote(self.schedule(), side="SELL", quantity=1, price=100, trade_date=D(2024, 2, 1))
        by_code = {line["component"]: line["amount_paise"] for line in buy["lines"]}
        self.assertEqual(by_code["BROKERAGE"], 2000)
        self.assertEqual(by_code["GST"], 360)
        self.assertEqual(by_code["STAMP"], 100)
        self.assertEqual(by_code["STT"], 10)
        self.assertEqual(buy["total_paise"], 2000 + 360 + 100 + 10)
        sell_codes = {line["component"]: line["amount_paise"] for line in sell["lines"]}
        self.assertEqual(sell_codes["BROKERAGE"], 0)
        self.assertEqual(sell_codes["STAMP"], 0)
        self.assertEqual(sell_codes["GST"], 0)
        self.assertEqual(sell_codes["STT"], 10)
        self.assertEqual(sell["total_paise"], 10)
        self.assertEqual(buy["state"], "ESTIMATED")

    def test_half_up_paise_and_a_missing_schedule_is_refused(self):
        odd = self.schedule()
        odd["components"] = [{"code": "STT", "BUY": {"model": "BPS_OF_VALUE", "bps": 1},
                              "SELL": {"model": "NONE"}}]
        quoted = charges.quote(odd, side="BUY", quantity=1, price=50, trade_date=D(2024, 2, 1))
        self.assertEqual(quoted["lines"][0]["amount_paise"], 1)
        self.assertEqual(quoted["coverage"], "PARTIAL")
        with self.assertRaises(charges.ChargeScheduleError):
            charges.quote(None, side="BUY", quantity=1, price=1, trade_date=D(2024, 2, 1))
        with self.assertRaises(charges.ChargeScheduleError):
            charges.quote(self.schedule(effective_to="2024-01-31"), side="BUY", quantity=1, price=1,
                          trade_date=D(2024, 2, 1))
        bad = self.schedule()
        bad["components"] = [{"code": "GST", "model": "PERCENT_OF_COMPONENTS", "percent": 18, "of": ["GST"]}]
        with self.assertRaisesRegex(charges.ChargeScheduleError, "itself"):
            charges.quote(bad, side="BUY", quantity=1, price=1, trade_date=D(2024, 2, 1))

    def test_the_module_does_not_embed_a_tariff(self):
        with open(charges.__file__, encoding="utf-8") as handle:
            text = handle.read().upper()
        self.assertNotIn("ZERODHA", text)
        self.assertNotIn("NSE INDIA", text)


if __name__ == "__main__":
    unittest.main()
