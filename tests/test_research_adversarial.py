"""Adversarial tests: each one tries to break an invariant of the research pipeline.
Numbers refer to the questions in docs/owner/MASTER_IMPLEMENTATION_PROMPT.md section 21.11. SYNTHETIC data only.
"""

import json
import os
import re
import unittest
from unittest import mock

import _research as R
from _load import ROOT
from nse.research import models as m, qualification as q, readiness, reports, scanner, structure
from nse.research.deps import mtf, reference


def sweep(seeds=range(8), n=430):
    for seed in seeds:
        cs = R.random_walk(seed, n)
        cfg = scanner.ScanConfig(as_of=cs[-1].end, calendar=R.WeekdayCalendar(), calendar_label="TEST")
        snap = mtf.replay(cs, "D", htf=scanner.HTF, as_of=cs[-1].end, calendar=R.WeekdayCalendar())
        yield seed, scanner.scan([R.daily_input("S%d" % seed, cs)], cfg), snap


def replace_d_zone(b, status, engine_test_count=0, overlay_manual=()):
    """Keep the engine's ELIGIBLE verdict but give the overlay a different view."""
    key = [k for k in b.zones if k.startswith("D:")][0]
    st = b.zones[key]
    st.status = status
    st.manual_review = list(overlay_manual)
    if status == mtf.TESTED:
        st.base_touch_count, st.first_touch_at = 1, R.AS_OF
    b.series["D"].engine.assessments[0].zone.test_count = engine_test_count
    return b


class Invariants(unittest.TestCase):
    def test_q1_no_tested_zone_in_any_fresh_zone_report(self):
        for seed, res, snap in sweep():
            for z in res.symbols[0].fresh_zones:
                st = snap.zones["%s:%s" % (z["tf"], z["zone_id"])]
                self.assertTrue(st.usable_as_fresh_context, (seed, z["zone_id"]))
                self.assertEqual((st.base_touch_count, st.status), (0, mtf.FRESH))

    def test_q2_q4_engine_eligible_zone_the_overlay_rejects_never_reappears(self):
        for status in (mtf.TESTED, mtf.INVALIDATED, mtf.BASE_CLOSE_BEYOND_DL_PENDING):
            out = R.evaluate(replace_d_zone(R.ideal_mit_builder(), status))
            self.assertEqual(out["candidates"], [], status)
            self.assertEqual(len(out["blocked_zones"]), 1)
            self.assertIn(mtf.OVERLAY_NOT_FRESH, out["blocked_zones"][0]["reasons"])

    def test_q3_missing_history_is_not_freshness(self):
        for status in (mtf.UNKNOWN_DATA_GAP, mtf.UNVERIFIED_SESSION):
            out = R.evaluate(replace_d_zone(R.ideal_mit_builder(), status))
            self.assertEqual(out["candidates"], [])
            self.assertEqual(out["blocked_zones"][0]["disposition"], m.STATUS_DATA_INSUFFICIENT)
        out = R.evaluate(replace_d_zone(R.ideal_mit_builder(), mtf.MANUAL_REVIEW,
                                        overlay_manual=[mtf.EXCLUDED_SESSION_TOUCH]))
        self.assertEqual(out["candidates"], [])

    def test_q4_research_code_never_bypasses_the_overlay(self):
        folder = os.path.join(ROOT, "nse", "research")
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(folder, name), encoding="utf-8") as fh:
                src = fh.read()
            self.assertNotIn("run_engine(", src, name)
            self.assertIsNone(re.search(r"\.eligible\b(?!_after_overlay)", src), name)
        # the only zone sources in the qualification pathway are the two overlay methods
        with open(os.path.join(folder, "qualification.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("snap.eligible_after_overlay(exec_tf)", src)
        self.assertIn("snap.manual_review_after_overlay(exec_tf)", src)

    def test_candidates_equal_overlay_kept_zones_across_a_sweep(self):
        for seed, res, snap in sweep():
            kept = sorted(a.zone.id for a in snap.eligible_after_overlay("D")[0] + snap.manual_review_after_overlay("D")[0])
            self.assertEqual(sorted(c.zone["zone_id"] for c in res.candidates()), kept, seed)
            for c in res.candidates():
                self.assertEqual((c.zone["side"], c.zone["test_count"], c.zone["overlay_status"]),
                                 ("demand", 0, mtf.FRESH))


class Propagation(unittest.TestCase):
    def _manual_candidate(self):
        b = R.ideal_mit_builder()
        b.zones["M:m-coinciding"].dl_touched_at = R.AS_OF     # G6 -> MANUAL
        return R.only(R.evaluate(b))

    def test_q5_manual_review_survives_json_and_csv(self):
        c = self._manual_candidate()
        res = scanner.ScanResult("v", {}, R.AS_OF.isoformat(), None, m.MIT, "TEST", "ADHOC",
                                 [scanner.SymbolResult("SYN", scanner.SYMBOL_EVALUATED, [], 950.0, [c], [], [], [], {},
                                                       [], {}, [])])
        back = json.loads(reports.to_json(res))
        bc = back["symbols"][0]["candidates"][0]
        self.assertEqual(bc["status"], m.MANUAL_REVIEW)
        self.assertIn("G6:AGGRESSIVE_ENTRY_REVIEW", bc["manual_review"])
        self.assertEqual([x["code"] for x in bc["manual_checks"]], [x["code"] for x in c.manual_checks])
        [row] = reports.candidate_rows(res)
        self.assertIn("AGGRESSIVE_ENTRY_REVIEW", reports._cell(row["manual_review"]))
        self.assertIn("G6:AGGRESSIVE_ENTRY_REVIEW", reports.candidates_csv(res))
        self.assertIn(m.NOT_EXTERNALLY_VALIDATED, reports.candidates_csv(res))

    def test_q6_a_failed_g0_cannot_be_overridden(self):
        c = R.only(R.evaluate(R.ideal_mit_builder(), data_errors=["OHLC_INCONSISTENT"]))
        self.assertEqual(c.status, m.STATUS_DATA_INSUFFICIENT)
        for later in m.GATES[1:]:
            gs = [m.GateResult(g, m.PASS) for g in m.GATES]
            gs[0] = m.GateResult("G0", m.DATA_INSUFFICIENT)
            self.assertNotEqual(m.derive_status(gs), m.ACTIONABLE, later)

    def test_q7_intraday_cannot_be_a_candidate(self):
        import test_research_gates as G
        for n in (1, 5, 30):
            c = R.only(R.evaluate(G.wit_builder(recency=n), trade_type=m.WIT_75))
            self.assertEqual(c.status, m.BLOCKED_STATUS)
        cs = R.random_walk(1, 300)
        res = scanner.scan([R.daily_input("X", cs)], scanner.ScanConfig(as_of=cs[-1].end, trade_type=m.WIT_125))
        self.assertEqual((res.symbols[0].status, res.candidates()), (scanner.SYMBOL_BLOCKED, []))

    def test_q9_missing_higher_timeframe_is_not_no_conflict(self):
        for tf in ("M", "Q", "HY"):
            b = R.ideal_mit_builder()
            b.series.pop(tf)
            c = R.only(R.evaluate(b))
            self.assertNotEqual(c.status, m.ACTIONABLE, tf)
            self.assertNotEqual(c.gate("G5").outcome, m.PASS, tf)

    def test_q10_nothing_claims_external_validation(self):
        for row in readiness.report():
            self.assertFalse(row["externally_validated"], row["id"])
        for seed, res, snap in sweep(range(2)):
            self.assertIn(m.NOT_EXTERNALLY_VALIDATED, res.limitations)
            for c in res.candidates():
                self.assertIn(m.NOT_EXTERNALLY_VALIDATED, c.limitations)
                self.assertIn(m.TRADINGVIEW_PARITY_UNVERIFIED, c.limitations)
        self.assertNotIn("VALIDATED", [s for s in m.STATUS_ORDER])

    def test_q10_readiness_marks_unrun_or_failed_tests_unconfirmed(self):
        rows = {r["id"]: r for r in readiness.report(passed_modules={"test_zone_engine"})}
        self.assertEqual(rows["zone_engine"]["unit_tested_state"], "CONFIRMED")
        self.assertTrue(rows["mtf_overlay"]["unit_tested_state"].startswith("UNCONFIRMED"))
        self.assertTrue(rows["corporate_actions"]["blocked"])

    def test_q11_missing_reference_is_not_a_match(self):
        self.assertFalse(reference.coverage_summary([])["complete"])

    def test_q12_unresolved_rules_never_default_to_pass(self):
        X = q.matrix_long
        self.assertEqual(X(structure.LOC, "SIDEWAYS", None)[0], m.MANUAL)          # sector (D6)
        self.assertEqual(X(structure.HOC, "SIDEWAYS", None)[0], m.MANUAL)
        self.assertEqual(self._manual_candidate().gate("G6").outcome, m.MANUAL)     # touch tolerance
        no_rpt = R.only(R.evaluate(R.ideal_mit_builder(), risk=None))
        self.assertNotEqual(no_rpt.status, m.ACTIONABLE)
        b = R.ideal_mit_builder()
        b.add_series("W", R.rising(30))
        b.add_zone("W", "supply", 1200.0, 1230.0)
        self.assertEqual(R.only(R.evaluate(b)).gate("G4").outcome, m.MANUAL)          # never "sideways"

    def test_q13_equivalent_scans_agree(self):
        cs = R.random_walk(21, 420)
        cfg = scanner.ScanConfig(as_of=cs[-1].end, calendar=R.WeekdayCalendar())
        first = reports.to_json(scanner.scan([R.daily_input("A", cs)], cfg))
        for _ in range(3):
            self.assertEqual(reports.to_json(scanner.scan([R.daily_input("A", list(cs))], cfg)), first)


class LongHistory(unittest.TestCase):
    """On the long SYNTHETIC history (real replay)."""

    def test_an_in_progress_higher_timeframe_period_never_reaches_a_decision(self):
        cs = R.long_mit_candles()
        legout = [i for i, c in enumerate(cs) if c.close == round(101.5 * R.LONG_K, 2)][0]
        t = cs[legout + 1]                                   # mid-January 2024, a Wednesday
        snap = mtf.replay(cs, "D", htf=scanner.HTF, as_of=t.end, calendar=R.WeekdayCalendar())
        # January, Q1, H1, 2024 and the current week are all still forming at t
        self.assertEqual(snap.series["M"].candles[-1].period_key, "2023-12")
        self.assertEqual(snap.series["M"].in_progress_period, "2024-01")
        week = mtf.period_key("W", t.start.date())
        self.assertEqual(snap.series["W"].in_progress_period, week)
        for tf, key in (("Q", "2023-Q4"), ("HY", "2023-H2"), ("Y", "2023")):
            self.assertEqual(snap.series[tf].candles[-1].period_key, key, tf)
        self.assertNotIn(week, [c.period_key for c in snap.series["W"].candles])
        # the January dip is in no completed Monthly candle, so the Monthly RBR zone it touched
        # is TESTED through the daily overlay, which the engine's own Monthly view cannot see yet
        m_zone = [z for z in snap.zones.values() if z.tf == "M" and z.pattern == "RBR"][0]
        self.assertEqual((m_zone.status, m_zone.htf_test_count), (mtf.TESTED, 0))
        self.assertEqual(m_zone.events[0].source_tf, "D")
        self.assertLess(m_zone.first_touch_at, t.end)
        # and the candidate at t is identical whether or not later candles exist
        a = scanner.scan([R.daily_input("SYN", cs[:legout + 2])], scanner.ScanConfig(as_of=t.end, calendar=R.WeekdayCalendar()))
        b = scanner.scan([R.daily_input("SYN", cs)], scanner.ScanConfig(as_of=t.end, calendar=R.WeekdayCalendar()))
        self.assertEqual(reports.to_dict(a), reports.to_dict(b))

    def test_reports_make_no_unsupported_claim(self):
        cs = R.long_mit_candles()
        res = scanner.scan([R.daily_input("SYN", cs)], scanner.ScanConfig(as_of=cs[-1].end, calendar=R.WeekdayCalendar(),
                                                                          risk_per_trade=1000.0))
        text = (reports.to_json(res) + reports.candidates_csv(res) + json.dumps(reports.summary(res))).lower()
        for claim in ("profitable", "approved for trading", "validated against tradingview", "guaranteed"):
            self.assertNotIn(claim, text, claim)
        # "externally validated" may appear only negated
        rest = text.replace("not_externally_validated", "").replace("nothing here is externally validated", "")
        self.assertNotIn("externally validated", rest)
        self.assertIn("no status approves a trade", text)


class TestsExerciseTheirPath(unittest.TestCase):
    """Q14: a gate whose check is disabled must change the outcome of the scenario built
    to fail it. If these canaries stopped failing, the gate tests would prove nothing."""

    def test_each_single_change_moves_the_ideal_scenario_off_actionable(self):
        b = R.ideal_mit_builder()
        b.add_zone("M", "supply", 920.0, 940.0, zid="m-opposing")     # below the price: only G5 sees it
        self.assertEqual(R.only(R.evaluate(b)).status, m.REJECTED)
        self.assertEqual(R.only(R.evaluate(R.ideal_mit_builder())).status, m.ACTIONABLE)

    def test_disabling_the_conflict_gate_is_detected(self):
        b = R.ideal_mit_builder()
        b.add_zone("M", "supply", 920.0, 940.0, zid="m-opposing")
        self.assertEqual(R.only(R.evaluate(b)).gate("G5").outcome, m.FAIL)
        with mock.patch.object(q.structure, "htf_conflict", return_value=(m.PASS, ["disabled"], [])):
            self.assertEqual(R.only(R.evaluate(b)).status, m.ACTIONABLE)

    def test_disabling_the_matrix_is_detected(self):
        b = R.ideal_mit_builder()
        b.add_series("W", [1000.0 * 0.99 ** i for i in range(60)])
        b.add_zone("W", "supply", 1200.0, 1230.0)
        self.assertEqual(R.only(R.evaluate(b)).status, m.REJECTED)
        with mock.patch.object(q, "matrix_long", return_value=(m.PASS, "disabled")), \
                mock.patch.object(q, "_g8", return_value=m.GateResult("G8", m.PASS)):
            # the RB 1232 caution still holds it at review, but the matrix rejection is gone
            self.assertEqual(R.only(R.evaluate(b)).status, m.MANUAL_REVIEW)


class _Prebuilt(object):
    """A SnapBuilder stand-in that hands evaluate() an already-edited snapshot."""
    def __init__(self, snap):
        self.snap = snap

    def build(self):
        return self.snap


class AuditRegressions20261106(unittest.TestCase):
    """Defects confirmed by the 2026-11-06 multi-agent audit, each reproduced end to end
    with the real replay before the fix."""

    def _long_scan(self, candles, as_of, calendar=None):
        cfg = scanner.ScanConfig(as_of=as_of, calendar=calendar or R.WeekdayCalendar(), calendar_label="T",
                                 risk_per_trade=1000.0, corporate_action_coverage=R.verified_ca("SYN"))
        s = scanner.scan([R.daily_input("SYN", candles)], cfg).symbols[0]
        return [c for c in s.candidates if c.zone["proximal"] == R.LONG_PL]

    def test_in_progress_candle_through_the_pl_is_never_a_plain_fresh_pass(self):
        import dataclasses, datetime
        cs = R.long_mit_candles()
        self.assertEqual([c.status for c in self._long_scan(cs, cs[-1].end)], [m.ACTIONABLE])
        nd = R.weekdays(cs[-1].start.date() + datetime.timedelta(1), 1)[0]
        noon = datetime.datetime.combine(nd, datetime.time(12, 0))
        inprog = dataclasses.replace(R.candle(nd, 170.0, 170.5, R.LONG_PL - 0.5, 170.0), end=noon, complete=False)
        [c] = self._long_scan(cs + [inprog], noon)
        self.assertEqual(c.gate("G1").outcome, m.MANUAL)
        self.assertIn(m.INCOMPLETE_CANDLE_TOUCH, c.gate("G1").manual_review)
        self.assertEqual(c.status, m.MANUAL_REVIEW)
        # an in-progress candle that stays above the PL changes nothing (completed candles only)
        above = dataclasses.replace(inprog, low=R.LONG_PL + 1.0)
        self.assertEqual([x.status for x in self._long_scan(cs + [above], noon)], [m.ACTIONABLE])

    def test_excluded_session_touch_on_a_coinciding_htf_dl_is_unknown_not_untouched(self):
        import datetime
        base = R.long_mit_candles()
        first = base[-17].start.date()
        sunday = first - datetime.timedelta(days=first.weekday() + 1)
        muhurat = R.candle(sunday, 165.0, 166.0, 148.0, 165.0)        # below the Monthly DL

        class Cal(R.WeekdayCalendar):
            def session_type(self, d):
                return "EXCLUDED_MUHURAT" if d == sunday else "CLOSED"

        [c] = self._long_scan(sorted(base + [muhurat], key=lambda x: x.start), base[-1].end, Cal())
        self.assertNotEqual(c.status, m.ACTIONABLE)
        self.assertEqual(c.gate("G6").outcome, m.MANUAL)
        self.assertIsNot(c.gate("G6").evidence.get("htf_zone_dl_untouched"), True)

    def test_tested_htf_zone_with_a_later_gap_has_unknown_dl_status(self):
        import datetime
        b = R.ideal_mit_builder()
        snap = b.build()
        key = [k for k in snap.zones if k.startswith("M:")][0]
        st = snap.zones[key]
        st.status, st.first_touch_at, st.manual_review = mtf.TESTED, R.AS_OF - datetime.timedelta(days=30), []
        snap.data_gaps.append(mtf.DataGap(R.AS_OF.date() - datetime.timedelta(days=5), True, "MISSING_SESSION"))
        view = [v for v in structure.zone_views(snap, "M") if "%s:%s" % ("M", v.zone_id) == key][0]
        self.assertIsNone(view.dl_untouched)

    def test_a_gap_between_formation_and_the_first_touch_also_hides_the_dl(self):
        # Agent 6 review H1: the window starts at formation, not at the first touch
        import datetime
        b = R.ideal_mit_builder()
        snap = b.build()
        st = snap.zones["M:m-coinciding"]
        st.first_touch_at = R.AS_OF - datetime.timedelta(days=2)
        gap_day = st.creation_period_end.date() + datetime.timedelta(days=1)
        self.assertLess(gap_day, st.first_touch_at.date())
        snap.data_gaps.append(mtf.DataGap(gap_day, True, "MISSING_SESSION"))
        [v] = [v for v in structure.zone_views(snap, "M") if v.zone_id == "m-coinciding"]
        self.assertIsNone(v.dl_untouched)
        c = R.only(R.evaluate(_Prebuilt(snap)))
        self.assertNotEqual(c.status, m.ACTIONABLE)
        self.assertEqual(c.gate("G6").outcome, m.MANUAL)

    def test_a_forming_candle_stamped_with_its_scheduled_close_is_still_touch_evidence(self):
        # Agent 6 review H2: the forming bar is end=15:30 while as_of is noon
        import dataclasses, datetime
        cs = R.long_mit_candles()
        nd = R.weekdays(cs[-1].start.date() + datetime.timedelta(1), 1)[0]
        noon = datetime.datetime.combine(nd, datetime.time(12, 0))
        forming = dataclasses.replace(R.candle(nd, 170.0, 170.5, R.LONG_PL - 0.5, 170.0), complete=False)
        self.assertGreater(forming.end, noon)
        [c] = self._long_scan(cs + [forming], noon)
        self.assertEqual((c.gate("G1").outcome, c.status), (m.MANUAL, m.MANUAL_REVIEW))
        # and the fresh-zone report says the same thing as G1 (review M1)
        cfg = scanner.ScanConfig(as_of=noon, calendar=R.WeekdayCalendar(), calendar_label="T", risk_per_trade=1000.0)
        rows = scanner.scan([R.daily_input("SYN", cs + [forming])], cfg).symbols[0].fresh_zones
        [row] = [r for r in rows if r["tf"] == "D" and r["proximal"] == R.LONG_PL]
        self.assertTrue(row["zone_level"].startswith(m.INCOMPLETE_CANDLE_TOUCH))
        # a COMPLETE candle ending after as_of is the future: never read, not even as evidence
        future = dataclasses.replace(forming, complete=True)
        self.assertEqual([x.status for x in self._long_scan(cs + [future], noon)], [m.ACTIONABLE])


class CouncilRegressions20261108(unittest.TestCase):
    """Attacks on the 2026-11-08 changes (P-LOC-2 redraw, D43, D45)."""

    def test_vloc_coinciding_with_a_tested_zone_that_is_not_the_boundary_is_manual(self):
        # the redrawn curve's fresh boundary holds price (VLOC) but the Daily zone overlaps only
        # a TESTED Monthly demand: the VLOC + Coinciding route must not open through it
        b = R.SnapBuilder()
        b.add_series("D", [700.0] * 60)
        b.add_zone("D", "demand", 690.0, 682.0, normal_dl=684.0, created_index=50)
        b.add_series("W", R.rising(60))
        b.add_zone("W", "supply", 1200.0, 1230.0)
        b.add_series("M", [800.0 + i for i in range(60)])
        b.add_zone("M", "demand", 700.0, 694.0, zid="m-fresh")
        b.add_zone("M", "demand", 692.0, 660.0, status=mtf.TESTED, zid="m-tested-in")
        b.add_zone("M", "supply", 1500.0, 1550.0, zid="m-top")
        for tf in ("Q", "HY", "Y"):
            b.add_series(tf, [800.0, 820.0, 840.0, 860.0])
        c = R.only(R.evaluate(b, price=695.0))
        self.assertEqual(c.gate("G3").evidence["position_at_price"], [structure.VLOC])
        self.assertEqual((c.gate("G6").outcome, c.gate("G6").evidence["htf_zone"]["zone_id"]), (m.MANUAL, "m-tested-in"))
        self.assertIn("COINCIDING_ZONE_IS_NOT_CURVE_BOUNDARY", c.gate("G6").manual_review)
        self.assertEqual(c.status, m.MANUAL_REVIEW)

    def test_a_redrawn_curve_never_uses_the_coinciding_bonus_away_from_vloc(self):
        # P-LOC-2 at 880: the Daily zone overlaps the skipped tested Monthly zone, so G6 may say
        # COINCIDING; the matrix only grants Coinciding at VLOC, and the position is LOC
        c = R.only(R.evaluate(R.ideal_mit_builder(), price=880.0))
        self.assertEqual(c.gate("G3").evidence["redrawn_past_tested"], ["m-coinciding"])
        self.assertNotIn(structure.VLOC, c.gate("G3").evidence["position_at_price"])
        self.assertFalse(any("Coinciding" in r for r in c.gate("G4").reasons), c.gate("G4").reasons)

    def test_a_d43_restriction_survives_every_export(self):
        cs = R.long_mit_candles(k=1.75)
        cfg = scanner.ScanConfig(as_of=cs[-1].end, calendar=R.WeekdayCalendar(), calendar_label="TEST_WEEKDAYS",
                                 risk_per_trade=1000.0)
        res = scanner.scan([R.daily_input("AGR", cs)], cfg)
        [c] = res.candidates()
        self.assertIn("G5:PINE_ONLY_ZONE_REVIEW", c.manual_review)
        self.assertNotEqual(c.status, m.ACTIONABLE)
        self.assertIn("G5:PINE_ONLY_ZONE_REVIEW", reports.candidates_csv(res))
        doc = json.loads(reports.to_json(res))
        self.assertIn("pine_only_findings", json.dumps(doc))
        self.assertIn("PINE_ONLY_ZONE_REVIEW", json.dumps(doc))

    def test_dataclasses_replace_cannot_bypass_the_d45_limits(self):
        import dataclasses
        from nse.research import backtest as bt
        ok = bt.ExecutionModel(entry="ENTRY_MAX", stop="NORMAL_WIDE", target="STRUCTURAL", statuses=(m.ACTIONABLE,),
                               entry_expiry_sessions=10, cancel_if_target_first=False, gap_fill="AT_OPEN",
                               same_bar="STOP_FIRST", cost_pct_per_side=0.0, slippage_pct_per_side=0.0)
        for over in (dict(max_open_positions=11), dict(monthly_trade_cap=None), dict(entry_expiry_sessions=20)):
            with self.assertRaises(ValueError, msg=over):
                dataclasses.replace(ok, **over)


if __name__ == "__main__":
    unittest.main()
