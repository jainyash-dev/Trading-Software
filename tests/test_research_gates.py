"""G0-G8 unit tests for nse/research. All snapshots are SYNTHETIC (tests/_research.py).

The reference scenario (ideal_mit_builder) passes every automated gate. Each test
changes one input and checks the gate outcome and the final status, so a gate that
stopped working would show up as an unexpected ACTIONABLE.
"""

import unittest

import _research as R
from nse.research import levels, models as m, qualification as q, structure, trend
from nse.research.deps import mtf, ze

ACT = m.ACTIONABLE


def gates(c):
    return {g.gate: g.outcome for g in c.gates}


def falling(n, start=1500.0, step=0.01):
    return [start * (1 - step) ** i for i in range(n)]


class StatusDerivation(unittest.TestCase):
    def _gates(self, **over):
        return [m.GateResult(g, over.get(g, m.PASS)) for g in m.GATES]

    def test_all_pass_is_actionable_and_nothing_better_exists(self):
        self.assertEqual(m.derive_status(self._gates()), ACT)
        self.assertNotIn("APPROVED", " ".join(m.STATUS_ORDER))

    def test_the_most_restrictive_outcome_wins_wherever_it_sits(self):
        for g in m.GATES:
            self.assertEqual(m.derive_status(self._gates(**{g: m.FAIL})), m.REJECTED, g)
            self.assertEqual(m.derive_status(self._gates(**{g: m.DATA_INSUFFICIENT})), m.STATUS_DATA_INSUFFICIENT, g)
            self.assertEqual(m.derive_status(self._gates(**{g: m.MANUAL})), m.MANUAL_REVIEW, g)
            self.assertEqual(m.derive_status(self._gates(**{g: m.NOT_EVALUATED})), m.MANUAL_REVIEW, g)
            self.assertEqual(m.derive_status(self._gates(**{g: m.BLOCKED})), m.BLOCKED_STATUS, g)
        self.assertEqual(m.derive_status(self._gates(G0=m.DATA_INSUFFICIENT, G7=m.FAIL)), m.REJECTED)
        self.assertEqual(m.derive_status(self._gates(G0=m.BLOCKED, G7=m.FAIL)), m.BLOCKED_STATUS)

    def test_a_missing_or_unknown_gate_is_refused(self):
        with self.assertRaises(ValueError):
            m.derive_status(self._gates()[:-1])
        with self.assertRaises(ValueError):
            m.GateResult("G9", m.PASS)
        with self.assertRaises(ValueError):
            m.GateResult("G1", "MAYBE")


class Reference(unittest.TestCase):
    def test_ideal_scenario_passes_every_automated_gate(self):
        c = R.only(R.evaluate(R.ideal_mit_builder()))
        self.assertEqual(c.status, ACT)
        self.assertEqual(set(gates(c).values()), {m.PASS})
        self.assertEqual(c.manual_review, [])
        # the checklist always travels with an actionable candidate (spec 8)
        self.assertEqual([x["code"] for x in c.manual_checks], [x[0] for x in m.CHECKLIST])
        self.assertIn(m.NOT_EXTERNALLY_VALIDATED, c.limitations)
        self.assertIn(m.TRADINGVIEW_PARITY_UNVERIFIED, c.limitations)


class G0(unittest.TestCase):
    def test_data_error_stops_at_g0(self):
        c = R.only(R.evaluate(R.ideal_mit_builder(), data_errors=["DUPLICATE_DATE 2025-01-02"]))
        self.assertEqual(c.status, m.STATUS_DATA_INSUFFICIENT)
        self.assertEqual(gates(c)["G0"], m.DATA_INSUFFICIENT)
        self.assertEqual(set(gates(c)[g] for g in m.GATES[1:]), {m.NOT_EVALUATED})

    def test_truncated_execution_series_is_data_insufficient(self):
        b = R.ideal_mit_builder()
        b.series["D"].truncated_at = "2025-06-20"
        c = R.only(R.evaluate(b))
        self.assertEqual((gates(c)["G0"], c.status), (m.DATA_INSUFFICIENT, m.STATUS_DATA_INSUFFICIENT))

    def test_no_calendar_or_unresolved_dates_need_review(self):
        b = R.ideal_mit_builder()
        b.calendar_validated = False
        c = R.only(R.evaluate(b))
        self.assertEqual((gates(c)["G0"], c.status), (m.MANUAL, m.MANUAL_REVIEW))
        self.assertIn("G0:" + m.CALENDAR_UNVALIDATED, c.manual_review)
        b = R.ideal_mit_builder()
        b.unresolved = [R.DT(2025, 3, 3).date()]
        self.assertEqual(R.only(R.evaluate(b)).status, m.MANUAL_REVIEW)


def wit_builder(recency=5, daily=None, weekly=None):
    """WIT roles: W location, D trend gate, 75m execution, D target. SYNTHETIC."""
    b = R.SnapBuilder()
    b.add_series("75m", [940.0] * 40)
    b.add_zone("75m", "demand", 890.0, 870.0, normal_dl=875.0, created_index=39 - recency)
    b.add_series("D", daily or R.rising(60))
    b.add_zone("D", "supply", 1200.0, 1230.0)
    b.add_series("W", weekly or [800.0 + i for i in range(60)])
    b.add_zone("W", "demand", 900.0, 850.0, status=mtf.TESTED, zid="w-coinciding")
    b.add_zone("W", "demand", 700.0, 650.0, zid="w-bottom")
    b.add_zone("W", "supply", 1500.0, 1550.0, zid="w-top")
    b.add_series("M", [800.0 + i for i in range(60)])
    for tf in ("Q", "HY", "Y"):
        b.add_series(tf, [800.0, 820.0, 840.0, 860.0])
    return b


class Wit(unittest.TestCase):
    def test_wit_is_always_blocked_but_its_gates_still_follow_wit_roles(self):
        for tt in (m.WIT_75, m.WIT_125):
            b = wit_builder()
            if tt == m.WIT_125:
                b.series["125m"] = b.series.pop("75m")
                for k in list(b.zones):
                    if k.startswith("75m:"):
                        b.zones["125m:" + k[4:]] = b.zones.pop(k)
            c = R.only(R.evaluate(b, trade_type=tt))
            self.assertEqual(c.status, m.BLOCKED_STATUS, tt)
            self.assertEqual(gates(c)["G0"], m.BLOCKED)
            self.assertEqual(c.gate("G4").evidence["gate"]["tf"], "D")    # D22: Daily is the WIT trend gate
            self.assertEqual(c.gate("G3").evidence["tf"], "W")            # D16: Weekly curve

    def test_wit_ignores_a_falling_weekly_trend_that_rejects_mit(self):
        wit = R.only(R.evaluate(wit_builder(weekly=falling(60, 1000.0)), trade_type=m.WIT_75))
        self.assertEqual(gates(wit)["G4"], m.PASS)                     # no Weekly gate for WIT (D22)
        b = R.ideal_mit_builder()
        b.add_series("W", falling(60, 1000.0))
        b.add_zone("W", "supply", 1200.0, 1230.0)
        mit = R.only(R.evaluate(b))
        self.assertEqual((gates(mit)["G4"], mit.status), (m.FAIL, m.REJECTED))   # LOC + Down (RB 1896)

    def test_wit_recency_bands(self):
        def g1(n):
            return R.only(R.evaluate(wit_builder(recency=n), trade_type=m.WIT_75)).gate("G1")
        self.assertEqual(g1(8).outcome, m.PASS)
        self.assertEqual(g1(9).outcome, m.MANUAL)
        self.assertEqual(g1(25).outcome, m.MANUAL)
        self.assertIn("re-verify HTF", " ".join(g1(25).reasons))

    def test_mit_has_no_recency_gate(self):
        b = R.ideal_mit_builder()
        self.assertEqual(R.only(R.evaluate(b)).gate("G1").outcome, m.PASS)
        self.assertNotIn("candles_since_formation", R.only(R.evaluate(b)).gate("G1").evidence)


class G1G2(unittest.TestCase):
    def test_overlay_inconsistency_is_refused(self):
        b = R.ideal_mit_builder()
        b.zones["D:" + b.series["D"].engine.assessments[0].zone.id].base_touch_count = 1
        with self.assertRaises(AssertionError):
            R.evaluate(b)

    def test_engine_manual_review_zone_is_manual_at_best(self):
        b = R.ideal_mit_builder()
        b.series["D"].engine.assessments.clear()
        b.zones.clear()
        b = R.ideal_mit_builder()
        a = b.series["D"].engine.assessments[0]
        a.status, a.manual_review = ze.MANUAL_REVIEW, [ze.PINE_SCORE_DIFFERS]
        c = R.only(R.evaluate(b))
        self.assertEqual((gates(c)["G2"], c.status), (m.MANUAL, m.MANUAL_REVIEW))
        self.assertIn("G2:" + ze.PINE_SCORE_DIFFERS, c.manual_review)

    def test_core_below_seven_never_becomes_a_candidate(self):
        b = R.ideal_mit_builder()
        a = b.series["D"].engine.assessments[0]
        a.status, a.reasons = ze.INELIGIBLE, [ze.CORE_BELOW_7]
        self.assertEqual(R.evaluate(b)["candidates"], [])


class G3(unittest.TestCase):
    def test_eqb_with_strong_up_passes(self):
        c = R.only(R.evaluate(R.ideal_mit_builder(), price=1150.0))
        self.assertEqual(c.gate("G3").evidence["position_at_price"], [structure.EQB])
        self.assertEqual(c.status, ACT)

    def test_cmp_hoc_is_not_overridden_by_execution_pl_at_loc(self):
        c = R.only(R.evaluate(R.ideal_mit_builder(), price=1300.0))      # HOC at CMP, LOC at the execution PL
        self.assertEqual((gates(c)["G3"], gates(c)["G4"], c.status), (m.MANUAL, m.FAIL, m.REJECTED))
        self.assertEqual(c.gate("G3").evidence["position_at_price"], [structure.HOC])
        self.assertNotIn("position_at_execution_pl", c.gate("G3").evidence)

    def test_vhoc_is_rejected(self):
        b = R.ideal_mit_builder()
        b.series["D"].engine.assessments.clear()
        b.zones = {k: v for k, v in b.zones.items() if not k.startswith("D:")}
        b.add_zone("D", "demand", 1510.0, 1490.0, created_index=50)
        c = R.only(R.evaluate(b, price=1520.0))
        self.assertEqual((gates(c)["G3"], c.status), (m.FAIL, m.REJECTED))

    def test_incomplete_curve_needs_review(self):
        b = R.ideal_mit_builder()
        b.zones.pop("M:m-top")
        b.series["M"].engine.assessments[:] = [a for a in b.series["M"].engine.assessments if a.zone.id != "m-top"]
        c = R.only(R.evaluate(b))
        self.assertEqual(gates(c)["G3"], m.MANUAL)
        self.assertTrue(any("NO_FRESH_SUPPLY_ABOVE" in r or "HIGHEST_PRICE" in r for r in c.gate("G3").reasons))

    def test_boundary_of_unknown_freshness_is_not_skipped(self):
        b = R.ideal_mit_builder()
        b.zones["M:m-bottom"].status = mtf.UNKNOWN_DATA_GAP
        c = R.only(R.evaluate(b))
        self.assertEqual(gates(c)["G3"], m.MANUAL)
        self.assertIn("BOUNDARY_FRESHNESS_UNKNOWN m-bottom", c.gate("G3").reasons)

    def test_tested_boundary_is_skipped(self):
        b = R.ideal_mit_builder()
        b.zones["M:m-bottom"].status = mtf.TESTED
        b.add_zone("M", "demand", 500.0, 450.0, zid="m-lower")
        c = R.only(R.evaluate(b))
        ev = c.gate("G3").evidence
        self.assertEqual(ev["bottom"]["zone_id"], "m-lower")
        self.assertIn("m-bottom", ev["skipped_tested_boundaries"])

    def test_price_inside_a_tested_monthly_demand_needs_review(self):
        c = R.only(R.evaluate(R.ideal_mit_builder(), price=880.0))
        self.assertEqual(gates(c)["G3"], m.MANUAL)
        self.assertTrue(any(r.startswith("PRICE_INSIDE_TESTED_HTF_DEMAND") for r in c.gate("G3").reasons))

    def test_missing_location_series_is_data_insufficient(self):
        b = R.ideal_mit_builder()
        b.series.pop("M")
        b.zones = {k: v for k, v in b.zones.items() if not k.startswith("M:")}
        c = R.only(R.evaluate(b))
        self.assertEqual((gates(c)["G3"], c.status), (m.DATA_INSUFFICIENT, m.STATUS_DATA_INSUFFICIENT))

    def test_positions_on_exact_levels_are_both_neighbours(self):
        bot = structure.ZoneView("M", "b", "demand", "DBR", 0.0 + 100, 90.0, 90.0, "", m.Z_FRESH, "FRESH", [], True, "", 7)
        top = structure.ZoneView("M", "t", "supply", "RBD", 200.0, 210.0, 210.0, "", m.Z_FRESH, "FRESH", [], True, "", 7)
        cv = {"bottom": bot, "top": top, "issues": []}
        self.assertEqual(structure.positions(cv, 133.33), {structure.LOC, structure.EQB})
        self.assertEqual(structure.positions(cv, 166.66), {structure.EQB, structure.HOC})
        self.assertEqual(structure.positions(cv, 100.0), {structure.VLOC, structure.LOC})
        self.assertEqual(structure.positions(cv, 95.0), {structure.VLOC})
        self.assertEqual(structure.positions(cv, 85.0), {structure.BELOW_CURVE})
        self.assertEqual(structure.positions(cv, 205.0), {structure.VHOC})
        self.assertEqual(structure.positions(cv, 120.0), {structure.LOC})


class Trend(unittest.TestCase):
    def test_clock_thresholds_are_pines_strict_inequalities(self):
        self.assertEqual(trend.clock_position(2.0), "1 o'clock")
        self.assertEqual(trend.clock_position(2.0001), "12 o'clock")
        self.assertEqual(trend.clock_position(0.1), "3 o'clock")
        self.assertEqual(trend.clock_position(-0.1), "3-4 o'clock")
        self.assertEqual(trend.clock_position(-2.0), "6 o'clock")

    def test_insufficient_history_is_never_sideways(self):
        r = trend.reading_from_closes([100.0] * 54)
        self.assertEqual((r["status"], r["readings"]), (trend.INSUFFICIENT_HISTORY, []))
        self.assertEqual(trend.reading_from_closes([100.0] * 55)["readings"], [trend.SIDEWAYS])

    def test_extreme_up_label_is_preserved_while_matrix_reading_is_strong_up(self):
        reading = trend.reading_from_closes(R.rising(60))
        self.assertEqual(reading["position"], "12 o'clock")
        self.assertEqual(reading["readings"], [trend.STRONG_UP])
        self.assertEqual(reading["rulebook_label"], "Extreme Uptrend")

    def test_weekly_trend_cases(self):
        def run(closes, price=950.0):
            b = R.ideal_mit_builder()
            b.add_series("W", closes)
            b.add_zone("W", "supply", 1200.0, 1230.0)
            return R.only(R.evaluate(b, price=price))
        flat = run([900.0] * 60)
        self.assertEqual((gates(flat)["G4"], flat.status), (m.MANUAL, m.MANUAL_REVIEW))    # LOC + Sideways: sector
        short = run(R.rising(54))
        self.assertEqual(gates(short)["G4"], m.MANUAL)
        self.assertIn("TREND_INSUFFICIENT_HISTORY", short.gate("G4").manual_review)
        one = R.rising(60, step=0.003)            # about 1.5% over 5 candles: 1 o'clock (strong or moderate)
        self.assertEqual(trend.reading_from_closes(one)["position"], "1 o'clock")
        self.assertEqual(gates(run(one))["G4"], m.PASS)                 # LOC: both readings pass
        self.assertEqual(gates(run(one, price=1150.0))["G4"], m.MANUAL)  # EQB: only Strong Up passes

    def test_truncated_weekly_series_is_data_insufficient(self):
        b = R.ideal_mit_builder()
        b.series["W"].truncated_at = "2025-W20"
        c = R.only(R.evaluate(b))
        self.assertEqual(gates(c)["G4"], m.DATA_INSUFFICIENT)

    def test_monthly_trend_is_context_not_a_gate(self):
        b = R.ideal_mit_builder()
        b.series["M"].candles[:] = R.SnapBuilder().add_series("M", falling(60)).series["M"].candles
        c = R.only(R.evaluate(b))
        self.assertEqual(c.status, ACT)                                  # D21: never a gate
        self.assertTrue(any("M trend context reads down" in e for e in c.evidence_against))

    def test_weekly_sideways_at_vloc_is_extreme_caution(self):
        b = R.ideal_mit_builder()
        b.series["D"].engine.assessments.clear()
        b.zones = {k: v for k, v in b.zones.items() if not k.startswith("D:")}
        b.add_zone("D", "demand", 680.0, 660.0, created_index=50)
        b.add_series("W", [900.0] * 60)
        b.add_zone("W", "supply", 1200.0, 1230.0)
        c = R.only(R.evaluate(b, price=690.0))
        self.assertEqual(c.gate("G3").evidence["position_at_price"], [structure.VLOC])
        self.assertEqual(gates(c)["G6"], m.PASS)
        self.assertEqual(gates(c)["G4"], m.MANUAL)
        self.assertIn("RB 1232", " ".join(c.gate("G4").reasons))

    def test_matrix_rows(self):
        X = q.matrix_long
        self.assertEqual(X(structure.LOC, trend.DOWN, None)[0], m.FAIL)
        self.assertEqual(X(structure.EQB, trend.SIDEWAYS, None)[0], m.FAIL)
        self.assertEqual(X(structure.EQB, trend.DOWN, None)[0], m.FAIL)  # R5 / RB 1599
        self.assertEqual(X(structure.HOC, trend.STRONG_UP, None)[0], m.FAIL)
        self.assertEqual(X(structure.HOC, trend.SIDEWAYS, None)[0], m.MANUAL)
        self.assertEqual(X(structure.HOC, trend.DOWN, None)[0], m.MANUAL)  # RF3 decides in G8
        self.assertEqual(X(structure.VHOC, trend.STRONG_UP, None)[0], m.FAIL)
        self.assertEqual(X(structure.VLOC, trend.DOWN, None)[0], m.MANUAL)
        self.assertEqual(X(structure.VLOC, trend.SIDEWAYS, structure.COINCIDING)[0], m.PASS)
        self.assertEqual(X(structure.VLOC, trend.SIDEWAYS, structure.ABOVE_HTF_PL)[0], m.MANUAL)
        self.assertEqual(X(structure.LOC, trend.MILD_UP, None)[0], m.MANUAL)


class ApprovedR5(unittest.TestCase):
    def evaluate_at(self, price, weekly_closes):
        b = R.ideal_mit_builder()
        b.add_series("W", weekly_closes)
        b.add_zone("W", "supply", 1200.0, 1230.0)
        return R.only(R.evaluate(b, price=price))

    def test_eqb_down_rejects_long(self):
        c = self.evaluate_at(1150.0, falling(60))
        self.assertEqual(c.gate("G3").evidence["position_at_price"], [structure.EQB])
        self.assertEqual((c.gate("G4").outcome, c.status), (m.FAIL, m.REJECTED))

    def test_hoc_sideways_is_manual_pending_sector_support(self):
        c = self.evaluate_at(1400.0, [900.0] * 60)
        self.assertEqual(c.gate("G3").evidence["position_at_price"], [structure.HOC])
        self.assertEqual((c.gate("G4").outcome, c.status), (m.MANUAL, m.MANUAL_REVIEW))

    def test_hoc_down_follows_rf3_without_exception(self):
        c = self.evaluate_at(1400.0, falling(60))
        self.assertEqual(c.gate("G4").outcome, m.MANUAL)
        self.assertIn("RF3 trend strongly against: FAIL", " ".join(c.gate("G8").reasons))
        self.assertEqual(c.status, m.REJECTED)


def with_m_supply(pl, dl, status=mtf.FRESH):
    b = R.ideal_mit_builder()
    b.add_zone("M", "supply", pl, dl, status=status, zid="m-opposing")
    return b


class G5(unittest.TestCase):
    def test_fresh_monthly_supply_within_5_percent_rejects(self):
        c = R.only(R.evaluate(with_m_supply(920.0, 960.0)))
        self.assertEqual((gates(c)["G5"], c.status), (m.FAIL, m.REJECTED))

    def test_tested_or_5_to_10_percent_is_review(self):
        self.assertEqual(gates(R.only(R.evaluate(with_m_supply(920.0, 960.0, mtf.TESTED))))["G5"], m.MANUAL)
        self.assertEqual(gates(R.only(R.evaluate(with_m_supply(960.0, 990.0))))["G5"], m.MANUAL)
        self.assertEqual(gates(R.only(R.evaluate(with_m_supply(920.0, 960.0, mtf.UNKNOWN_DATA_GAP))))["G5"], m.MANUAL)

    def test_broken_opposing_zone_is_no_conflict(self):
        c = R.only(R.evaluate(with_m_supply(920.0, 960.0, mtf.INVALIDATED)))
        self.assertEqual((gates(c)["G5"], c.status), (m.PASS, ACT))         # RB 1313

    def test_the_measuring_point_can_decide(self):
        c = R.only(R.evaluate(with_m_supply(935.0, 960.0)))     # 5.06% from the PL, 4.47% from the entry max
        self.assertEqual(gates(c)["G5"], m.MANUAL)

    def test_weekly_supply_within_10_percent_is_evidence_for_review(self):
        b = R.ideal_mit_builder()
        b.add_zone("W", "supply", 960.0, 990.0, status=mtf.TESTED)
        self.assertEqual(gates(R.only(R.evaluate(b)))["G5"], m.MANUAL)

    def test_missing_htf_series_is_never_no_conflict(self):
        b = R.ideal_mit_builder()
        b.series.pop("Q")
        c = R.only(R.evaluate(b))
        self.assertEqual((gates(c)["G5"], c.status), (m.DATA_INSUFFICIENT, m.STATUS_DATA_INSUFFICIENT))
        b = R.ideal_mit_builder()
        b.series.pop("Y")
        self.assertEqual(gates(R.only(R.evaluate(b)))["G5"], m.MANUAL)
        b = R.ideal_mit_builder()
        b.add_series("HY", [800.0, 820.0])            # too short for the engine
        self.assertEqual(gates(R.only(R.evaluate(b)))["G5"], m.DATA_INSUFFICIENT)


class G6(unittest.TestCase):
    def test_non_overlapping_execution_zone_above_htf_is_aggressive_manual(self):
        b = R.ideal_mit_builder()
        b.zones["M:m-coinciding"].dl_touched_at = R.AS_OF          # D15: DL touched -> no longer qualifies
        c = R.only(R.evaluate(b))
        self.assertEqual((gates(c)["G6"], c.status), (m.MANUAL, m.MANUAL_REVIEW))
        self.assertEqual(c.gate("G6").evidence["class"], structure.AGGRESSIVE)
        self.assertIn("G6:AGGRESSIVE_ENTRY_REVIEW", c.manual_review)

    def test_actual_range_overlap_is_coinciding_even_if_execution_pl_is_above_htf_pl(self):
        b = R.ideal_mit_builder()
        b.series["D"].engine.assessments.clear()
        b.zones = {k: v for k, v in b.zones.items() if not k.startswith("D:")}
        b.add_zone("D", "demand", 910.0, 880.0, created_index=50)
        c = R.only(R.evaluate(b, price=950.0))
        self.assertEqual(c.gate("G6").outcome, m.PASS)
        self.assertEqual(c.gate("G6").evidence["class"], structure.COINCIDING)
        self.assertEqual(c.gate("G6").evidence["execution_range"], [880.0, 910.0])

    def test_exact_shared_boundary_counts_as_overlap(self):
        b = R.ideal_mit_builder()
        b.series["D"].engine.assessments.clear()
        b.zones = {k: v for k, v in b.zones.items() if not k.startswith("D:")}
        b.add_zone("D", "demand", 920.0, 900.0, created_index=50)
        c = R.only(R.evaluate(b, price=950.0))  # monthly demand ends at PL 900
        self.assertEqual(c.gate("G6").evidence["class"], structure.COINCIDING)

    def test_below_the_htf_dl_is_invalid(self):
        b = R.ideal_mit_builder()
        b.series["D"].engine.assessments.clear()
        b.zones = {k: v for k, v in b.zones.items() if not k.startswith("D:")}
        b.add_zone("D", "demand", 640.0, 620.0, created_index=50)
        c = R.only(R.evaluate(b))
        self.assertEqual((gates(c)["G6"], c.status), (m.FAIL, m.REJECTED))

    def test_hidden_dl_status_needs_review(self):
        b = R.ideal_mit_builder()
        b.zones["M:m-coinciding"].status = mtf.UNKNOWN_DATA_GAP
        self.assertEqual(gates(R.only(R.evaluate(b)))["G6"], m.MANUAL)

    def test_unknown_freshness_is_not_assumed_qualifying_for_coinciding(self):
        b = R.ideal_mit_builder()
        # The HTF zone has no recorded DL touch, but its overlay freshness is unresolved.
        b.zones["M:m-coinciding"].status = mtf.MANUAL_REVIEW
        c = R.only(R.evaluate(b))
        self.assertEqual(c.gate("G6").outcome, m.MANUAL)
        self.assertEqual(c.gate("G6").evidence["class"], structure.HTF_ZONE_STATUS_UNKNOWN)
        self.assertTrue(any("freshness or DL-touch status is unknown" in r for r in c.gate("G6").reasons))

    def test_no_qualifying_zone_is_a_standard_setup(self):
        cls, zone, unknown = structure.coinciding([], 100.0, 90.0)
        self.assertEqual((cls, zone, unknown), (structure.NO_QUALIFYING_HTF_ZONE, None, []))

    def test_known_absence_passes_g6_but_missing_curve_still_blocks_candidate(self):
        b = R.ideal_mit_builder()
        b.series["M"].engine.assessments[:] = [a for a in b.series["M"].engine.assessments
                                               if a.zone.side != "demand"]
        b.zones = {k: v for k, v in b.zones.items() if not (k.startswith("M:") and v.side == "demand")}
        c = R.only(R.evaluate(b))
        self.assertEqual(c.gate("G6").outcome, m.PASS)
        self.assertEqual(c.gate("G3").outcome, m.MANUAL)
        self.assertNotEqual(c.status, m.ACTIONABLE)

    def test_unknown_dl_status_is_not_known_absence(self):
        b = R.ideal_mit_builder()
        b.zones["M:m-coinciding"].status = mtf.UNKNOWN_DATA_GAP
        b.zones["M:m-bottom"].status = mtf.UNKNOWN_DATA_GAP
        c = R.only(R.evaluate(b))
        self.assertEqual(c.gate("G6").outcome, m.MANUAL)
        self.assertNotEqual(c.status, m.ACTIONABLE)


class G7(unittest.TestCase):
    def _target(self, pl, status=mtf.FRESH):
        b = R.ideal_mit_builder()
        b.zones.pop([k for k in b.zones if k.startswith("W:")][0])
        b.series["W"].engine.assessments.clear()
        if pl is not None:
            b.add_zone("W", "supply", pl, pl + 30.0, status=status)
        return R.only(R.evaluate(b))

    def test_rr_cases(self):
        self.assertEqual(self._target(1200.0).gate("G7").outcome, m.PASS)
        fail = self._target(905.0)
        self.assertEqual((fail.gate("G7").outcome, fail.status), (m.FAIL, m.REJECTED))
        self.assertIn("RF8", fail.gate("G7").reasons[0])
        self.assertEqual(self._target(950.0).gate("G7").outcome, m.MANUAL)          # depends on the buffer

    def test_no_or_unknown_target_is_review_with_a_reference_only(self):
        none = self._target(None)
        self.assertEqual(none.gate("G7").outcome, m.MANUAL)
        self.assertIn("mathematical_2_to_1_reference", none.gate("G7").evidence)
        self.assertEqual(self._target(1200.0, mtf.UNKNOWN_DATA_GAP).gate("G7").outcome, m.MANUAL)
        self.assertEqual(self._target(1200.0, mtf.TESTED).gate("G7").outcome, m.MANUAL)   # skipped; none left

    def test_ranges_use_every_tier_that_could_apply(self):
        r = levels.ranges(500.0, 480.0, 490.0)        # 500 sits on a printed tier edge (B9)
        self.assertEqual(r["entry"], [500.5, 505.0])
        self.assertEqual(r["sl"]["normal"], [482.0, 489.0])
        self.assertEqual(r["sl"]["exceptional"], [472.0, 479.0])
        self.assertEqual(levels.quantity_range(r, 1000.0), [30, 86])     # widest risk first
        self.assertIsNone(levels.quantity_range(r, None))


class Levels(unittest.TestCase):
    def test_quantity_uses_exact_prices_regression(self):
        # defect found 2026-11-02: float 100.30 - 100.10 floored 1000 / risk to 4999 (RB 2162)
        rng = {"entry": [100.3, 100.3], "sl": {"normal": [100.1, 100.1], "exceptional": [100.1, 100.1]}}
        self.assertEqual(levels.quantity_range(rng, 1000.0), [5000, 5000])
        rng = {"entry": [983.0, 983.0], "sl": {"normal": [963.0, 963.0], "exceptional": [963.0, 963.0]}}
        self.assertEqual(levels.quantity_range(rng, 1000.0), [50, 50])          # RB 2169-2179

    def test_rr_range_equals_the_brute_force_extremes(self):
        import itertools
        import random
        rnd = random.Random(5)
        for _ in range(200):
            dl = rnd.uniform(5, 3000)
            normal = dl + rnd.uniform(0, dl * 0.02)
            pl = normal + rnd.uniform(0.05, dl * 0.05)
            rng = levels.ranges(pl, dl, normal)
            self.assertTrue(rng["valid"], rng["problems"])
            target = rng["entry"][1] + rnd.uniform(0.1, pl * 0.3)
            entries = [rng["entry"][0] + (rng["entry"][1] - rng["entry"][0]) * i / 10 for i in range(11)]
            sls = [a + (b - a) * i / 10 for a, b in rng["sl"].values() for i in range(11)]
            rrs = [(target - e) / (e - s) for e, s in itertools.product(entries, sls)]
            got = levels.rr_range(rng, target)["rr"]
            self.assertAlmostEqual(got[0], min(rrs), places=3)
            self.assertAlmostEqual(got[1], max(rrs), places=3)
            self.assertLess(rng["sl"]["exceptional"][1], dl + 1e-9)
            self.assertGreater(rng["entry"][0], pl)

    def test_invalid_levels_are_reported_not_computed(self):
        self.assertIn("STOP_LOSS_NOT_POSITIVE", " ".join(levels.ranges(0.9, 0.6, 0.7)["problems"]))
        self.assertIn("ZONE_GEOMETRY_INVALID", " ".join(levels.ranges(100.0, 105.0, 105.0)["problems"]))
        self.assertIn("ZONE_GEOMETRY_INVALID", " ".join(levels.ranges(100.0, 95.0, 90.0)["problems"]))
        self.assertFalse(levels.ranges(float("nan"), 1.0, 1.0)["valid"])
        b = R.ideal_mit_builder()
        b.series["D"].engine.assessments.clear()
        b.zones = {k: v for k, v in b.zones.items() if not k.startswith("D:")}
        b.add_zone("D", "demand", 0.9, 0.6, normal_dl=0.7, created_index=50)
        c = R.only(R.evaluate(b, price=1.0))
        g7 = c.gate("G7")
        self.assertEqual(g7.outcome, m.MANUAL)
        self.assertIn("LEVELS_INVALID", g7.manual_review)
        self.assertNotIn("rr", g7.evidence)
        self.assertIsNone(g7.evidence.get("quantity"))
        self.assertNotEqual(c.status, m.ACTIONABLE)

    def test_target_inside_the_entry_range_or_below_is_never_a_target(self):
        zone = structure.ZoneView("W", "s", "supply", "RBD", 1003.0, 1010.0, 1010.0, "", m.Z_FRESH, "FRESH", [], True, "", 7)
        t, issue = levels.select_target([zone], 1005.0, 1000.0)
        self.assertIsNone(t)
        self.assertTrue(issue.startswith("TARGET_ZONE_INSIDE_ENTRY_RANGE"))
        below = structure.ZoneView("W", "b", "supply", "RBD", 990.0, 995.0, 995.0, "", m.Z_FRESH, "FRESH", [], True, "", 7)
        self.assertEqual(levels.select_target([below], 1005.0, 1000.0), (None, "NO_FRESH_SUPPLY_ABOVE_ENTRY"))


class G8(unittest.TestCase):
    def test_trend_clearly_against_is_rf3(self):
        b = R.ideal_mit_builder()
        b.add_series("W", falling(60, 1000.0))
        b.add_zone("W", "supply", 1200.0, 1230.0)
        self.assertEqual(gates(R.only(R.evaluate(b)))["G8"], m.FAIL)

    def test_poor_closing_and_missing_inputs_are_review(self):
        b = R.ideal_mit_builder()
        b.series["D"].engine.assessments[0].zone.strong_closing = False
        self.assertIn("RF7", R.only(R.evaluate(b)).gate("G8").manual_review)
        no_rpt = R.only(R.evaluate(R.ideal_mit_builder(), risk=None))
        self.assertEqual((gates(no_rpt)["G8"], no_rpt.status), (m.MANUAL, m.MANUAL_REVIEW))
        b = R.ideal_mit_builder()
        b.series.pop("Y")
        self.assertIn("EC1", R.only(R.evaluate(b)).gate("G8").manual_review)


if __name__ == "__main__":
    unittest.main()
