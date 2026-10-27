"""nse/zone-engine tests. All candles are SYNTHETIC (not market data), built by hand so
every proximal line, distal line, count and score can be checked with a pencil.

Price conventions in the scenarios: F = a doji filler (body 0, a base candle that
cannot start a cluster because no strong candle precedes it).
"""

import os
import unittest

from _load import load

ze = load(os.path.join("nse", "zone-engine"), "zone_engine")
Candle = ze.Candle

F = (100, 101, 99, 100)


def bars(rows, start=0):
    return [Candle(start + i, *r) for i, r in enumerate(rows)]


def mirror(candles, k=200.0):
    """Reflect prices: a bull candle becomes a bear candle with the same body ratio."""
    return [Candle(c.time, k - c.open, k - c.low, k - c.high, k - c.close, c.complete)
            for c in candles]


def zone_at(result, start, side=None):
    out = [a for a in result.assessments if a.zone.start_index == start
           and (side is None or a.zone.side == side)]
    return out[0] if out else None


# DBR: bear leg-in, one base, explosive bull leg-out above the leg-in high, then a second
# strong bull candle (leg-out count 2).
DBR = [
    F,
    (100, 100.5, 94, 95),         # 1 leg-in: body 5 / range 6.5 = 0.77, strong bear
    (95, 96, 94.5, 95.2),         # 2 base: 0.2 / 1.5; PL = 95.2, cluster wicks 94.5-96
    (95.5, 102, 95.3, 101.5),     # 3 leg-out: 6 / 6.7; close 101.5 > max(100.5, 96)
    (101.5, 105, 101, 104.5),     # 4 strong bull: leg-out count 2
]
# RBR: bull leg-in, one base, bull leg-out above max(leg-in high, cluster high).
RBR = [
    F,
    (95, 101, 94.5, 100.5),       # 1 leg-in: 5.5 / 6.5, strong bull
    (100.5, 101.2, 99.8, 100.3),  # 2 base: PL 100.5, wicks 99.8-101.2
    (100.4, 106, 100.2, 105.5),   # 3 leg-out: close 105.5 > 101.2
    (105.5, 109, 105, 108.5),     # 4 strong bull
]


def dbr_with_bases(n):
    rows = [F, (100, 100.5, 94, 95), (95, 96, 94.5, 95.2)]
    rows += [(95.2, 95.8, 94.7, 95.1)] * (n - 1)       # base 0.1 / 1.1, inside, no breakout
    rows += [(95.5, 102, 95.3, 101.5), (101.5, 105, 101, 104.5)]
    return bars(rows)


class Patterns(unittest.TestCase):
    def test_dbr_geometry_score_and_eligibility(self):
        r = ze.run_engine(bars(DBR), "D")
        a = zone_at(r, 2)
        z = a.zone
        self.assertEqual((z.side, z.pattern, z.reversal, z.zero_base), ("demand", "DBR", True, False))
        self.assertAlmostEqual(z.proximal, 95.2)
        self.assertAlmostEqual(z.distal, 94.0)          # leg-in low is the extreme wick (RB 337)
        self.assertAlmostEqual(z.normal_distal, 94.5)
        self.assertTrue(z.exceptional)
        self.assertEqual((z.base_count, z.legout_count, z.test_count), (1, 2, 0))
        self.assertTrue(z.strong_closing)
        self.assertEqual((a.score.freshness, a.score.strength, a.score.base, a.score.core),
                         (3.0, 2.0, 2.0, 7.0))
        self.assertEqual(a.status, ze.ELIGIBLE)
        self.assertEqual(a.reasons, [])
        self.assertEqual(a.manual_review, [])
        self.assertEqual(a.manual_checks, [ze.LEGOUT_RELATIVE_SIZE_CONTEXT])
        self.assertEqual([x.zone.id for x in r.eligible], [z.id])

    def test_dbr_with_one_legout_candle_is_six_of_seven(self):
        r = ze.run_engine(bars(DBR[:4]), "D")
        a = zone_at(r, 2)
        self.assertEqual((a.zone.legout_count, a.score.strength, a.score.core), (1, 1.0, 6.0))
        self.assertEqual(a.status, ze.INELIGIBLE)
        self.assertEqual(a.reasons, [ze.CORE_BELOW_7])
        self.assertEqual(r.eligible, [])

    def test_rbr(self):
        r = ze.run_engine(bars(RBR), "D")
        a = zone_at(r, 2)
        z = a.zone
        self.assertEqual((z.side, z.pattern, z.reversal), ("demand", "RBR", False))
        self.assertAlmostEqual(z.proximal, 100.5)
        self.assertAlmostEqual(z.distal, 99.8)           # continuous: base and leg-out only (RB 339)
        self.assertFalse(z.exceptional)
        self.assertEqual(a.score.core, 7.0)
        self.assertEqual(a.status, ze.ELIGIBLE)

    def test_rbd_is_supply_context_only(self):
        r = ze.run_engine(mirror(bars(DBR)), "D")
        a = zone_at(r, 2)
        z = a.zone
        self.assertEqual((z.side, z.pattern, z.reversal), ("supply", "RBD", True))
        self.assertAlmostEqual(z.proximal, 104.8)
        self.assertAlmostEqual(z.distal, 106.0)
        self.assertEqual(a.score.core, 7.0)
        self.assertEqual(a.status, ze.CONTEXT_ONLY)
        self.assertEqual(a.reasons, [ze.SUPPLY_CONTEXT_ONLY])
        self.assertEqual(r.eligible, [])                 # no short candidates (D2)
        self.assertEqual([x.zone.id for x in r.context_supply], [z.id])

    def test_dbd_is_supply_context_only(self):
        r = ze.run_engine(mirror(bars(RBR)), "D")
        a = zone_at(r, 2)
        self.assertEqual((a.zone.side, a.zone.pattern, a.zone.reversal), ("supply", "DBD", False))
        self.assertAlmostEqual(a.zone.proximal, 99.5)
        self.assertAlmostEqual(a.zone.distal, 100.2)
        self.assertEqual(a.status, ze.CONTEXT_ONLY)
        self.assertEqual(r.eligible, [])


class ZeroBase(unittest.TestCase):
    ROWS = [F, F, F,
            (100, 100.5, 95, 95.5),      # 3 strong bear: 4.5 / 5.5
            (95.6, 101, 95.2, 100.6)]    # 4 strong bull: 5 / 5.8, no gap (95.2 < 100.5)

    def test_zero_base_scores_with_pine_reference_and_tag(self):
        r = ze.run_engine(bars(self.ROWS), "D")
        a = zone_at(r, 3)
        z = a.zone
        self.assertTrue(z.zero_base)
        self.assertEqual((z.pattern, z.base_count, z.legout_count, z.has_gap), ("DBR", 0, 1, False))
        self.assertAlmostEqual(z.proximal, 95.6)
        self.assertAlmostEqual(z.distal, 95.0)
        self.assertFalse(z.exceptional)
        self.assertEqual((a.score.base, a.score.base_basis), (2.0, ze.TAG_ZB))
        self.assertIn(ze.TAG_ZB, a.tags)
        self.assertEqual(a.score.core, 6.0)               # 3 + 1 + 2
        self.assertEqual((a.status, a.reasons), (ze.INELIGIBLE, [ze.CORE_BELOW_7]))

    def test_zero_base_reaches_seven_with_a_second_leg_out_and_stays_eligible(self):
        rows = self.ROWS + [(100.6, 104, 100.4, 103.8)]   # strong bull, bar 1 after creation
        a = zone_at(ze.run_engine(bars(rows), "D"), 3)
        self.assertEqual((a.zone.legout_count, a.score.core), (2, 7.0))
        self.assertEqual(a.status, ze.ELIGIBLE)           # not rejected for zero bases (D5)
        self.assertIn(ze.TAG_ZB, a.tags)

    def test_zero_base_needs_two_rulebook_strong_candles(self):
        rows = [F, F, F,
                (100, 100.5, 97, 98.25),          # bear body 1.75 / 3.5 = exactly 0.5: not strong
                (98.3, 101, 98.2, 100.6)]
        r = ze.run_engine(bars(rows), "D")
        self.assertEqual(r.assessments, [])


class BaseCount(unittest.TestCase):
    def test_one_to_five_bases(self):
        expected = {1: (2.0, 7.0), 2: (2.0, 7.0), 3: (2.0, 7.0), 4: (1.0, 6.0), 5: (1.0, 6.0)}
        for n, (base_pts, core) in expected.items():
            a = zone_at(ze.run_engine(dbr_with_bases(n), "D"), 2)
            self.assertEqual(a.zone.base_count, n, n)
            self.assertEqual((a.score.base, a.score.core), (base_pts, core), n)
            self.assertEqual(a.status, ze.ELIGIBLE if core == 7.0 else ze.INELIGIBLE, n)

    def test_six_bases_is_a_garbage_area_with_no_zone(self):
        r = ze.run_engine(dbr_with_bases(6), "D")
        self.assertEqual(r.assessments, [])
        self.assertEqual([p["reason"] for p in r.rejected_patterns], [ze.EV_GARBAGE_AREA])
        self.assertEqual(r.rejected_patterns[0]["cluster_start"], 2)


    def test_base_closing_outside_a_full_cluster_needs_manual_review(self):
        # M3 (user decision 2026-10-26): five bases inside 94.5-96, then a base candle
        # (body 0.9 / 2.4) closing above the cluster. Not counted as a 6th base, not
        # dismissed: recorded for manual review, and no zone is created.
        weak_break = (95.3, 97, 94.6, 96.2)
        rows = [F, (100, 100.5, 94, 95), (95, 96, 94.5, 95.2)] + [(95.2, 95.8, 94.7, 95.1)] * 4
        rows += [weak_break, (96.2, 102, 96.1, 101.5)]
        for side, candles in (("demand", bars(rows)), ("supply", mirror(bars(rows)))):
            with self.subTest(side):
                r = ze.run_engine(candles, "D")
                self.assertEqual(r.assessments, [])
                found = [p for p in r.rejected_patterns if p["reason"] == "BASE_CLOSED_OUTSIDE_CLUSTER"]
                self.assertEqual(len(found), 1)
                p = found[0]
                self.assertEqual((p["index"], p["cluster_start"], p["base_count"], p["disposition"]),
                                 (7, 2, 5, ze.MANUAL_REVIEW))
                hi, lo = (96, 94.5) if side == "demand" else (105.5, 104)
                self.assertEqual((p["cluster_high"], p["cluster_low"]), (hi, lo))
                self.assertNotIn(ze.EV_GARBAGE_AREA, [x["reason"] for x in r.rejected_patterns])
                self.assertIn("BASE_CLOSED_OUTSIDE_CLUSTER", [e["event"] for e in r.events])
        # with room left in the cluster the same candle simply ends it: nothing ambiguous
        short = [F, (100, 100.5, 94, 95), (95, 96, 94.5, 95.2), (95.2, 95.8, 94.7, 95.1),
                 weak_break, (96.2, 102, 96.1, 101.5)]
        r = ze.run_engine(bars(short), "D")
        self.assertEqual([p["reason"] for p in r.rejected_patterns], [])


class StrongCandles(unittest.TestCase):
    def rows(self, legin_open):
        return [F,
                (legin_open, 100.5, 94.5, 97),     # range 6; body = open - 97
                (97, 97.8, 96.5, 97.2),            # base
                (97.5, 103, 97.3, 102.5),          # leg-out above 100.5
                (102.5, 106, 102, 105.5)]

    def test_body_exactly_half_is_not_strong(self):
        c = bars(self.rows(100))[1]
        self.assertEqual(ze.body_ratio(c), 0.5)
        self.assertEqual(ze.run_engine(bars(self.rows(100)), "D").assessments, [])

    def test_bull_body_exactly_half_is_not_strong(self):
        cs = mirror(bars(self.rows(100)))                 # the exactly-half candle becomes a bull leg-in
        self.assertEqual(ze.body_ratio(cs[1]), 0.5)
        self.assertTrue(cs[1].close > cs[1].open)
        self.assertEqual(ze.run_engine(cs, "D").assessments, [])

    def test_leg_in_strong_only_by_close_break_is_pine_only(self):
        rows = [F,
                (99.5, 100, 97.5, 98.5),          # body 1 / 2.5 = 0.4, closes below the prior low 99
                (98.5, 99, 98, 98.6),             # base
                (98.7, 104, 98.5, 103.5)]         # explosive bull above 100
        r = ze.run_engine(bars(rows), "D")
        self.assertEqual(r.assessments, [])
        self.assertEqual([(p["pattern"], p["start_index"]) for p in r.pine_only_zones], [("DBR", 1)])
        m = ze.run_engine(mirror(bars(rows)), "D")         # bull leg-in closing above the prior high
        self.assertEqual(m.assessments, [])
        self.assertEqual([(p["pattern"], p["start_index"]) for p in m.pine_only_zones], [("RBD", 1)])

    def test_body_just_over_half_is_strong(self):
        r = ze.run_engine(bars(self.rows(100.06)), "D")
        self.assertEqual(zone_at(r, 2).zone.pattern, "DBR")

    def test_close_break_without_body_is_pine_only(self):
        rows = [F, (100, 100.5, 94, 95), (95, 96, 94.5, 95.2),
                (99, 101.5, 95.5, 100.9),          # body 1.9 / 6 = 0.32, but closes above 96 and 100.5
                (100.9, 104, 100.5, 103.8)]
        r = ze.run_engine(bars(rows), "D")
        self.assertEqual(r.assessments, [])                      # rulebook: no explosive leg-out
        self.assertEqual(len(r.pine_only_zones), 1)
        p = r.pine_only_zones[0]
        self.assertEqual((p["reason"], p["pattern"], p["start_index"], p["created_index"]),
                         (ze.PINE_ONLY_ZONE, "DBR", 2, 3))


class Achievement(unittest.TestCase):
    HEAD = [F,
            (110, 112, 94, 95),          # 1 strong bear leg-in, high 112
            (95, 96, 94.5, 95.2),        # 2 base
            (95.5, 101, 95.3, 100.5)]    # 3 strong bull leg-out, but close 100.5 < 112

    def test_failure_sets_pending(self):
        r = ze.run_engine(bars(self.HEAD), "D")
        self.assertEqual(r.assessments, [])
        self.assertEqual([e["event"] for e in r.events], [ze.EV_PENDING_SET])

    def test_daily_pending_completes_on_the_next_bar(self):
        rows = self.HEAD + [(100.5, 114, 100.2, 113),      # strong bull, close 113 > 112
                            (113, 117, 112.5, 116.5)]
        r = ze.run_engine(bars(rows), "D")
        a = zone_at(r, 2)
        z = a.zone
        self.assertEqual((z.pattern, z.created_index, z.legout_index, z.from_pending), ("DBR", 4, 3, True))
        self.assertAlmostEqual(z.proximal, 95.2)
        self.assertAlmostEqual(z.distal, 94.0)
        self.assertEqual((z.legout_count, a.score.core, a.status), (2, 7.0, ze.ELIGIBLE))
        # counting the first leg-out too gives 3 candles: still 7/7, so no ambiguity flag
        self.assertTrue(z.pending_first_legout_explosive)
        self.assertEqual(a.manual_review, [])

    def test_daily_pending_expires_after_one_bar(self):
        rows = self.HEAD + [(100.5, 101, 100, 100.6),      # base: no achievement
                            (100.6, 114, 100.4, 113)]      # would achieve, but too late on D
        r = ze.run_engine(bars(rows), "D")
        self.assertIsNone(zone_at(r, 2))
        miss = [p for p in r.rejected_patterns if p["reason"] == ze.EV_ACHIEVEMENT_NOT_MET]
        self.assertEqual([(p["cluster_start"], p["index"]) for p in miss], [(2, 4)])

    def test_weekly_pending_allows_two_bars(self):
        rows = self.HEAD + [(100.5, 101, 100, 100.6), (100.6, 114, 100.4, 113)]
        r = ze.run_engine(bars(rows), "W")
        z = zone_at(r, 2).zone
        self.assertEqual((z.pattern, z.created_index, z.from_pending), ("DBR", 5, True))
        self.assertEqual(r.rejected_patterns, [])

    def test_weekly_pending_expires_after_two_bars(self):
        rows = self.HEAD + [(100.5, 101, 100, 100.6), (100.6, 100.9, 100.3, 100.5),
                            (100.5, 114, 100.4, 113)]
        r = ze.run_engine(bars(rows), "W")
        self.assertIsNone(zone_at(r, 2))
        self.assertEqual([p["index"] for p in r.rejected_patterns
                          if p["reason"] == ze.EV_ACHIEVEMENT_NOT_MET], [5])

    def test_pl_touch_inside_the_pending_window_needs_review(self):
        rows = self.HEAD + [(96, 114, 95.0, 113),          # achieves, wick touches PL 95.2
                            (113, 117, 112.5, 116.5)]
        a = zone_at(ze.run_engine(bars(rows), "D"), 2)
        self.assertEqual(a.zone.pending_window_touch_indices, [4])
        self.assertEqual(a.zone.test_count, 0)             # Pine timing: tests start after bar 4
        self.assertEqual(a.score.core, 7.0)
        self.assertEqual(a.status, ze.MANUAL_REVIEW)
        self.assertIn(ze.PENDING_WINDOW_PL_TOUCH, a.manual_review)


class Freshness(unittest.TestCase):
    def run_with(self, extra):
        return zone_at(ze.run_engine(bars(DBR + extra), "D"), 2)

    def test_untouched_zone_is_fresh(self):
        a = self.run_with([(104.5, 106, 103, 105)])
        self.assertEqual((a.zone.test_count, a.status), (0, ze.ELIGIBLE))

    def test_near_miss_is_not_a_test(self):
        a = self.run_with([(104.5, 105, 95.25, 100)])     # low 95.25 > PL 95.2 (RB 696)
        self.assertEqual((a.zone.test_count, a.status), (0, ze.ELIGIBLE))

    def test_wick_touch_tests_the_zone(self):
        a = self.run_with([(104.5, 105, 95.0, 100)])
        self.assertEqual((a.zone.test_count, a.zone.test_indices), (1, [5]))
        self.assertEqual((a.score.freshness, a.score.core), (1.5, 5.5))
        self.assertEqual((a.status, a.reasons), (ze.INELIGIBLE, [ze.ZONE_TESTED]))

    def test_gap_through_tests_the_zone(self):
        a = self.run_with([(94.8, 96, 94.5, 95.8)])       # opens below PL (RB 697)
        self.assertEqual(a.zone.test_count, 1)
        self.assertEqual(a.reasons, [ze.ZONE_TESTED])

    def test_creation_bar_is_never_a_test(self):
        a = zone_at(ze.run_engine(bars(DBR[:4]), "D"), 2)
        self.assertEqual(a.zone.test_count, 0)


class TestedExclusion(unittest.TestCase):
    def test_tested_zone_is_excluded_from_candidates_and_display(self):
        r = ze.run_engine(bars(DBR + [(104.5, 105, 95.0, 100)]), "D")
        a = zone_at(r, 2)
        self.assertEqual(a.status, ze.INELIGIBLE)
        self.assertIn(ze.ZONE_TESTED, a.reasons)
        self.assertNotIn(a.zone.id, [x.zone.id for x in r.eligible])
        self.assertNotIn(a.zone.id, [x.zone.id for x in r.fresh_zones])
        self.assertIn(a.zone.id, [x.zone.id for x in r.assessments])   # kept in the audit view
        self.assertEqual(a.manual_checks, [])

    def test_tested_supply_zone_leaves_the_context_list(self):
        r = ze.run_engine(mirror(bars(DBR + [(104.5, 105, 95.0, 100)])), "D")
        a = zone_at(r, 2)
        self.assertEqual(a.reasons, [ze.SUPPLY_CONTEXT_ONLY, ze.ZONE_TESTED])
        self.assertEqual(r.context_supply, [])


class Invalidation(unittest.TestCase):
    def test_close_beyond_distal_invalidates_permanently(self):
        rows = DBR + [(104.5, 105, 93, 93.5),       # close 93.5 < DL 94
                      (93.5, 110, 93.4, 109.5)]     # recovery does not revive it
        r = ze.run_engine(bars(rows), "D")
        a = zone_at(r, 2)
        self.assertEqual(a.zone.invalidated_index, 5)
        self.assertFalse(a.zone.active)
        self.assertEqual((a.status, a.reasons), (ze.INELIGIBLE, [ze.ZONE_INVALIDATED]))
        self.assertEqual(r.eligible, [])
        self.assertNotIn(a.zone.id, [x.zone.id for x in r.fresh_zones])

    def test_wick_beyond_distal_without_close_does_not_invalidate(self):
        a = zone_at(ze.run_engine(bars(DBR + [(104.5, 105, 93.5, 96)]), "D"), 2)
        self.assertTrue(a.zone.active)
        self.assertEqual(a.zone.dl_touch_index, 5)
        self.assertEqual(a.reasons, [ze.ZONE_TESTED])

    def test_supply_invalidation_mirrors(self):
        rows = mirror(bars(DBR + [(104.5, 105, 93, 93.5)]))
        a = zone_at(ze.run_engine(rows, "D"), 2)
        self.assertEqual(a.zone.invalidated_index, 5)
        self.assertIn(ze.ZONE_INVALIDATED, a.reasons)


class TransitionCandles(unittest.TestCase):
    HEAD = [F, (100, 100.5, 94, 95),
            (95, 97, 93, 95.2),              # 2 base, wicks 93-97
            (94, 96.5, 93.5, 95.8)]          # 3 transition: inside, body 1.8 / 3 = 0.6

    def test_ambiguous_count_that_changes_the_score_goes_to_review(self):
        rows = self.HEAD + [
            (95.5, 96, 94, 95.4),            # 4 base
            (94.2, 96.8, 94, 96.2),          # 5 transition: 2 / 2.8 = 0.71
            (96, 96.5, 95, 95.9),            # 6 base
            (96, 103, 95.8, 102.5),          # 7 leg-out
            (102.5, 106, 102, 105.5)]        # 8 strong bull
        a = zone_at(ze.run_engine(bars(rows), "D"), 2)
        z = a.zone
        self.assertEqual((z.base_count, z.transition_count, z.base_count_incl_transitions), (3, 2, 5))
        self.assertAlmostEqual(z.proximal, 96.2)         # transitions widen the body envelope (PS 1424)
        self.assertEqual(a.score.core, 7.0)
        self.assertIn(6.0, [x.core for x in a.readings])
        self.assertEqual(a.status, ze.MANUAL_REVIEW)
        self.assertEqual(a.manual_review, [ze.BASE_COUNT_TRANSITION_AMBIGUITY])
        self.assertEqual(a.evidence["base_count_incl_transitions"], 5)

    def test_ambiguity_that_does_not_change_the_score_is_only_reported(self):
        rows = self.HEAD + [(96, 103, 95.8, 102.5), (102.5, 106, 102, 105.5)]
        a = zone_at(ze.run_engine(bars(rows), "D"), 2)
        self.assertEqual((a.zone.base_count, a.zone.transition_count), (1, 1))
        self.assertEqual(a.evidence["base_count_incl_transitions"], 2)
        self.assertEqual(a.status, ze.ELIGIBLE)
        self.assertEqual(a.manual_review, [])


class QualitativeRules(unittest.TestCase):
    def test_gap_lifting_strength_is_never_auto_accepted(self):
        rows = [F, F, F,
                (100, 100.5, 95, 95.5),          # strong bear
                (101, 106, 100.8, 105.5)]        # strong bull opening above 100.5: gap 0.3
        a = zone_at(ze.run_engine(bars(rows), "D"), 3)
        self.assertTrue(a.zone.has_gap)
        self.assertAlmostEqual(a.evidence["gap_size"], 0.3)
        self.assertEqual((a.zone.legout_count, a.score.strength, a.score.core), (1, 2.0, 7.0))
        self.assertEqual(a.status, ze.MANUAL_REVIEW)
        self.assertEqual(a.manual_review, [ze.GAP_MEANINGFULNESS_UNVERIFIED])
        self.assertIn(ze.TAG_ZB, a.tags)

    def test_cluster_window_gap_is_flagged_too(self):
        rows = [F, (100, 100.5, 94, 95), (95, 96, 94.5, 95.2),
                (97, 102, 96.2, 101.5)]          # leg-out low 96.2 > cluster high 96
        a = zone_at(ze.run_engine(bars(rows), "D"), 2)
        self.assertAlmostEqual(a.zone.gap_size, 0.2)
        self.assertEqual(a.status, ze.MANUAL_REVIEW)
        self.assertIn(ze.GAP_MEANINGFULNESS_UNVERIFIED, a.manual_review)

    def test_relative_size_is_evidence_not_a_threshold(self):
        big = zone_at(ze.run_engine(bars(DBR), "D"), 2)
        small_rows = list(DBR)
        small_rows[3] = (95.5, 100.8, 95.3, 100.6)       # leg-out barely larger, still achieves
        small_rows[4] = (100.6, 104, 100.4, 103.8)
        small = zone_at(ze.run_engine(bars(small_rows), "D"), 2)
        for a in (big, small):
            self.assertEqual(a.status, ze.ELIGIBLE)
            self.assertEqual(a.manual_checks, [ze.LEGOUT_RELATIVE_SIZE_CONTEXT])
            self.assertTrue(a.evidence["legout_ranges"])
            self.assertTrue(a.evidence["base_ranges"])
        self.assertNotEqual(big.evidence["legout_ranges"], small.evidence["legout_ranges"])

    def test_interrupted_leg_out_and_pine_freeze_go_to_review(self):
        rows = DBR[:4] + [(101.5, 102, 101, 101.5),       # 4 doji: breaks the sequence
                          (101.5, 106, 101.2, 105.5)]     # 5 strong bull; also ends a new RBR cluster
        r = ze.run_engine(bars(rows), "D")
        a = zone_at(r, 2)
        self.assertEqual((a.zone.legout_count, a.zone.legout_count_consecutive), (2, 1))
        self.assertEqual(a.evidence["legout_count_pine"], 1)   # Pine counts only the newest zone
        self.assertEqual(a.score.core, 7.0)
        self.assertEqual(a.status, ze.MANUAL_REVIEW)
        self.assertEqual(a.manual_review, [ze.LEGOUT_SEQUENCE_INTERRUPTED, ze.PINE_SCORE_DIFFERS])
        self.assertEqual(zone_at(r, 4).zone.pattern, "RBR")


class CompletedCandlesAndLookahead(unittest.TestCase):
    FULL = DBR + [(104.5, 105, 95.0, 100)]               # bar 5 tests the zone

    def test_as_of_equals_the_prefix_and_ignores_later_candles(self):
        cut = ze.run_engine(bars(self.FULL), "D", as_of=4)
        prefix = ze.run_engine(bars(self.FULL[:5]), "D")
        self.assertEqual(cut.to_dict(), prefix.to_dict())
        self.assertEqual(zone_at(cut, 2).status, ze.ELIGIBLE)
        self.assertEqual(zone_at(ze.run_engine(bars(self.FULL), "D"), 2).status, ze.INELIGIBLE)

    def test_trailing_incomplete_candle_is_ignored(self):
        cs = bars(DBR)
        cs.append(Candle(5, 104.5, 105, 95.0, 100, complete=False))
        r = ze.run_engine(cs, "D")
        self.assertEqual(r.ignored_incomplete, [5])
        self.assertEqual((r.candles_received, r.candles_processed), (6, 5))
        self.assertEqual(zone_at(r, 2).status, ze.ELIGIBLE)

    def test_incomplete_candle_inside_the_series_is_an_error(self):
        cs = bars(DBR)
        cs[2] = Candle(2, 95, 96, 94.5, 95.2, complete=False)
        with self.assertRaises(ValueError):
            ze.run_engine(cs, "D")

    def test_insufficient_history(self):
        r = ze.run_engine(bars(DBR[:2]), "D")
        self.assertTrue(r.insufficient_history)
        self.assertEqual((r.reasons, r.assessments, r.candles_processed), ([ze.INSUFFICIENT_HISTORY], [], 2))

    def test_bad_input_is_refused(self):
        with self.assertRaises(ValueError):
            ze.run_engine(bars(DBR), "60m")               # D16: no 60/120-minute substitutes
        with self.assertRaises(ValueError):
            ze.run_engine(bars(DBR), "120m")
        with self.assertRaises(ValueError):
            ze.run_engine([Candle(0, *F), Candle(0, *F), Candle(1, *F)], "D")
        with self.assertRaises(ValueError):
            ze.run_engine([Candle(0, 100, 99, 98, 100)], "D")   # open above high

    def test_quarterly_has_no_pine_reference(self):
        r = ze.run_engine(bars(DBR), "Q")
        a = zone_at(r, 2)
        self.assertIn(ze.TAG_NO_PINE_REFERENCE, a.tags)
        self.assertEqual(r.pine_only_zones, [])
        self.assertEqual(a.status, ze.ELIGIBLE)

    def test_result_serialises(self):
        d = ze.run_engine(bars(DBR), "D").to_dict()
        self.assertEqual(d["timeframe"], "D")
        self.assertNotIn("_consecutive_open", d["assessments"][0]["zone"])

    def test_serialised_derived_lists_equal_the_properties(self):
        # audit L4: the derived lists are part of the serialised result
        for r in (ze.run_engine(bars(DBR), "D"), ze.run_engine(mirror(bars(DBR)), "D")):
            d = r.to_dict()["derived"]
            for name in ("eligible", "manual_review_zones", "context_supply", "fresh_zones"):
                self.assertEqual(d[name], [a.zone.id for a in getattr(r, name)], name)
        self.assertEqual(ze.run_engine(bars(DBR), "D").to_dict()["derived"]["eligible"], ["demand-2-3"])
        self.assertEqual(ze.run_engine(mirror(bars(DBR)), "D").to_dict()["derived"]["context_supply"],
                         ["supply-2-3"])


PEND = Achievement.HEAD      # pending demand: leg-out at bar 3 closes 100.5, below the 112 leg-in high
LATE = (100.6, 114, 100.4, 113)   # strong bull closing 113 > 112


class PendingLegoutAmbiguity(unittest.TestCase):
    """Audit P12: the first leg-out (body 0.88) and the achievement candle (body 0.91) both
    pass the rulebook body test. Pine counts one leg-out (PS 688); the rulebook's "2+
    explosive candles" (RB 728) may count two. The engine must not choose silently."""

    def test_p12_ambiguity_goes_to_manual_review_not_eligible(self):
        rows = PEND + [(100.5, 114, 100.2, 113), (113, 113.5, 112.6, 113.1)]   # then a doji-like bar
        r = ze.run_engine(bars(rows), "D")
        a = zone_at(r, 2)
        self.assertGreater(ze.body_ratio(bars(rows)[3]), 0.5)
        self.assertGreater(ze.body_ratio(bars(rows)[4]), 0.5)
        self.assertTrue(a.zone.pending_first_legout_explosive)
        self.assertEqual((a.zone.legout_count, a.score.strength, a.score.core), (1, 1.0, 6.0))
        self.assertIn(("first leg-out of a pending zone also counted", 7.0),
                      [(x.name, x.core) for x in a.readings])
        self.assertEqual(a.status, ze.MANUAL_REVIEW)
        self.assertEqual(a.manual_review, [ze.PENDING_LEGOUT_COUNT_AMBIGUOUS])
        self.assertEqual(a.reasons, [])
        self.assertEqual(r.eligible, [])                 # an alternative 7/7 never makes it eligible


class HigherTimeframeEngine(unittest.TestCase):
    def test_m1_no_cluster_starts_while_a_weekly_zone_is_pending(self):
        # bar 4 is a base candle one bar after a strong candle: on D it starts an RBR cluster
        # (PS 1386); on W the cluster logic is skipped while pending (PS 1932)
        rows = PEND + [(100.5, 101, 100, 100.6), LATE]
        w = ze.run_engine(bars(rows), "W")
        self.assertEqual([(a.zone.pattern, a.zone.start_index, a.zone.created_index) for a in w.assessments],
                         [("DBR", 2, 5)])
        d = ze.run_engine(bars(rows), "D")
        self.assertEqual([(a.zone.pattern, a.zone.start_index, a.zone.created_index) for a in d.assessments],
                         [("RBR", 4, 5)])

    def test_m3_weekly_pending_window_touch_is_flagged(self):
        rows = PEND + [(100.5, 101, 95.0, 100.6),        # window bar: low 95.0 <= PL 95.2
                       LATE, (113, 117, 112.5, 116.5)]
        a = zone_at(ze.run_engine(bars(rows), "W"), 2)
        self.assertEqual((a.zone.created_index, a.zone.pending_window_touch_indices), (5, [4]))
        self.assertAlmostEqual(a.zone.distal, 94.0)
        self.assertEqual(a.zone.test_count, 0)
        self.assertEqual(a.score.core, 7.0)
        self.assertEqual(a.status, ze.MANUAL_REVIEW)
        self.assertIn(ze.PENDING_WINDOW_PL_TOUCH, a.manual_review)

    def test_m4_weekly_zero_base_waits_for_pending(self):
        rows = PEND + [(100.5, 101, 96, 96.5)]           # strong bear after the strong bull leg-out
        w = ze.run_engine(bars(rows), "W")
        self.assertEqual(w.assessments, [])               # PS 2158: blocked while pending
        d = ze.run_engine(bars(rows), "D")                # daily zero-base ignores pending (PS 1722)
        a = zone_at(d, 3)
        self.assertEqual((a.zone.side, a.zone.pattern, a.zone.zero_base), ("supply", "RBD", True))
        self.assertAlmostEqual(a.zone.proximal, 100.5)
        self.assertAlmostEqual(a.zone.distal, 101.0)

    def test_m13_intraday_timeframes_use_the_chart_engine(self):
        rows = PEND + [(100.5, 101, 100, 100.6), LATE]
        for tf in ("75m", "125m", "D"):
            r = ze.run_engine(bars(rows), tf)
            self.assertEqual(r.variant, "chart", tf)
            self.assertIsNone(zone_at(r, 2), tf)          # one later bar only, so no DBR from bar 2
            self.assertEqual([p["index"] for p in r.rejected_patterns
                              if p["reason"] == ze.EV_ACHIEVEMENT_NOT_MET], [4], tf)
        for tf in ("W", "M", "Q", "HY", "Y"):
            r = ze.run_engine(bars(rows), tf)
            self.assertEqual(r.variant, "htf", tf)
            self.assertEqual(zone_at(r, 2).zone.created_index, 5, tf)


class PineComparisonFlags(unittest.TestCase):
    def test_m5_pine_geometry_difference_is_flagged(self):
        # bar 3 is a small bear candle closing below the prior low: Pine treats it as strong
        # (PS 333), so Pine's leg-in for the bar-4 cluster is bar 3 (low 89.5); the rulebook's
        # leg-in stays bar 1 (low 90). Same zone, different distal line.
        rows = [F, (100, 100.5, 90, 91), (91, 92, 90.5, 91.2), (91, 91.5, 89.5, 90.2),
                (90.3, 91, 90.1, 90.5), (90.6, 102, 90.4, 101.5), (101.5, 105, 101, 104.5)]
        r = ze.run_engine(bars(rows), "D")
        a = zone_at(r, 4)
        self.assertEqual((a.zone.pattern, a.zone.created_index), ("DBR", 5))
        self.assertAlmostEqual(a.zone.distal, 90.0)
        self.assertEqual(a.score.core, 7.0)
        self.assertEqual(a.status, ze.MANUAL_REVIEW)
        self.assertEqual(a.manual_review, [ze.PINE_GEOMETRY_DIFFERS])
        self.assertEqual(r.eligible, [])

    def test_m6_rulebook_zone_without_a_pine_match_is_flagged(self):
        # bar 3 is a small bull candle closing above the prior high: Pine's leg-in becomes
        # bull (RBR), the rulebook's stays the bar-1 bear candle (DBR)
        rows = [F, (100, 100.5, 90, 91), (91, 92, 90.5, 91.2), (91.6, 92.8, 91.2, 92.3),
                (92.3, 92.7, 92.0, 92.4), (92.5, 103, 92.3, 102.5), (102.5, 106, 102, 105.5)]
        r = ze.run_engine(bars(rows), "D")
        a = zone_at(r, 4)
        self.assertEqual((a.zone.pattern, a.score.core), ("DBR", 7.0))
        self.assertIsNone(a.evidence["legout_count_pine"])
        self.assertEqual(a.status, ze.MANUAL_REVIEW)
        self.assertEqual(a.manual_review, [ze.PINE_NO_MATCHING_ZONE])
        self.assertEqual([(p["pattern"], p["start_index"], p["created_index"]) for p in r.pine_only_zones],
                         [("RBR", 4, 5)])


STRONG_UP = [(104.5, 108, 104, 107.5), (107.5, 111, 107, 110.5),
             (110.5, 114, 110, 113.5), (113.5, 117, 113, 116.5)]   # body 0.75 each


class LegoutCountLimits(unittest.TestCase):
    def test_source_window_limits_the_count_to_four(self):
        # PS 1771: bars 1-3 after creation, so at most 1 + 3 = 4 (the cap of 5 cannot bind)
        a = zone_at(ze.run_engine(bars(DBR + STRONG_UP), "D"), 2)
        self.assertEqual((a.zone.legout_count, a.zone.legout_count_consecutive), (4, 4))

    def test_m7_cap_mechanism_with_a_wider_window(self):
        # NOT a source configuration: widens the window only to exercise the cap (PS 1771)
        rules = ze.Rules(legout_track_bars=6)
        a = zone_at(ze.run_engine(bars(DBR + STRONG_UP), "D", rules=rules), 2)
        self.assertEqual((a.zone.legout_count, a.zone.legout_count_consecutive), (5, 5))


class PendingReplacement(unittest.TestCase):
    def test_source_timing_never_replaces_a_pending_zone(self):
        rows = PEND + [(100.5, 101, 100, 100.6), (100.1, 101.2, 100.0, 100.95), (101, 106, 100.9, 105.5)]
        r = ze.run_engine(bars(rows), "D")
        self.assertNotIn(ze.EV_PENDING_REPLACED, [e["event"] for e in r.events])

    def test_m9_newer_pending_replaces_the_older_one(self):
        # NOT a source configuration: a longer window is the only way two pendings can overlap
        rules = ze.Rules(pending_bars=4)
        rows = PEND + [(100.5, 101, 100, 100.6),        # 4 base: new cluster, leg-in = bar 3
                       (100.1, 101.2, 100.0, 100.95),    # 5 strong bull, fails 101 -> new pending
                       (101, 106, 100.9, 105.5)]         # 6 achieves the new pending only
        r = ze.run_engine(bars(rows), "D", rules=rules)
        self.assertIn(ze.EV_PENDING_REPLACED, [e["event"] for e in r.events])
        self.assertEqual([(a.zone.pattern, a.zone.start_index, a.zone.created_index) for a in r.assessments],
                         [("RBR", 4, 6)])


class GeometryAndScoringEdges(unittest.TestCase):
    def test_m2_creation_candle_touching_pl_is_not_a_test(self):
        rows = list(DBR)
        rows[3] = (95.1, 102, 95.0, 101.5)              # leg-out opens inside the base, low 95.0 <= PL
        a = zone_at(ze.run_engine(bars(rows), "D"), 2)
        self.assertLessEqual(rows[3][2], a.zone.proximal)
        self.assertEqual((a.zone.test_count, a.status), (0, ze.ELIGIBLE))
        zb = zone_at(ze.run_engine(bars(ZeroBase.ROWS + [(100.6, 104, 100.4, 103.8)]), "D"), 3)
        self.assertLessEqual(ZeroBase.ROWS[4][2], zb.zone.proximal)   # a zero-base leg-out always touches
        self.assertEqual((zb.zone.test_count, zb.status), (0, ze.ELIGIBLE))

    def test_m8_twice_tested_zone_scores_zero_freshness(self):
        rows = DBR + [(104.5, 105, 95.0, 100), (100, 100.5, 95.0, 99)]
        a = zone_at(ze.run_engine(bars(rows), "D"), 2)
        self.assertEqual((a.zone.test_count, a.score.freshness, a.score.core), (2, 0.0, 4.0))
        self.assertEqual((a.status, a.reasons), (ze.INELIGIBLE, [ze.ZONE_TESTED]))

    def test_m10_supply_zero_base_proximal(self):
        a = zone_at(ze.run_engine(mirror(bars(ZeroBase.ROWS)), "D"), 3)
        self.assertEqual((a.zone.side, a.zone.pattern, a.zone.zero_base), ("supply", "RBD", True))
        self.assertAlmostEqual(a.zone.proximal, 104.4)   # min(max(o1,c1), max(o,c)), PS 1748
        self.assertAlmostEqual(a.zone.distal, 105.0)
        self.assertIn(ze.TAG_ZB, a.tags)

    def test_m12_close_between_normal_and_exceptional_distal_does_not_invalidate(self):
        # exceptional DL 94.0 (leg-in low), normal DL 94.5: a close at 94.2 is inside the zone
        a = zone_at(ze.run_engine(bars(DBR + [(100, 100.5, 94.1, 94.2)]), "D"), 2)
        self.assertTrue(a.zone.exceptional)
        self.assertTrue(a.zone.active)
        self.assertIsNone(a.zone.invalidated_index)
        self.assertEqual(a.reasons, [ze.ZONE_TESTED])

    def test_m14_supply_window_gap(self):
        rows = [F, (100, 100.5, 94, 95), (95, 96, 94.5, 95.2), (97, 102, 96.2, 101.5)]
        a = zone_at(ze.run_engine(mirror(bars(rows)), "D"), 2)
        self.assertEqual(a.zone.side, "supply")
        self.assertTrue(a.zone.has_gap)
        self.assertAlmostEqual(a.zone.gap_size, 0.2)     # cluster low 104 minus leg-out high 103.8
        self.assertIn(("gap not meaningful", 6.0), [(x.name, x.core) for x in a.readings])


class EligibilityInvariants(unittest.TestCase):
    def test_no_tested_invalidated_supply_or_flagged_zone_is_ever_eligible(self):
        import random
        rnd = random.Random(20261026)
        seen = 0
        for tf in ("D", "W", "75m"):
            for _ in range(150):
                p, rows = 100.0, []
                for _ in range(40):
                    o = p
                    c = o + rnd.uniform(-4, 4)
                    rows.append((round(o, 2), round(max(o, c) + rnd.uniform(0, 3), 2),
                                 round(min(o, c) - rnd.uniform(0, 3), 2), round(c, 2)))
                    p = c
                for a in ze.run_engine(bars(rows), tf).eligible:
                    seen += 1
                    z = a.zone
                    self.assertTrue(z.is_demand and z.active and z.fresh)
                    self.assertEqual((a.score.core, a.manual_review, a.reasons), (7.0, [], []))
                    self.assertNotIn(ze.PENDING_LEGOUT_COUNT_AMBIGUOUS, [r for r in a.manual_review])
        self.assertGreater(seen, 0)


if __name__ == "__main__":
    unittest.main()
