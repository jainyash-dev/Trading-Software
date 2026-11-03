"""Risk engine tests (nse/research/risk.py). Expected values come from the Rulebook: the
Chapter 3 worked examples (RB 2169-2204), the RPT stage table (RB 53-59, 2208-2214), the
10-trade ceiling (RB 2392, 2408), C2 R:R >= 2 (RB 82), size by risk (RB 68) and never
average down (RB 69, 2140). Candidate records are SYNTHETIC (tests/_research.py).
"""

import argparse
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

import _research as R
from nse.research import levels, models as m, reports, risk


def cfg(**kw):
    base = {"capital": 100000.0, "rpt_pct": 1.0, "stage": risk.LEARNING, "trades_this_month": 0}
    base.update(kw)
    return risk.RiskConfig(**base)


def checks(plan):
    return {c["code"]: c["outcome"] for c in plan["checks"]}


def actionable_candidate():
    c = R.only(R.evaluate(R.ideal_mit_builder()))
    assert c.status == m.ACTIONABLE, c.status
    return reports.to_dict(c)


class WorkedExamples(unittest.TestCase):
    """RB 2169-2204: capital 1,00,000, RPT 1% = 1,000."""

    def test_example_1_standard_mit_trade(self):
        p = risk.plan_trade(983.0, 963.0, 1023.0, cfg())        # 2:1 target = 983 + 2 x 20
        self.assertEqual(p["rpt_amount"], 1000.0)
        self.assertEqual(p["quantity"], 50)
        self.assertEqual(p["loss_if_stopped"], 1000.0)
        self.assertEqual(p["profit_at_target"], 2000.0)
        self.assertEqual(p["rr"], 2.0)
        self.assertEqual(checks(p)["RR_MIN_2"], m.PASS)

    def test_example_2_expensive_stock(self):
        p = risk.plan_trade(2450.0, 2400.0, None, cfg(rpt_pct=None, rpt_amount=1000.0))
        self.assertEqual((p["quantity"], p["loss_if_stopped"]), (20, 1000.0))

    def test_example_3_cheap_stock_rounds_down_to_999(self):
        p = risk.plan_trade(48.0, 45.0, None, cfg())
        self.assertEqual((p["quantity"], p["loss_if_stopped"], p["rpt_shortfall"]), (333, 999.0, 1.0))
        self.assertEqual(checks(p)["RPT_NOT_EXCEEDED"], m.PASS)      # RB 2204: 999 is accepted

    def test_never_more_than_rpt_and_exact_decimal(self):
        # 100.3 - 100.1 is 0.19999999999998863 in binary floats; the formula gives exactly 5000
        p = risk.plan_trade(100.3, 100.1, None, cfg())
        self.assertEqual((p["quantity"], p["loss_if_stopped"]), (5000, 1000.0))
        for e, s in ((983.35, 963.05), (48.1, 45.05), (2450.5, 2399.95), (101.0, 100.7)):
            p = risk.plan_trade(e, s, None, cfg())
            self.assertLessEqual(p["loss_if_stopped"], 1000.0)
            self.assertLess(p["rpt_shortfall"], p["risk_per_share"])   # floor: less than one more share

    def test_quantity_agrees_with_levels_quantity_range_on_the_examples(self):
        for e, s, q in ((983.0, 963.0, 50), (2450.0, 2400.0, 20), (48.0, 45.0, 333)):
            point = {"entry": [e, e], "sl": {"normal": [s, s], "exceptional": [s, s]}}
            self.assertEqual(levels.quantity_range(point, 1000.0), [q, q])
            self.assertEqual(risk.plan_trade(e, s, None, cfg())["quantity"], q)


class Levels(unittest.TestCase):
    def test_zero_negative_and_non_finite_distance_are_invalid(self):
        for e, s in ((100.0, 100.0), (100.0, 101.0), (float("nan"), 90.0), (100.0, float("inf"))):
            p = risk.plan_trade(e, s, 130.0, cfg())
            self.assertEqual(p["status"], risk.INVALID_LEVELS, (e, s))
            self.assertIsNone(p["quantity"])
            self.assertEqual(checks(p)["LEVELS"], m.FAIL)

    def test_non_positive_entry_or_stop_is_invalid(self):
        for e, s in ((0.0, -1.0), (-5.0, -10.0), (10.0, 0.0), (10.0, -1.0)):
            self.assertEqual(risk.plan_trade(e, s, 30.0, cfg())["status"], risk.INVALID_LEVELS)

    def test_non_finite_target_is_invalid(self):
        self.assertEqual(risk.plan_trade(100.0, 90.0, float("inf"), cfg())["status"], risk.INVALID_LEVELS)

    def test_rpt_too_small_for_one_share_fails(self):
        p = risk.plan_trade(5000.0, 3000.0, 9000.0, cfg())         # 1 share risks 2000 > RPT 1000
        self.assertEqual(p["quantity"], 0)
        self.assertEqual(checks(p)["QUANTITY"], m.FAIL)
        self.assertEqual(p["status"], risk.PLAN_FAIL)


class RewardRisk(unittest.TestCase):
    def test_boundary_two_passes_below_two_fails(self):
        self.assertEqual(checks(risk.plan_trade(100.0, 90.0, 120.0, cfg()))["RR_MIN_2"], m.PASS)
        p = risk.plan_trade(100.0, 90.0, 119.99, cfg())
        self.assertEqual(checks(p)["RR_MIN_2"], m.FAIL)
        self.assertEqual(p["status"], risk.PLAN_FAIL)

    def test_target_below_entry_fails_and_missing_target_is_manual(self):
        self.assertEqual(checks(risk.plan_trade(100.0, 90.0, 95.0, cfg()))["RR_MIN_2"], m.FAIL)
        p = risk.plan_trade(100.0, 90.0, None, cfg())
        self.assertEqual(checks(p)["RR_MIN_2"], m.MANUAL)
        self.assertEqual(p["status"], risk.PLAN_MANUAL)


class Capital(unittest.TestCase):
    def test_capital_insufficient_is_manual_and_never_resized(self):
        # RPT 1000 / risk 1 = 1000 shares x 500 = 5,00,000 > capital 1,00,000 (RB 68: size by risk)
        p = risk.plan_trade(500.0, 499.0, 510.0, cfg())
        self.assertEqual(p["quantity"], 1000)
        self.assertEqual(p["capital_required"], 500000.0)
        self.assertEqual(checks(p)["CAPITAL_SUFFICIENT"], m.MANUAL)
        self.assertIn("CAPITAL_INSUFFICIENT", [c["reason"] for c in p["checks"] if c["code"] == "CAPITAL_SUFFICIENT"][0])
        self.assertEqual(p["status"], risk.PLAN_MANUAL)
        self.assertFalse(p["approved"])

    def test_position_limit_not_configured_by_default(self):
        p = risk.plan_trade(983.0, 963.0, 1023.0, cfg())
        self.assertEqual(checks(p)["POSITION_VALUE_LIMIT"], risk.NOT_CONFIGURED)
        self.assertEqual(p["status"], risk.PLAN_WITHIN)              # NOT_CONFIGURED is not a restriction

    def test_position_limit_when_configured(self):
        # 50 x 983 = 49,150 = 49.15% of capital
        self.assertEqual(checks(risk.plan_trade(983.0, 963.0, 1023.0, cfg(max_position_value_pct=50.0)))
                         ["POSITION_VALUE_LIMIT"], m.PASS)
        p = risk.plan_trade(983.0, 963.0, 1023.0, cfg(max_position_value_pct=40.0))
        self.assertEqual(checks(p)["POSITION_VALUE_LIMIT"], m.MANUAL)
        self.assertEqual(p["quantity"], 50)                          # not reduced to fit


class Instrument(unittest.TestCase):
    def test_derivative_fails_cash_equity_passes(self):
        self.assertEqual(checks(risk.plan_trade(983.0, 963.0, 1023.0, cfg(), derivative=True))
                         ["INSTRUMENT_CASH_EQUITY"], m.FAIL)
        self.assertEqual(risk.plan_trade(983.0, 963.0, 1023.0, cfg(), derivative=True)["status"], risk.PLAN_FAIL)
        self.assertEqual(checks(risk.plan_trade(983.0, 963.0, 1023.0, cfg()))["INSTRUMENT_CASH_EQUITY"], m.PASS)


class Config(unittest.TestCase):
    def test_validation_errors(self):
        bad = [dict(capital=0), dict(capital=-1), dict(capital=float("nan")),
               dict(rpt_amount=1000.0),                                    # both given (rpt_pct in base)
               dict(rpt_pct=None), dict(rpt_pct=0.0), dict(rpt_pct=-1.0),
               dict(stage="EXPERT"), dict(trades_this_month=-1), dict(trades_this_month=1.5),
               dict(trades_this_month=True), dict(max_position_value_pct=0.0),
               dict(max_position_value_pct=150.0), dict(open_risk_amount=-1.0)]
        for kw in bad:
            with self.assertRaises(ValueError, msg=kw):
                cfg(**kw)

    def test_stage_bands(self):
        def stage(**kw):
            return risk.assess_config(cfg(**kw))["checks"][0]["outcome"]
        self.assertEqual(stage(rpt_pct=1.0), m.PASS)                            # top of Learning, inclusive
        self.assertEqual(stage(rpt_pct=0.5), m.PASS)
        self.assertEqual(stage(rpt_pct=1.01), m.FAIL)                           # above Learning max
        self.assertEqual(stage(rpt_pct=1.5, stage=risk.INTERMEDIATE), m.PASS)
        self.assertEqual(stage(rpt_pct=1.6, stage=risk.INTERMEDIATE), m.FAIL)
        self.assertEqual(stage(rpt_pct=2.0, stage=risk.PROFESSIONAL), m.PASS)
        self.assertEqual(stage(rpt_pct=2.01, stage=risk.PROFESSIONAL), m.FAIL)
        self.assertEqual(stage(rpt_pct=0.4), m.MANUAL)                          # below the band: not stated
        self.assertEqual(stage(rpt_pct=1.0, stage=None), m.MANUAL)              # stage not declared
        self.assertEqual(stage(rpt_pct=2.0, stage=None), m.MANUAL)
        self.assertEqual(stage(rpt_pct=2.5, stage=None), m.FAIL)                # above every stage
        self.assertEqual(stage(rpt_pct=None, rpt_amount=1500.0), m.FAIL)        # 1.5% for Learning

    def test_monthly_ceiling_boundary(self):
        def month(n):
            return risk.assess_config(cfg(trades_this_month=n))["checks"][1]["outcome"]
        self.assertEqual(month(9), m.PASS)
        self.assertEqual(month(10), m.FAIL)
        self.assertEqual(month(11), m.FAIL)
        self.assertEqual(month(None), m.MANUAL)
        p = risk.plan_trade(983.0, 963.0, 1023.0, cfg(trades_this_month=10))
        self.assertEqual(p["status"], risk.PLAN_FAIL)

    def test_max_monthly_risk_is_evidence_only(self):
        a = risk.assess_config(cfg(open_risk_amount=9500.0))                    # 9.5% open + 1% = 10.5%
        self.assertEqual(a["evidence"]["stage_max_monthly_risk_pct"], [5.0, 10.0])
        self.assertEqual(a["evidence"]["open_risk_pct_with_this_trade"], 10.5)
        self.assertEqual([c["code"] for c in a["checks"]], ["RPT_STAGE_BAND", "MONTHLY_TRADE_LIMIT"])
        self.assertEqual(a["outcome"], m.PASS)


class AveragingDown(unittest.TestCase):
    def test_below_average_fails_otherwise_manual(self):
        pos = {"quantity": 50, "average_price": 983.0}
        p = risk.plan_add_to_position(pos, 970.0)
        self.assertEqual((p["status"], p["checks"][0]["outcome"]), (risk.PLAN_FAIL, m.FAIL))
        self.assertIn("RB 69, 2140, 2229", p["checks"][0]["sources"])
        for price in (983.0, 1000.0):
            self.assertEqual(risk.plan_add_to_position(pos, price)["checks"][0]["outcome"], m.MANUAL)
        self.assertFalse(p["approved"])

    def test_bad_position(self):
        for pos, price in (({"quantity": 0, "average_price": 10.0}, 9.0), ({"quantity": 5, "average_price": 0}, 9.0),
                           ({"quantity": 5, "average_price": 10.0}, float("nan")), ({}, 9.0)):
            with self.assertRaises(ValueError):
                risk.plan_add_to_position(pos, price)


class CandidatePlan(unittest.TestCase):
    def test_actionable_candidate_gets_a_range_over_every_buffer(self):
        c = actionable_candidate()
        p = risk.risk_plan_for_candidate(c, cfg())
        lv = c["levels"]
        self.assertEqual(p["candidate_status"], m.ACTIONABLE)
        self.assertEqual(p["entry_range"], lv["entry"])
        self.assertEqual(p["sl_values"], sorted(set(v for pair in lv["sl"].values() for v in pair)))
        self.assertEqual(len(p["combinations"]), len(set(lv["entry"])) * len(p["sl_values"]))
        target = [g for g in c["gates"] if g["gate"] == "G7"][0]["evidence"]["target"]["proximal"]
        self.assertEqual(p["target"], target)
        dists = [e - s for e in lv["entry"] for s in p["sl_values"]]
        self.assertEqual(p["quantity_range"], [int(1000 // max(dists)), int(1000 // min(dists))])
        self.assertLessEqual(p["max_loss_if_stopped"], 1000.0)
        self.assertEqual(p["rr"], levels.rr_range(lv, target))              # one R:R implementation
        self.assertEqual(p["status"], risk.PLAN_WITHIN)
        self.assertEqual([x["code"] for x in p["manual_checks"]], ["BUFFER_SELECTION"])
        self.assertTrue(p["manual_checks_pending"])
        self.assertFalse(p["approved"])
        self.assertIn(m.NOT_EXTERNALLY_VALIDATED, p["limitations"])
        self.assertIn("BUFFER_SELECTION", p["candidate_manual_checks"])

    def test_risk_plan_never_changes_the_candidate(self):
        c = actionable_candidate()
        before = json.dumps(c, sort_keys=True)
        risk.risk_plan_for_candidate(c, cfg(trades_this_month=10))
        self.assertEqual(json.dumps(c, sort_keys=True), before)

    def test_non_actionable_statuses_get_no_sizing(self):
        for status in (m.REJECTED, m.BLOCKED_STATUS, m.STATUS_DATA_INSUFFICIENT, m.MANUAL_REVIEW):
            c = dict(actionable_candidate(), status=status, status_reasons=["G7: R:R < 2"])
            p = risk.risk_plan_for_candidate(c, cfg())
            self.assertEqual(p["status"], risk.NOT_APPLICABLE_STATUS)
            self.assertEqual(p["candidate_status"], status)
            self.assertEqual(p["status_reasons"], ["G7: R:R < 2"])
            for k in ("quantity_range", "combinations", "capital_required_range", "max_loss_if_stopped"):
                self.assertNotIn(k, p)

    def test_real_non_actionable_candidates_are_not_sized(self):
        # through the qualification pathway: a G0 data error, and a price that changes G3
        for kw in ({"data_errors": ["DUPLICATE_DATE 2025-01-02"]}, {"price": 1600.0}):
            c = reports.to_dict(R.only(R.evaluate(R.ideal_mit_builder(), **kw)))
            self.assertNotEqual(c["status"], m.ACTIONABLE)
            p = risk.risk_plan_for_candidate(c, cfg())
            self.assertEqual((p["status"], p["candidate_status"]), (risk.NOT_APPLICABLE_STATUS, c["status"]))
            self.assertNotIn("quantity_range", p)

    def test_invalid_candidate_levels(self):
        c = actionable_candidate()
        c["levels"] = dict(c["levels"], valid=False, problems=["ZONE_GEOMETRY_INVALID"])
        p = risk.risk_plan_for_candidate(c, cfg())
        self.assertEqual(p["status"], risk.INVALID_LEVELS)
        self.assertNotIn("quantity_range", p)

    def test_config_failure_propagates_to_the_plan(self):
        p = risk.risk_plan_for_candidate(actionable_candidate(), cfg(trades_this_month=10))
        self.assertEqual(p["status"], risk.PLAN_FAIL)
        p = risk.risk_plan_for_candidate(actionable_candidate(), cfg(stage=None))
        self.assertEqual(p["status"], risk.PLAN_MANUAL)

    def test_deterministic(self):
        c = actionable_candidate()
        a = risk.to_json(risk.risk_plan_for_candidate(c, cfg()))
        b = risk.to_json(risk.risk_plan_for_candidate(actionable_candidate(), cfg()))
        self.assertEqual(a, b)


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.scan = os.path.join(self.tmp, "scan.json")
        act = actionable_candidate()
        rej = dict(act, status=m.REJECTED, zone=dict(act["zone"], zone_id="z-rejected"))
        with open(self.scan, "w", encoding="utf-8") as fh:
            json.dump({"as_of": "2025-06-30T15:30:00", "trade_type": m.MIT,
                       "symbols": [{"symbol": "SYN", "candidates": [rej, act]}]}, fh)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_cli(self, argv):
        p = argparse.ArgumentParser()
        sub = p.add_subparsers(dest="cmd")
        risk.add_commands(sub)
        args = p.parse_args(argv)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = args.func(args)
        return code, buf.getvalue()

    def test_writes_deterministic_json(self):
        out = os.path.join(self.tmp, "a", "risk.json")
        argv = ["risk-plan", "--scan", self.scan, "--capital", "100000", "--rpt-pct", "1", "--stage", "LEARNING",
                "--trades-this-month", "3", "--out", out]
        code, _ = self.run_cli(argv)
        self.assertEqual(code, 0)
        with open(out, encoding="utf-8") as fh:
            first = fh.read()
        self.run_cli(argv)
        with open(out, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), first)
        d = json.loads(first)
        self.assertEqual(d["plan_status_counts"], {risk.NOT_APPLICABLE_STATUS: 1, risk.PLAN_WITHIN: 1})
        self.assertFalse(d["approved"])

    def test_exit_codes(self):
        base = ["risk-plan", "--scan", self.scan, "--capital", "100000"]
        self.assertEqual(self.run_cli(base + ["--rpt-pct", "1", "--trades-this-month", "10"])[0], 1)
        self.assertEqual(self.run_cli(base + ["--rpt-pct", "-1"])[0], 2)
        self.assertEqual(self.run_cli(["risk-plan", "--scan", os.path.join(self.tmp, "missing.json"),
                                       "--capital", "1", "--rpt-amount", "1"])[0], 2)
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.run_cli(base + ["--rpt-pct", "1", "--rpt-amount", "1000"])          # exactly one



class AuditRegressions(unittest.TestCase):
    """Rulebook audit 2026-11-02: a check failing for only some buffer / SL choices is the
    trader's choice (spec 6.3 DEPENDS -> MANUAL, B9), never a whole-plan FAIL."""

    def test_buffer_dependent_failure_is_manual(self):
        plans = [{"checks": [risk._check("QUANTITY", risk.PASS, "ok", ["RB 2162"])]},
                 {"checks": [risk._check("QUANTITY", risk.FAIL, "0 shares at the widest SL", ["RB 2162"])]}]
        [c] = risk._merge(plans)
        self.assertEqual(c["outcome"], risk.MANUAL)
        self.assertIn("DEPENDS_ON_BUFFER", c["reason"])

    def test_failure_for_every_choice_stays_fail(self):
        plans = [{"checks": [risk._check("QUANTITY", risk.FAIL, "x", [])]} for _ in range(3)]
        self.assertEqual(risk._merge(plans)[0]["outcome"], risk.FAIL)

    def test_stage_reading_is_labelled_for_the_owner(self):
        c = risk.assess_config(risk.RiskConfig(capital=100000, rpt_pct=1.5, stage="LEARNING"))
        stage = [x for x in c["checks"] if x["code"] == "RPT_STAGE_BAND"][0] if isinstance(c, dict) else \
            [x for x in c if x["code"] == "RPT_STAGE_BAND"][0]
        self.assertEqual(stage["outcome"], risk.FAIL)
        self.assertTrue(any("P-RISK-1" in s for s in stage["sources"]))


class ReviewRegressions(unittest.TestCase):
    def test_edited_actionable_status_is_never_sized(self):
        c = actionable_candidate()
        [g1] = [g for g in c["gates"] if g["gate"] == "G1"]
        g1["outcome"] = m.FAIL                           # status still says ACTIONABLE
        p = risk.risk_plan_for_candidate(c, cfg())
        self.assertEqual(p["status"], risk.NOT_APPLICABLE_STATUS)
        self.assertIn("STATUS_INCONSISTENT_WITH_GATES", p["reason"])
        self.assertNotIn("quantity_range", p)

    def test_scan_limitations_reach_every_plan(self):
        scan = {"as_of": "x", "trade_type": "MIT", "limitations": ["UNIVERSE_UNVERIFIED"],
                "symbols": [{"symbol": "SYN", "limitations": ["SESSION_TIMES_ASSUMED"],
                             "candidates": [actionable_candidate()]}]}
        out = risk.plans_for_scan(scan, cfg())
        self.assertIn("UNIVERSE_UNVERIFIED", out["limitations"])
        self.assertTrue({"UNIVERSE_UNVERIFIED", "SESSION_TIMES_ASSUMED"} <= set(out["plans"][0]["limitations"]))

if __name__ == "__main__":
    unittest.main()
