"""nse/mtf-freshness tests. All candles are SYNTHETIC (not market data).

Most scenarios use an explicit trading-day calendar. Weeks W0-W4 have one session each
(Mondays), so each weekly candle equals that day's candle and the weekly zone is the
same DBR the Zone Engine tests use: PL 95.2, exceptional DL 94.0, created in W3 and
scored 7/7 after W4. Week W5 (10-14 Feb 2025) has five sessions for the intraperiod
cases. Calendars here are test fixtures, not a validated NSE calendar.
"""

import datetime
import os
import random
import unittest

from _load import load

mtf = load(os.path.join("nse", "mtf-freshness"), "mtf_freshness")
TC = mtf.TimedCandle
D = datetime.date
DT = datetime.datetime

MONDAYS = [D(2025, 1, 6) + datetime.timedelta(weeks=i) for i in range(5)]   # W0..W4
W5 = [D(2025, 2, 10) + datetime.timedelta(days=i) for i in range(5)]       # Mon..Fri
W6_MON = D(2025, 2, 17)
DBR_WEEKS = [(100, 101, 99, 100), (100, 100.5, 94, 95), (95, 96, 94.5, 95.2),
             (95.5, 102, 95.3, 101.5), (101.5, 105, 101, 104.5)]
CALM = {0: (104.5, 105, 103, 104), 1: (104, 104.5, 102, 103), 2: (103, 104, 101, 102),
        3: (102, 103, 101, 102.5), 4: (102.5, 103.5, 102, 103)}
KEY = "W:demand-2-3"


class Cal(object):
    def __init__(self, days):
        self.days = set(days)

    def is_trading_day(self, d):
        return d in self.days


def day(d, o, h, l, c):
    return TC(DT.combine(d, datetime.time(9, 15)), DT.combine(d, datetime.time(15, 30)), o, h, l, c)


def close(d):
    return DT.combine(d, datetime.time(15, 30))


def weekly_case(w5=None, missing=(), extra=()):
    """Monday-only W0-W4, then W5 Mon-Fri (rows overridable), then optional extra days."""
    rows = dict(CALM)
    rows.update(w5 or {})
    cs = [day(d, *r) for d, r in zip(MONDAYS, DBR_WEEKS)]
    cs += [day(W5[i], *rows[i]) for i in range(5) if i not in missing]
    cs += [day(d, *r) for d, r in extra]
    cal = Cal(MONDAYS + W5 + [d for d, _ in extra])
    return cs, cal


def mirror(cs, k=200.0):
    return [TC(c.start, c.end, k - c.open, k - c.low, k - c.high, k - c.close, c.complete) for c in cs]


class MidweekTouches(unittest.TestCase):
    def test_weekly_zone_tested_by_wednesday_not_by_the_weekly_candle(self):
        cs, cal = weekly_case({2: (103, 103.5, 95.0, 100)})          # Wednesday low 95.0 <= PL 95.2
        tue = mtf.replay(cs, "D", htf=("W",), as_of=close(W5[1]), calendar=cal)
        self.assertEqual(tue.zones[KEY].status, mtf.FRESH)
        self.assertTrue(tue.zones[KEY].usable_as_fresh_context)
        wed = mtf.replay(cs, "D", htf=("W",), as_of=close(W5[2]), calendar=cal)
        z = wed.zones[KEY]
        self.assertEqual((z.status, z.first_touch_at, z.base_touch_count), (mtf.TESTED, close(W5[2]), 1))
        self.assertEqual(z.htf_test_count, 0)                         # Pine view: week not finished
        self.assertEqual(z.engine_status, "ZONE_ELIGIBLE")            # the engine alone still says eligible
        kept, blocked = wed.eligible_after_overlay("W")
        self.assertEqual(kept, [])
        self.assertEqual([a.zone.id for a, _ in blocked], ["demand-2-3"])
        self.assertIn(mtf.OVERLAY_NOT_FRESH, blocked[0][1])
        fri = mtf.replay(cs, "D", htf=("W",), as_of=close(W5[4]), calendar=cal)
        self.assertEqual((fri.zones[KEY].status, fri.zones[KEY].htf_test_count), (mtf.TESTED, 1))

    def test_daily_base_events_carry_day_level_precision(self):
        cs, cal = weekly_case({2: (103, 103.5, 95.0, 100)})
        e = mtf.replay(cs, "D", htf=("W",), as_of=close(W5[2]), calendar=cal).zones[KEY].events[0]
        self.assertEqual((e.kind, e.source_tf, e.time, e.candle_start, e.htf_period_key),
                         (mtf.PL_TOUCH, "D", close(W5[2]), DT(2025, 2, 12, 9, 15), "2025-W07"))

    def test_monthly_zone_tested_mid_month(self):
        months = [D(2025, 1, 6), D(2025, 2, 3), D(2025, 3, 3), D(2025, 4, 7), D(2025, 5, 5)]
        june = [D(2025, 6, 2) + datetime.timedelta(days=i) for i in range(5)]
        rows = {0: (104.5, 105, 103, 104), 1: (104, 104.5, 102, 103), 2: (103, 103.5, 95.0, 100),
                3: (100, 102, 99.5, 101), 4: (101, 103, 100.5, 102)}
        cs = [day(d, *r) for d, r in zip(months, DBR_WEEKS)] + [day(june[i], *rows[i]) for i in range(5)]
        cal = Cal(months + june)
        key = "M:demand-2-3"
        before = mtf.replay(cs, "D", htf=("M",), as_of=close(june[1]), calendar=cal)
        self.assertEqual(before.zones[key].status, mtf.FRESH)
        mid = mtf.replay(cs, "D", htf=("M",), as_of=close(june[2]), calendar=cal)
        self.assertEqual((mid.zones[key].status, mid.zones[key].htf_test_count), (mtf.TESTED, 0))
        end = mtf.replay(cs, "D", htf=("M",), as_of=close(june[4]), calendar=cal)
        self.assertEqual(end.zones[key].htf_test_count, 1)


class GapsAndCrossings(unittest.TestCase):
    def snap(self, wed, as_of_day=4):
        cs, cal = weekly_case({2: wed})
        return mtf.replay(cs, "D", htf=("W",), as_of=close(W5[as_of_day]), calendar=cal).zones[KEY]

    def test_near_miss_stays_fresh(self):
        z = self.snap((103, 103.5, 95.25, 100))
        self.assertEqual((z.status, z.events), (mtf.FRESH, []))

    def test_gap_through_counts_as_a_touch(self):
        z = self.snap((94.8, 96, 94.5, 95.8))                          # opens below PL after a 102 close
        self.assertEqual(z.status, mtf.TESTED)
        self.assertIsNone(z.dl_touched_at)

    def test_candle_crossing_the_whole_zone_is_tested_not_invalidated(self):
        z = self.snap((100, 101, 93.5, 96))                            # low below DL 94, close back inside
        self.assertEqual(z.status, mtf.TESTED)
        self.assertEqual(z.dl_touched_at, close(W5[2]))
        self.assertIsNone(z.invalidated_period_end)
        self.assertNotIn(mtf.BASE_CLOSE_BEYOND_DL, [e.kind for e in z.events])


class DistalLine(unittest.TestCase):
    RECOVER = {2: (103, 103.5, 93, 93.5), 3: (93.5, 99, 93.4, 98.5), 4: (98.5, 100, 98, 99)}
    BREAK = {2: (103, 103.5, 93, 93.5), 3: (93.5, 96, 93.4, 95), 4: (95, 95.5, 93.6, 93.8)}

    def test_base_close_beyond_dl_is_manual_until_the_week_closes_back_inside(self):
        cs, cal = weekly_case(self.RECOVER)
        wed = mtf.replay(cs, "D", htf=("W",), as_of=close(W5[2]), calendar=cal).zones[KEY]
        self.assertEqual(wed.status, mtf.BASE_CLOSE_BEYOND_DL_PENDING)
        self.assertIn(mtf.BASE_CLOSE_BEYOND_DL, wed.manual_review)
        self.assertFalse(wed.usable_as_fresh_context)
        fri = mtf.replay(cs, "D", htf=("W",), as_of=close(W5[4]), calendar=cal).zones[KEY]
        self.assertEqual(fri.status, mtf.TESTED)                       # weekly close 99 > DL 94 (A1)
        self.assertIsNone(fri.invalidated_period_end)
        self.assertIn(mtf.BASE_CLOSE_BEYOND_DL_RESOLVED, fri.manual_review)

    def test_weekly_close_beyond_dl_invalidates_permanently(self):
        cs, cal = weekly_case(self.BREAK, extra=[(W6_MON, (93.8, 110, 93.7, 109))])
        thu = mtf.replay(cs, "D", htf=("W",), as_of=close(W5[3]), calendar=cal).zones[KEY]
        self.assertEqual(thu.status, mtf.BASE_CLOSE_BEYOND_DL_PENDING)
        fri = mtf.replay(cs, "D", htf=("W",), as_of=close(W5[4]), calendar=cal).zones[KEY]
        self.assertEqual((fri.status, fri.invalidated_period_end), (mtf.INVALIDATED, close(W5[4])))
        later = mtf.replay(cs, "D", htf=("W",), as_of=close(W6_MON), calendar=cal).zones[KEY]
        self.assertEqual(later.status, mtf.INVALIDATED)
        self.assertTrue(all(e.time <= close(W5[4]) for e in later.events))


class CreationAndCompletion(unittest.TestCase):
    W3 = [D(2025, 1, 27) + datetime.timedelta(days=i) for i in range(5)]
    LEGOUT_DAYS = [(95.5, 96, 95.0, 95.8), (95.8, 98, 95.7, 97.9), (97.9, 100, 97.8, 99.9),
                   (99.9, 101, 99.5, 100.8), (100.8, 102, 100.5, 101.5)]   # weekly 95.5/102/95.0/101.5

    def case(self):
        cs = [day(d, *r) for d, r in zip(MONDAYS[:3], DBR_WEEKS[:3])]
        cs += [day(d, *r) for d, r in zip(self.W3, self.LEGOUT_DAYS)]
        cs += [day(MONDAYS[4], *DBR_WEEKS[4])]
        return cs, Cal(MONDAYS[:3] + self.W3 + [MONDAYS[4]])

    def test_touch_inside_the_creation_week_is_not_a_test(self):
        cs, cal = self.case()                                          # Monday of the leg-out week dips to 95.0
        z = mtf.replay(cs, "D", htf=("W",), as_of=close(MONDAYS[4]), calendar=cal).zones[KEY]
        self.assertEqual((z.status, z.events, z.creation_period_end), (mtf.FRESH, [], close(self.W3[4])))

    def test_unfinished_week_cannot_create_a_zone(self):
        cs, cal = self.case()
        wed = mtf.replay(cs, "D", htf=("W",), as_of=close(self.W3[2]), calendar=cal)
        self.assertEqual(wed.zones, {})
        self.assertEqual(wed.series["W"].in_progress_period, "2025-W05")
        fri = mtf.replay(cs, "D", htf=("W",), as_of=close(self.W3[4]), calendar=cal)
        self.assertIn(KEY, fri.zones)
        self.assertEqual(fri.zones[KEY].known_at, close(self.W3[4]))


class Holidays(unittest.TestCase):
    def case(self):
        return weekly_case(missing=(4,), extra=[(W6_MON, (103, 104, 102.5, 103.5))])

    def test_calendar_completes_a_holiday_week_on_its_last_session(self):
        cs, _ = self.case()
        cal = Cal(MONDAYS + W5[:4] + [W6_MON])                         # Friday 14 Feb is a holiday
        s = mtf.replay(cs, "D", htf=("W",), as_of=close(W5[3]), calendar=cal)
        self.assertEqual(s.series["W"].candles[-1].period_key, "2025-W07")
        self.assertEqual(s.series["W"].candles[-1].known_at, close(W5[3]))
        self.assertEqual(s.data_gaps, [])
        self.assertTrue(s.calendar_validated)

    def test_without_a_calendar_completion_waits_for_the_next_week(self):
        cs, _ = self.case()
        thu = mtf.replay(cs, "D", htf=("W",), as_of=close(W5[3]))
        self.assertEqual(thu.series["W"].in_progress_period, "2025-W07")
        self.assertIn(mtf.CALENDAR_UNVALIDATED, thu.limitations)
        mon = mtf.replay(cs, "D", htf=("W",), as_of=close(W6_MON))
        w07 = [h for h in mon.series["W"].candles if h.period_key == "2025-W07"][0]
        self.assertEqual(w07.known_at, close(W6_MON))                  # one session late, never early
        self.assertIsNone(w07.sessions_expected)
        fri_gap = [g for g in mon.data_gaps if g.date == W5[4]]
        self.assertEqual([(g.kind, g.verified) for g in fri_gap], [("MISSING_SESSION", False)])


class DataGaps(unittest.TestCase):
    def test_missing_session_makes_an_untouched_zone_unknown(self):
        cs, cal = weekly_case(missing=(2,))                            # Wednesday is a trading day, no data
        s = mtf.replay(cs, "D", htf=("W",), as_of=close(W5[4]), calendar=cal)
        z = s.zones[KEY]
        self.assertEqual(z.status, mtf.UNKNOWN_DATA_GAP)
        self.assertFalse(z.usable_as_fresh_context)
        self.assertIn("MISSING_SESSION 2025-02-12", z.reasons)
        self.assertEqual(s.series["W"].truncated_at, "2025-W07")
        self.assertIn(mtf.HTF_SERIES_TRUNCATED_AT_GAP, s.series["W"].reasons)

    def test_touch_before_the_gap_is_still_a_test(self):
        cs, cal = weekly_case({1: (104, 104.5, 95.0, 100)}, missing=(2,))
        z = mtf.replay(cs, "D", htf=("W",), as_of=close(W5[4]), calendar=cal).zones[KEY]
        self.assertEqual(z.status, mtf.TESTED)

    def test_partial_intraday_session_is_a_verified_gap(self):
        mon = D(2025, 1, 6)
        cs = [TC(DT(2025, 1, 6, 9, 15), DT(2025, 1, 6, 10, 30), 100, 101, 99, 100),
              TC(DT(2025, 1, 6, 11, 45), DT(2025, 1, 6, 13, 0), 100, 101, 99, 100)]   # 10:30-11:45 missing
        s = mtf.replay(cs, "75m", htf=("D",), as_of=DT(2025, 1, 6, 16, 0), calendar=Cal([mon]))
        self.assertEqual([(g.date, g.kind, g.verified) for g in s.data_gaps], [(mon, "PARTIAL_SESSION", True)])

    def test_partial_first_period_needs_review(self):
        wk0 = [D(2025, 1, 8), D(2025, 1, 9), D(2025, 1, 10)]          # data starts on a Wednesday
        rows = [(100, 100.5, 97, 98), (98, 99, 95, 96), (96, 97, 94, 95)]   # weekly leg-in 100/100.5/94/95
        cs = [day(d, *r) for d, r in zip(wk0, rows)]
        cs += [day(d, *r) for d, r in zip(MONDAYS[1:], DBR_WEEKS[2:])]
        cal = Cal([D(2025, 1, 6), D(2025, 1, 7)] + wk0 + MONDAYS[1:])
        s = mtf.replay(cs, "D", htf=("W",), as_of=close(MONDAYS[4]), calendar=cal)
        self.assertTrue(s.series["W"].candles[0].partial_first_period)
        z = s.zones["W:demand-1-2"]
        self.assertIn(mtf.PARTIAL_FIRST_PERIOD, z.manual_review)
        self.assertFalse(z.usable_as_fresh_context)
        self.assertNotEqual(z.status, mtf.FRESH)                       # (3 Feb is also a gap here)


class SupplyMirror(unittest.TestCase):
    SKEY = "W:supply-2-3"

    def test_midweek_touch(self):
        cs, cal = weekly_case({2: (103, 103.5, 95.0, 100)})
        cs = mirror(cs)
        z = mtf.replay(cs, "D", htf=("W",), as_of=close(W5[2]), calendar=cal).zones[self.SKEY]
        self.assertAlmostEqual(z.proximal, 104.8)
        self.assertEqual((z.status, z.htf_test_count), (mtf.TESTED, 0))

    def test_close_beyond_dl_then_recovery(self):
        cs, cal = weekly_case(DistalLine.RECOVER)
        cs = mirror(cs)
        wed = mtf.replay(cs, "D", htf=("W",), as_of=close(W5[2]), calendar=cal).zones[self.SKEY]
        self.assertEqual(wed.status, mtf.BASE_CLOSE_BEYOND_DL_PENDING)
        fri = mtf.replay(cs, "D", htf=("W",), as_of=close(W5[4]), calendar=cal).zones[self.SKEY]
        self.assertEqual(fri.status, mtf.TESTED)

    def test_weekly_close_beyond_dl_invalidates(self):
        cs, cal = weekly_case(DistalLine.BREAK)
        z = mtf.replay(mirror(cs), "D", htf=("W",), as_of=close(W5[4]), calendar=cal).zones[self.SKEY]
        self.assertEqual(z.status, mtf.INVALIDATED)


def split_day(d, o, h, l, c):
    """Five 75-minute candles whose daily OHLC is exactly (o, h, l, c)."""
    t = [DT.combine(d, datetime.time(9, 15)) + datetime.timedelta(minutes=75 * i) for i in range(6)]
    rows = [(o, max(o, l), l, l), (l, h, l, h), (h, h, c, c), (c, c, c, c), (c, c, c, c)]
    return [TC(t[i], t[i + 1], *rows[i]) for i in range(5)]


class WitIntraday(unittest.TestCase):
    DAYS = [D(2025, 1, 6) + datetime.timedelta(days=i) for i in range(5)]    # Mon..Fri
    NEXT_MON = D(2025, 1, 13)

    def case(self):
        cs = []
        for d, r in zip(self.DAYS, DBR_WEEKS):
            cs += split_day(d, *r)
        t = [DT(2025, 1, 13, 9, 15) + datetime.timedelta(minutes=75 * i) for i in range(6)]
        cs += [TC(t[0], t[1], 104.5, 105, 104, 104.2),
               TC(t[1], t[2], 104.2, 104.3, 95.0, 96)]                  # touches the daily PL 95.2
        return cs, Cal(self.DAYS + [self.NEXT_MON])

    def test_75m_base_tests_a_daily_zone_intraday_and_blocks_eligibility(self):
        cs, cal = self.case()
        before = mtf.replay(cs, "75m", htf=("D",), as_of=DT(2025, 1, 13, 10, 30), calendar=cal)
        kept, blocked = before.eligible_after_overlay("D")
        engine_ids = [a.zone.id for a in before.series["D"].engine.eligible]
        self.assertEqual([a.zone.id for a in kept], engine_ids)        # no touch: nothing removed
        self.assertEqual(engine_ids, ["demand-2-3"])
        after = mtf.replay(cs, "75m", htf=("D",), as_of=DT(2025, 1, 13, 11, 45), calendar=cal)
        z = after.zones["D:demand-2-3"]
        self.assertEqual((z.status, z.first_touch_at), (mtf.TESTED, DT(2025, 1, 13, 11, 45)))
        e = z.events[0]
        self.assertEqual((e.source_tf, e.candle_start), ("75m", DT(2025, 1, 13, 10, 30)))
        self.assertEqual([a.zone.id for a in after.series["D"].engine.eligible], ["demand-2-3"])
        kept, blocked = after.eligible_after_overlay("D")
        self.assertEqual(kept, [])                                      # tested zone never eligible
        self.assertEqual([a.zone.id for a, _ in blocked], ["demand-2-3"])
        self.assertEqual(after.data_gaps, [])                           # Monday is still in progress


class ReplayProperties(unittest.TestCase):
    def test_as_of_equals_prefix_at_every_cut(self):
        cs, cal = weekly_case(DistalLine.BREAK, extra=[(W6_MON, (93.8, 110, 93.7, 109))])
        cuts = sorted(set(c.end for c in cs)) + [DT(2025, 2, 12, 12, 0)]
        for t in cuts:
            full = mtf.replay(cs, "D", htf=("W", "M"), as_of=t, calendar=cal).to_dict()
            prefix = mtf.replay([c for c in cs if c.end <= t], "D", htf=("W", "M"), as_of=t,
                                calendar=cal).to_dict()
            self.assertEqual(full, prefix, t)

    def test_replay_is_deterministic(self):
        cs, cal = weekly_case({2: (103, 103.5, 95.0, 100)})
        a = mtf.replay(cs, "D", htf=("W", "M"), calendar=cal).to_dict()
        b = mtf.replay(list(cs), "D", htf=("W", "M"), calendar=cal).to_dict()
        self.assertEqual(a, b)

    def test_tested_and_invalidated_are_monotonic(self):
        rnd = random.Random(20261026)
        start = D(2024, 1, 1)
        days = [start + datetime.timedelta(days=i) for i in range(260)]
        days = [d for d in days if d.weekday() < 5]
        cal = Cal(days)
        for _ in range(3):
            p, cs = 100.0, []
            for d in days:
                o = p
                c = o + rnd.uniform(-3, 3)
                cs.append(day(d, round(o, 2), round(max(o, c) + rnd.uniform(0, 2), 2),
                              round(min(o, c) - rnd.uniform(0, 2), 2), round(c, 2)))
                p = c
            seen_not_fresh, seen_invalid = set(), set()
            for d in days[20::3]:
                s = mtf.replay(cs, "D", htf=("W", "M"), as_of=close(d), calendar=cal)
                for key in seen_not_fresh:
                    self.assertIn(key, s.zones)
                    self.assertNotEqual(s.zones[key].status, mtf.FRESH, key)
                for key in seen_invalid:
                    self.assertEqual(s.zones[key].status, mtf.INVALIDATED, key)
                for key, z in s.zones.items():
                    if z.status != mtf.FRESH:
                        seen_not_fresh.add(key)
                    if z.status == mtf.INVALIDATED:
                        seen_invalid.add(key)
                for tf in ("W", "M"):
                    kept, _ = s.eligible_after_overlay(tf)
                    eng = s.series[tf].engine
                    engine_ids = set(a.zone.id for a in eng.eligible) if eng is not None else set()
                    self.assertLessEqual(set(a.zone.id for a in kept), engine_ids)   # only removes
                    for a in kept:
                        self.assertTrue(a.zone.is_demand)
                        self.assertEqual(s.zones["%s:%s" % (tf, a.zone.id)].status, mtf.FRESH)
            self.assertTrue(seen_not_fresh)


class Consistency(unittest.TestCase):
    def test_engine_touch_without_a_base_touch_raises(self):
        cs, cal = weekly_case()
        original = mtf._build_series

        def corrupt(*args, **kw):
            s = original(*args, **kw)
            if s.candles and len(s.candles) > 5:
                s.candles[5].low = 90.0                                 # not from the base data
            return s
        mtf._build_series = corrupt
        try:
            with self.assertRaises(RuntimeError):
                mtf.replay(cs, "D", htf=("W",), as_of=close(W5[4]), calendar=cal)
        finally:
            mtf._build_series = original


class InputValidation(unittest.TestCase):
    def test_refuses_bad_inputs(self):
        cs, cal = weekly_case()
        with self.assertRaises(ValueError):
            mtf.replay(cs, "60m", htf=("D",))                           # does not tile 375 minutes
        with self.assertRaises(ValueError):
            mtf.replay(cs, "D", htf=("4H",))                            # unknown timeframe (D over D is
                                                                        # allowed since the audit, DailyZones)
        aware = TC(DT(2025, 3, 3, 9, 15, tzinfo=datetime.timezone.utc),
                   DT(2025, 3, 3, 15, 30, tzinfo=datetime.timezone.utc), 1, 2, 0.5, 1.5)
        with self.assertRaises((ValueError, TypeError)):
            mtf.replay(cs + [aware], "D", htf=("W",))
        with self.assertRaises(ValueError):
            mtf.replay([TC(DT(2025, 1, 6, 9, 0), DT(2025, 1, 6, 10, 15), 1, 2, 0.5, 1.5)], "75m", htf=("D",))
        with self.assertRaises(ValueError):
            mtf.replay([cs[1], cs[0]], "D", htf=("W",))

    def test_trailing_incomplete_candle_is_ignored(self):
        cs, cal = weekly_case({2: (103, 103.5, 95.0, 100)})
        cs = [c for c in cs if c.start.date() <= W5[1]]
        cs.append(TC(DT(2025, 2, 12, 9, 15), DT(2025, 2, 12, 15, 30), 103, 103.5, 95.0, 100, complete=False))
        s = mtf.replay(cs, "D", htf=("W",), as_of=close(W5[2]), calendar=cal)
        self.assertEqual(s.ignored_incomplete, [close(W5[2])])
        self.assertEqual(s.zones[KEY].status, mtf.UNKNOWN_DATA_GAP)    # Wednesday has no completed data


class SessionCal(Cal):
    """A test calendar that also names excluded sessions, like nse_calendar.session_type."""

    def __init__(self, days, excluded):
        Cal.__init__(self, days)
        self.excluded = dict(excluded)

    def session_type(self, d):
        if d in self.excluded:
            return self.excluded[d]
        return "NORMAL" if d in self.days else ("WEEKEND" if d.weekday() >= 5 else "HOLIDAY")


FULL_WEEKS = [[D(2025, 1, 6) + datetime.timedelta(weeks=w, days=k) for k in range(5)] for w in range(6)]


def full_weeks_case(skip=()):
    """Six Mon-Fri weeks (identical days, so each weekly candle is the DBR row) plus the
    next Monday, for the no-calendar mode where every missing weekday is a gap."""
    rows = DBR_WEEKS + [CALM[0]]
    cs = [day(d, *r) for w, r in zip(FULL_WEEKS, rows) for d in w if d not in skip]
    return cs + [day(W6_MON, *CALM[0])]


class ExcludedSessions(unittest.TestCase):
    """H1 (Phase 1 audit): calendar-excluded or unclassifiable sessions never enter
    aggregation or the touch count, are recorded, and block fresh use where relevant."""

    def test_calendar_excluded_session_is_not_aggregated_or_counted(self):
        cs, _ = weekly_case({4: (103, 103.5, 95.0, 100)})              # Friday low 95.0 <= PL 95.2
        cal = SessionCal(MONDAYS + W5[:4], {W5[4]: "EXCLUDED_MUHURAT"})
        for side, data, key in (("demand", cs, KEY), ("supply", mirror(cs), "W:supply-2-3")):
            with self.subTest(side):
                s = mtf.replay(data, "D", htf=("W",), as_of=close(W5[4]), calendar=cal)
                z = s.zones[key]
                self.assertEqual([e.kind for e in z.events], [])
                self.assertEqual(s.series["W"].candles[-1].sessions_present, 4)
                self.assertEqual(z.status, "MANUAL_REVIEW")                # never reported FRESH
                self.assertIn("EXCLUDED_SESSION_TOUCH", z.manual_review)
                self.assertFalse(z.usable_as_fresh_context)
                self.assertEqual([(x.date, x.classification) for x in s.excluded_candles],
                                 [(W5[4], "EXCLUDED_MUHURAT")])
                self.assertEqual(s.data_gaps, [])

    def test_evening_intraday_candle_is_excluded_not_a_crash(self):
        sun = D(2025, 1, 12)                                            # a Sunday Muhurat-style session
        cs = []
        for d, r in zip(WitIntraday.DAYS, DBR_WEEKS):
            cs += split_day(d, *r)
        cs.append(TC(DT(2025, 1, 12, 18, 0), DT(2025, 1, 12, 19, 15), 104, 104.5, 95.0, 104))
        cs += split_day(WitIntraday.NEXT_MON, *CALM[0])
        as_of = close(WitIntraday.NEXT_MON)
        cal = SessionCal(WitIntraday.DAYS + [WitIntraday.NEXT_MON], {sun: "EXCLUDED_MUHURAT"})
        with_cal = mtf.replay(cs, "75m", htf=("D",), as_of=as_of, calendar=cal)
        z = with_cal.zones["D:demand-2-3"]
        self.assertEqual((z.status, z.events), ("MANUAL_REVIEW", []))
        self.assertIn("EXCLUDED_SESSION_TOUCH", z.manual_review)
        self.assertEqual([(x.date, x.classification) for x in with_cal.excluded_candles],
                         [(sun, "EXCLUDED_MUHURAT")])
        no_cal = mtf.replay(cs, "75m", htf=("D",), as_of=as_of)
        z = no_cal.zones["D:demand-2-3"]
        self.assertEqual(z.status, "UNVERIFIED_SESSION")
        self.assertFalse(z.usable_as_fresh_context)
        self.assertEqual([x.classification for x in no_cal.excluded_candles], ["UNVERIFIED_SESSION"])
        # a weekday evening candle (as on Friday 1 Nov 2024) is caught by its hours, not its date
        weekday = [c for c in cs if c.start.date() != sun]
        weekday.append(TC(DT(2025, 1, 13, 18, 0), DT(2025, 1, 13, 19, 15), 104, 104.5, 95.0, 104))
        late = DT(2025, 1, 13, 19, 15)
        for calendar, why in ((None, "UNVERIFIED_SESSION"), (cal, "OUTSIDE_REGULAR_HOURS")):
            s = mtf.replay(weekday, "75m", htf=("D",), as_of=late, calendar=calendar)
            self.assertEqual(s.zones["D:demand-2-3"].status, "UNVERIFIED_SESSION")
            self.assertEqual([x.classification for x in s.excluded_candles], [why])

    def test_weekend_candle_without_a_calendar_is_unverified(self):
        sat = D(2025, 2, 15)
        cs = full_weeks_case()
        cs.insert(len(cs) - 1, day(sat, *CALM[0]))                    # does not touch the zone
        s = mtf.replay(cs, "D", htf=("W",), as_of=close(W6_MON))
        z = s.zones[KEY]
        self.assertFalse(z.usable_as_fresh_context)
        self.assertEqual(z.status, "UNVERIFIED_SESSION")
        self.assertIn("UNVERIFIED_SESSION 2025-02-15", z.reasons)
        self.assertEqual(s.series["W"].candles[-1].sessions_present, 5)
        self.assertEqual([(x.date, x.classification) for x in s.excluded_candles],
                         [(sat, "UNVERIFIED_SESSION")])
        clean = mtf.replay(full_weeks_case(), "D", htf=("W",), as_of=close(W6_MON))
        self.assertEqual(clean.zones[KEY].status, mtf.FRESH)          # the same data minus Saturday


class FormationGaps(unittest.TestCase):
    """H2 (Phase 1 audit): a gap in the leg-in, base or leg-out period blocks fresh use."""

    def test_gap_inside_a_formation_week_is_never_fresh(self):
        cal = Cal([d for w in FULL_WEEKS for d in w] + [W6_MON])
        for week, name in ((1, "leg-in"), (2, "base"), (3, "leg-out")):
            for missing in FULL_WEEKS[week]:                           # Monday is the period's first day
                with self.subTest(name, day=missing):
                    cs = full_weeks_case(skip=(missing,))
                    z = mtf.replay(cs, "D", htf=("W",), as_of=close(W6_MON)).zones[KEY]
                    self.assertEqual(z.status, mtf.UNKNOWN_DATA_GAP)
                    self.assertFalse(z.usable_as_fresh_context)
                    self.assertIn("MISSING_SESSION %s (unverified: no calendar)" % missing.isoformat(), z.reasons)
                    s = mtf.replay(cs, "D", htf=("W",), as_of=close(W6_MON), calendar=cal)
                    self.assertNotIn(KEY, s.zones)                     # calendar mode: series ends at the gap
                    self.assertEqual(s.series["W"].truncated_at, mtf.period_key("W", missing))

    def test_a_whole_missing_period_ends_the_series(self):
        # The leg-in week is followed by a strong up week, then the base and leg-out weeks.
        # If the up week (2025-W03) has no data, joining W02 to W04 fabricates a DBR that
        # never existed (demand-1-2). With a calendar the series must end at the gap.
        rows = [(100, 100.5, 94, 95), (95, 99, 94.8, 98.8)] + DBR_WEEKS[2:] + [CALM[0]]
        cal = Cal([d for w in FULL_WEEKS for d in w] + [W6_MON])

        def replay(skip, calendar):
            cs = [day(d, *r) for w, r in zip(FULL_WEEKS, rows) for d in w if d not in skip]
            return mtf.replay(cs + [day(W6_MON, *CALM[0])], "D", htf=("W",), as_of=close(W6_MON),
                              calendar=calendar)
        self.assertEqual(list(replay((), cal).zones), ["W:demand-2-3"])        # the real zone
        s = replay(FULL_WEEKS[1], cal)
        self.assertEqual(s.series["W"].truncated_at, "2025-W03")
        self.assertEqual([h.period_key for h in s.series["W"].candles], ["2025-W02"])
        self.assertEqual(s.zones, {})
        no_cal = replay(FULL_WEEKS[1], None).zones                           # A5: no truncation,
        self.assertEqual({k: z.status for k, z in no_cal.items()},           # but never fresh
                         {"W:demand-1-2": mtf.UNKNOWN_DATA_GAP})


    def test_a_missing_last_period_is_reported_as_truncation(self):
        # calendar mode: data ends Friday 14 Feb, but the week of 17 Feb is expected and
        # wholly missing. The series must say so, not look complete up to as_of.
        nxt = [W6_MON + datetime.timedelta(days=i) for i in range(5)]
        cal = Cal([d for w in FULL_WEEKS for d in w] + nxt)
        s = mtf.replay(full_weeks_case()[:-1], "D", htf=("W",), as_of=close(nxt[4]), calendar=cal)
        self.assertEqual(s.series["W"].truncated_at, "2025-W08")
        self.assertIn(mtf.HTF_SERIES_TRUNCATED_AT_GAP, s.series["W"].reasons)
        self.assertEqual(s.zones[KEY].status, mtf.UNKNOWN_DATA_GAP)


class DailyZones(unittest.TestCase):
    """Daily zones get the same session and gap checks when replayed over a daily base."""
    DAYS = [D(2025, 1, 6) + datetime.timedelta(days=i) for i in range(5)]
    LATER = [D(2025, 1, 13), D(2025, 1, 14), D(2025, 1, 15), D(2025, 1, 16)]

    def case(self, skip=()):
        cs = [day(d, *r) for d, r in zip(self.DAYS, DBR_WEEKS)]
        return cs + [day(d, *CALM[0]) for d in self.LATER if d not in skip]

    def test_missing_day_after_creation_blocks_a_daily_zone(self):
        cs = self.case(skip=(self.LATER[1],))
        engine_alone = mtf.ze.run_engine([mtf.ze.Candle(c.end, c.open, c.high, c.low, c.close) for c in cs], "D")
        self.assertEqual([a.zone.id for a in engine_alone.eligible], ["demand-2-3"])   # sees no gap
        as_of = close(self.LATER[3])
        s = mtf.replay(cs, "D", htf=("D",), as_of=as_of)
        z = s.zones["D:demand-2-3"]
        self.assertEqual(z.status, mtf.UNKNOWN_DATA_GAP)
        self.assertIn("MISSING_SESSION 2025-01-14 (unverified: no calendar)", z.reasons)
        self.assertEqual(s.eligible_after_overlay("D")[0], [])
        cal = Cal(self.DAYS + self.LATER)
        s = mtf.replay(cs, "D", htf=("D",), as_of=as_of, calendar=cal)
        self.assertEqual(s.series["D"].truncated_at, "2025-01-14")
        self.assertEqual(s.zones["D:demand-2-3"].status, mtf.UNKNOWN_DATA_GAP)
        clean = mtf.replay(self.case(), "D", htf=("D",), as_of=as_of, calendar=cal)
        self.assertEqual([a.zone.id for a in clean.eligible_after_overlay("D")[0]], ["demand-2-3"])


class StatusPrecedence(unittest.TestCase):
    def test_several_issues_give_one_status_and_keep_every_reason(self):
        sat = D(2025, 2, 15)
        cs = full_weeks_case(skip=(W5[2],))
        cs.insert(len(cs) - 1, day(sat, *CALM[0]))
        z = mtf.replay(cs, "D", htf=("W",), as_of=close(W6_MON)).zones[KEY]
        self.assertEqual(z.status, mtf.UNVERIFIED_SESSION)              # outranks the data gap
        self.assertIn("UNVERIFIED_SESSION 2025-02-15", z.reasons)
        self.assertIn("MISSING_SESSION 2025-02-12 (unverified: no calendar)", z.reasons)
        cs = full_weeks_case()
        cs.insert(len(cs) - 1, day(sat, 104, 104.5, 95.0, 104))          # touches PL 95.2
        z = mtf.replay(cs, "D", htf=("W",), as_of=close(W6_MON)).zones[KEY]
        self.assertEqual(z.status, mtf.UNVERIFIED_SESSION)              # the touch is not trusted either
        self.assertEqual(z.events, [])


class PeriodBoundaries(unittest.TestCase):
    def test_year_end_week_month_and_year_split(self):
        wk = [D(2024, 12, 30) + datetime.timedelta(days=k) for k in range(5)]   # ISO 2025-W01
        nxt = D(2025, 1, 6)
        cs = [day(d, 100 + k, 101 + k, 99 + k, 100.5 + k) for k, d in enumerate(wk)] + [day(nxt, 105, 106, 104, 105)]
        weekdays = [wk[0] + datetime.timedelta(days=i) for i in range(400)]
        cal = Cal([d for d in weekdays if d.weekday() < 5])
        s = mtf.replay(cs, "D", htf=("W", "M", "Q", "HY", "Y"), as_of=close(nxt), calendar=cal)
        w = s.series["W"].candles
        self.assertEqual([(h.period_key, h.start.date(), h.end.date(), h.low, h.high) for h in w],
                         [("2025-W01", wk[0], wk[4], 99, 105)])
        for tf, key in (("M", "2024-12"), ("Q", "2024-Q4"), ("HY", "2024-H2"), ("Y", "2024")):
            got = [(h.period_key, h.end.date(), h.close) for h in s.series[tf].candles]
            self.assertEqual(got[0], (key, wk[1], 101.5), tf)
        self.assertEqual([h.period_key for h in s.series["M"].candles], ["2024-12"])
        self.assertEqual(s.series["M"].in_progress_period, "2025-01")


if __name__ == "__main__":
    unittest.main()
